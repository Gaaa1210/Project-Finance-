import { useEffect, useState } from "react";
import { buscarAnalise } from "../api.js";
import { Carregando, ErroTela, SeloTicker } from "../componentes/Comuns.jsx";
import { IconeVoltar } from "../componentes/Icones.jsx";
import { reais, reaisCompacto } from "../formatacao.js";
import AbaAnalise from "./empresa/AbaAnalise.jsx";
import AbaValuation from "./empresa/AbaValuation.jsx";
import NoticiasEmpresa from "./NoticiasEmpresa.jsx";

const SECOES = ["Análise", "Valuation", "Notícias"];

/**
 * Página de uma empresa, com 3 seções:
 *   Análise (Raio-X, alertas, histórico, indicadores) · Valuation (3 cenários) · Notícias
 */
export default function Empresa({ ticker, empresa, rotuloVoltar = "Empresas", aoVoltar, secaoInicial = "Análise" }) {
  const [secao, setSecao] = useState(secaoInicial);
  const [analise, setAnalise] = useState(null);
  const [erro, setErro] = useState(null);

  function carregar() {
    setErro(null);
    buscarAnalise(ticker).then(setAnalise).catch((e) => setErro(e.message));
  }

  useEffect(carregar, [ticker]);

  const nome = empresa?.nome && empresa.nome !== ticker ? empresa.nome : analise?.empresa.nome ?? ticker;
  const setor = empresa?.setor;
  const tipo = setor?.startsWith("FII") ? "FII" : "Ação";

  return (
    <>
      <button type="button" className="botao-voltar" onClick={aoVoltar}>
        <IconeVoltar /> {rotuloVoltar}
      </button>

      <header className="noticias-topo">
        <SeloTicker ticker={ticker} tipo={tipo} />
        <div>
          <h1>{nome}</h1>
          <p className="cabecalho-sub">
            {ticker}
            {setor ? ` · ${setor}` : ""}
            {analise?.preco.valor ? ` · ${reais(analise.preco.valor)}` : ""}
            {analise?.preco.valor_mercado ? ` · ${reaisCompacto(analise.preco.valor_mercado)}` : ""}
          </p>
        </div>
      </header>

      <div className="segmentado secoes-empresa" role="tablist">
        {SECOES.map((s) => (
          <button key={s} type="button" className={secao === s ? "ativo" : ""} onClick={() => setSecao(s)}>
            {s}
          </button>
        ))}
      </div>

      {secao === "Notícias" ? (
        <NoticiasEmpresa ticker={ticker} embutido />
      ) : erro ? (
        <ErroTela mensagem={erro} aoTentarDeNovo={carregar} />
      ) : !analise ? (
        <Carregando texto="Calculando indicadores e valuation…" />
      ) : (
        <>
          {analise.avisos.length > 0 && (
            <ul className="avisos-analise">
              {analise.avisos.map((a) => <li key={a}>{a}</li>)}
            </ul>
          )}
          {secao === "Análise" ? <AbaAnalise analise={analise} /> : <AbaValuation analise={analise} />}
          <p className="rodape">{analise.fonte} Não é recomendação de investimento.</p>
        </>
      )}
    </>
  );
}
