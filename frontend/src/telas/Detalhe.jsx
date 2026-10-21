import { useEffect, useState } from "react";
import { buscarAtivo } from "../api.js";
import GraficoPreco from "../componentes/GraficoPreco.jsx";
import { Avisos, Carregando, ErroTela, FaixaOffline, Rodape, Variacao } from "../componentes/Comuns.jsx";
import { IconeSeta, IconeVoltar } from "../componentes/Icones.jsx";
import { corDoValor, dataBR, numero, percentual, reais, reaisComSinal } from "../formatacao.js";

/** Tela 3 — Detalhe do ativo: gráfico com preço médio, compras e proventos. */
export default function Detalhe({ ticker, aoVoltar, rotuloVoltar = "Ativos", aoAbrirEmpresa }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  function carregar() {
    setErro(null);
    buscarAtivo(ticker).then(setDados).catch((e) => setErro(e.message));
  }

  // useEffect roda quando a tela abre (e se o ticker mudar).
  useEffect(carregar, [ticker]);

  const voltar = (
    <button type="button" className="botao-voltar" onClick={aoVoltar}>
      <IconeVoltar /> {rotuloVoltar}
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
        <Carregando texto={`Buscando ${ticker}…`} />
      </>
    );
  }

  const a = dados.ativo;
  const temCotacao = a.preco_atual != null;

  return (
    <>
      {voltar}
      <header className="detalhe-topo">
        <p className="cabecalho-sub">
          {a.tipo} · {a.setor}
        </p>
        <h1>{a.ticker}</h1>
        {temCotacao && (
          <p className="detalhe-preco">
            <span>{reais(a.preco_atual)}</span>
            <Variacao pct={a.variacao_dia_pct} /> <small>hoje</small>
          </p>
        )}
      </header>
      <FaixaOffline ativo={dados.modo_offline} />

      {aoAbrirEmpresa && a.tipo !== "FII" && a.tipo !== "ETF" && (
        <button type="button" className="cartao botao-empresa" onClick={() => aoAbrirEmpresa({ ticker: a.ticker, setor: a.setor })}>
          <span>
            <strong>Análise e valuation da empresa</strong>
            <small>Raio-X, sinais de alerta, preço justo em 3 cenários</small>
          </span>
          <IconeSeta />
        </button>
      )}

      <section className="cartao">
        <GraficoPreco pontos={dados.historico} precoMedio={a.preco_medio} compras={dados.compras} />
      </section>

      <section className="cartao">
        <h2>Minha posição</h2>
        <dl className="grade-numeros">
          <Item rotulo="Quantidade" valor={`${numero(a.quantidade)} cotas`} />
          <Item rotulo="Preço médio" valor={reais(a.preco_medio)} />
          <Item rotulo="Total investido" valor={reais(a.total_investido)} />
          <Item rotulo="Valor atual" valor={reais(a.valor_atual)} />
          <Item
            rotulo="Lucro"
            valor={temCotacao ? `${reaisComSinal(a.lucro_reais)}` : "—"}
            extra={temCotacao ? percentual(a.lucro_pct) : null}
            cor={corDoValor(a.lucro_reais)}
          />
          <Item
            rotulo="Proventos"
            valor={reais(a.dividendos_recebidos)}
            cor={corDoValor(a.dividendos_recebidos)}
          />
          <Item
            rotulo="Retorno total (com proventos)"
            valor={temCotacao ? reaisComSinal(a.retorno_total_reais) : "—"}
            extra={temCotacao ? percentual(a.retorno_total_pct) : null}
            cor={corDoValor(a.retorno_total_reais)}
            largo
          />
        </dl>
      </section>

      <section className="cartao">
        <h2>Minhas compras</h2>
        <ul className="lista-simples">
          {dados.compras.map((c, i) => (
            <li key={i}>
              <span>
                <strong>{dataBR(c.data)}</strong>
                <small>
                  {numero(c.quantidade)} × {reais(c.preco_pago)}
                  {c.taxas ? ` + ${reais(c.taxas)} de taxas` : ""}
                </small>
              </span>
              <strong>{reais(c.custo)}</strong>
            </li>
          ))}
        </ul>
      </section>

      <section className="cartao">
        <h2>Proventos recebidos</h2>
        {dados.proventos.length === 0 ? (
          <p className="vazio">Nenhum provento desde a sua primeira compra.</p>
        ) : (
          <ul className="lista-simples">
            {dados.proventos.map((p) => (
              <li key={p.data_ex}>
                <span>
                  <strong>Data ex {dataBR(p.data_ex)}</strong>
                  <small>
                    {reais(p.valor_por_cota)} por cota × {numero(p.quantidade)}
                  </small>
                </span>
                <strong className="positivo">{reaisComSinal(p.total)}</strong>
              </li>
            ))}
          </ul>
        )}
        <p className="nota">
          Valores brutos do Yahoo Finance. O JCP tem 15% de IR retido na fonte, e alguns
          pagamentos podem faltar.
        </p>
      </section>

      <Avisos avisos={dados.avisos} />
      <Rodape />
    </>
  );
}

function Item({ rotulo, valor, extra, cor = "", largo = false }) {
  return (
    <div className={largo ? "largo" : ""}>
      <dt>{rotulo}</dt>
      <dd className={cor}>
        {valor}
        {extra && <small> {extra}</small>}
      </dd>
    </div>
  );
}
