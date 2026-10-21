"""
Camada de "serviço": prepara os dados que o app (React) vai mostrar.

O servidor (api.py) só recebe os pedidos do app e chama as funções daqui.
Aqui juntamos planilha + cotações + cálculos e devolvemos tudo em dicionários
simples (que viram JSON, o "idioma" que o navegador entende).

Por que separar do api.py? Porque assim dá para testar estas funções sem
precisar ligar o servidor.
"""

import math
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from carteira import calculos_acoes as calc
from carteira.acoes import resumir_acoes, totalizar_acoes
from carteira.cotacoes import ErroCotacao, buscar_dados_ticker, buscar_historico
from carteira.empresas import EMPRESAS, encontrar_empresa
from carteira.noticias import buscar_noticias
from carteira.planilha import (
    CAMINHO_PADRAO,
    ErroPlanilha,
    adicionar_compra_acao,
    ler_compras_acoes,
)

# Guardamos as cotações por 5 minutos. Assim, abrir e fechar telas no app
# não faz o servidor perguntar ao Yahoo toda hora (fica mais rápido também).
CACHE_SEGUNDOS = 5 * 60

ORDEM_TIPOS = ["Ação", "ETF", "FII"]


class _Cache:
    """
    Guarda o resultado de uma função por alguns segundos.
    Se pedirem a mesma coisa de novo dentro do prazo, devolve o resultado guardado.
    Erros NÃO são guardados: na próxima vez tentamos de novo.
    """

    def __init__(self, funcao, segundos: int):
        self.funcao = funcao
        self.segundos = segundos
        self._guardado = {}

    def __call__(self, *argumentos):
        agora = time.monotonic()
        if argumentos in self._guardado:
            momento, valor = self._guardado[argumentos]
            if agora - momento < self.segundos:
                return valor
        valor = self.funcao(*argumentos)
        self._guardado[argumentos] = (agora, valor)
        return valor


_cotacao_real = _Cache(buscar_dados_ticker, CACHE_SEGUNDOS)
_historico_real = _Cache(buscar_historico, CACHE_SEGUNDOS)


def escolher_fontes(offline: bool):
    """Devolve (função de cotação, função de histórico): reais ou fictícias."""
    if offline:
        from carteira.dados_exemplo import buscar_dados_ficticios, buscar_historico_ficticio
        return buscar_dados_ficticios, buscar_historico_ficticio
    return _cotacao_real, _historico_real


# ---------------------------------------------------------------------------
# Conversão para JSON
# ---------------------------------------------------------------------------

def para_json(valor):
    """
    Converte valores do pandas/numpy em valores simples que viram JSON:
      - datas  -> texto "2025-03-10"
      - NaN (número vazio) -> None (vira null no JSON)
      - números do numpy -> números normais do Python
    """
    if valor is None or valor is pd.NaT:
        return None
    if isinstance(valor, (pd.Timestamp, datetime, date)):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, (float, np.floating)):
        return None if math.isnan(valor) else round(float(valor), 6)
    if isinstance(valor, np.integer):
        return int(valor)
    return valor


def _linha_para_json(linha: dict) -> dict:
    return {chave: para_json(valor) for chave, valor in linha.items()}


# ---------------------------------------------------------------------------
# Carteira inteira (telas Início, Ativos e Desempenho)
# ---------------------------------------------------------------------------

