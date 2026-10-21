"""
Testes das notícias e do filtro de credibilidade. Não usam internet: usam
feeds RSS de exemplo, no mesmo formato que o Google News devolve.

Como rodar (dentro da pasta backend):
    python3 -m unittest discover tests -v
"""

import unittest
from datetime import datetime, timezone

from carteira.credibilidade import eh_sensacionalista, identificar_fonte
from carteira.empresas import encontrar_empresa, ticker_valido
from carteira.noticias import (
    ErroNoticias,
    agrupar_em_historias,
    buscar_noticias,
    filtrar_confiaveis,
    ler_feed,
    montar_busca,
    palavras_do_titulo,
    parecidas,
)

AGORA = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

SITES = {
    "InfoMoney": "https://www.infomoney.com.br",
    "Valor Econômico": "https://valor.globo.com",
    "Exame": "https://exame.com",
    "Estadão": "https://www.estadao.com.br",
    "Money Times": "https://www.moneytimes.com.br",
    "Folha": "https://www1.folha.uol.com.br",
    "Blog do Zé Investidor": "https://blogdoze.com.br",
    "Reuters": "https://www.reuters.com",
    "Bloomberg": "https://www.bloomberg.com",
    "Penny Stocks Daily": "https://pennystocksdaily.net",
}


def item(titulo, fonte, data):
    return f"""
    <item>
      <title>{titulo} - {fonte}</title>
      <link>https://news.google.com/rss/articles/{abs(hash(titulo + fonte))}?oc=5</link>
      <guid isPermaLink="false">{abs(hash(titulo + fonte))}</guid>
      <pubDate>{data}</pubDate>
      <description>&lt;a href="#"&gt;{titulo}&lt;/a&gt;</description>
      <source url="{SITES[fonte]}">{fonte}</source>
    </item>"""


def feed(*itens):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>"Petrobras" when:7d - Google Notícias</title>
    <language>pt-BR</language>
    {''.join(itens)}
  </channel>
