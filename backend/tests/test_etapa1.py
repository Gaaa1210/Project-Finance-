"""
Testes automáticos da Etapa 1.

Um teste é um pequeno programa que confere se uma função dá o resultado esperado.
Se alguém mudar uma conta e quebrar algo, o teste avisa.

Rodar (dentro da pasta backend):
    python -m unittest discover tests -v
"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from carteira import calculos_acoes as calc
from carteira.acoes import resumir_acoes, totalizar_acoes
from carteira.cotacoes import DadosCotacao, ErroCotacao, normalizar_ticker
from carteira.formatacao import formatar_percentual, formatar_reais
from carteira.planilha import ErroPlanilha, converter_numero, ler_compras_acoes


def compras_exemplo() -> pd.DataFrame:
    """Duas compras de PETR4, para os testes."""
    return pd.DataFrame({
        "ticker": ["PETR4", "PETR4"],
        "quantidade": [100.0, 50.0],
        "preco_pago": [30.0, 36.0],
        "taxas": [5.0, 5.0],
        "data_compra": pd.to_datetime(["2025-01-10", "2025-06-10"]),
        "tipo": ["Ação", "Ação"],
        "setor": ["Petróleo", "Petróleo"],
    })


class TestCalculos(unittest.TestCase):

    def test_preco_medio_inclui_taxas(self):
        r = calc.calcular_preco_medio(compras_exemplo())
        self.assertEqual(r["quantidade"], 150)
        self.assertAlmostEqual(r["total_investido"], 4810.0)       # 3005 + 1805
        self.assertAlmostEqual(r["preco_medio"], 4810.0 / 150)     # 32,0667

    def test_lucro(self):
        reais, pct = calc.calcular_lucro(1200, 1000)
        self.assertAlmostEqual(reais, 200)
        self.assertAlmostEqual(pct, 0.20)

    def test_prejuizo(self):
        reais, pct = calc.calcular_lucro(800, 1000)
        self.assertAlmostEqual(reais, -200)
        self.assertAlmostEqual(pct, -0.20)

    def test_variacao_dia(self):
        reais, pct = calc.calcular_variacao_dia(100, 10.5, 10.0)
        self.assertAlmostEqual(reais, 50)
        self.assertAlmostEqual(pct, 0.05)

    def test_dividendos_respeitam_data_ex(self):
        dividendos = pd.Series(
            [1.0, 1.0, 1.0],
            index=pd.to_datetime(["2025-01-05",    # antes de tudo: 0 ações
                                  "2025-03-01",    # só a 1ª compra: 100 ações
                                  "2025-06-10"]),  # data ex = dia da 2ª compra: ainda 100
        )
        self.assertAlmostEqual(calc.calcular_dividendos_recebidos(compras_exemplo(), dividendos), 200)

    def test_dividendos_vazios(self):
        self.assertEqual(calc.calcular_dividendos_recebidos(compras_exemplo(), pd.Series(dtype=float)), 0)

    def test_retorno_total(self):
        reais, pct = calc.calcular_retorno_total(1100, 50, 1000)
        self.assertAlmostEqual(reais, 150)
        self.assertAlmostEqual(pct, 0.15)


class TestResumo(unittest.TestCase):

    def test_resumo_com_preco_fixo(self):
        def buscar_falso(ticker):
            return DadosCotacao(ticker, preco_atual=40.0, fechamento_anterior=38.0)

        resumo, avisos = resumir_acoes(compras_exemplo(), buscar_cotacao=buscar_falso)
        petr = resumo.iloc[0]
        self.assertEqual(avisos, [])
        self.assertAlmostEqual(petr["valor_atual"], 6000)           # 150 x 40
        self.assertAlmostEqual(petr["lucro_reais"], 6000 - 4810)
        self.assertAlmostEqual(petr["variacao_dia_reais"], 300)     # 150 x 2

    def test_ticker_inexistente_nao_derruba_o_resto(self):
        compras = pd.concat([compras_exemplo(), compras_exemplo().assign(ticker="XXXX3")])

        def buscar(ticker):
            if ticker == "XXXX3":
                raise ErroCotacao("XXXX3: não encontrado")
            return DadosCotacao(ticker, 40.0, 40.0)

        resumo, avisos = resumir_acoes(compras, buscar_cotacao=buscar)
        self.assertEqual(len(resumo), 2)
        self.assertEqual(len(avisos), 1)
        totais = totalizar_acoes(resumo)
        self.assertEqual(totais["ativos_sem_cotacao"], 1)
        self.assertAlmostEqual(totais["valor_atual"], 6000)

    def test_sem_internet_avisa(self):
        def buscar(ticker):
            raise ErroCotacao("sem rede")

        resumo, avisos = resumir_acoes(compras_exemplo(), buscar_cotacao=buscar)
        self.assertIn("internet", avisos[0])
        self.assertEqual(totalizar_acoes(resumo)["valor_atual"], 0)


class TestPlanilha(unittest.TestCase):

    def _salvar(self, tabela: pd.DataFrame) -> Path:
        pasta = Path(tempfile.mkdtemp())
        caminho = pasta / "teste.xlsx"
        tabela.to_excel(caminho, sheet_name="acoes", index=False)
        return caminho

    def test_converter_numero_brasileiro(self):
        self.assertEqual(converter_numero("32,50"), 32.5)
        self.assertEqual(converter_numero("R$ 1.234,56"), 1234.56)
        self.assertIsNone(converter_numero(""))

    def test_planilha_inexistente(self):
        with self.assertRaises(ErroPlanilha):
            ler_compras_acoes(Path("/nao/existe.xlsx"))

    def test_planilha_vazia(self):
        caminho = self._salvar(pd.DataFrame(columns=["ticker", "quantidade", "preco_pago", "data_compra"]))
        with self.assertRaises(ErroPlanilha) as ctx:
            ler_compras_acoes(caminho)
        self.assertIn("vazia", str(ctx.exception))

    def test_linha_invalida_mostra_numero_da_linha(self):
        caminho = self._salvar(pd.DataFrame({
            "ticker": ["PETR4", "VALE3"], "quantidade": [10, -5],
            "preco_pago": [30, 60], "data_compra": ["10/01/2025", "11/01/2025"],
        }))
        with self.assertRaises(ErroPlanilha) as ctx:
            ler_compras_acoes(caminho)
        self.assertIn("Linha 3", str(ctx.exception))

    def test_data_brasileira(self):
        caminho = self._salvar(pd.DataFrame({
            "ticker": ["petr4"], "quantidade": [10], "preco_pago": ["30,50"],
            "data_compra": ["05/03/2025"],
        }))
        compras = ler_compras_acoes(caminho)
        self.assertEqual(compras.iloc[0]["ticker"], "PETR4")
        self.assertEqual(compras.iloc[0]["data_compra"], pd.Timestamp("2025-03-05"))
        self.assertEqual(compras.iloc[0]["tipo"], "Ação")  # valor padrão


class TestFormatacao(unittest.TestCase):

    def test_formatos(self):
        self.assertEqual(formatar_reais(1234.5), "R$ 1.234,50")
        self.assertEqual(formatar_reais(-10), "-R$ 10,00")
        self.assertEqual(formatar_reais(None), "—")
        self.assertEqual(formatar_percentual(0.1234), "+12,34%")
        self.assertEqual(normalizar_ticker(" petr4 "), "PETR4.SA")
        self.assertEqual(normalizar_ticker("^BVSP"), "^BVSP")


if __name__ == "__main__":
    unittest.main()
