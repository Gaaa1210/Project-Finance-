"""
Notícias de uma empresa, pelo Google News (feed RSS, grátis e sem cadastro).

Como funciona, passo a passo:
  1. Montamos uma busca, ex.:  ("Petrobras" OR "PETR4") when:7d
     ("when:7d" = só notícias dos últimos 7 dias)
  2. Baixamos DOIS feeds RSS (arquivos XML com até ~100 notícias cada):
       - em português, notícias do Brasil;
       - em inglês, para pegar Reuters, Bloomberg, FT, WSJ, CNBC, BBC...
         (só para empresas com nome internacional, ver empresas.py)
  3. Lemos o XML: título, jornal, endereço do site, link e data de cada notícia.
  4. FILTRO DE CREDIBILIDADE (ver credibilidade.py): só ficam notícias de
     veículos conhecidos e sem título sensacionalista.
  5. Juntamos notícias parecidas: quando vários jornais publicam a mesma
     história, ela vira um item só. Com 2+ veículos, ganha o selo "Confirmada".
  6. Damos uma nota de "em alta" para cada história e devolvemos as 20 maiores.

Limitações (honestas):
  - O feed RSS do Google News não é uma API oficial; o formato pode mudar.
  - O filtro reduz o risco de notícia falsa, mas não garante que tudo é verdade.
  - Só mostramos título, jornal e link (alguns sites têm paywall).
  - Notícias em inglês aparecem em inglês (não traduzimos).
"""

import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from carteira.credibilidade import (
    NOMES_NIVEIS,
    PESOS_NIVEIS,
    Fonte,
    eh_sensacionalista,
    identificar_fonte,
)

URL_GOOGLE_NEWS = "https://news.google.com/rss/search"

# Configuração de idioma/país de cada busca no Google News.
IDIOMAS = {
    "pt": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},  # português, Brasil
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},      # inglês, internacional
}


class ErroNoticias(Exception):
    """Não foi possível buscar as notícias (mensagem amigável)."""


@dataclass
class Noticia:
    titulo: str
    fonte: str
    link: str
    publicada_em: datetime        # sempre em UTC
    posicao: int                  # ordem em que o Google devolveu (0 = mais relevante)
    site: str = ""                # endereço do site do jornal (ex.: https://www.infomoney.com.br)
    idioma: str = "pt"
    veiculo: Optional[Fonte] = None  # preenchido pelo filtro de credibilidade


@dataclass
class Historia:
    """Uma história = uma ou mais notícias parecidas, de jornais diferentes."""
    noticias: list = field(default_factory=list)

    @property
    def principal(self) -> Noticia:
        # A notícia mostrada é a do veículo de maior nível; empate: a mais relevante.
        return min(self.noticias, key=lambda n: (_nivel(n), n.posicao))

    @property
    def fontes(self) -> list:
        # dict.fromkeys mantém a ordem e tira repetidos
        return list(dict.fromkeys(n.fonte for n in sorted(self.noticias, key=lambda n: (_nivel(n), n.posicao))))

    @property
    def mais_recente(self) -> datetime:
        return max(n.publicada_em for n in self.noticias)

    @property
    def melhor_posicao(self) -> int:
        return min(n.posicao for n in self.noticias)

    @property
    def confirmada(self) -> bool:
        """Confirmada = publicada por 2 ou mais veículos da lista de confiáveis."""
        return len(self.fontes) >= 2


def _nivel(noticia: Noticia) -> int:
    return noticia.veiculo.nivel if noticia.veiculo else 9


# ---------------------------------------------------------------------------
# 1 e 2. Montar a busca e baixar o feed
# ---------------------------------------------------------------------------

def montar_busca(termos: list, dias: int) -> str:
    """
    ["Petrobras", "PETR4"], 7  ->  ("Petrobras" OR "PETR4") when:7d
    As aspas fazem o Google procurar a expressão exata.
    """
    expressoes = " OR ".join(f'"{termo}"' for termo in termos)
    return f"({expressoes}) when:{dias}d"


def baixar_feed(busca: str, idioma: str = "pt") -> str:
    """Baixa o feed RSS do Google News e devolve o texto XML."""
    try:
        import requests
    except ImportError:
        raise ErroNoticias("A biblioteca requests não está instalada. Rode: pip install -r requirements.txt")

    try:
        resposta = requests.get(
            URL_GOOGLE_NEWS,
            params={"q": busca, **IDIOMAS[idioma]},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh) ProjectFinance/1.0"},
            timeout=15,
        )
    except requests.RequestException as erro:
        raise ErroNoticias(
            "Não consegui acessar o Google News. Verifique sua internet. "
            f"(detalhe técnico: {type(erro).__name__})"
        )

    if resposta.status_code != 200:
        raise ErroNoticias(
            f"O Google News respondeu com erro {resposta.status_code}. Tente de novo em alguns minutos."
        )
    return resposta.text


