"""
ETAPA 1: lê a planilha e mostra o resumo de ações, ETFs e FIIs no terminal.

Como usar (dentro da pasta backend):
    python etapa1.py              -> preços reais do Yahoo Finance (precisa de internet)
    python etapa1.py --offline    -> preços FICTÍCIOS, para testar sem internet

Isto é uma ferramenta de acompanhamento e estudo, não recomendação de investimento.
"""

import sys

from carteira.acoes import resumir_acoes, totalizar_acoes
from carteira.cotacoes import buscar_dados_ticker
from carteira.formatacao import formatar_percentual, formatar_reais
from carteira.planilha import ErroPlanilha, ler_compras_acoes


def main() -> None:
    modo_offline = "--offline" in sys.argv

    # 1. Ler a planilha
    try:
        compras = ler_compras_acoes()
    except ErroPlanilha as erro:
        print(f"\n❌ {erro}\n")
        sys.exit(1)  # encerra o programa com código de erro

    print(f"\n✅ Li {len(compras)} compras de {compras['ticker'].nunique()} ativos.")

    # 2. Escolher de onde vêm os preços
    if modo_offline:
        from carteira.dados_exemplo import buscar_dados_ficticios
        buscar = buscar_dados_ficticios
        print("⚠️  MODO OFFLINE: preços e proventos FICTÍCIOS, só para teste.\n")
    else:
        buscar = buscar_dados_ticker
        print("🔎 Buscando cotações no Yahoo Finance (atraso de ~15 min)...\n")

    # 3. Calcular
    resumo, avisos = resumir_acoes(compras, buscar_cotacao=buscar)
    totais = totalizar_acoes(resumo)

    # 4. Mostrar
    mostrar_tabela(resumo)
    mostrar_totais(totais)

    if avisos:
        print("\n⚠️  Avisos:")
        for aviso in avisos:
            print(f"   - {aviso}")

    print("\nObs.: proventos vêm do Yahoo e são valores brutos (o JCP tem 15% de IR "
          "retido); podem faltar alguns.\n")


def mostrar_tabela(resumo) -> None:
    """Imprime uma linha por ativo, com números no formato brasileiro."""
    cabecalho = (f"{'Ativo':<8}{'Tipo':<6}{'Qtd':>6}{'Preço médio':>14}{'Preço atual':>14}"
                 f"{'Investido':>15}{'Valor atual':>15}{'Lucro':>15}{'Lucro %':>10}"
                 f"{'Hoje %':>9}{'Proventos':>13}{'Ret. total %':>14}")
    print(cabecalho)
    print("-" * len(cabecalho))

    for _, a in resumo.iterrows():
        # .get() devolve None se a coluna não existir (ativo sem cotação)
        print(
            f"{a['ticker']:<8}{a['tipo']:<6}{a['quantidade']:>6.0f}"
            f"{formatar_reais(a['preco_medio']):>14}"
            f"{formatar_reais(a.get('preco_atual')):>14}"
            f"{formatar_reais(a['total_investido']):>15}"
            f"{formatar_reais(a.get('valor_atual')):>15}"
            f"{formatar_reais(a.get('lucro_reais')):>15}"
            f"{formatar_percentual(a.get('lucro_pct')):>10}"
            f"{formatar_percentual(a.get('variacao_dia_pct')):>9}"
            f"{formatar_reais(a.get('dividendos_recebidos')):>13}"
            f"{formatar_percentual(a.get('retorno_total_pct')):>14}"
        )


def mostrar_totais(t: dict) -> None:
    print("\n📊 TOTAL (ações, ETFs e FIIs)")
    print(f"   Total investido:      {formatar_reais(t['total_investido'])}")
    print(f"   Valor atual:          {formatar_reais(t['valor_atual'])}")
    print(f"   Lucro/prejuízo:       {formatar_reais(t['lucro_reais'])} "
          f"({formatar_percentual(t['lucro_pct'])})")
    print(f"   Variação de hoje:     {formatar_reais(t['variacao_dia_reais'])}")
    print(f"   Proventos recebidos:  {formatar_reais(t['dividendos_recebidos'])}")
    if t["ativos_sem_cotacao"]:
        print(f"   ({t['ativos_sem_cotacao']} ativo(s) sem cotação ficaram fora do "
              "valor atual e do lucro)")


if __name__ == "__main__":
    main()
