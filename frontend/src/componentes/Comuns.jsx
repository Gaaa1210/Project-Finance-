// Pedaços pequenos usados em várias telas.
import { corDoValor, percentual, reaisComSinal } from "../formatacao.js";

/** Título grande no topo da tela, no estilo do iOS. */
export function Cabecalho({ titulo, subtitulo, acao }) {
  return (
    <header className="cabecalho">
      <div>
        {subtitulo && <p className="cabecalho-sub">{subtitulo}</p>}
        <h1>{titulo}</h1>
      </div>
      {acao}
    </header>
  );
}

/** Faixa amarela avisando que os preços são fictícios. */
export function FaixaOffline({ ativo }) {
  if (!ativo) return null;
  return (
    <div className="faixa-offline" role="status">
      Modo offline: preços e proventos <strong>fictícios</strong>
    </div>
  );
}

/** Lista de avisos (ativo sem cotação, sem internet etc.). */
export function Avisos({ avisos }) {
  if (!avisos || avisos.length === 0) return null;
  return (
    <section className="cartao avisos">
      <h2>Avisos</h2>
      <ul>
        {avisos.map((aviso) => (
          <li key={aviso}>{aviso}</li>
        ))}
      </ul>
    </section>
  );
}

/** "+R$ 120,30 (+4,76%)" pintado de verde ou vermelho. */
export function Variacao({ reais, pct, pilula = false }) {
  const cor = corDoValor(reais ?? pct);
  return (
    <span className={`variacao ${cor}${pilula ? " pilula" : ""}`}>
      {reais !== undefined && reaisComSinal(reais)}
      {reais !== undefined && pct !== undefined && " "}
      {pct !== undefined && (reais !== undefined ? `(${percentual(pct)})` : percentual(pct))}
    </span>
  );
}

/** Quadradinho colorido com as letras do ticker (ex.: "PE" para PETR4). */
export function SeloTicker({ ticker, tipo }) {
  const classe = tipo === "FII" ? "fii" : tipo === "ETF" ? "etf" : "acao";
  return <span className={`selo ${classe}`}>{ticker.slice(0, 4)}</span>;
}

export function Rodape() {
  return (
    <p className="rodape">
      Ferramenta de acompanhamento e estudo. Não é recomendação de investimento.
      Cotações do Yahoo Finance com cerca de 15 minutos de atraso.
    </p>
  );
}

export function Carregando({ texto = "Carregando…" }) {
  return (
    <div className="carregando" role="status">
      <span className="rodinha" />
      {texto}
    </div>
  );
}

export function ErroTela({ mensagem, aoTentarDeNovo }) {
  return (
    <section className="cartao erro-tela">
      <h2>Algo deu errado</h2>
      <p>{mensagem}</p>
      {aoTentarDeNovo && (
        <button type="button" className="botao secundario" onClick={aoTentarDeNovo}>
          Tentar de novo
        </button>
      )}
    </section>
  );
}
