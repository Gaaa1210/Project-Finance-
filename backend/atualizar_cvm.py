"""
Baixa os balanços da CVM e guarda no banco data/cvm.sqlite.

Como usar (dentro da pasta backend, com o .venv ativado):
    python3 atualizar_cvm.py                 -> balanços anuais desde 2015 + trimestrais recentes
    python3 atualizar_cvm.py --desde 2010    -> desde 2010 (o mais antigo que a CVM tem)
    python3 atualizar_cvm.py --forcar        -> baixa tudo de novo, mesmo o que já tem

A primeira vez demora alguns minutos (são ~150 MB de arquivos). Depois, só os
anos recentes são baixados de novo. Rode de vez em quando (ex.: depois de cada
temporada de balanços: março, maio, agosto e novembro).
"""

import sys
import time

from carteira.cvm import CAMINHO_BANCO, PASTA_CVM, atualizar


def main() -> None:
    desde = 2015
    if "--desde" in sys.argv:
        try:
            desde = int(sys.argv[sys.argv.index("--desde") + 1])
        except (IndexError, ValueError):
            print("Use assim: python3 atualizar_cvm.py --desde 2010")
            sys.exit(1)
    desde = max(desde, 2010)  # a CVM só tem a partir de 2010

    print(f"\n📥 Baixando balanços da CVM desde {desde} (arquivos em {PASTA_CVM})...\n")
    inicio = time.time()
    atualizar(desde=desde, forcar="--forcar" in sys.argv)

    tamanho = CAMINHO_BANCO.stat().st_size / 1024 / 1024 if CAMINHO_BANCO.exists() else 0
    print(f"\n✅ Pronto em {time.time() - inicio:.0f} s. Banco: {CAMINHO_BANCO} ({tamanho:.0f} MB)")
    print("   Teste com: python3 testar_cvm.py PETR4\n")


if __name__ == "__main__":
    main()
