"""
Testes do banco de balanços da CVM. Não usam internet: montamos arquivos .zip
no mesmo formato dos dados abertos da CVM (CSV com ';', acentos em latin-1,
valores em milhares, linhas 'PENÚLTIMO' e reapresentações).

Como rodar (dentro da pasta backend):
    python3 -m unittest discover tests -v
"""

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from carteira.cvm import abrir_banco, carregar_balancos, carregar_tickers
from carteira.demonstrativos import ErroDemonstrativos, serie_anual

CABECALHO = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
             "ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA")
CABECALHO_BP = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
                "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA")

CNPJ_PETRO = "33.000.167/0001-01"
CNPJ_BANCO = "00.000.000/0001-91"
CNPJ_PEQUENA = "11.111.111/0001-11"


def linha(cnpj, nome, ano, conta, descricao, valor, ordem="ÚLTIMO", versao=1, escala="MIL", dre=True):
    ref = f"{ano}-12-31"
    if dre:
        return f"{cnpj};{ref};{versao};{nome};1;DF Consolidado;REAL;{escala};{ordem};{ano}-01-01;{ref};{conta};{descricao};{valor};S"
    return f"{cnpj};{ref};{versao};{nome};1;DF Consolidado;REAL;{escala};{ordem};{ref};{conta};{descricao};{valor};S"


