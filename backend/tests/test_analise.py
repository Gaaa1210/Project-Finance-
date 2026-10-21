"""
Testes dos indicadores, do semáforo, dos alertas e do valuation.
As contas do valuation foram escolhidas para dar resultados fáceis de conferir à mão.

Como rodar (dentro da pasta backend):
    python3 -m unittest discover tests -v
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from carteira import indicadores as ind
from carteira import valuation as val
from carteira.analise import montar_analise, recalcular_valuation
from carteira.cotacoes import DadosCotacao, ErroCotacao
from carteira.cvm import abrir_banco, carregar_balancos, carregar_tickers
from tests.test_cvm import montar_dfp, montar_fca

PREMISSAS_SIMPLES = {
    "crescimento": 0.0, "margem_ebit": 0.20, "capex_receita": 0.05, "depreciacao_receita": 0.05,
    "capital_giro_receita": 0.0, "aliquota_ir": 0.0, "wacc": 0.10, "crescimento_perpetuo": 0.0,
}
BASE_SIMPLES = {"receita": 100.0, "divida_liquida": 50.0, "acoes": 10.0, "preco": 12.0, "patrimonio_liquido": 100.0}


def tabela_exemplo(**mudancas):
    """6 anos de uma empresa saudável e crescendo 10% ao ano."""
    anos = list(range(2020, 2026))
    receita = [100 * 1.1 ** i for i in range(6)]
    dados = {
        "receita_liquida": receita,
        "lucro_bruto": [r * 0.4 for r in receita],
        "ebit": [r * 0.2 for r in receita],
        "ebitda": [r * 0.25 for r in receita],
        "depreciacao": [r * 0.05 for r in receita],
        "resultado_financeiro": [-2.0] * 6,
        "lucro_antes_ir": [r * 0.2 - 2 for r in receita],
        "ir_csll": [-(r * 0.2 - 2) * 0.3 for r in receita],
        "lucro_liquido": [r * 0.13 for r in receita],
        "lucro_controladores": [r * 0.13 for r in receita],
        "patrimonio_liquido": [80 + 5 * i for i in range(6)],
        "ativo_circulante": [60.0] * 6,
        "passivo_circulante": [30.0] * 6,
        "caixa": [10.0] * 6,
        "aplicacoes_financeiras": [5.0] * 6,
        "emprestimos_cp": [5.0] * 6,
        "emprestimos_lp": [25.0] * 6,
        "divida_bruta": [30.0] * 6,
        "divida_liquida": [15.0] * 6,
        "fluxo_operacional": [r * 0.15 for r in receita],
        "capex": [r * 0.06 for r in receita],
        "fluxo_caixa_livre": [r * 0.09 for r in receita],
        "dividendos_pagos": [r * 0.05 for r in receita],
    }
    dados.update(mudancas)
    return pd.DataFrame(dados, index=anos)


class TestValuation(unittest.TestCase):
    def test_perpetuidade_sem_crescimento_vale_fluxo_dividido_pelo_wacc(self):
        # Caixa livre = 20 por ano para sempre, WACC 10%  ->  empresa vale 20 / 0,10 = 200
        resultado = val.valor_cenario(PREMISSAS_SIMPLES, BASE_SIMPLES)
        self.assertAlmostEqual(resultado["valor_empresa"], 200.0, places=6)
        self.assertAlmostEqual(resultado["valor_acoes"], 150.0, places=6)   # 200 − dívida 50
        self.assertAlmostEqual(resultado["preco_justo"], 15.0, places=6)    # 150 / 10 ações
        self.assertAlmostEqual(resultado["potencial"], 0.25, places=6)      # 15 / 12 − 1

    def test_projecao_ano_a_ano(self):
        premissas = {**PREMISSAS_SIMPLES, "crescimento": 0.10, "aliquota_ir": 0.30, "capital_giro_receita": 0.10}
        ano1 = val.projetar(premissas, BASE_SIMPLES)[0]
        self.assertAlmostEqual(ano1["receita"], 110.0)
        self.assertAlmostEqual(ano1["nopat"], 110 * 0.2 * 0.7)
        self.assertAlmostEqual(ano1["variacao_capital_giro"], 1.0)  # 10% de (110 − 100)
        self.assertAlmostEqual(ano1["fluxo_caixa_livre"], 15.4 + 5.5 - 5.5 - 1.0)
        self.assertAlmostEqual(ano1["valor_presente"], ano1["fluxo_caixa_livre"] / 1.1)

    def test_capex_na_perpetuidade_nunca_abaixo_da_depreciacao(self):
        # Capex 2% e depreciação 5%: nos 5 anos usa 2%; na perpetuidade, 5%.
        premissas = {**PREMISSAS_SIMPLES, "capex_receita": 0.02}
        r = val.valor_cenario(premissas, BASE_SIMPLES)
        self.assertEqual(r["capex_perpetuidade"], 0.05)
        self.assertAlmostEqual(r["projecao"][0]["capex"], 2.0)
        # Ano 6 = 20 de caixa livre (como se capex = depreciação) -> terminal 20 / 0,10 = 200
        self.assertAlmostEqual(r["valor_terminal"], 200.0)

    def test_wacc_menor_que_perpetuidade_e_recusado(self):
        with self.assertRaises(val.ErroValuation):
            val.valor_cenario({**PREMISSAS_SIMPLES, "crescimento_perpetuo": 0.12}, BASE_SIMPLES)

    def test_wacc(self):
        w = val.calcular_wacc(0.10, 1.2, 0.05, 0.02, 0.34, valor_acoes=300, divida_bruta=100)
        self.assertAlmostEqual(w["custo_acionista"], 0.16)          # 10% + 1,2 × 5%
        self.assertAlmostEqual(w["peso_divida"], 0.25)
        self.assertAlmostEqual(w["wacc"], 0.16 * 0.75 + 0.12 * 0.66 * 0.25)

    def test_banco_pvp_justo(self):
        # ROE 20%, custo 15%, crescimento 5%  ->  P/VP justo = (20 − 5) / (15 − 5) = 1,5
        r = val.valor_cenario_financeira({"roe": 0.20, "custo_acionista": 0.15, "crescimento_perpetuo": 0.05}, BASE_SIMPLES)
        self.assertAlmostEqual(r["pvp_justo"], 1.5)
        self.assertAlmostEqual(r["preco_justo"], 15.0)  # PL 100 × 1,5 / 10 ações

    def test_valuation_reverso_acha_o_crescimento(self):
        premissas = {**PREMISSAS_SIMPLES, "crescimento": 0.07, "crescimento_perpetuo": 0.03}
        preco_justo = val.valor_cenario(premissas, BASE_SIMPLES)["preco_justo"]
        base = {**BASE_SIMPLES, "preco": preco_justo}
        reverso = val.valuation_reverso({**premissas, "crescimento": 0.0}, base)
        self.assertAlmostEqual(reverso["valor_implicito"], 0.07, places=5)
        self.assertFalse(reverso["fora_do_intervalo"])

    def test_valuation_reverso_fora_do_intervalo(self):
        base = {**BASE_SIMPLES, "preco": 10_000.0}  # preço absurdo
        self.assertEqual(val.valuation_reverso(PREMISSAS_SIMPLES, base)["fora_do_intervalo"], "acima")

    def test_sensibilidade_centro_e_o_neutro(self):
        premissas = {**PREMISSAS_SIMPLES, "crescimento_perpetuo": 0.03}
        tabela = val.sensibilidade(premissas, BASE_SIMPLES)
        self.assertAlmostEqual(tabela["precos"][2][2], val.valor_cenario(premissas, BASE_SIMPLES)["preco_justo"])
        # WACC maior (linha de baixo) -> preço menor
        self.assertLess(tabela["precos"][4][2], tabela["precos"][0][2])

    def test_tres_cenarios_e_ponderado(self):
        cenarios = {
            "negativo": {**PREMISSAS_SIMPLES, "margem_ebit": 0.10},
            "neutro": PREMISSAS_SIMPLES,
            "positivo": {**PREMISSAS_SIMPLES, "margem_ebit": 0.30},
        }
        r = val.avaliar(cenarios, BASE_SIMPLES)
        precos = [r["resultados"][n]["preco_justo"] for n in val.CENARIOS]
        self.assertLess(precos[0], precos[1])
        self.assertLess(precos[1], precos[2])
        self.assertAlmostEqual(r["preco_ponderado"], 0.25 * precos[0] + 0.5 * precos[1] + 0.25 * precos[2])

    def test_premissas_padrao_em_ordem(self):
        tabela = tabela_exemplo()
        base = val.montar_base(tabela, None, 50.0, 10.0)
        mercado = {"taxa_livre_risco": 0.11, "beta": 1.0, "premio_risco": 0.05, "spread_divida": 0.02}
        p = val.premissas_padrao(tabela, base, mercado)["cenarios"]
        self.assertAlmostEqual(p["neutro"]["crescimento"], 0.10, places=4)  # cresceu 10% todo ano
        self.assertLess(p["negativo"]["crescimento"], p["neutro"]["crescimento"])
        self.assertGreater(p["positivo"]["crescimento"], p["neutro"]["crescimento"])
        self.assertLess(p["negativo"]["margem_ebit"], p["positivo"]["margem_ebit"])
        self.assertGreater(p["negativo"]["wacc"], p["positivo"]["wacc"])
        for nome in val.CENARIOS:
            self.assertLess(p[nome]["crescimento_perpetuo"], p[nome]["wacc"])


class TestMercado(unittest.TestCase):
    def test_url_do_focus_com_espacos_codificados(self):
        from carteira.mercado import url_focus
        url = url_focus()
        self.assertIn("$filter=Indicador%20eq%20'Selic'", url)
        self.assertIn("$orderby=Data%20desc", url)
        self.assertNotIn("+", url)

    def test_escolhe_selic_de_3_anos_mais_recente(self):
        from carteira.mercado import escolher_selic_longo_prazo
        registros = [
            {"Indicador": "Selic", "Data": "2026-10-10", "DataReferencia": "2029", "Mediana": 10.5},
            {"Indicador": "Selic", "Data": "2026-10-17", "DataReferencia": "2029", "Mediana": 10.25},
            {"Indicador": "Selic", "Data": "2026-10-17", "DataReferencia": "2026", "Mediana": 14.75},
        ]
        escolhido = escolher_selic_longo_prazo(registros, 2026)
        self.assertAlmostEqual(escolhido["valor"], 0.1025)
        self.assertTrue(escolhido["longo_prazo"])
        self.assertIsNone(escolher_selic_longo_prazo(registros[2:], 2026))


class TestIndicadores(unittest.TestCase):
    def setUp(self):
        self.tabela = tabela_exemplo()
        lista = ind.calcular_indicadores(self.tabela, None, preco=20.0, acoes=10.0)
        self.v = {i["id"]: i for i in lista}
        self.lista = lista

    def test_cagr(self):
        self.assertAlmostEqual(ind.cagr(100, 161.051, 5), 0.10, places=5)
        self.assertIsNone(ind.cagr(-10, 50, 5))
        self.assertAlmostEqual(self.v["cagr_receita_5a"]["valor"], 0.10, places=5)
        self.assertEqual(self.v["cagr_receita_5a"]["status"], "verde")

    def test_rentabilidade(self):
        ultimo = self.tabela.iloc[-1]
        self.assertAlmostEqual(self.v["roe"]["valor"], ultimo["lucro_controladores"] / ultimo["patrimonio_liquido"], places=5)
        self.assertAlmostEqual(self.v["margem_ebit"]["valor"], 0.20, places=5)
        self.assertIsNone(self.v["margem_ebit"]["status"])  # sem regra universal

    def test_endividamento(self):
        ultimo = self.tabela.iloc[-1]
        self.assertAlmostEqual(self.v["divida_liquida_ebitda"]["valor"], 15 / ultimo["ebitda"], places=5)
        self.assertEqual(self.v["divida_liquida_ebitda"]["status"], "verde")
        self.assertAlmostEqual(self.v["liquidez_corrente"]["valor"], 2.0)

    def test_caixa_liquido_e_verde(self):
        lista = ind.calcular_indicadores(tabela_exemplo(divida_liquida=[-20.0] * 6), None, None, None)
        dl = {i["id"]: i for i in lista}["divida_liquida_ebitda"]
        self.assertLess(dl["valor"], 0)
        self.assertEqual(dl["status"], "verde")

    def test_multiplos(self):
        ultimo = self.tabela.iloc[-1]
        valor_mercado = 200.0
        self.assertAlmostEqual(self.v["p_l"]["valor"], valor_mercado / ultimo["lucro_controladores"], places=5)
        self.assertAlmostEqual(self.v["ev_ebitda"]["valor"], (valor_mercado + 15) / ultimo["ebitda"], places=5)
        self.assertAlmostEqual(self.v["dividend_yield"]["valor"], ultimo["dividendos_pagos"] / valor_mercado, places=5)

    def test_sem_preco_multiplos_vazios(self):
        lista = ind.calcular_indicadores(self.tabela, None, preco=None, acoes=None)
        self.assertIsNone({i["id"]: i for i in lista}["p_l"]["valor"])

    def test_dividendos(self):
        self.assertEqual(self.v["anos_pagando"]["valor"], 6)
        self.assertAlmostEqual(self.v["dividendos_cobertos"]["valor"], 0.09 / 0.05, places=5)

    def test_raio_x_tem_seis_categorias_com_frase(self):
        categorias = ind.raio_x(self.lista)
        self.assertEqual([c["id"] for c in categorias], list(ind.CATEGORIAS))
        for categoria in categorias:
            self.assertTrue(categoria["resumo"])
        crescimento = categorias[0]
        self.assertEqual(crescimento["status"], "verde")
        self.assertIn("10,0%", crescimento["resumo"])

    def test_banco_sem_endividamento_e_caixa(self):
        lista = ind.calcular_indicadores(self.tabela, None, 20.0, 10.0, financeira=True)
        ids = {i["id"] for i in lista}
        self.assertNotIn("divida_liquida_ebitda", ids)
        self.assertIn("roe", ids)
        categorias = {c["id"]: c for c in ind.raio_x(lista, financeira=True)}
        self.assertIsNone(categorias["endividamento"]["status"])

    def test_empresa_saudavel_sem_alertas(self):
        self.assertEqual(ind.sinais_de_alerta(self.tabela, self.lista), [])

    def test_alertas(self):
        ruim = tabela_exemplo(
            receita_liquida=[100, 98, 95, 90, 85, 80],
            ebit=[20, 18, 15, 12, 9, 6],
            lucro_liquido=[10, 5, -3, 2, -4, 1],
            patrimonio_liquido=[50, 40, 30, 20, 10, -5],
        )
        lista = ind.calcular_indicadores(ruim, None, None, None)
        titulos = " | ".join(a["titulo"] for a in ind.sinais_de_alerta(ruim, lista))
        self.assertIn("Patrimônio líquido negativo", titulos)
        self.assertIn("Prejuízo em 2", titulos)
        self.assertIn("Receita caindo", titulos)
        self.assertIn("Margem operacional caindo", titulos)


class TestAnaliseCompleta(unittest.TestCase):
    """Do banco da CVM até o JSON que vai para a tela."""

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.banco = self.pasta / "cvm.sqlite"
        conexao = abrir_banco(self.banco)
        carregar_tickers(conexao, montar_fca(self.pasta))
        for ano, lucro in [(2022, 80000000), (2023, 90000000), (2024, 100000000)]:
            carregar_balancos(conexao, montar_dfp(self.pasta, ano, lucro), "DFP", ano)
        conexao.close()

        def cotacao(ticker):
            if ticker != "PETR4":
                raise ErroCotacao(f"{ticker}: sem cotação.")
            return DadosCotacao("PETR4", 38.0, 37.5)

        self.cotacao = cotacao

    def tearDown(self):
        shutil.rmtree(self.pasta)

    def test_analise_completa_vira_json(self):
        a = montar_analise("PETR4", offline=True, caminho_banco=self.banco, buscar_cotacao=self.cotacao)
        json.dumps(a)
        self.assertEqual(a["empresa"]["ticker"], "PETR4")
        self.assertEqual(len(a["raio_x"]), 6)
        self.assertAlmostEqual(a["preco"]["valor_mercado"], 38.0 * (13044496930 - 222760), delta=1)
        resultados = a["valuation"]["resultados"]
        self.assertEqual(set(resultados), {"negativo", "neutro", "positivo"})
        self.assertLess(resultados["negativo"]["preco_justo"], resultados["positivo"]["preco_justo"])
        self.assertIsNotNone(a["valuation"]["reverso"])
        self.assertEqual(len(a["valuation"]["sensibilidade"]["precos"]), 5)

    def test_recalcular_com_premissas_editadas(self):
        a = montar_analise("PETR4", offline=True, caminho_banco=self.banco, buscar_cotacao=self.cotacao)
        cenarios = a["valuation"]["premissas"]["cenarios"]
        mais_margem = {**cenarios, "neutro": {**cenarios["neutro"], "margem_ebit": cenarios["neutro"]["margem_ebit"] + 0.05}}
        r = recalcular_valuation("PETR4", mais_margem, offline=True, caminho_banco=self.banco, buscar_cotacao=self.cotacao)
        self.assertGreater(r["resultados"]["neutro"]["preco_justo"], a["valuation"]["resultados"]["neutro"]["preco_justo"])

    def test_recalcular_com_premissa_faltando(self):
        with self.assertRaises(ValueError):
            recalcular_valuation("PETR4", {"neutro": {}}, offline=True, caminho_banco=self.banco, buscar_cotacao=self.cotacao)

    def test_banco_usa_modelo_proprio(self):
        a = montar_analise("BEXE3", offline=True, caminho_banco=self.banco, buscar_cotacao=self.cotacao)
        self.assertTrue(a["empresa"]["financeira"])
        self.assertIn("Gordon", a["valuation"]["metodo"])
        self.assertTrue(any("Sem cotação" in aviso for aviso in a["avisos"]))


if __name__ == "__main__":
    unittest.main()
