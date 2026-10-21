import { useState } from "react";
import { Cabecalho, Carregando, ErroTela, SeloTicker } from "../componentes/Comuns.jsx";
import { IconeBusca, IconeFechar, IconeSeta } from "../componentes/Icones.jsx";
import { pareceTicker } from "../formatacao.js";

/**
 * Aba Notícias: lista de empresas com uma barra de busca.
 * Tocar numa empresa abre as 20 notícias mais em alta dela.
 */
export default function Noticias({ empresas, erro, aoTentarDeNovo, abrirEmpresa }) {
  const [busca, setBusca] = useState("");

  const cabecalho = <Cabecalho titulo="Notícias" subtitulo="As mais em alta de cada empresa" />;

  if (erro && !empresas) {
    return (
      <>
        {cabecalho}
        <ErroTela mensagem={erro} aoTentarDeNovo={aoTentarDeNovo} />
      </>
    );
  }
  if (!empresas) {
    return (
      <>
        {cabecalho}
        <Carregando texto="Carregando empresas…" />
      </>
    );
  }

  // Filtra pelo que foi digitado (nome, ticker ou setor), sem ligar para acentos.
  const termo = normalizar(busca);
  const combina = (e) => !termo || normalizar(`${e.ticker} ${e.nome} ${e.setor}`).includes(termo);
  const carteira = empresas.carteira.filter(combina);
  const outras = empresas.outras.filter(combina);

  // Digitou um ticker que não está na lista? Oferece buscar mesmo assim.
  const tickerDigitado = busca.trim().toUpperCase();
  const todos = [...empresas.carteira, ...empresas.outras];
  const oferecerTicker = pareceTicker(tickerDigitado) && !todos.some((e) => e.ticker === tickerDigitado);

  return (
    <>
      {cabecalho}

      <label className="barra-busca">
        <IconeBusca />
        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Empresa, ticker ou setor"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck="false"
          enterKeyHint="search"
        />
        {busca && (
          <button type="button" className="limpar-busca" onClick={() => setBusca("")} aria-label="Limpar busca">
            <IconeFechar />
          </button>
        )}
      </label>

      {oferecerTicker && (
        <ul className="cartao lista">
          <LinhaEmpresa
            empresa={{ ticker: tickerDigitado, nome: `Buscar notícias de ${tickerDigitado}`, setor: "Ticker fora da lista" }}
            aoAbrir={abrirEmpresa}
          />
        </ul>
      )}

      {carteira.length > 0 && (
        <Grupo titulo="Na sua carteira" empresas={carteira} aoAbrir={abrirEmpresa} />
      )}
      {outras.length > 0 && (
        <Grupo titulo={termo ? "Outras empresas" : "Empresas da B3"} empresas={outras} aoAbrir={abrirEmpresa} />
      )}

      {carteira.length === 0 && outras.length === 0 && !oferecerTicker && (
        <p className="vazio centro">
          Nenhuma empresa encontrada. Digite o ticker completo (ex.: VALE3) para buscar qualquer empresa da B3.
        </p>
      )}

      <p className="rodape">Notícias do Google Notícias. Os links abrem no site de cada jornal.</p>
    </>
  );
}

function Grupo({ titulo, empresas, aoAbrir }) {
  return (
    <section className="grupo">
      <div className="grupo-topo">
        <h2>{titulo}</h2>
        <span>{empresas.length}</span>
      </div>
      <ul className="cartao lista">
        {empresas.map((empresa) => (
          <LinhaEmpresa key={empresa.ticker} empresa={empresa} aoAbrir={aoAbrir} />
        ))}
      </ul>
    </section>
  );
}

function LinhaEmpresa({ empresa, aoAbrir }) {
  const tipo = empresa.ticker.endsWith("11") && empresa.setor.startsWith("FII") ? "FII" : "Ação";
  return (
    <li>
      <button type="button" className="linha-ativo" onClick={() => aoAbrir(empresa.ticker)}>
        <SeloTicker ticker={empresa.ticker} tipo={tipo} />
        <span className="linha-ativo-meio">
          <strong>{empresa.nome}</strong>
          <small>
            {empresa.ticker} · {empresa.setor}
          </small>
        </span>
        <IconeSeta />
      </button>
    </li>
  );
}

// "Itaú" -> "itau" (para a busca não depender de acentos nem maiúsculas)
function normalizar(texto) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}
