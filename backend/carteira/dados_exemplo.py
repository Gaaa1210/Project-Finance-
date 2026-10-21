"""
Cotações FICTÍCIAS para testar o app sem internet (modo --offline).

Estes números NÃO são preços reais. Servem só para você ver os cálculos
funcionando. Com internet, o app usa o Yahoo Finance de verdade.
"""

import random

import pandas as pd

from carteira.cotacoes import DadosCotacao, ErroCotacao

_PRECOS_FICTICIOS = {
    # ticker: (preço atual, fechamento anterior, {data ex: provento por ação})
    "PETR4":  (37.80, 37.40, {"2025-08-21": 0.45, "2025-11-24": 0.47}),
    "ITUB4":  (36.20, 36.50, {"2025-07-01": 0.02, "2025-08-01": 0.02, "2025-12-01": 0.30}),
    "IVVB11": (380.00, 377.00, {}),
    "HGLG11": (160.00, 160.50, {"2025-02-28": 1.10, "2025-05-30": 1.10, "2025-12-30": 1.10}),
}


def buscar_dados_ficticios(ticker: str) -> DadosCotacao:
    """Mesma "forma" da função do Yahoo, mas com os preços fictícios acima."""
    if ticker not in _PRECOS_FICTICIOS:
        raise ErroCotacao(f"{ticker}: sem preço fictício no modo offline.")
    atual, anterior, proventos = _PRECOS_FICTICIOS[ticker]
    dividendos = pd.Series(proventos, dtype=float)
    dividendos.index = pd.to_datetime(dividendos.index)
    return DadosCotacao(ticker, atual, anterior, dividendos)


def buscar_historico_ficticio(ticker: str, inicio) -> pd.Series:
    """
    Histórico de preços FICTÍCIO para o gráfico no modo offline.

    É uma "caminhada aleatória": cada dia o preço sobe ou desce um pouquinho
    ao acaso, terminando no preço atual fictício. Sempre gera a mesma curva
    para o mesmo ticker (a "semente" do sorteio é o próprio ticker).
    """
    if ticker not in _PRECOS_FICTICIOS:
        raise ErroCotacao(f"{ticker}: sem preço fictício no modo offline.")

    preco_atual = _PRECOS_FICTICIOS[ticker][0]
    hoje = pd.Timestamp.today().normalize()
    dias = pd.bdate_range(start=pd.Timestamp(inicio), end=hoje)  # só dias úteis
    if len(dias) == 0:
        dias = pd.DatetimeIndex([hoje])

    sorteio = random.Random(ticker)
    precos = []
    preco = preco_atual
    # Andamos de trás para frente: começamos no preço de hoje e voltamos no tempo.
    for _ in dias:
        precos.append(preco)
        preco = preco / (1 + sorteio.gauss(0, 0.012))
    precos.reverse()

    return pd.Series(precos, index=dias).round(2)
