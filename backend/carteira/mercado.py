"""
Dados de mercado usados no valuation:
  - taxa livre de risco: a Selic que o mercado espera no longo prazo
    (Boletim Focus do Banco Central). Se não der, a Selic atual. Se não der, um padrão.
  - beta: o quanto a ação costuma oscilar em relação ao Ibovespa
    (beta 1,2 = quando o Ibovespa sobe 10%, a ação tende a subir 12%).

Tudo vem com a FONTE junto, para o app mostrar de onde saiu cada número.
Todos são só sugestões: na tela de valuation dá para trocar qualquer um.
"""

import time
from datetime import date

# Usados quando não for possível buscar na internet.
TAXA_LIVRE_RISCO_PADRAO = 0.12   # 12% ao ano
BETA_PADRAO = 1.0

URL_FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
URL_SGS_SELIC = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1"

_cache = {}
DURACAO_CACHE = 12 * 3600  # 12 horas


def _guardado(chave, funcao):
    agora = time.monotonic()
    if chave in _cache and agora - _cache[chave][0] < DURACAO_CACHE:
        return _cache[chave][1]
    valor = funcao()
    _cache[chave] = (agora, valor)
    return valor


def _numero(texto) -> float:
    return float(str(texto).replace(",", "."))


# ---------------------------------------------------------------------------
# Taxa livre de risco
# ---------------------------------------------------------------------------

def taxa_livre_risco(offline: bool = False) -> dict:
    """
    {"valor": 0.115, "fonte": "Boletim Focus: Selic esperada para 2029 (mediana)"}
    """
    if offline:
        return {"valor": TAXA_LIVRE_RISCO_PADRAO, "fonte": "Padrão do app (modo offline)"}
    return _guardado("taxa_livre_risco", _buscar_taxa_livre_risco)


def _buscar_taxa_livre_risco() -> dict:
    try:
        import requests
    except ImportError:
        return {"valor": TAXA_LIVRE_RISCO_PADRAO, "fonte": "Padrão do app (12% ao ano)"}

    # 1ª opção: Selic esperada para daqui a 3 anos (Focus). É a melhor estimativa de
    # juros "normais" de longo prazo, sem o efeito de um momento de Selic alta ou baixa.
    motivo_focus = ""
    try:
        resposta = requests.get(url_focus(), timeout=20, headers={"Accept": "application/json"})
        resposta.raise_for_status()
        escolhido = escolher_selic_longo_prazo(resposta.json().get("value", []), date.today().year)
        if escolhido:
            return escolhido
        motivo_focus = "sem projeção de Selic para os próximos anos na resposta"
    except Exception as erro:
        motivo_focus = f"{type(erro).__name__}: {str(erro)[:80]}"

    # 2ª opção: Selic meta atual (Banco Central, série 432).
    try:
        dados = requests.get(URL_SGS_SELIC, params={"formato": "json"}, timeout=15).json()
        return {
            "valor": _numero(dados[-1]["valor"]) / 100,
            "fonte": (f"Banco Central: Selic meta atual ({dados[-1]['data']}). ATENÇÃO: são juros de hoje, não de "
                      f"longo prazo; o Focus falhou ({motivo_focus}). Se a Selic estiver alta, o WACC fica alto."),
            "longo_prazo": False,
        }
    except Exception:
        pass

    return {"valor": TAXA_LIVRE_RISCO_PADRAO, "fonte": f"Padrão do app (não consegui acessar o Banco Central: {motivo_focus})",
            "longo_prazo": False}


def url_focus() -> str:
    """
    Endereço da consulta ao Boletim Focus (expectativas anuais da Selic).
    Montamos à mão porque o serviço do Banco Central (padrão "OData") precisa dos
    espaços como %20 e do '$' sem codificar; a biblioteca requests trocaria por '+' e '%24'.
    """
    from urllib.parse import quote

    filtro = quote("Indicador eq 'Selic'", safe="'")
    ordem = quote("Data desc")
    return f"{URL_FOCUS}?$top=200&$filter={filtro}&$orderby={ordem}&$format=json"


def escolher_selic_longo_prazo(registros: list, ano_atual: int):
    """
    Dos registros do Focus, pega a mediana mais recente da Selic esperada para
    daqui a 3 anos (ou 4, ou 2, nessa ordem de preferência).
    """
    for distancia in (3, 4, 2):
        ano_alvo = ano_atual + distancia
        candidatos = [r for r in registros
                      if str(r.get("DataReferencia")) == str(ano_alvo) and r.get("Mediana") not in (None, "")]
        if candidatos:
            mais_recente = max(candidatos, key=lambda r: str(r.get("Data", "")))
            return {
                "valor": _numero(mais_recente["Mediana"]) / 100,
                "fonte": f"Boletim Focus ({mais_recente.get('Data', '')}): Selic esperada para {ano_alvo} (mediana)",
                "longo_prazo": True,
            }
    return None


# ---------------------------------------------------------------------------
# Beta
# ---------------------------------------------------------------------------

def calcular_beta(retornos_acao, retornos_indice) -> float:
    """
    Beta = covariância(ação, índice) / variância(índice).
    Depois "puxamos" o beta um pouco para 1 (ajuste de Blume: 2/3 do beta medido
    + 1/3 de 1), porque betas extremos tendem a voltar para perto de 1 com o tempo.
    """
    import pandas as pd

    juntos = pd.concat([retornos_acao, retornos_indice], axis=1, join="inner").dropna()
    if len(juntos) < 30:
        raise ValueError("histórico curto demais para calcular o beta")
    acao, indice = juntos.iloc[:, 0], juntos.iloc[:, 1]
    beta = acao.cov(indice) / indice.var()
    ajustado = 2 / 3 * beta + 1 / 3
    return float(min(max(ajustado, 0.3), 2.5))


def beta_da_acao(ticker: str, offline: bool = False) -> dict:
    """{"valor": 1.12, "fonte": "Calculado: retornos semanais de 2 anos contra o Ibovespa"}"""
    if offline:
        return {"valor": BETA_PADRAO, "fonte": "Padrão do app (modo offline)"}
    return _guardado(("beta", ticker), lambda: _buscar_beta(ticker))


def _buscar_beta(ticker: str) -> dict:
    try:
        import yfinance as yf

        from carteira.cotacoes import normalizar_ticker

        def retornos(codigo):
            historico = yf.Ticker(codigo).history(period="2y", interval="1wk", auto_adjust=True)
            fechamento = historico["Close"].dropna()
            fechamento.index = fechamento.index.tz_localize(None).normalize()
            return fechamento.pct_change().dropna()

        valor = calcular_beta(retornos(normalizar_ticker(ticker)), retornos("^BVSP"))
        return {"valor": round(valor, 2), "fonte": "Calculado: retornos semanais de 2 anos contra o Ibovespa (ajustado)"}
    except Exception:
        return {"valor": BETA_PADRAO, "fonte": "Padrão do app (não consegui calcular o beta)"}
