"""
Testa a busca de notícias no terminal (precisa de internet).

Como usar (dentro da pasta backend, com o .venv ativado):
    python3 testar_noticias.py PETR4
"""

import sys

from carteira.empresas import encontrar_empresa
from carteira.noticias import ErroNoticias, buscar_noticias


def main() -> None:
    ticker = sys.argv[1] if len(sys.argv) > 1 else "PETR4"
    try:
        empresa = encontrar_empresa(ticker)
        resultado = buscar_noticias(empresa)
    except (ValueError, ErroNoticias) as erro:
        print(f"\n❌ {erro}\n")
        sys.exit(1)

    print(f"\n📰 {empresa['nome']} ({empresa['ticker']}): "
          f"{len(resultado['noticias'])} notícias em alta dos últimos "
          f"{resultado['periodo_dias']} dias ({resultado['total_encontradas']} encontradas)")
    filtradas = resultado["filtradas"]
    print(f"   Filtro: {filtradas['fonte_desconhecida']} de fontes desconhecidas e "
          f"{filtradas['sensacionalista']} sensacionalistas ficaram de fora.")
    if not resultado["busca_internacional"]:
        print("   (empresa sem nome internacional: só imprensa brasileira)")
    print()
    for posicao, n in enumerate(resultado["noticias"], start=1):
        repercussao = f"  ✔ confirmada por {n['veiculos']} veículos" if n["confirmada"] else ""
        regiao = "🌎" if n["regiao"] == "Internacional" else "🇧🇷"
        print(f"{posicao:>2}. {n['titulo']}")
        print(f"    {regiao} {n['fonte']} · {n['publicada_em'][:16].replace('T', ' ')} UTC{repercussao}")
    print()


if __name__ == "__main__":
    main()