def montar_dfp(pasta: Path, ano: int, lucro_petro: float, versao_petro: int = 1) -> Path:
    p, n = CNPJ_PETRO, "PETROLEO BRASILEIRO S.A. PETROBRAS"
    # Numa reapresentação, TODAS as linhas do documento ganham a versão nova.
    v = versao_petro
    dre = [
        linha(p, n, ano, "3.01", "Receita de Venda de Bens e/ou Serviços", 500000000, versao=v),
        linha(p, n, ano, "3.02", "Custo dos Bens e/ou Serviços Vendidos", -250000000, versao=v),
        linha(p, n, ano, "3.03", "Resultado Bruto", 250000000, versao=v),
        linha(p, n, ano, "3.05", "Resultado Antes do Resultado Financeiro e dos Tributos", 180000000, versao=v),
        linha(p, n, ano, "3.06", "Resultado Financeiro", -20000000, versao=v),
        linha(p, n, ano, "3.11", "Lucro/Prejuízo Consolidado do Período", lucro_petro, versao=v),
        linha(p, n, ano, "3.11.01", "Atribuído a Sócios da Empresa Controladora", lucro_petro - 1000000, versao=v),
        # Ano anterior repetido para comparação: deve ser IGNORADO
        linha(p, n, ano, "3.01", "Receita de Venda de Bens e/ou Serviços", 1, ordem="PENÚLTIMO", versao=v),
        # Banco: plano de contas diferente
        linha(CNPJ_BANCO, "BANCO EXEMPLO S.A.", ano, "3.01", "Receitas da Intermediação Financeira", 90000000),
        linha(CNPJ_BANCO, "BANCO EXEMPLO S.A.", ano, "3.11", "Lucro ou Prejuízo Líquido Consolidado do Período", 20000000),
    ]
    if versao_petro > 1:
        # Versão antiga do mesmo documento (ainda no arquivo): deve ser ignorada
        dre.append(linha(p, n, ano, "3.11", "Lucro/Prejuízo Consolidado do Período", 999, versao=1))
        dre.append(linha(p, n, ano, "3.01", "Receita de Venda de Bens e/ou Serviços", 999, versao=1))
    bpa = [
        linha(p, n, ano, "1", "Ativo Total", 1000000000, dre=False, versao=v),
        linha(p, n, ano, "1.01", "Ativo Circulante", 200000000, dre=False, versao=v),
        linha(p, n, ano, "1.01.01", "Caixa e Equivalentes de Caixa", 40000000, dre=False, versao=v),
        linha(p, n, ano, "1.01.02", "Aplicações Financeiras", 10000000, dre=False, versao=v),
    ]
    bpp = [
        linha(p, n, ano, "2.01.04", "Empréstimos e Financiamentos", 30000000, dre=False, versao=v),
        linha(p, n, ano, "2.02.01", "Empréstimos e Financiamentos", 270000000, dre=False, versao=v),
        linha(p, n, ano, "2.03", "Patrimônio Líquido Consolidado", 400000000, dre=False, versao=v),
    ]
    dfc = [
        linha(p, n, ano, "6.01", "Caixa Líquido Atividades Operacionais", 200000000, versao=v),
        linha(p, n, ano, "6.01.01", "Caixa Gerado nas Operações", 210000000, versao=v),
        linha(p, n, ano, "6.01.01.01", "Lucro líquido do exercício", 100000000, versao=v),
        linha(p, n, ano, "6.01.01.02", "Depreciação, depleção e amortização", 60000000, versao=v),
        linha(p, n, ano, "6.01.01.03", "Amortização de direito de uso", 10000000, versao=v),
        linha(p, n, ano, "6.02", "Caixa Líquido Atividades de Investimento", -70000000, versao=v),
        linha(p, n, ano, "6.02.01", "Aquisição de ativos imobilizados e intangíveis", -75000000, versao=v),
        linha(p, n, ano, "6.02.02", "Recebimento pela venda de ativos", 5000000, versao=v),
        linha(p, n, ano, "6.03", "Caixa Líquido Atividades de Financiamento", -120000000, versao=v),
        linha(p, n, ano, "6.03.01", "Amortização de empréstimos", -60000000, versao=v),
        linha(p, n, ano, "6.03.02", "Dividendos pagos a acionistas", -50000000, versao=v),
        linha(p, n, ano, "6.03.03", "Juros sobre capital próprio pagos", -10000000, versao=v),
    ]
    # Empresa que só publica balanço individual (escala em reais)
    dre_ind = [linha(CNPJ_PEQUENA, "PEQUENA S.A.", ano, "3.11", "Lucro/Prejuízo do Período", 5000000, escala="UNIDADE")]

    destino = pasta / f"dfp_cia_aberta_{ano}.zip"
    with zipfile.ZipFile(destino, "w") as z:
        def gravar(nome, cabecalho, linhas):
            z.writestr(nome, ("\n".join([cabecalho] + linhas) + "\n").encode("latin-1"))
        gravar(f"dfp_cia_aberta_DRE_con_{ano}.csv", CABECALHO, dre)
        gravar(f"dfp_cia_aberta_DRE_ind_{ano}.csv", CABECALHO, dre_ind + [
            linha(p, n, ano, "3.11", "Lucro/Prejuízo do Período", 123, versao=v)])  # Petrobras individual: ignorado
        gravar(f"dfp_cia_aberta_BPA_con_{ano}.csv", CABECALHO_BP, bpa)
        gravar(f"dfp_cia_aberta_BPP_con_{ano}.csv", CABECALHO_BP, bpp)
        gravar(f"dfp_cia_aberta_DFC_MI_con_{ano}.csv", CABECALHO, dfc)
        gravar(f"dfp_cia_aberta_DVA_con_{ano}.csv", CABECALHO, [])  # não usamos
        gravar(f"dfp_cia_aberta_composicao_capital_{ano}.csv",
               "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;QT_ACAO_ORDIN_CAP_INTEGR;QT_ACAO_PREF_CAP_INTEGR;"
               "QT_ACAO_TOTAL_CAP_INTEGR;QT_ACAO_ORDIN_TESOURO;QT_ACAO_PREF_TESOURO;QT_ACAO_TOTAL_TESOURO",
               [f"{p};{ano}-12-31;{v};{n};1;7442454142;5602042788;13044496930;0;222760;222760"])
    return destino


def montar_itr(pasta: Path, ano: int, receita_acumulada: float, receita_trimestre: float, lucro_acumulado: float) -> Path:
    """ITR de 30/06: a DRE traz o trimestre (abr-jun) e o acumulado (jan-jun)."""
    p, n, ref = CNPJ_PETRO, "PETROLEO BRASILEIRO S.A. PETROBRAS", f"{ano}-06-30"

    def dre(conta, descricao, valor, inicio):
        return f"{p};{ref};1;{n};1;DF Consolidado;REAL;MIL;ÚLTIMO;{inicio};{ref};{conta};{descricao};{valor};S"

    def bp(conta, descricao, valor):
        return f"{p};{ref};1;{n};1;DF Consolidado;REAL;MIL;ÚLTIMO;{ref};{conta};{descricao};{valor};S"

    linhas_dre = [
        dre("3.01", "Receita de Venda de Bens e/ou Serviços", receita_acumulada, f"{ano}-01-01"),
        dre("3.01", "Receita de Venda de Bens e/ou Serviços", receita_trimestre, f"{ano}-04-01"),
        dre("3.11", "Lucro/Prejuízo Consolidado do Período", lucro_acumulado, f"{ano}-01-01"),
        dre("3.11", "Lucro/Prejuízo Consolidado do Período", lucro_acumulado / 2, f"{ano}-04-01"),
    ]
    linhas_bpp = [bp("2.03", "Patrimônio Líquido Consolidado", 450000000)]
    destino = pasta / f"itr_cia_aberta_{ano}.zip"
    with zipfile.ZipFile(destino, "w") as z:
        z.writestr(f"itr_cia_aberta_DRE_con_{ano}.csv", ("\n".join([CABECALHO] + linhas_dre) + "\n").encode("latin-1"))
        z.writestr(f"itr_cia_aberta_BPP_con_{ano}.csv", ("\n".join([CABECALHO_BP] + linhas_bpp) + "\n").encode("latin-1"))
    return destino


