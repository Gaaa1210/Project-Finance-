"""
Testes da camada de serviço (o que o app React recebe) e da gravação de compras.
Rodam sem internet: usam o modo offline e uma planilha temporária.

Como rodar (dentro da pasta backend):
    python3 -m unittest discover tests -v
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from carteira import servico
from carteira.planilha import ErroPlanilha, ler_compras_acoes
from criar_planilha_exemplo import ACOES, FUNDOS, RENDA_FIXA


def criar_planilha_temporaria(pasta: Path, acoes: pd.DataFrame = ACOES) -> Path:
    caminho = pasta / "carteira.xlsx"
    with pd.ExcelWriter(caminho, engine="openpyxl") as arquivo:
        acoes.to_excel(arquivo, sheet_name="acoes", index=False)
        RENDA_FIXA.to_excel(arquivo, sheet_name="renda_fixa", index=False)
        FUNDOS.to_excel(arquivo, sheet_name="fundos", index=False)
    return caminho


class TestServico(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.caminho = criar_planilha_temporaria(self.pasta)

    def tearDown(self):
        shutil.rmtree(self.pasta)

    def test_carteira_vira_json(self):
        carteira = servico.montar_carteira(self.caminho, offline=True)
        json.dumps(carteira)  # não pode dar erro (sem NaN, datas viram texto)
        self.assertEqual(len(carteira["ativos"]), 4)
        self.assertTrue(carteira["modo_offline"])

    def test_alocacao_soma_100_por_cento(self):
        carteira = servico.montar_carteira(self.caminho, offline=True)
        for grupo in ("tipo", "setor", "ativo"):
            soma = sum(item["pct"] for item in carteira["alocacao"][grupo])
            self.assertAlmostEqual(soma, 1.0)

    def test_alocacao_por_tipo(self):
        carteira = servico.montar_carteira(self.caminho, offline=True)
        por_tipo = {i["nome"]: i["valor"] for i in carteira["alocacao"]["tipo"]}
        # Valores fictícios: PETR4 150 x 37,80 + ITUB4 80 x 36,20
        self.assertAlmostEqual(por_tipo["Ação"], 150 * 37.80 + 80 * 36.20)
        self.assertAlmostEqual(por_tipo["FII"], 30 * 160.00)

    def test_detalhe_do_ativo(self):
        detalhe = servico.detalhar_ativo("hglg11", self.caminho, offline=True)
        json.dumps(detalhe)
        self.assertEqual(detalhe["ativo"]["ticker"], "HGLG11")
        self.assertEqual(len(detalhe["compras"]), 2)
        self.assertGreater(len(detalhe["historico"]), 100)
        # O histórico fictício termina no preço atual fictício.
        self.assertAlmostEqual(detalhe["historico"][-1]["preco"], 160.00)
        # Proventos fictícios do HGLG11: 1,10 em 28/02 (20 cotas) e 30/05 (20 cotas)
        # e 30/12 (30 cotas, depois da 2ª compra).
        totais = sorted(p["total"] for p in detalhe["proventos"])
        self.assertEqual(totais, [22.0, 22.0, 33.0])

    def test_detalhe_de_ativo_que_nao_existe(self):
        with self.assertRaises(KeyError):
            servico.detalhar_ativo("XPTO3", self.caminho, offline=True)

    def test_planilha_vazia_vira_carteira_vazia(self):
        caminho = criar_planilha_temporaria(self.pasta, ACOES.iloc[0:0])
        carteira = servico.montar_carteira(caminho, offline=True)
        self.assertEqual(carteira["ativos"], [])
        self.assertEqual(carteira["totais"]["valor_atual"], 0.0)


class TestListarEmpresas(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.caminho = criar_planilha_temporaria(self.pasta)

    def tearDown(self):
        shutil.rmtree(self.pasta)

    def test_carteira_primeiro_sem_repetir(self):
        empresas = servico.listar_empresas(self.caminho)
        tickers_carteira = [e["ticker"] for e in empresas["carteira"]]
        self.assertEqual(sorted(tickers_carteira), ["HGLG11", "ITUB4", "IVVB11", "PETR4"])
        outras = [e["ticker"] for e in empresas["outras"]]
        self.assertNotIn("PETR4", outras)
        self.assertIn("VALE3", outras)

    def test_sem_planilha_mostra_so_a_lista(self):
        empresas = servico.listar_empresas(self.pasta / "nao_existe.xlsx")
        self.assertEqual(empresas["carteira"], [])
        self.assertGreater(len(empresas["outras"]), 30)


class TestRegistrarCompra(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.caminho = criar_planilha_temporaria(self.pasta)

    def tearDown(self):
        shutil.rmtree(self.pasta)

    def test_grava_compra_nova(self):
        servico.registrar_compra({
            "ticker": "bbas3", "quantidade": 10, "preco_pago": 27.5,
            "data_compra": "2025-10-01", "tipo": "Ação", "setor": "Financeiro", "taxas": 1.0,
        }, self.caminho)
        compras = ler_compras_acoes(self.caminho)
        self.assertEqual(len(compras), 7)
        nova = compras.iloc[-1]
        self.assertEqual(nova["ticker"], "BBAS3")
        self.assertEqual(nova["data_compra"], pd.Timestamp(2025, 10, 1))
        self.assertEqual(nova["taxas"], 1.0)

    def test_compra_invalida_nao_e_gravada(self):
        with self.assertRaises(ErroPlanilha):
            servico.registrar_compra({
                "ticker": "PETR4", "quantidade": 0, "preco_pago": 30,
                "data_compra": "2025-10-01",
            }, self.caminho)
        self.assertEqual(len(ler_compras_acoes(self.caminho)), 6)

    def test_data_no_futuro_e_recusada(self):
        with self.assertRaises(ErroPlanilha):
            servico.registrar_compra({
                "ticker": "PETR4", "quantidade": 1, "preco_pago": 30,
                "data_compra": "2099-01-01",
            }, self.caminho)


if __name__ == "__main__":
    unittest.main()
