"""
Busca de cotações e proventos no Yahoo Finance (biblioteca yfinance).

- É grátis e não precisa de cadastro.
- Os preços da B3 chegam com cerca de 15 minutos de atraso.
- Ativos brasileiros precisam do sufixo ".SA" no Yahoo (PETR4 -> PETR4.SA).
  Você escreve só "PETR4" na planilha; o código adiciona o ".SA" sozinho.
"""

import logging
from dataclasses import dataclass, field

import pandas as pd

# O yfinance escreve avisos técnicos em inglês no terminal quando algo falha.
# Silenciamos esses avisos porque mostramos nossas próprias mensagens amigáveis.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class ErroCotacao(Exception):
    """Não foi possível obter a cotação de um ativo (mensagem amigável)."""


@dataclass
class DadosCotacao:
    """
    Os dados de mercado de UM ativo.
    Uma "dataclass" é um jeito simples de criar um objeto que só guarda dados.
    """
    ticker: str
    preco_atual: float
    fechamento_anterior: float
    # field(default_factory=...) cria uma série vazia nova para cada objeto.
    dividendos: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))


def normalizar_ticker(ticker: str) -> str:
    """
    Converte o ticker da planilha para o formato do Yahoo.
      "petr4"   -> "PETR4.SA"
      "IVVB11"  -> "IVVB11.SA"
      "AAPL.US" -> fica como está (já tem ponto)
      "^BVSP"   -> fica como está (índices começam com ^)
    """
    ticker = ticker.strip().upper()
    if "." in ticker or ticker.startswith("^"):
        return ticker
    return f"{ticker}.SA"


def buscar_dados_ticker(ticker: str) -> DadosCotacao:
    """
    Busca preço atual, fechamento anterior e proventos de um ativo.
    Gera ErroCotacao se o ativo não existir ou se não houver internet.
    """
    # Importamos aqui dentro para dar uma mensagem clara se a biblioteca faltar.
    try:
        import yfinance as yf
    except ImportError:
        raise ErroCotacao(
            "A biblioteca yfinance não está instalada. "
            "Rode: pip install -r requirements.txt"
        )

    codigo_yahoo = normalizar_ticker(ticker)

    try:
        ativo = yf.Ticker(codigo_yahoo)
        # Últimos 5 dias, para garantir pelo menos 2 pregões (fins de semana e feriados).
        # auto_adjust=False: queremos o preço real negociado, não um preço "ajustado".
        historico = ativo.history(period="5d", auto_adjust=False)
        dividendos = ativo.dividends
    except Exception as erro:
        # Qualquer falha de rede cai aqui (sem internet, Yahoo fora do ar etc.).
        raise ErroCotacao(
            f"{ticker}: não consegui acessar o Yahoo Finance. "
            f"Verifique sua internet. (detalhe técnico: {type(erro).__name__})"
        )

    if historico is None or historico.empty:
        raise ErroCotacao(
            f"{ticker}: não encontrei esse ativo no Yahoo Finance. "
            "Confira se o ticker está certo (ex.: PETR4, IVVB11, HGLG11)."
        )

    fechamentos = historico["Close"].dropna()
    preco_atual = float(fechamentos.iloc[-1])
    # Se só existir um dia de dados, usamos o próprio preço (variação do dia = 0).
    fechamento_anterior = float(fechamentos.iloc[-2]) if len(fechamentos) > 1 else preco_atual

    return DadosCotacao(
        ticker=ticker,
        preco_atual=preco_atual,
        fechamento_anterior=fechamento_anterior,
        dividendos=_limpar_datas(dividendos),
    )


def _limpar_datas(serie: pd.Series) -> pd.Series:
    """
    O Yahoo devolve datas com fuso horário (ex.: 2024-03-05 00:00-03:00).
    As datas da planilha não têm fuso. Para comparar as duas, removemos o fuso
    e o horário, ficando só com o dia.
    """
    if serie is None or len(serie) == 0:
        return pd.Series(dtype=float)
    serie = serie.copy()
    if getattr(serie.index, "tz", None) is not None:
        serie.index = serie.index.tz_localize(None)
    serie.index = pd.to_datetime(serie.index).normalize()
    return serie.astype(float)
