"""
Mostra no terminal a análise completa de uma empresa: Raio-X, alertas e valuation.

Como usar (dentro da pasta backend, com o .venv ativado):
    python3 testar_analise.py PETR4
    python3 testar_analise.py WEGE3 --offline   -> sem internet (preço e taxas padrão)

Precisa do banco da CVM (python3 atualizar_cvm.py).
"""

import sys

from carteira.analise import montar_analise
from carteira.demonstrativos import ErroDemonstrativos

CORES = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴", None: "⚪"}


def pct(valor):
    return "—" if valor is None else f"{valor * 100:.1f}%".replace(".", ",")


def reais(valor):
    return "—" if valor is None else f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    ticker = argumentos[0] if argumentos else "PETR4"
    try:
        a = montar_analise(ticker, offline="--offline" in sys.argv)
    except ErroDemonstrativos as erro:
        print(f"\n❌ {erro}\n")
        sys.exit(1)

    e, p, v = a["empresa"], a["preco"], a["valuation"]
    acoes = f"{p['acoes'] / 1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".") if p["acoes"] else "—"
    print(f"\n🏢 {e['nome']} ({e['ticker']}) · preço {reais(p['valor'])} · ações em circulação {acoes}")
    for aviso in a["avisos"]:
        print(f"   ⚠️  {aviso}")

    print("\n📋 RAIO-X")
    for c in a["raio_x"]:
        nota = "—" if c["nota"] is None else f"{c['nota']:.1f}".replace(".", ",")
        print(f"   {CORES[c['status']]} {c['nome']:<17} {nota:>4}/10  {c['resumo']}")

    print("\n🚩 SINAIS DE ALERTA")
    for alerta in a["alertas"] or [{"titulo": "Nenhum"}]:
        print(f"   - {alerta['titulo']}")

    print(f"\n💰 VALUATION ({v['metodo']})")
    for nome in ("negativo", "neutro", "positivo"):
        r = v["resultados"].get(nome, {})
        print(f"   {nome:<9} preço justo {reais(r.get('preco_justo')):>14}   potencial {pct(r.get('potencial')):>8}")
    print(f"   ponderado {reais(v['preco_ponderado']):>23}   potencial {pct(v['potencial_ponderado']):>8}")
    if v.get("reverso"):
        nome_variavel = "ROE" if v["reverso"]["variavel"] == "roe" else "crescimento da receita (5 anos)"
        print(f"   O preço atual supõe {nome_variavel} de {pct(v['reverso']['valor_implicito'])} ao ano")

    print("\n   Premissas do cenário neutro:")
    for campo, valor in v["premissas"]["cenarios"]["neutro"].items():
        print(f"      {campo:<22} {pct(valor)}")
    m = v["mercado"]
    print(f"\n   Taxa livre de risco: {pct(m['taxa_livre_risco'])} ({m['fontes']['taxa_livre_risco']})")
    print(f"   Beta: {str(m['beta']).replace('.', ',')} ({m['fontes']['beta']})")
    capex_perp = v["resultados"].get("neutro", {}).get("capex_perpetuidade")
    if capex_perp:
        print(f"   Capex na perpetuidade (neutro): {pct(capex_perp)} da receita (nunca abaixo da depreciação)")
    print()


if __name__ == "__main__":
    main()