def montar_carteira(caminho: Path = CAMINHO_PADRAO, offline: bool = False) -> dict:
    """Tudo que as telas Início, Ativos e Desempenho precisam, em um pedido só."""
    buscar_cotacao, _ = escolher_fontes(offline)

    try:
        compras = ler_compras_acoes(caminho)
    except ErroPlanilha as erro:
        # Planilha sem compras não é erro para o app: mostramos a carteira vazia
        # e a pessoa pode adicionar a primeira compra pela tela "Adicionar".
        if "está vazia" in str(erro):
            return _carteira_vazia(offline)
        raise

    resumo, avisos = resumir_acoes(compras, buscar_cotacao=buscar_cotacao)
    totais = totalizar_acoes(resumo)
    ativos = [_linha_para_json(linha) for linha in resumo.to_dict("records")]

    return {
        "modo_offline": offline,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "totais": _linha_para_json(totais),
        "ativos": ativos,
        "alocacao": {
            "tipo": calcular_alocacao(ativos, "tipo"),
            "setor": calcular_alocacao(ativos, "setor"),
            "ativo": calcular_alocacao(ativos, "ticker"),
        },
        "avisos": avisos,
    }


def _carteira_vazia(offline: bool) -> dict:
    return {
        "modo_offline": offline,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "totais": _linha_para_json(totalizar_acoes(pd.DataFrame())),
        "ativos": [],
        "alocacao": {"tipo": [], "setor": [], "ativo": []},
        "avisos": [],
    }


def calcular_alocacao(ativos: list[dict], campo: str) -> list[dict]:
    """
    Quanto da carteira está em cada grupo (por tipo, setor ou ativo).

    Usa o valor atual de cada ativo. Se um ativo ficou sem cotação, usamos
    o total investido nele, para ele não sumir do gráfico.
    """
    grupos: dict[str, float] = {}
    for ativo in ativos:
        valor = ativo.get("valor_atual")
        if valor is None:
            valor = ativo["total_investido"]
        nome = ativo.get(campo) or "Não informado"
        grupos[nome] = grupos.get(nome, 0.0) + valor

    total = sum(grupos.values())
    alocacao = [
        {"nome": nome, "valor": round(valor, 2), "pct": valor / total if total else 0.0}
        for nome, valor in grupos.items()
    ]
    # Do maior para o menor (fica mais fácil de ler no gráfico).
    return sorted(alocacao, key=lambda item: item["valor"], reverse=True)


# ---------------------------------------------------------------------------
# Um ativo (tela de Detalhe)
# ---------------------------------------------------------------------------

def detalhar_ativo(ticker: str, caminho: Path = CAMINHO_PADRAO, offline: bool = False) -> dict:
    """
    Dados da tela de detalhe: resumo, histórico de preços, compras e proventos.
    Gera KeyError se o ativo não estiver na planilha.
    """
    buscar_cotacao, buscar_hist = escolher_fontes(offline)
    ticker = ticker.strip().upper()

    compras = ler_compras_acoes(caminho)
    compras_do_ativo = compras[compras["ticker"] == ticker]
    if compras_do_ativo.empty:
        raise KeyError(ticker)

    resumo, avisos = resumir_acoes(compras_do_ativo, buscar_cotacao=buscar_cotacao)
    linha = _linha_para_json(resumo.to_dict("records")[0])

    # Histórico desde 30 dias antes da primeira compra, para o gráfico.
    inicio = compras_do_ativo["data_compra"].min() - pd.Timedelta(days=30)
    try:
        historico = buscar_hist(ticker, inicio)
        pontos = [{"data": para_json(d), "preco": para_json(p)} for d, p in historico.items()]
    except ErroCotacao as erro:
        pontos = []
        avisos.append(str(erro))

    # Proventos: só os que você recebeu (tinha cotas antes da data ex).
    proventos = []
    try:
        dados = buscar_cotacao(ticker)
        for data_ex, valor_por_cota in dados.dividendos.items():
            quantidade = calc.calcular_quantidade_na_data(compras_do_ativo, data_ex)
            if quantidade > 0:
                proventos.append({
                    "data_ex": para_json(data_ex),
                    "valor_por_cota": para_json(valor_por_cota),
                    "quantidade": quantidade,
                    "total": round(quantidade * float(valor_por_cota), 2),
                })
    except ErroCotacao:
        pass  # o aviso já veio do resumir_acoes
    proventos.sort(key=lambda p: p["data_ex"], reverse=True)

    lista_compras = [
        {
            "data": para_json(c["data_compra"]),
            "quantidade": c["quantidade"],
            "preco_pago": c["preco_pago"],
            "taxas": c["taxas"],
            "custo": round(calc.calcular_custo_compra(c["quantidade"], c["preco_pago"], c["taxas"]), 2),
        }
        for c in compras_do_ativo.sort_values("data_compra", ascending=False).to_dict("records")
    ]

    return {
        "modo_offline": offline,
        "ativo": linha,
        "historico": pontos,
        "compras": lista_compras,
        "proventos": proventos,
        "avisos": list(dict.fromkeys(avisos)),
    }


