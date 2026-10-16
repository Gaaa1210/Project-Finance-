"""
Cria a planilha de exemplo em data/carteira.xlsx.

Como usar:
    python criar_planilha_exemplo.py

ATENÇÃO: os valores são apenas exemplos para testar o app.
Depois, apague essas linhas e coloque as suas compras reais.
Se o arquivo já existir, o script NÃO sobrescreve (para não apagar seus dados),
a menos que você rode:  python criar_planilha_exemplo.py --sobrescrever
"""

import sys
from datetime import date

import pandas as pd

from carteira.planilha import CAMINHO_PADRAO

# Uma linha por compra. Repare que PETR4 e HGLG11 aparecem duas vezes:
# o app junta as duas compras e calcula o preço médio sozinho.
ACOES = pd.DataFrame([
    {"ticker": "PETR4",  "tipo": "Ação", "setor": "Petróleo e Gás", "quantidade": 100,
     "preco_pago": 36.50, "data_compra": date(2025, 3, 10), "taxas": 4.90},
    {"ticker": "PETR4",  "tipo": "Ação", "setor": "Petróleo e Gás", "quantidade": 50,
     "preco_pago": 38.20, "data_compra": date(2025, 9, 2), "taxas": 4.90},
    {"ticker": "ITUB4",  "tipo": "Ação", "setor": "Financeiro", "quantidade": 80,
     "preco_pago": 33.10, "data_compra": date(2025, 5, 15), "taxas": 4.90},
    {"ticker": "IVVB11", "tipo": "ETF",  "setor": "Internacional", "quantidade": 10,
     "preco_pago": 345.00, "data_compra": date(2025, 6, 20), "taxas": 0},
    {"ticker": "HGLG11", "tipo": "FII",  "setor": "Logística", "quantidade": 20,
     "preco_pago": 158.00, "data_compra": date(2025, 1, 8), "taxas": 0},
    {"ticker": "HGLG11", "tipo": "FII",  "setor": "Logística", "quantidade": 10,
     "preco_pago": 155.40, "data_compra": date(2025, 11, 12), "taxas": 0},
])

# Renda fixa: usada na Etapa 2. Já deixamos o formato pronto.
RENDA_FIXA = pd.DataFrame([
    {"nome": "CDB Banco Exemplo", "tipo": "CDB", "valor_investido": 5000.00,
     "data_compra": date(2025, 4, 1), "data_vencimento": date(2027, 4, 1), "taxa": "110% do CDI"},
    {"nome": "LCI Banco Exemplo", "tipo": "LCI", "valor_investido": 3000.00,
     "data_compra": date(2025, 7, 10), "data_vencimento": date(2026, 12, 10), "taxa": "95% do CDI"},
    {"nome": "Tesouro IPCA+ 2029", "tipo": "Tesouro", "valor_investido": 2000.00,
     "data_compra": date(2025, 2, 14), "data_vencimento": date(2029, 5, 15), "taxa": "IPCA + 6%"},
    {"nome": "CDB Prefixado Exemplo", "tipo": "CDB", "valor_investido": 1000.00,
     "data_compra": date(2025, 8, 5), "data_vencimento": date(2027, 8, 5), "taxa": "13% pré"},
])

# Fundos: usada na Etapa 3. Por enquanto só o cabeçalho (preencha com seus fundos).
FUNDOS = pd.DataFrame(columns=["nome", "cnpj", "valor_investido", "data_compra"])


def criar_planilha(sobrescrever: bool = False) -> None:
    if CAMINHO_PADRAO.exists() and not sobrescrever:
        print(f"A planilha já existe em {CAMINHO_PADRAO}. Nada foi alterado.")
        print("Para recriar do zero: python criar_planilha_exemplo.py --sobrescrever")
        return

    CAMINHO_PADRAO.parent.mkdir(parents=True, exist_ok=True)  # cria a pasta data/

    # ExcelWriter permite escrever várias abas no mesmo arquivo.
    with pd.ExcelWriter(CAMINHO_PADRAO, engine="openpyxl",
                        date_format="DD/MM/YYYY") as arquivo:
        ACOES.to_excel(arquivo, sheet_name="acoes", index=False)
        RENDA_FIXA.to_excel(arquivo, sheet_name="renda_fixa", index=False)
        FUNDOS.to_excel(arquivo, sheet_name="fundos", index=False)

        # Deixa as colunas mais largas e as datas no formato brasileiro.
        for aba in arquivo.sheets.values():
            for coluna in aba.columns:
                aba.column_dimensions[coluna[0].column_letter].width = 18
                for celula in coluna[1:]:
                    if celula.is_date:
                        celula.number_format = "DD/MM/YYYY"

    print(f"Planilha de exemplo criada em {CAMINHO_PADRAO}")


if __name__ == "__main__":
    criar_planilha(sobrescrever="--sobrescrever" in sys.argv)
