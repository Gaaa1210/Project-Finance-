import { Avisos, Cabecalho, FaixaOffline, Rodape, SeloTicker } from "../componentes/Comuns.jsx";
import { IconeSeta } from "../componentes/Icones.jsx";
import { NOMES_TIPOS, corDoValor, numero, percentual, reais } from "../formatacao.js";

const ORDEM = ["Ação", "ETF", "FII"];

/** Tela 2 — Ativos: lista agrupada por tipo. Toque num ativo para ver o detalhe. */
export default function Ativos({ carteira, abrirAtivo, irPara }) {
  const { ativos } = carteira;

  // Junta os ativos por tipo: { "Ação": [...], "ETF": [...], "FII": [...] }
  const grupos = {};
  for (const ativo of ativos) {
    (grupos[ativo.tipo] ??= []).push(ativo);
  }
  const tipos = Object.keys(grupos).sort((a, b) => ORDEM.indexOf(a) - ORDEM.indexOf(b));

  return (
    <>
      <Cabecalho
        titulo="Ativos"
        subtitulo={`${ativos.length} ${ativos.length === 1 ? "ativo" : "ativos"} na carteira`}
      />
      <FaixaOffline ativo={carteira.modo_offline} />

      {ativos.length === 0 && (
        <section className="cartao vazio-grande">
          <p>Nenhum ativo ainda.</p>
          <button type="button" className="botao" onClick={() => irPara("adicionar")}>
            Adicionar compra
          </button>
        </section>
      )}

      {tipos.map((tipo) => {
        const lista = [...grupos[tipo]].sort(
          (a, b) => (b.valor_atual ?? b.total_investido) - (a.valor_atual ?? a.total_investido)
        );
        const subtotal = lista.reduce((s, a) => s + (a.valor_atual ?? a.total_investido), 0);
        return (
          <section key={tipo} className="grupo">
            <div className="grupo-topo">
              <h2>{NOMES_TIPOS[tipo] ?? tipo}</h2>
              <span>{reais(subtotal)}</span>
            </div>
            <ul className="cartao lista">
              {lista.map((ativo) => (
                <li key={ativo.ticker}>
                  <button type="button" className="linha-ativo" onClick={() => abrirAtivo(ativo.ticker)}>
                    <SeloTicker ticker={ativo.ticker} tipo={ativo.tipo} />
                    <span className="linha-ativo-meio">
                      <strong>{ativo.ticker}</strong>
                      <small>
                        {numero(ativo.quantidade)} cotas · PM {reais(ativo.preco_medio)}
                      </small>
                    </span>
                    <span className="linha-ativo-fim">
                      <strong>{reais(ativo.valor_atual ?? ativo.total_investido)}</strong>
                      <small className={corDoValor(ativo.lucro_pct)}>
                        {ativo.valor_atual == null ? "sem cotação" : percentual(ativo.lucro_pct)}
                      </small>
                    </span>
                    <IconeSeta />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      <Avisos avisos={carteira.avisos} />
      <Rodape />
    </>
  );
}