def montar_fca(pasta: Path) -> Path:
    cabecalho = ("CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;Valor_Mobiliario;"
                 "Sigla_Classe_Acao_Preferencial;Classe_Acao_Preferencial;Codigo_Negociacao;Composicao_BDR_Unit;"
                 "Mercado;Sigla_Entidade_Administradora;Entidade_Administradora;Data_Inicio_Negociacao;"
                 "Data_Fim_Negociacao;Segmento;Data_Inicio_Listagem;Data_Fim_Listagem")
    linhas = [
        f"{CNPJ_PETRO};2025-01-01;1;1;PETROLEO BRASILEIRO S.A. PETROBRAS;Ações Ordinárias;;;PETR3;;Bolsa;B3;B3;;;Nível 2;;",
        f"{CNPJ_PETRO};2025-01-01;1;1;PETROLEO BRASILEIRO S.A. PETROBRAS;Ações Preferenciais;PN;Preferencial;PETR4;;Bolsa;B3;B3;;;Nível 2;;",
        f"{CNPJ_BANCO};2025-01-01;1;2;BANCO EXEMPLO S.A.;Ações Ordinárias;;;BEXE3;;Bolsa;B3;B3;;;;;",
        f"{CNPJ_PETRO};2025-01-01;1;1;PETROLEO BRASILEIRO S.A. PETROBRAS;Debêntures;;;;;Balcão;;;;;;;",
    ]
    destino = pasta / "fca_cia_aberta_2025.zip"
    with zipfile.ZipFile(destino, "w") as z:
        z.writestr("fca_cia_aberta_valor_mobiliario_2025.csv", ("\n".join([cabecalho] + linhas) + "\n").encode("latin-1"))
        z.writestr("fca_cia_aberta_geral_2025.csv", "CNPJ_Companhia\n")
    return destino


