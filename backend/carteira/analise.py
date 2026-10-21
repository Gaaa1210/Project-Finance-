"""
Junta tudo para a tela de análise de uma empresa:
  balanços da CVM + preço atual + indicadores + semáforo + alertas + valuation.

Duas funções principais (usadas pelo api.py):
  montar_analise(ticker)                 -> a análise completa, com as premissas sugeridas
  recalcular_valuation(ticker, premissas) -> só o valuation, com premissas que você mudou
"""

import math
from datetime import datetime
from pathlib import Path

from carteira import indicadores as ind
from carteira import mercado, valuation
from carteira.cotacoes import ErroCotacao
from carteira.cvm import CAMINHO_BANCO
from carteira.demonstrativos import serie_anual

# Regra extra do semáforo de "Preço": potencial até o preço justo do cenário neutro.
ind.REGRAS["potencial_valuation"] = ("maior", 0.20, 0.0, "verde ≥ 20% abaixo do preço justo neutro · amarelo entre 0% e 20% · vermelho acima do preço justo")


def limpar(objeto):
    """Converte para tipos que viram JSON: NaN/infinito -> None, números do numpy -> float."""
    if isinstance(objeto, dict):
        return {chave: limpar(valor) for chave, valor in objeto.items()}
    if isinstance(objeto, (list, tuple)):
        return [limpar(valor) for valor in objeto]
    if hasattr(objeto, "item") and not isinstance(objeto, (str, bytes)):
        objeto = objeto.item()  # número do numpy -> número do Python
    if isinstance(objeto, float):
        return None if math.isnan(objeto) or math.isinf(objeto) else round(objeto, 6)
    return objeto


def _dados_de_mercado(ticker: str, offline: bool) -> dict:
    taxa = mercado.taxa_livre_risco(offline)
    beta = mercado.beta_da_acao(ticker, offline)
    return {
        "taxa_livre_risco": taxa["valor"],
        "beta": beta["valor"],
        "premio_risco": valuation.PREMIO_RISCO_PADRAO,
        "spread_divida": valuation.SPREAD_DIVIDA_PADRAO,
        "taxa_longo_prazo": taxa.get("longo_prazo", True),
        "fontes": {
            "taxa_livre_risco": taxa["fonte"],
            "beta": beta["fonte"],
            "premio_risco": "Premissa do app: 5% acima da taxa livre de risco para uma ação de beta 1",
            "spread_divida": "Premissa do app: empresas pagam ~2% acima da taxa livre de risco",
        },
    }


def _preco(ticker: str, buscar_cotacao) -> tuple:
    try:
        dados = buscar_cotacao(ticker)
        return dados.preco_atual, None
    except ErroCotacao as erro:
        return None, str(erro)


def _base_e_serie(ticker, offline, caminho_banco, buscar_cotacao):
    serie = serie_anual(ticker, caminho_banco)
    preco, aviso_preco = _preco(serie["ticker"], buscar_cotacao)
    acoes = serie["acoes"]["quantidade"] if serie.get("acoes") else None
    base = valuation.montar_base(serie["tabela"], serie["ultimos_12_meses"], preco, acoes)
    return serie, base, aviso_preco


