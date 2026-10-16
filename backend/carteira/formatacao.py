"""
Funções para mostrar números do jeito brasileiro: R$ 1.234,56 e 12,34%.
"""

import math


def numero_valido(valor) -> bool:
    """Retorna True se 'valor' é um número de verdade (não vazio e não NaN)."""
    if valor is None:
        return False
    try:
        return not math.isnan(float(valor))
    except (TypeError, ValueError):
        return False


def formatar_reais(valor) -> str:
    """
    Transforma 1234.5 em 'R$ 1.234,50'.
    Se o valor não existir (por exemplo, cotação indisponível), mostra '—'.
    """
    if not numero_valido(valor):
        return "—"
    # Primeiro formatamos no padrão americano: 1,234.50
    texto = f"{abs(valor):,.2f}"
    # Depois trocamos: vírgula -> X, ponto -> vírgula, X -> ponto  =>  1.234,50
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {texto}"


def formatar_percentual(valor, mostrar_sinal: bool = True) -> str:
    """
    Transforma 0.1234 em '+12,34%'.
    Atenção: no código, percentuais são guardados como fração (0.10 = 10%).
    """
    if not numero_valido(valor):
        return "—"
    sinal = "+" if (mostrar_sinal and valor > 0) else ""
    texto = f"{valor * 100:.2f}".replace(".", ",")
    return f"{sinal}{texto}%"
