import { Cabecalho, FaixaOffline, Rodape } from "../componentes/Comuns.jsx";
import { corDoValor, percentual, reais, reaisComSinal } from "../formatacao.js";

/**
 * Tela 4 — Desempenho.
 * Hoje mostra o retorno de cada ativo (dados que já temos).
 * A comparação com CDI, Ibovespa e IPCA precisa dos índices do Banco Central (Etapa 2).
 */
export default function Desempenho({ carteira, abrirAtivo }) {
  const cotados = carteira.ativos.filter((a) => a.retorno_total_pct != null);
  const ordenados = [...cotados].sort((a, b) => b.retorno_total_pct - a.retorno_total_pct);
  const maiorAbsoluto = Math.max(...ordenados.map((a) => Math.abs(a.retorno_total_pct)), 0.0001);

  const valorizacao = cotados.reduce((s, a) => s + a.lucro_reais, 0);
  const proventos = cotados.reduce((s, a) => s + (a.dividendos_recebidos || 0), 0);
  const investido = cotados.reduce((s, a) => s + a.total_investido, 0);
  const retorno = valorizacao + proventos;

  return (
    <>
      <Cabecalho titulo="Desempenho" subtitulo="Ações, ETFs e FIIs" />
      <FaixaOffline ativo={carteira.modo_offline} />

      <section className="cartao">
        <h2>De onde veio o seu retorno</h2>
        <ul className="lista-simples">
          <li>
            <span>Valorização das cotas</span>
            <strong className={corDoValor(valorizacao)}>{reaisComSinal(valorizacao)}</strong>
          </li>
          <li>
            <span>Proventos recebidos</span>
            <strong className={corDoValor(proventos)}>{reaisComSinal(proventos)}</strong>
          </li>
          <li className="total">
            <span>Retorno total</span>
            <strong className={corDoValor(retorno)}>
              {reaisComSinal(retorno)}{" "}
              <small>{investido ? percentual(retorno / investido) : "—"}</small>
            </strong>
          </li>
        </ul>
      </section>

      <section className="cartao">
        <h2>Retorno total por ativo</h2>
        <p className="nota">Valorização + proventos, desde a primeira compra.</p>
        {ordenados.length === 0 && <p className="vazio">Nenhum ativo com cotação.</p>}
        <ul className="barras">
          {ordenados.map((a) => {
            const largura = (Math.abs(a.retorno_total_pct) / maiorAbsoluto) * 50;
            const positivo = a.retorno_total_pct >= 0;
            return (
              <li key={a.ticker} onClick={() => abrirAtivo(a.ticker)}>
                <span className="barras-nome">{a.ticker}</span>
                <span className="barras-trilho">
                  <span className="barras-zero" />
                  <span
                    className={`barras-barra ${positivo ? "positivo" : "negativo"}`}
                    style={{
                      width: `${largura}%`,
                      left: positivo ? "50%" : `${50 - largura}%`,
                    }}
                  />
                </span>
                <span className={`barras-valor ${corDoValor(a.retorno_total_pct)}`}>
                  {percentual(a.retorno_total_pct)}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="cartao em-breve">
        <h2>Carteira vs CDI, Ibovespa e IPCA</h2>
        <p>
          A comparação em 1, 6 e 12 meses chega na Etapa 2, quando o app passar a buscar
          os índices do Banco Central. Até lá, nenhum número é mostrado aqui para não
          inventar dados.
        </p>
        <p className="nota">Total investido considerado: {reais(investido)}</p>
      </section>

      <Rodape />
    </>
  );
}
