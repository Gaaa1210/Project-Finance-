"""
SERVIDOR do app (FastAPI).

Ele fica rodando no seu Mac e responde aos pedidos das telas em React:
    GET  /api/carteira         -> resumo da carteira (Início, Ativos, Desempenho)
    GET  /api/ativos/PETR4     -> detalhe de um ativo (gráfico, compras, proventos)
    POST /api/compras          -> grava uma compra nova na planilha
    GET  /api/empresas         -> empresas da aba Notícias
    GET  /api/noticias/PETR4   -> as 20 notícias mais em alta da empresa
    GET  /api/fundamentos/PETR4 -> balanços anuais da CVM (receita, lucro, dívida...)
    GET  /api/analise/PETR4    -> indicadores, semáforo, alertas e valuation com 3 cenários
    POST /api/valuation/PETR4  -> recalcula o valuation com as premissas que você mudou

Como rodar (dentro da pasta backend, com o .venv ativado):
    python3 api.py              -> preços reais do Yahoo Finance
    python3 api.py --offline    -> preços FICTÍCIOS, para testar sem internet

Depois de ligado, abra http://localhost:8000/docs para ver e testar a API
direto no navegador (o FastAPI cria essa página sozinho).
"""

import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from carteira import analise, servico
from carteira.demonstrativos import ErroDemonstrativos
from carteira.noticias import ErroNoticias
from carteira.planilha import ErroPlanilha

# O modo offline é passado por uma "variável de ambiente" (ver o fim do arquivo).
MODO_OFFLINE = os.environ.get("CARTEIRA_OFFLINE") == "1"

app = FastAPI(title="Project Finance", description="API do painel da carteira")

# CORS: permite que as telas (que rodam em outro endereço, localhost:5173)
# conversem com este servidor (localhost:8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PremissasValuation(BaseModel):
    """Premissas editadas na tela de valuation (um dicionário por cenário)."""
    cenarios: dict
    pesos: Optional[dict] = None


class NovaCompra(BaseModel):
    """
    O formato de uma compra enviada pelo formulário do app.
    O FastAPI confere sozinho se os campos vieram com o tipo certo.
    """
    ticker: str
    quantidade: float
    preco_pago: float
    data_compra: str  # "2025-03-10"
    tipo: str = "Ação"
    setor: Optional[str] = None
    taxas: Optional[float] = 0.0


@app.get("/api/saude")
def saude():
    """Só para conferir se o servidor está ligado."""
    return {"ok": True, "modo_offline": MODO_OFFLINE}


@app.get("/api/carteira")
def carteira():
    try:
        return servico.montar_carteira(offline=MODO_OFFLINE)
    except ErroPlanilha as erro:
        # 400 = "o problema está nos dados" (aqui, na planilha)
        raise HTTPException(status_code=400, detail=str(erro))


@app.get("/api/ativos/{ticker}")
def ativo(ticker: str):
    try:
        return servico.detalhar_ativo(ticker, offline=MODO_OFFLINE)
    except KeyError:
        # 404 = "não encontrado"
        raise HTTPException(status_code=404, detail=f"{ticker} não está na sua planilha.")
    except ErroPlanilha as erro:
        raise HTTPException(status_code=400, detail=str(erro))


@app.post("/api/compras", status_code=201)
def nova_compra(compra: NovaCompra):
    try:
        return servico.registrar_compra(compra.model_dump())
    except ErroPlanilha as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    except PermissionError:
        raise HTTPException(
            status_code=409,
            detail="Não consegui salvar a planilha. Feche o carteira.xlsx no Excel e tente de novo.",
        )


@app.get("/api/empresas")
def empresas():
    return servico.listar_empresas()


@app.get("/api/noticias/{ticker}")
def noticias(ticker: str, limite: int = 20):
    # As notícias são sempre reais (mesmo no modo offline): não inventamos manchetes.
    try:
        return servico.noticias_da_empresa(ticker, limite=min(max(limite, 1), 50))
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    except ErroNoticias as erro:
        # 503 = "serviço indisponível no momento"
        raise HTTPException(status_code=503, detail=str(erro))


@app.get("/api/fundamentos/{ticker}")
def fundamentos(ticker: str):
    # Precisa do banco da CVM: rode antes "python3 atualizar_cvm.py".
    try:
        return servico.fundamentos_da_empresa(ticker)
    except ErroDemonstrativos as erro:
        raise HTTPException(status_code=404, detail=str(erro))


@app.get("/api/analise/{ticker}")
def analise_empresa(ticker: str):
    try:
        return analise.montar_analise(ticker, offline=MODO_OFFLINE)
    except ErroDemonstrativos as erro:
        raise HTTPException(status_code=404, detail=str(erro))


@app.post("/api/valuation/{ticker}")
def recalcular_valuation(ticker: str, premissas: PremissasValuation):
    try:
        return analise.recalcular_valuation(ticker, premissas.cenarios, premissas.pesos, offline=MODO_OFFLINE)
    except ErroDemonstrativos as erro:
        raise HTTPException(status_code=404, detail=str(erro))
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))


if __name__ == "__main__":
    import uvicorn

    if "--offline" in sys.argv:
        os.environ["CARTEIRA_OFFLINE"] = "1"
        print("⚠️  MODO OFFLINE: preços e proventos FICTÍCIOS, só para teste.")

    # host="0.0.0.0" deixa o iPhone (no mesmo Wi-Fi) acessar o servidor.
    # reload=True reinicia o servidor sozinho quando você salva um arquivo .py.
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