# ---------------------------------------------------------------------------
# 3. Ler o XML
# ---------------------------------------------------------------------------

def ler_feed(xml_texto: str, idioma: str = "pt") -> list:
    """
    Transforma o XML do feed numa lista de Noticia.

    Cada notícia no XML se parece com:
      <item>
        <title>Petrobras anuncia dividendos - InfoMoney</title>
        <link>https://news.google.com/rss/articles/...</link>
        <pubDate>Mon, 19 Oct 2026 14:00:00 GMT</pubDate>
        <source url="https://www.infomoney.com.br">InfoMoney</source>
      </item>
    """
    try:
        raiz = ET.fromstring(xml_texto)
    except ET.ParseError:
        raise ErroNoticias("O Google News devolveu uma resposta que não consegui ler.")

    noticias = []
    for posicao, item in enumerate(raiz.iter("item")):
        titulo = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        elemento_fonte = item.find("source")
        fonte = (elemento_fonte.text or "").strip() if elemento_fonte is not None else ""
        site = elemento_fonte.get("url", "") if elemento_fonte is not None else ""
        if not titulo or not link:
            continue  # notícia incompleta: pulamos

        # O Google coloca o jornal no fim do título: "Manchete - InfoMoney".
        if not fonte and " - " in titulo:
            fonte = titulo.rsplit(" - ", 1)[1]
        if fonte and titulo.endswith(f" - {fonte}"):
            titulo = titulo[: -len(f" - {fonte}")].strip()

        noticias.append(Noticia(
            titulo=titulo,
            fonte=fonte or "Fonte não informada",
            link=link,
            publicada_em=_ler_data(item.findtext("pubDate")),
            posicao=posicao,
            site=site,
            idioma=idioma,
        ))
    return noticias


def _ler_data(texto) -> datetime:
    """'Mon, 19 Oct 2026 14:00:00 GMT' -> datetime em UTC. Sem data: 'agora'."""
    try:
        data = parsedate_to_datetime(texto)
        if data.tzinfo is None:
            data = data.replace(tzinfo=timezone.utc)
        return data.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 4. Filtro de credibilidade
# ---------------------------------------------------------------------------

def filtrar_confiaveis(noticias: list) -> tuple:
    """
    Separa as notícias aprovadas das descartadas.
    Devolve (aprovadas, contagem) — a contagem diz quantas saíram e por quê.
    """
    aprovadas = []
    contagem = {"fonte_desconhecida": 0, "sensacionalista": 0}
    for noticia in noticias:
        veiculo = identificar_fonte(noticia.site, noticia.fonte)
        if veiculo is None:
            contagem["fonte_desconhecida"] += 1
            continue
        if eh_sensacionalista(noticia.titulo):
            contagem["sensacionalista"] += 1
            continue
        noticia.veiculo = veiculo
        noticia.fonte = veiculo.nome  # nome padronizado (ex.: "Valor Econômico")
        aprovadas.append(noticia)
    return aprovadas, contagem


# ---------------------------------------------------------------------------
# 5. Juntar notícias parecidas
# ---------------------------------------------------------------------------

# Palavras muito comuns que não ajudam a comparar títulos.
_PALAVRAS_VAZIAS = {
    "para", "como", "mais", "sobre", "apos", "entre", "pelo", "pela", "com", "que",
    "dos", "das", "nos", "nas", "uma", "seus", "suas", "diz", "veja", "hoje",
    "the", "and", "for", "with", "its", "from", "says", "after", "over",
}


def palavras_do_titulo(titulo: str) -> set:
    """'Petrobras anuncia R$ 10 bi em dividendos' -> {'petrobras', 'anuncia', 'dividendos', ...}"""
    sem_acento = unicodedata.normalize("NFKD", titulo.lower()).encode("ascii", "ignore").decode()
    palavras = re.findall(r"[a-z0-9]+", sem_acento)
    return {p for p in palavras if len(p) >= 3 and p not in _PALAVRAS_VAZIAS}


def parecidas(a: set, b: set, limite: float = 0.45) -> bool:
    """
    Duas notícias contam a mesma história se dividem boa parte das palavras.
    Usamos o "índice de Jaccard": palavras em comum / palavras no total.
    """
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= limite


def agrupar_em_historias(noticias: list) -> list:
    """Junta notícias parecidas (do mesmo idioma) numa só história."""
    historias = []
    palavras_das_historias = []
    for noticia in sorted(noticias, key=lambda n: (n.idioma, n.posicao)):
        palavras = palavras_do_titulo(noticia.titulo)
        for historia, palavras_historia in zip(historias, palavras_das_historias):
            if historia.noticias[0].idioma == noticia.idioma and parecidas(palavras, palavras_historia):
                historia.noticias.append(noticia)
                break
        else:  # o "else" do for roda quando NÃO houve break: é uma história nova
            historias.append(Historia(noticias=[noticia]))
            palavras_das_historias.append(palavras)
    return historias