# ---------------------------------------------------------------------------
# Nova compra (tela Adicionar)
# ---------------------------------------------------------------------------

def registrar_compra(dados: dict, caminho: Path = CAMINHO_PADRAO) -> dict:
    """Grava a compra na planilha e devolve a compra limpa, pronta para JSON."""
    compra = adicionar_compra_acao(dados, caminho)
    return _linha_para_json(compra)


# ---------------------------------------------------------------------------
# Notícias (aba Notícias)
# ---------------------------------------------------------------------------

# Notícias guardadas por 15 minutos (evita pedir ao Google a cada toque).
_noticias_cache = _Cache(lambda ticker, limite: buscar_noticias(encontrar_empresa(ticker), limite), 15 * 60)


def listar_empresas(caminho: Path = CAMINHO_PADRAO) -> dict:
    """
    Empresas da aba Notícias: as da sua carteira primeiro, depois a lista da B3.
    Se a planilha não puder ser lida, mostramos só a lista da B3.
    """
    try:
        compras = ler_compras_acoes(caminho)
        tickers_carteira = list(dict.fromkeys(compras["ticker"]))
        setores = dict(zip(compras["ticker"], compras["setor"]))
    except ErroPlanilha:
        tickers_carteira, setores = [], {}

    carteira = []
    for ticker in tickers_carteira:
        try:
            empresa = dict(encontrar_empresa(ticker))
        except ValueError:
            continue  # ticker com formato estranho: fica de fora das notícias
        if empresa["setor"] == "Não informado":
            empresa["setor"] = setores.get(ticker, "Não informado")
        carteira.append(_empresa_para_json(empresa))

    na_carteira = {e["ticker"] for e in carteira}
    outras = [_empresa_para_json(e) for e in EMPRESAS if e["ticker"] not in na_carteira]
    outras.sort(key=lambda e: e["nome"].lower())
    return {"carteira": carteira, "outras": outras}


def _empresa_para_json(empresa: dict) -> dict:
    return {k: empresa[k] for k in ("ticker", "nome", "setor")}


def noticias_da_empresa(ticker: str, limite: int = 20) -> dict:
    """As notícias mais em alta. Gera ValueError (ticker inválido) ou ErroNoticias."""
    ticker = ticker.strip().upper()
    encontrar_empresa(ticker)  # confere o formato antes de usar o cache
    return _noticias_cache(ticker, limite)


# ---------------------------------------------------------------------------
# Balanços da CVM (relatório de saúde da empresa)
# ---------------------------------------------------------------------------

def fundamentos_da_empresa(ticker: str) -> dict:
    """Série anual dos balanços (CVM). Gera ErroDemonstrativos se não achar."""
    from carteira.demonstrativos import serie_anual

    serie = serie_anual(ticker)
    tabela = serie["tabela"]
    return {
        "ticker": serie["ticker"],
        "cnpj": serie["cnpj"],
        "empresa": serie["empresa"],
        "financeira": serie["financeira"],
        "fonte": "CVM — Demonstrações Financeiras Padronizadas (DFP)",
        "anos": [int(ano) for ano in tabela.index],
        # Uma lista por número, na mesma ordem dos anos. Ex.: "receita_liquida": [..., ...]
        "series": {coluna: [para_json(v) for v in tabela[coluna]] for coluna in tabela.columns},
    }
