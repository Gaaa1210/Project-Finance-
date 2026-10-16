"""
Cotações FICTÍCIAS para testar o app sem internet (modo --offline).

Estes números NÃO são preços reais. Servem só para você ver os cálculos
funcionando. Com internet, o app usa o Yahoo Finance de verdade.
"""

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
