import { useEffect, useState } from "react";
import { buscarNoticias } from "../api.js";
import { ErroTela, SeloTicker } from "../componentes/Comuns.jsx";
import {
  IconeConfirmada,
  IconeEmAlta,
  IconeEscudo,
  IconeLinkExterno,
  IconeVoltar,
} from "../componentes/Icones.jsx";
import { tempoAtras } from "../formatacao.js";

const FILTROS = ["Todas", "Brasil", "Internacional"];

/**
 * As 20 notícias mais em alta (e de fontes confiáveis) de uma empresa.
 * Cada uma abre no site do jornal.
 */
export default function NoticiasEmpresa({ ticker, aoVoltar, embutido = false }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [filtro, setFiltro] = useState("Todas");

  function carregar() {
    setErro(null);
    setDados(null);
    buscarNoticias(ticker).then(setDados).catch((e) => setErro(e.message));
  }

  useEffect(carregar, [ticker]);

  // "embutido" = dentro da página da empresa (que já tem o título e o botão de voltar).
  const voltar = embutido ? null : (
    <button type="button" className="botao-voltar" onClick={aoVoltar}>
      <IconeVoltar /> Notícias
    </button>
  );

  if (erro) {
    return (
      <>
        {voltar}
        <ErroTela mensagem={erro} aoTentarDeNovo={carregar} />
      </>
    );
  }
  if (!dados) {
    return (
      <>
        {voltar}
        <EsqueletoNoticias ticker={ticker} />
      </>
    );
  }

  const { empresa } = dados;
  const noticias = dados.noticias.filter((n) => filtro === "Todas" || n.regiao === filtro);
  const [destaque, ...demais] = noticias;
  const tipo = empresa.setor.startsWith("FII") ? "FII" : "Ação";
  const escondidas = dados.filtradas.fonte_desconhecida + dados.filtradas.sensacionalista;

  return (
    <>
      {voltar}
      {!embutido && <header className="noticias-topo">
        <SeloTicker ticker={empresa.ticker} tipo={tipo} />
        <div>
          <h1>{empresa.nome}</h1>
          <p className="cabecalho-sub">
            {empresa.ticker} · {empresa.setor}
          </p>
        </div>
      </header>}

      <p className="noticias-resumo">
        <IconeEmAlta /> {dados.noticias.length} em alta · últimos {dados.periodo_dias} dias
      </p>

      {dados.busca_internacional && (
        <div className="segmentado filtro-regiao" role="tablist">
          {FILTROS.map((f) => (
            <button key={f} type="button" className={filtro === f ? "ativo" : ""} onClick={() => setFiltro(f)}>
              {f}
            </button>
          ))}
        </div>
      )}

      <FiltroCredibilidade escondidas={escondidas} filtradas={dados.filtradas} />

      {noticias.length === 0 && (
        <section className="cartao vazio-grande">
          <p>
            {filtro === "Todas"
              ? `Nenhuma notícia de fonte confiável nos últimos ${dados.periodo_dias} dias.`
              : `Nenhuma notícia ${filtro === "Brasil" ? "da imprensa brasileira" : "da imprensa internacional"} entre as mais em alta.`}
          </p>
        </section>
      )}

      {destaque && (
        <a className="cartao noticia-destaque" href={destaque.link} target="_blank" rel="noopener noreferrer">
          <span className="selo-alta">
            <IconeEmAlta /> Mais em alta
          </span>
          <h2 lang={destaque.idioma === "en" ? "en" : "pt-BR"}>{destaque.titulo}</h2>
          <InfoNoticia noticia={destaque} comIcone />
        </a>
      )}

      {demais.length > 0 && (
        <ol className="cartao lista-noticias">
          {demais.map((noticia, i) => (
            <li key={noticia.link}>
              <a href={noticia.link} target="_blank" rel="noopener noreferrer">
                <span className="posicao">{i + 2}</span>
                <span className="noticia-corpo">
                  <strong lang={noticia.idioma === "en" ? "en" : "pt-BR"}>{noticia.titulo}</strong>
                  <InfoNoticia noticia={noticia} />
                </span>
              </a>
            </li>
          ))}
        </ol>
      )}

      <p className="nota">
        “Em alta” combina quantos veículos publicaram a mesma história, quão recente ela é, a
        relevância no Google Notícias e o nível do veículo. “Confirmada” = publicada por 2 ou
        mais veículos confiáveis. Notícias internacionais aparecem em inglês.
      </p>
      <p className="rodape">
        Fonte: Google Notícias · atualizado {tempoAtras(dados.atualizado_em)}. Não é recomendação de investimento.
      </p>
    </>
  );
}

function FiltroCredibilidade({ escondidas, filtradas }) {
  return (
    <div className="filtro-credibilidade">
      <IconeEscudo />
      <span>
        <strong>Só fontes confiáveis.</strong>{" "}
        {escondidas === 0
          ? "Nenhuma notícia precisou ser escondida."
          : `${escondidas} ${escondidas === 1 ? "notícia escondida" : "notícias escondidas"}: ` +
            [
              filtradas.fonte_desconhecida && `${filtradas.fonte_desconhecida} de fontes desconhecidas`,
              filtradas.sensacionalista && `${filtradas.sensacionalista} com título sensacionalista`,
            ]
              .filter(Boolean)
              .join(" e ") +
            "."}
      </span>
    </div>
  );
}

function InfoNoticia({ noticia, comIcone = false }) {
  return (
    <span className="noticia-info">
      {noticia.idioma === "en" && <span className="etiqueta-idioma">EN</span>}
      <span className="noticia-fonte">{noticia.fonte}</span>
      <span>· {tempoAtras(noticia.publicada_em)}</span>
      {noticia.confirmada && (
        <span className="confirmada" title={`Também em: ${noticia.outras_fontes.join(", ")}`}>
          <IconeConfirmada /> Confirmada · {noticia.veiculos} veículos
        </span>
      )}
      {comIcone && <IconeLinkExterno />}
    </span>
  );
}

// Blocos cinza piscando enquanto as notícias carregam.
function EsqueletoNoticias({ ticker }) {
  return (
    <div aria-busy="true" aria-label={`Buscando notícias de ${ticker}`}>
      <div className="esqueleto titulo" />
      <div className="esqueleto linha curta" />
      <div className="cartao">
        <div className="esqueleto linha" />
        <div className="esqueleto linha" />
        <div className="esqueleto linha curta" />
      </div>
      <div className="cartao">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="esqueleto-item">
            <div className="esqueleto linha" />
            <div className="esqueleto linha curta" />
          </div>
        ))}
      </div>
    </div>
  );
}