# ---------------------------------------------------------------------------
# 6. Nota de "em alta"
# ---------------------------------------------------------------------------

MEIA_VIDA_HORAS = 48  # a cada 2 dias, o peso de "novidade" cai pela metade


def calcular_nota(historia: Historia, agora: datetime) -> float:
    """
    Nota de "em alta" de uma história (quanto maior, mais em alta). Junta 4 coisas:

      - Repercussão: quantos veículos confiáveis publicaram a história.
        1 veículo = 1,0 | 2 = 1,6 | 4 = 2,2 | 8 = 2,8 ... (cresce devagar)
      - Novidade: notícia de agora vale 1,0; de 2 dias atrás, 0,5; de 4 dias, 0,25.
      - Relevância: a ordem do próprio Google (1ª posição = 1,0, e vai caindo).
      - Credibilidade: veículo de referência vale 1,0; veículo conhecido, 0,75.
    """
    repercussao = 1 + 0.6 * math.log2(len(historia.fontes))
    horas = max((agora - historia.mais_recente).total_seconds() / 3600, 0)
    novidade = 0.5 ** (horas / MEIA_VIDA_HORAS)
    relevancia = 1 / (1 + historia.melhor_posicao / 15)
    nivel = _nivel(historia.principal)
    credibilidade = PESOS_NIVEIS.get(nivel, 0.5)
    return repercussao * (0.35 + 0.65 * novidade) * (0.5 + 0.5 * relevancia) * credibilidade


def selecionar_em_alta(noticias: list, limite: int = 20, agora: datetime = None) -> list:
    """Agrupa, dá nota e devolve as 'limite' histórias mais em alta, já em ordem."""
    agora = agora or datetime.now(timezone.utc)
    historias = agrupar_em_historias(noticias)
    historias.sort(key=lambda h: calcular_nota(h, agora), reverse=True)
    return [(h, calcular_nota(h, agora)) for h in historias[:limite]]


# ---------------------------------------------------------------------------
# Tudo junto
# ---------------------------------------------------------------------------

def buscar_noticias(empresa: dict, limite: int = 20, baixar=baixar_feed, agora: datetime = None) -> dict:
    """
    As 'limite' notícias mais em alta (e confiáveis) de uma empresa.

    Procura nos últimos 7 dias. Se sobrarem poucas depois do filtro, amplia para 30.
    'baixar' é a função que baixa o feed (nos testes, passamos um feed de exemplo).
    """
    agora = agora or datetime.now(timezone.utc)

    # Buscas a fazer: sempre em português; em inglês só se a empresa tiver nome internacional.
    buscas = [("pt", empresa["busca"])]
    if empresa.get("busca_en"):
        buscas.append(("en", empresa["busca_en"]))

    def coletar(dias):
        todas = []
        for idioma, termos in buscas:
            todas += ler_feed(baixar(montar_busca(termos, dias), idioma), idioma)
        aprovadas, contagem = filtrar_confiaveis(todas)
        return todas, aprovadas, contagem

    periodo = 7
    todas, aprovadas, contagem = coletar(periodo)
    if len(agrupar_em_historias(aprovadas)) < limite:
        periodo = 30
        todas, aprovadas, contagem = coletar(periodo)

    selecionadas = selecionar_em_alta(aprovadas, limite, agora)

    return {
        "empresa": {k: empresa[k] for k in ("ticker", "nome", "setor")},
        "periodo_dias": periodo,
        "busca_internacional": len(buscas) > 1,
        "total_encontradas": len(todas),
        "filtradas": contagem,
        "atualizado_em": agora.isoformat(timespec="seconds"),
        "noticias": [_historia_para_json(h, nota) for h, nota in selecionadas],
    }


def _historia_para_json(historia: Historia, nota: float) -> dict:
    principal = historia.principal
    return {
        "titulo": principal.titulo,
        "fonte": principal.fonte,
        "link": principal.link,
        "publicada_em": principal.publicada_em.isoformat(timespec="seconds"),
        "idioma": principal.idioma,
        # "Brasil" = imprensa em português; "Internacional" = imprensa em inglês.
        "regiao": "Internacional" if principal.idioma == "en" else "Brasil",
        "nivel": NOMES_NIVEIS[principal.veiculo.nivel],
        "confirmada": historia.confirmada,
        "veiculos": len(historia.fontes),
        "outras_fontes": [f for f in historia.fontes if f != principal.fonte],
        "nota": round(nota, 3),
    }
