"""
Mostra no terminal os principais números anuais de uma empresa, vindos da CVM.

Como usar (dentro da pasta backend, com o .venv ativado):
    python3 testar_cvm.py PETR4
    python3 testar_cvm.py WEGE3 --contas     -> mostra também o nome das contas encontradas
"""

import sys

from carteira.demonstrativos import ErroDemonstrativos, serie_anual

# O que mostrar, em que ordem, e com qual nome
LINHAS = [
    ("receita_liquida", "Receita líquida"),
    ("lucro_bruto", "Lucro bruto"),
    ("ebit", "EBIT"),
    ("depreciacao", "Depreciação e amortiz."),
    ("ebitda", "EBITDA"),
    ("resultado_financeiro", "Resultado financeiro"),
    ("lucro_liquido", "Lucro líquido"),
    ("lucro_controladores", "  dos controladores"),
    ("ativo_total", "Ativo total"),
    ("patrimonio_liquido", "Patrimônio líquido"),
    ("caixa", "Caixa"),
    ("aplicacoes_financeiras", "Aplicações financeiras"),
    ("divida_bruta", "Dívida bruta"),
    ("divida_liquida", "Dívida líquida"),
    ("fluxo_operacional", "Caixa das operações"),
    ("capex", "Capex"),
    ("fluxo_caixa_livre", "Fluxo de caixa livre"),
    ("dividendos_pagos", "Dividendos/JCP pagos"),
]


def em_bilhoes(valor) -> str:
    """12345678900 -> '12,3' (em bilhões de reais)"""
    if valor is None or valor != valor:  # valor != valor é True para NaN
        return "—"
    return f"{valor / 1e9:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    ticker = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "PETR4"
    try:
        serie = serie_anual(ticker)
    except ErroDemonstrativos as erro:
        print(f"\n❌ {erro}\n")
        sys.exit(1)

    tabela = serie["tabela"]
    print(f"\n🏢 {serie['empresa']} ({serie['ticker']}) · CNPJ {serie['cnpj']}")
    if serie["financeira"]:
        print("   ⚠️  Banco/seguradora: plano de contas diferente; EBIT, dívida e capex não se aplicam.")
    print("   Valores em R$ bilhões · fonte: CVM (DFP, consolidado)\n")

    anos = list(tabela.index)
    print(f"{'':<24}" + "".join(f"{ano:>9}" for ano in anos))
    for coluna, nome in LINHAS:
        print(f"{nome:<24}" + "".join(f"{em_bilhoes(tabela.at[ano, coluna]):>9}" for ano in anos))
    print()

    if "--contas" in sys.argv:
        print(f"🔎 Contas encontradas pelo nome no fluxo de caixa de {anos[-1]}:")
        for nome, contas in serie["contas_por_nome_ultimo_ano"].items():
            print(f"   {nome}:")
            for codigo, descricao, valor in contas or [("", "(nenhuma conta encontrada)", None)]:
                print(f"      {codigo:<14} {descricao[:60]:<60} {em_bilhoes(valor):>8}")
        print()


if __name__ == "__main__":
    main()