class TestCVM(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.banco = self.pasta / "cvm.sqlite"
        conexao = abrir_banco(self.banco)
        carregar_tickers(conexao, montar_fca(self.pasta))
        carregar_balancos(conexao, montar_dfp(self.pasta, 2023, 90000000), "DFP", 2023)
        carregar_balancos(conexao, montar_dfp(self.pasta, 2024, 100000000, versao_petro=2), "DFP", 2024)
        self.conexao = conexao

    def tearDown(self):
        self.conexao.close()
        shutil.rmtree(self.pasta)

    def test_tickers_viram_cnpj(self):
        tickers = dict(self.conexao.execute("SELECT ticker, cnpj FROM tickers").fetchall())
        self.assertEqual(tickers["PETR4"], CNPJ_PETRO)
        self.assertEqual(tickers["PETR3"], CNPJ_PETRO)
        self.assertEqual(len(tickers), 3)  # a debênture sem código fica de fora

    def test_valores_em_reais_e_so_ultimo_exercicio(self):
        serie = serie_anual("PETR4", self.banco)
        tabela = serie["tabela"]
        self.assertEqual(list(tabela.index), [2023, 2024])
        # 500.000.000 mil = R$ 500 bilhões (e a linha 'PENÚLTIMO' foi ignorada)
        self.assertEqual(tabela.at[2024, "receita_liquida"], 500e9)
        self.assertEqual(tabela.at[2024, "ebit"], 180e9)

    def test_fica_com_a_versao_mais_recente(self):
        tabela = serie_anual("PETR4", self.banco)["tabela"]
        self.assertEqual(tabela.at[2024, "lucro_liquido"], 100e9)  # não 999 mil (versão 1)
        self.assertEqual(tabela.at[2023, "lucro_liquido"], 90e9)

    def test_consolidado_tem_preferencia(self):
        # O individual da Petrobras (123) não substitui o consolidado.
        self.assertEqual(serie_anual("PETR3", self.banco)["tabela"].at[2024, "lucro_liquido"], 100e9)

    def test_divida_e_caixa(self):
        t = serie_anual("PETR4", self.banco)["tabela"]
        self.assertEqual(t.at[2024, "divida_bruta"], 300e9)       # 30 + 270
        self.assertEqual(t.at[2024, "divida_liquida"], 250e9)     # 300 - 40 - 10

    def test_contas_procuradas_pelo_nome(self):
        t = serie_anual("PETR4", self.banco)["tabela"]
        self.assertEqual(t.at[2024, "depreciacao"], 70e9)         # 60 + 10 (direito de uso)
        self.assertEqual(t.at[2024, "ebitda"], 250e9)             # 180 + 70
        self.assertEqual(t.at[2024, "capex"], 75e9)               # positivo; venda de ativos não entra
        self.assertEqual(t.at[2024, "dividendos_pagos"], 60e9)    # 50 + 10 de JCP; amortização não entra
        self.assertEqual(t.at[2024, "fluxo_caixa_livre"], 125e9)  # 200 - 75

    def test_banco_e_identificado(self):
        serie = serie_anual("BEXE3", self.banco)
        self.assertTrue(serie["financeira"])
        self.assertFalse(serie_anual("PETR4", self.banco)["financeira"])

    def test_recarregar_o_mesmo_ano_nao_duplica(self):
        carregar_balancos(self.conexao, montar_dfp(self.pasta, 2024, 100000000, versao_petro=2), "DFP", 2024)
        self.assertEqual(serie_anual("PETR4", self.banco)["tabela"].at[2024, "receita_liquida"], 500e9)
        quantidade = self.conexao.execute(
            "SELECT COUNT(*) FROM contas WHERE cnpj = ? AND cd_conta = '3.01' AND dt_refer = '2024-12-31'",
            (CNPJ_PETRO,)).fetchone()[0]
        self.assertEqual(quantidade, 1)

    def test_acoes_em_circulacao(self):
        acoes = serie_anual("PETR4", self.banco)["acoes"]
        self.assertEqual(acoes["quantidade"], 13044496930 - 222760)  # total − tesouraria

    def test_ultimos_12_meses_sem_trimestral_usa_o_ano(self):
        ttm = serie_anual("PETR4", self.banco)["ultimos_12_meses"]
        self.assertEqual(ttm["tipo"], "anual")
        self.assertEqual(ttm["lucro_liquido"], 100e9)

    def test_ultimos_12_meses_com_trimestral(self):
        # 2024 (ano) + jan-jun/2025 − jan-jun/2024
        carregar_balancos(self.conexao, montar_itr(self.pasta, 2024, 240000000, 130000000, 40000000), "ITR", 2024)
        carregar_balancos(self.conexao, montar_itr(self.pasta, 2025, 280000000, 150000000, 60000000), "ITR", 2025)
        ttm = serie_anual("PETR4", self.banco)["ultimos_12_meses"]
        self.assertEqual(ttm["tipo"], "12 meses")
        self.assertEqual(ttm["referencia"], "2025-06-30")
        self.assertEqual(ttm["receita_liquida"], (500 + 280 - 240) * 1e9)  # usa o acumulado, não o trimestre
        self.assertEqual(ttm["lucro_liquido"], (100 + 60 - 40) * 1e9)
        self.assertEqual(ttm["patrimonio_liquido"], 450e9)  # balanço do último trimestre

    def test_ticker_desconhecido(self):
        with self.assertRaises(ErroDemonstrativos):
            serie_anual("XPTO3", self.banco)

    def test_fii_tem_mensagem_propria(self):
        with self.assertRaises(ErroDemonstrativos) as contexto:
            serie_anual("HGLG11", self.banco)
        self.assertIn("FII", str(contexto.exception))

    def test_banco_inexistente(self):
        with self.assertRaises(ErroDemonstrativos):
            serie_anual("PETR4", self.pasta / "nao_existe.sqlite")


if __name__ == "__main__":
    unittest.main()