</rss>"""


FEED_PT = feed(
    item("Petrobras aprova pagamento de R$ 10 bilhões em dividendos", "InfoMoney", "Tue, 20 Oct 2026 10:00:00 GMT"),
    item("Petrobras eleva produção de petróleo no pré-sal", "Valor Econômico", "Mon, 19 Oct 2026 09:00:00 GMT"),
    item("Petrobras aprova R$ 10 bilhões em dividendos aos acionistas", "Exame", "Tue, 20 Oct 2026 11:00:00 GMT"),
    item("Dividendos: Petrobras aprova pagamento de R$ 10 bilhões", "Estadão", "Tue, 20 Oct 2026 08:30:00 GMT"),
    item("PETR4: o que esperar da ação nesta semana", "Money Times", "Wed, 14 Oct 2026 13:00:00 GMT"),
    item("Conselho da Petrobras discute novo plano estratégico", "Folha", "Sun, 18 Oct 2026 20:00:00 GMT"),
    # Estas duas devem ser filtradas:
    item("Petrobras vai quebrar, diz fonte anônima", "Blog do Zé Investidor", "Tue, 20 Oct 2026 11:30:00 GMT"),
    item("URGENTE: ação da Petrobras vai explodir!!", "Money Times", "Tue, 20 Oct 2026 11:45:00 GMT"),
)

FEED_EN = feed(
    item("Petrobras approves $1.8 billion dividend payout", "Reuters", "Tue, 20 Oct 2026 09:00:00 GMT"),
    item("Petrobras board approves dividend payout of $1.8 billion", "Bloomberg", "Tue, 20 Oct 2026 09:30:00 GMT"),
    item("Petrobras to triple returns, you won't believe it", "Penny Stocks Daily", "Tue, 20 Oct 2026 10:00:00 GMT"),
)


class TestLerFeed(unittest.TestCase):
    def test_le_titulo_fonte_site_e_data(self):
        noticias = ler_feed(FEED_PT)
        self.assertEqual(len(noticias), 8)
        primeira = noticias[0]
        # O " - InfoMoney" do fim do título é removido.
        self.assertEqual(primeira.titulo, "Petrobras aprova pagamento de R$ 10 bilhões em dividendos")
        self.assertEqual(primeira.fonte, "InfoMoney")
        self.assertEqual(primeira.site, "https://www.infomoney.com.br")
        self.assertEqual(primeira.publicada_em, datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc))

    def test_feed_vazio(self):
        self.assertEqual(ler_feed(feed()), [])

    def test_resposta_que_nao_e_xml(self):
        with self.assertRaises(ErroNoticias):
            ler_feed("<html>erro</html")


class TestCredibilidade(unittest.TestCase):
    def test_identifica_pelo_site(self):
        self.assertEqual(identificar_fonte("https://www.infomoney.com.br").nome, "InfoMoney")
        # Subdomínio mais específico ganha: E-Investidor é do Estadão, mas é nível 2.
        self.assertEqual(identificar_fonte("https://einvestidor.estadao.com.br").nivel, 2)
        self.assertEqual(identificar_fonte("https://www1.folha.uol.com.br").nome, "Folha de S.Paulo")

    def test_identifica_pelo_nome_quando_falta_site(self):
        self.assertEqual(identificar_fonte("", "Valor Econômico").nivel, 1)

    def test_fonte_desconhecida(self):
        self.assertIsNone(identificar_fonte("https://blogdoze.com.br", "Blog do Zé"))

    def test_sensacionalista(self):
        self.assertTrue(eh_sensacionalista("URGENTE: ação vai explodir"))
        self.assertTrue(eh_sensacionalista("Petrobras sobe 5%!!"))
        self.assertTrue(eh_sensacionalista("PETROBRAS ANUNCIA DIVIDENDOS GIGANTES HOJE"))
        self.assertTrue(eh_sensacionalista("You won't believe what Vale did"))

    def test_titulo_normal_nao_e_sensacionalista(self):
        self.assertFalse(eh_sensacionalista("Petrobras aprova dividendos de R$ 10 bilhões"))
        # Vários tickers em maiúsculas não contam como "gritar".
        self.assertFalse(eh_sensacionalista("PETR4, VALE3, ITUB4 e BBDC4 sobem com exterior"))

    def test_filtro_conta_o_que_saiu(self):
        aprovadas, contagem = filtrar_confiaveis(ler_feed(FEED_PT))
        self.assertEqual(len(aprovadas), 6)
        self.assertEqual(contagem, {"fonte_desconhecida": 1, "sensacionalista": 1})
        # O nome do veículo é padronizado pela lista.
        self.assertIn("Folha de S.Paulo", [n.fonte for n in aprovadas])


class TestAgrupar(unittest.TestCase):
    def test_palavras_sem_acento(self):
        self.assertIn("producao", palavras_do_titulo("Produção recorde"))

    def test_titulos_parecidos(self):
        a = palavras_do_titulo("Petrobras aprova pagamento de R$ 10 bilhões em dividendos")
        b = palavras_do_titulo("Dividendos: Petrobras aprova pagamento de R$ 10 bilhões")
        c = palavras_do_titulo("Petrobras eleva produção de petróleo no pré-sal")
        self.assertTrue(parecidas(a, b))
        self.assertFalse(parecidas(a, c))

    def test_mesma_historia_de_3_jornais_vira_uma_confirmada(self):
        aprovadas, _ = filtrar_confiaveis(ler_feed(FEED_PT))
        historias = agrupar_em_historias(aprovadas)
        dividendos = historias[0]
        self.assertEqual(sorted(dividendos.fontes), ["Estadão", "Exame", "InfoMoney"])
        self.assertTrue(dividendos.confirmada)
        self.assertEqual(len(historias), 4)


class TestBuscarNoticias(unittest.TestCase):
    def setUp(self):
        self.buscas = []

        def baixar_falso(busca, idioma):
            self.buscas.append((idioma, busca))
            return FEED_PT if idioma == "pt" else FEED_EN

        self.baixar = baixar_falso

    def buscar(self, ticker="PETR4", limite=20):
        return buscar_noticias(encontrar_empresa(ticker), limite=limite, baixar=self.baixar, agora=AGORA)

    def test_busca_exata_com_periodo(self):
        self.assertEqual(montar_busca(["Petrobras", "PETR4"], 7), '("Petrobras" OR "PETR4") when:7d')

    def test_busca_em_portugues_e_ingles(self):
        resultado = self.buscar()
        idiomas = {idioma for idioma, _ in self.buscas}
        self.assertEqual(idiomas, {"pt", "en"})
        self.assertTrue(resultado["busca_internacional"])
        regioes = {n["regiao"] for n in resultado["noticias"]}
        self.assertEqual(regioes, {"Brasil", "Internacional"})

    def test_internacional_agrupa_reuters_e_bloomberg(self):
        internacionais = [n for n in self.buscar()["noticias"] if n["regiao"] == "Internacional"]
        self.assertEqual(len(internacionais), 1)
        self.assertTrue(internacionais[0]["confirmada"])
        self.assertEqual(internacionais[0]["veiculos"], 2)

    def test_nada_de_fonte_desconhecida_ou_sensacionalista(self):
        resultado = self.buscar()
        fontes = {n["fonte"] for n in resultado["noticias"]}
        self.assertNotIn("Blog do Zé Investidor", fontes)
        self.assertNotIn("Penny Stocks Daily", fontes)
        self.assertFalse(any("URGENTE" in n["titulo"] for n in resultado["noticias"]))
        # 7 dias + 30 dias (ampliou), 2 idiomas: a contagem é da última busca.
        self.assertEqual(resultado["filtradas"], {"fonte_desconhecida": 2, "sensacionalista": 1})

    def test_ordem_em_alta(self):
        noticias = self.buscar()["noticias"]
        # A história dos dividendos (3 jornais, de hoje) fica em 1º lugar.
        self.assertIn("dividendos", noticias[0]["titulo"])
        self.assertEqual(noticias[0]["veiculos"], 3)
        self.assertEqual(noticias[0]["nivel"], "referencia")
        notas = [n["nota"] for n in noticias]
        self.assertEqual(notas, sorted(notas, reverse=True))

    def test_amplia_para_30_dias_se_achar_poucas(self):
        resultado = self.buscar()
        self.assertEqual(resultado["periodo_dias"], 30)
        self.assertTrue(self.buscas[0][1].endswith("when:7d"))
        self.assertTrue(self.buscas[-1][1].endswith("when:30d"))

    def test_nao_amplia_se_ja_tem_o_suficiente(self):
        resultado = self.buscar(limite=3)
        self.assertEqual(resultado["periodo_dias"], 7)
        self.assertEqual(len(resultado["noticias"]), 3)
        self.assertEqual(len(self.buscas), 2)  # pt + en, só uma vez

    def test_empresa_sem_nome_internacional_so_busca_no_brasil(self):
        resultado = self.buscar("HGLG11")
        self.assertFalse(resultado["busca_internacional"])
        self.assertEqual({idioma for idioma, _ in self.buscas}, {"pt"})


class TestEmpresas(unittest.TestCase):
    def test_empresa_da_lista(self):
        self.assertEqual(encontrar_empresa("petr4")["nome"], "Petrobras")

    def test_ticker_fora_da_lista_busca_pelo_ticker(self):
        empresa = encontrar_empresa("ABCD3")
        self.assertEqual(empresa["busca"], ["ABCD3"])

    def test_ticker_invalido(self):
        self.assertTrue(ticker_valido("B3SA3"))
        self.assertTrue(ticker_valido("HGLG11"))
        with self.assertRaises(ValueError):
            encontrar_empresa("petrobras")


if __name__ == "__main__":
    unittest.main()
