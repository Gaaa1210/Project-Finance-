"""
Lista de empresas da B3 que aparecem na aba Notícias.

Cada empresa tem:
  - ticker: o código na bolsa (ex.: PETR4)
  - nome:   como aparece no app
  - busca:  expressões usadas para procurar notícias (nome popular + ticker).
            Cada expressão é buscada exata, entre aspas. Evite palavras comuns
            sozinhas (ex.: "Vale" pegaria notícias sobre "vale a pena").
  - setor

  - busca_en (opcional): expressões em INGLÊS para buscar na imprensa internacional
            (Reuters, Bloomberg, FT...). Sem ela, a empresa só tem notícias do Brasil.

Quer adicionar uma empresa? É só copiar uma linha e trocar os dados.
Empresas que estão na sua carteira entram automaticamente, mesmo que não
estejam nesta lista.
"""

import re

EMPRESAS = [
    {"ticker": "PETR4", "nome": "Petrobras", "busca": ["Petrobras", "PETR4"], "busca_en": ["Petrobras"], "setor": "Petróleo e Gás"},
    {"ticker": "VALE3", "nome": "Vale", "busca": ["Vale S.A.", "mineradora Vale", "VALE3"], "busca_en": ["Vale SA", "miner Vale", "Vale mining"], "setor": "Mineração"},
    {"ticker": "ITUB4", "nome": "Itaú Unibanco", "busca": ["Itaú Unibanco", "ITUB4"], "busca_en": ["Itau Unibanco"], "setor": "Bancos"},
    {"ticker": "BBDC4", "nome": "Bradesco", "busca": ["Bradesco", "BBDC4"], "busca_en": ["Bradesco"], "setor": "Bancos"},
    {"ticker": "BBAS3", "nome": "Banco do Brasil", "busca": ["Banco do Brasil", "BBAS3"], "busca_en": ["Banco do Brasil"], "setor": "Bancos"},
    {"ticker": "SANB11", "nome": "Santander Brasil", "busca": ["Santander Brasil", "SANB11"], "busca_en": ["Santander Brasil"], "setor": "Bancos"},
    {"ticker": "BPAC11", "nome": "BTG Pactual", "busca": ["BTG Pactual", "BPAC11"], "busca_en": ["BTG Pactual"], "setor": "Bancos"},
    {"ticker": "ITSA4", "nome": "Itaúsa", "busca": ["Itaúsa", "ITSA4"], "busca_en": ["Itausa"], "setor": "Holding"},
    {"ticker": "B3SA3", "nome": "B3", "busca": ["B3SA3", "bolsa B3"], "busca_en": ["B3 SA", "Brazil exchange operator B3"], "setor": "Serviços Financeiros"},
    {"ticker": "BBSE3", "nome": "BB Seguridade", "busca": ["BB Seguridade", "BBSE3"], "setor": "Seguros"},
    {"ticker": "CXSE3", "nome": "Caixa Seguridade", "busca": ["Caixa Seguridade", "CXSE3"], "setor": "Seguros"},
    {"ticker": "ABEV3", "nome": "Ambev", "busca": ["Ambev", "ABEV3"], "busca_en": ["Ambev"], "setor": "Bebidas"},
    {"ticker": "WEGE3", "nome": "WEG", "busca": ["WEG", "WEGE3"], "busca_en": ["WEG SA"], "setor": "Bens Industriais"},
    {"ticker": "RENT3", "nome": "Localiza", "busca": ["Localiza", "RENT3"], "busca_en": ["Localiza"], "setor": "Aluguel de Carros"},
    {"ticker": "SUZB3", "nome": "Suzano", "busca": ["Suzano", "SUZB3"], "busca_en": ["Suzano"], "setor": "Papel e Celulose"},
    {"ticker": "KLBN11", "nome": "Klabin", "busca": ["Klabin", "KLBN11"], "busca_en": ["Klabin"], "setor": "Papel e Celulose"},
    {"ticker": "PRIO3", "nome": "PRIO", "busca": ["PRIO3", "PetroRio", "petroleira Prio"], "busca_en": ["PetroRio", "Prio SA"], "setor": "Petróleo e Gás"},
    {"ticker": "UGPA3", "nome": "Ultrapar", "busca": ["Ultrapar", "UGPA3"], "busca_en": ["Ultrapar"], "setor": "Petróleo e Gás"},
    {"ticker": "VBBR3", "nome": "Vibra Energia", "busca": ["Vibra Energia", "VBBR3"], "busca_en": ["Vibra Energia"], "setor": "Petróleo e Gás"},
    {"ticker": "CSAN3", "nome": "Cosan", "busca": ["Cosan", "CSAN3"], "busca_en": ["Cosan"], "setor": "Petróleo e Gás"},
    {"ticker": "GGBR4", "nome": "Gerdau", "busca": ["Gerdau", "GGBR4"], "busca_en": ["Gerdau"], "setor": "Siderurgia"},
    {"ticker": "CSNA3", "nome": "CSN", "busca": ["Companhia Siderúrgica Nacional", "CSNA3"], "busca_en": ["Companhia Siderurgica Nacional"], "setor": "Siderurgia"},
    {"ticker": "EQTL3", "nome": "Equatorial", "busca": ["Equatorial Energia", "EQTL3"], "busca_en": ["Equatorial Energia"], "setor": "Energia Elétrica"},
    {"ticker": "CMIG4", "nome": "Cemig", "busca": ["Cemig", "CMIG4"], "busca_en": ["Cemig"], "setor": "Energia Elétrica"},
    {"ticker": "ENEV3", "nome": "Eneva", "busca": ["Eneva", "ENEV3"], "busca_en": ["Eneva"], "setor": "Energia Elétrica"},
    {"ticker": "SBSP3", "nome": "Sabesp", "busca": ["Sabesp", "SBSP3"], "busca_en": ["Sabesp"], "setor": "Saneamento"},
    {"ticker": "RADL3", "nome": "Raia Drogasil", "busca": ["Raia Drogasil", "RADL3"], "setor": "Saúde"},
    {"ticker": "HYPE3", "nome": "Hypera", "busca": ["Hypera", "HYPE3"], "setor": "Saúde"},
    {"ticker": "VIVT3", "nome": "Vivo (Telefônica)", "busca": ["Telefônica Brasil", "VIVT3"], "busca_en": ["Telefonica Brasil"], "setor": "Telecom"},
    {"ticker": "TIMS3", "nome": "TIM", "busca": ["TIM Brasil", "TIMS3"], "busca_en": ["TIM Brasil"], "setor": "Telecom"},
    {"ticker": "TOTS3", "nome": "Totvs", "busca": ["Totvs", "TOTS3"], "busca_en": ["Totvs"], "setor": "Tecnologia"},
    {"ticker": "LREN3", "nome": "Lojas Renner", "busca": ["Lojas Renner", "LREN3"], "setor": "Varejo"},
    {"ticker": "MGLU3", "nome": "Magazine Luiza", "busca": ["Magazine Luiza", "MGLU3"], "busca_en": ["Magazine Luiza"], "setor": "Varejo"},
    {"ticker": "RAIL3", "nome": "Rumo", "busca": ["Rumo S.A.", "ferrovia Rumo", "RAIL3"], "busca_en": ["Rumo SA"], "setor": "Logística"},
    {"ticker": "CYRE3", "nome": "Cyrela", "busca": ["Cyrela", "CYRE3"], "setor": "Construção"},
    {"ticker": "MULT3", "nome": "Multiplan", "busca": ["Multiplan", "MULT3"], "setor": "Shoppings"},
    {"ticker": "HGLG11", "nome": "CSHG Logística (FII)", "busca": ["HGLG11"], "setor": "FII Logística"},
    {"ticker": "KNRI11", "nome": "Kinea Renda Imobiliária (FII)", "busca": ["KNRI11"], "setor": "FII Híbrido"},
    {"ticker": "MXRF11", "nome": "Maxi Renda (FII)", "busca": ["MXRF11"], "setor": "FII Papel"},
    {"ticker": "XPML11", "nome": "XP Malls (FII)", "busca": ["XPML11"], "setor": "FII Shoppings"},
]

# Formato de ticker da B3: 4 letras + 1 ou 2 números (PETR4, SANB11, B3SA3...).
_FORMATO_TICKER = re.compile(r"^[A-Z0-9]{4}\d{1,2}$")


def ticker_valido(ticker: str) -> bool:
    return bool(_FORMATO_TICKER.match(ticker.strip().upper()))


def encontrar_empresa(ticker: str) -> dict:
    """
    Devolve a empresa da lista. Se não estiver na lista (mas o ticker tiver
    o formato certo), cria uma "empresa" que busca notícias só pelo ticker.
    Gera ValueError se o ticker não tiver o formato da B3.
    """
    ticker = ticker.strip().upper()
    for empresa in EMPRESAS:
        if empresa["ticker"] == ticker:
            return empresa
    if not ticker_valido(ticker):
        raise ValueError(f"'{ticker}' não parece um ticker da B3 (ex.: PETR4, HGLG11).")
    return {"ticker": ticker, "nome": ticker, "busca": [ticker], "setor": "Não informado"}
