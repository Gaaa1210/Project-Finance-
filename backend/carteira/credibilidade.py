"""
Filtro de credibilidade das notícias.

IMPORTANTE (honestidade): nenhum programa consegue dizer com certeza se uma
notícia é verdadeira. O que este arquivo faz é reduzir MUITO o risco de
notícia falsa ou de baixa qualidade, com 3 regras simples:

  1. Só aceitamos notícias de veículos conhecidos (lista abaixo).
     Fonte desconhecida = notícia escondida.
  2. Descartamos títulos sensacionalistas ("URGENTE!!", "você não vai acreditar"...).
  3. Uma história publicada por 2 ou mais veículos da lista ganha o selo
     "Confirmada" (é muito raro vários jornais sérios errarem juntos).

Quer confiar (ou deixar de confiar) num veículo? Edite a lista FONTES.
  nivel 1 = referência (grandes jornais e agências, com checagem editorial forte)
  nivel 2 = conhecido (portais especializados, boa reputação, mais opinião/análise)
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Fonte:
    nome: str
    dominio: str   # endereço do site, sem "www." (subdomínios também valem)
    nivel: int     # 1 = referência, 2 = conhecido


FONTES = [
    # Fonte(nome, site, nível)
    # --- Brasil: referência ---
    Fonte("Valor Econômico", "valor.globo.com", 1),
    Fonte("Valor Investe", "valorinveste.globo.com", 1),
    Fonte("Pipeline Valor", "pipelinevalor.globo.com", 1),
    Fonte("Estadão", "estadao.com.br", 1),
    Fonte("Folha de S.Paulo", "folha.uol.com.br", 1),
    Fonte("O Globo", "oglobo.globo.com", 1),
    Fonte("g1", "g1.globo.com", 1),
    Fonte("Exame", "exame.com", 1),
    Fonte("InfoMoney", "infomoney.com.br", 1),
    Fonte("Brazil Journal", "braziljournal.com", 1),
    Fonte("NeoFeed", "neofeed.com.br", 1),
    Fonte("CNN Brasil", "cnnbrasil.com.br", 1),
    Fonte("Agência Brasil", "agenciabrasil.ebc.com.br", 1),
    Fonte("Bloomberg Línea", "bloomberglinea.com.br", 1),
    Fonte("BBC", "bbc.com", 1),  # bbc.com/portuguese e bbc.com/news
    Fonte("Reuters Brasil", "br.reuters.com", 1),
    # --- Brasil: conhecidos ---
    Fonte("Money Times", "moneytimes.com.br", 2),
    Fonte("Seu Dinheiro", "seudinheiro.com", 2),
    Fonte("E-Investidor", "einvestidor.estadao.com.br", 2),
    Fonte("IstoÉ Dinheiro", "istoedinheiro.com.br", 2),
    Fonte("Veja", "veja.abril.com.br", 2),
    Fonte("Poder360", "poder360.com.br", 2),
    Fonte("UOL Economia", "economia.uol.com.br", 2),
    Fonte("Forbes Brasil", "forbes.com.br", 2),
    Fonte("Suno Notícias", "suno.com.br", 2),
    Fonte("Investing.com Brasil", "br.investing.com", 2),
    Fonte("Época Negócios", "epocanegocios.globo.com", 2),
    Fonte("Times Brasil", "timesbrasil.com.br", 2),
    # --- Internacional: referência ---
    Fonte("Reuters", "reuters.com", 1),
    Fonte("Bloomberg", "bloomberg.com", 1),
    Fonte("Financial Times", "ft.com", 1),
    Fonte("The Wall Street Journal", "wsj.com", 1),
    Fonte("CNBC", "cnbc.com", 1),
    Fonte("BBC", "bbc.co.uk", 1),
    Fonte("Associated Press", "apnews.com", 1),
    Fonte("The Economist", "economist.com", 1),
    Fonte("The New York Times", "nytimes.com", 1),
    # --- Internacional: conhecidos ---
    Fonte("MarketWatch", "marketwatch.com", 2),
    Fonte("Barron's", "barrons.com", 2),
    Fonte("Yahoo Finance", "finance.yahoo.com", 2),
    Fonte("Forbes", "forbes.com", 2),
    Fonte("Fortune", "fortune.com", 2),
]

# Do domínio mais longo para o mais curto: assim "einvestidor.estadao.com.br"
# é reconhecido antes de "estadao.com.br".
_POR_DOMINIO = sorted(FONTES, key=lambda f: len(f.dominio), reverse=True)
_POR_NOME = {f.nome.lower(): f for f in FONTES}

NOMES_NIVEIS = {1: "referencia", 2: "conhecida"}
PESOS_NIVEIS = {1: 1.0, 2: 0.75}  # quanto cada nível "vale" na nota de em alta


def identificar_fonte(dominio: str, nome: str = "") -> Optional[Fonte]:
    """
    Descobre se o veículo está na lista. Primeiro pelo endereço do site
    (mais confiável), depois pelo nome. Devolve None se for desconhecido.
      "https://www.infomoney.com.br" -> Fonte("InfoMoney", ...)
    """
    dominio = (dominio or "").lower().strip()
    dominio = re.sub(r"^https?://", "", dominio).split("/")[0]
    if dominio.startswith("www."):
        dominio = dominio[4:]
    if dominio:
        for fonte in _POR_DOMINIO:
            if dominio == fonte.dominio or dominio.endswith("." + fonte.dominio):
                return fonte
    return _POR_NOME.get((nome or "").lower().strip())


# ---------------------------------------------------------------------------
# Títulos sensacionalistas
# ---------------------------------------------------------------------------

_EXPRESSOES_SENSACIONALISTAS = [
    # português (sem acento, porque comparamos o texto normalizado)
    r"\burgente\b", r"\bbomba\b", r"voce nao vai acreditar", r"ninguem esperava",
    r"\bchocante\b", r"\binacreditavel\b", r"\bexclusivo:? veja\b", r"veja o que aconteceu",
    r"o segredo (de|para|dos)", r"fique rico", r"dobr(ar|e) (o|seu) dinheiro",
    r"garantid[oa] de", r"\bimperdivel\b", r"compartilhe antes", r"vai explodir",
    r"ultima chance",
    # inglês
    r"you won'?t believe", r"\bshocking\b", r"\bbreaking!", r"get rich", r"\bmust see\b",
]
_PADRAO_SENSACIONALISTA = re.compile("|".join(_EXPRESSOES_SENSACIONALISTAS))


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def eh_sensacionalista(titulo: str) -> bool:
    """
    True se o título tiver cara de "caça-clique":
      - expressões típicas ("urgente", "você não vai acreditar"...);
      - dois ou mais pontos de exclamação/interrogação seguidos ("!!", "?!");
      - a maior parte das palavras em MAIÚSCULAS.
    """
    if _PADRAO_SENSACIONALISTA.search(_sem_acento(titulo)):
        return True
    if re.search(r"[!?]{2,}", titulo):
        return True
    # Palavras de 4+ letras. Tickers como "PETR4" não contam (têm número grudado).
    palavras = re.findall(r"\b[A-Za-zÀ-ÿ]{4,}\b", titulo)
    if len(palavras) >= 5:
        maiusculas = sum(1 for p in palavras if p.isupper())
        if maiusculas / len(palavras) > 0.6:
            return True
    return False