def montar_analise(ticker: str, offline: bool = False, caminho_banco: Path = CAMINHO_BANCO,
                   buscar_cotacao=None) -> dict:
    """A análise completa de uma empresa (gera ErroDemonstrativos se não houver balanços)."""
    if buscar_cotacao is None:
        from carteira.servico import escolher_fontes
        buscar_cotacao, _ = escolher_fontes(offline)

    serie, base, aviso_preco = _base_e_serie(ticker, offline, caminho_banco, buscar_cotacao)
    tabela, ttm, financeira = serie["tabela"], serie["ultimos_12_meses"], serie["financeira"]

    lista = ind.calcular_indicadores(tabela, ttm, base["preco"], base["acoes"], financeira)

    dados_mercado = _dados_de_mercado(serie["ticker"], offline)
    if financeira:
        premissas = valuation.premissas_padrao_financeira(tabela, base, dados_mercado)
    else:
        premissas = valuation.premissas_padrao(tabela, base, dados_mercado)
    resultado_valuation = valuation.avaliar(premissas["cenarios"], base, financeira=financeira)

    # O semáforo de "Preço" também considera o valuation do cenário neutro.
    neutro = resultado_valuation["resultados"].get("neutro", {})
    potencial = neutro.get("potencial")
    lista.append(ind._indicador(
        "potencial_valuation", "Potencial até o preço justo (neutro)", potencial, "pct",
        "Quanto o preço atual está abaixo (positivo) ou acima (negativo) do preço justo do cenário neutro.", "preco"))

    avisos = []
    if aviso_preco:
        avisos.append(f"Sem cotação: {aviso_preco} Múltiplos e preço justo por ação ficam vazios.")
    if not base["acoes"]:
        avisos.append("A CVM não informou a quantidade de ações desta empresa. Rode 'python3 atualizar_cvm.py' de novo; "
                      "sem isso, o valuation mostra o valor da empresa, mas não o preço por ação.")
    if ttm and ttm.get("tipo") == "anual":
        avisos.append("Sem balanço trimestral mais novo que o anual: os indicadores usam o último ano fechado.")
    if not offline and not dados_mercado["taxa_longo_prazo"]:
        avisos.append("Não consegui a Selic de longo prazo (Boletim Focus); o valuation usa a Selic de hoje, que pode "
                      "deixar o WACC alto e os preços justos baixos. Ajuste o WACC na aba Valuation se quiser.")
    if financeira:
        avisos.append("Banco/seguradora: valuation pelo modelo de P/VP justo (o fluxo de caixa descontado não se aplica).")

    return limpar({
        "empresa": {"ticker": serie["ticker"], "nome": serie["empresa"], "cnpj": serie["cnpj"], "financeira": financeira},
        "preco": {"valor": base["preco"], "acoes": base["acoes"], "valor_mercado": base["valor_mercado"],
                  "acoes_referencia": serie["acoes"]["referencia"] if serie.get("acoes") else None},
        "referencia": {
            "ultimo_ano": int(tabela.index[-1]) if len(tabela) else None,
            "ultimos_12_meses": ttm.get("referencia") if ttm else None,
            "tipo": ttm.get("tipo") if ttm else None,
        },
        "raio_x": ind.raio_x(lista, financeira),
        "indicadores": lista,
        "alertas": ind.sinais_de_alerta(tabela, lista, financeira),
        "historico": ind.historico(tabela),
        "valuation": {
            "base": base,
            "mercado": dados_mercado,
            "premissas": premissas,
            **resultado_valuation,
        },
        "avisos": avisos,
        "fonte": "Balanços: CVM (DFP/ITR). Cotação: Yahoo Finance (~15 min de atraso).",
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    })


CAMPOS_EMPRESA = ("crescimento", "margem_ebit", "capex_receita", "depreciacao_receita",
                  "capital_giro_receita", "aliquota_ir", "wacc", "crescimento_perpetuo")
CAMPOS_FINANCEIRA = ("roe", "custo_acionista", "crescimento_perpetuo")


def recalcular_valuation(ticker: str, cenarios: dict, pesos: dict = None, offline: bool = False,
                         caminho_banco: Path = CAMINHO_BANCO, buscar_cotacao=None) -> dict:
    """Recalcula o valuation com as premissas editadas na tela. Gera ValueError se faltar algo."""
    if buscar_cotacao is None:
        from carteira.servico import escolher_fontes
        buscar_cotacao, _ = escolher_fontes(offline)

    serie, base, _ = _base_e_serie(ticker, offline, caminho_banco, buscar_cotacao)
    financeira = serie["financeira"]
    campos = CAMPOS_FINANCEIRA if financeira else CAMPOS_EMPRESA

    limpos = {}
    for nome in valuation.CENARIOS:
        if nome not in cenarios:
            raise ValueError(f"Faltou o cenário '{nome}'.")
        try:
            limpos[nome] = {campo: float(cenarios[nome][campo]) for campo in campos}
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Premissas do cenário '{nome}' incompletas ou inválidas.")

    if pesos:
        pesos = {nome: max(float(pesos.get(nome, 0)), 0.0) for nome in valuation.CENARIOS}
    return limpar({"base": base, **valuation.avaliar(limpos, base, pesos, financeira)})
