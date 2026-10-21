import { useState } from "react";
import GraficoAnual from "../../componentes/GraficoAnual.jsx";
import { IconeAlerta, IconeConfirmada } from "../../componentes/Icones.jsx";
import { dataBR, formatarIndicador, percentual, reaisCompacto, vezes } from "../../formatacao.js";

const NOMES_STATUS = { verde: "Bom", amarelo: "Atenção", vermelho: "Fraco" };

/**
 * Seção "Análise" da página da empresa:
 *   1. Raio-X: nota de 0 a 10 em 6 aspectos, com uma frase de conclusão
 *   2. Sinais de alerta
 *   3. Histórico em gráficos (até 10 anos)
 *   4. Todos os indicadores, com a regra do semáforo e a explicação
 */
export default function AbaAnalise({ analise }) {
  const { raio_x: raioX, indicadores, alertas, historico, referencia } = analise;

  function abrirCategoria(id) {
    // Rola até a lista de indicadores daquela categoria.
    requestAnimationFrame(() => document.getElementById(`categoria-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  return (
    <>
      <p className="referencia-dados">
        {referencia.tipo === "12 meses"
          ? `Últimos 12 meses até ${dataBR(referencia.ultimos_12_meses)} · histórico até ${referencia.ultimo_ano}`
          : `Dados do ano de ${referencia.ultimo_ano}`}
      </p>

      <section className="raio-x">
        {raioX.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`cartao nota-categoria ${c.status ?? "sem-nota"}`}
            onClick={() => abrirCategoria(c.id)}
          >
            <span className="nota-topo">
              <span className="nota-nome">{c.nome}</span>
              <span className={`selo-status ${c.status ?? ""}`}>{c.status ? NOMES_STATUS[c.status] : "—"}</span>
            </span>
            <span className="nota-valor">
              {c.nota !== null ? c.nota.toFixed(1).replace(".", ",") : "—"}
              {c.nota !== null && <small>/10</small>}
            </span>
            <span className="nota-resumo">{c.resumo}</span>
          </button>
        ))}
      </section>

      <section className="cartao">
        <h2>Sinais de alerta</h2>
        {alertas.length === 0 ? (
          <p className="sem-alertas">
            <IconeConfirmada /> Nenhum sinal de alerta nos critérios analisados.
          </p>
        ) : (
          <ul className="lista-alertas">
            {alertas.map((a) => (
              <li key={a.titulo} className={a.nivel}>
                <IconeAlerta />
                <span>
                  <strong>{a.titulo}</strong>
                  <small>{a.explicacao}</small>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Historico historico={historico} />

      <h2 className="titulo-secao">Todos os indicadores</h2>
      {raioX.map((c) => {
        const itens = indicadores.filter((i) => i.categoria === c.id);
        if (itens.length === 0) return null;
        return (
          <section key={c.id} id={`categoria-${c.id}`} className="cartao grupo-indicadores">
            <h3>
              <span className={`bolinha-status ${c.status ?? ""}`} /> {c.nome}
            </h3>
            <ul>
              {itens.map((i) => (
                <LinhaIndicador key={i.id} indicador={i} />
              ))}
            </ul>
          </section>
        );
      })}

      <p className="nota">
        As notas resumem a saúde da empresa em cada aspecto, com regras gerais iguais para todas
        as empresas. Um setor pode ter características próprias (ex.: elétricas têm mais dívida;
        varejo tem margens menores). Toque num indicador para ver a regra e o que ele significa.
      </p>
    </>
  );
}

function LinhaIndicador({ indicador: i }) {
  const [aberto, setAberto] = useState(false);
  return (
    <li className={"linha-indicador" + (aberto ? " aberto" : "")}>
      <button type="button" onClick={() => setAberto(!aberto)}>
        <span className={`bolinha-status ${i.status ?? "neutra"}`} />
        <span className="indicador-nome">{i.nome}</span>
        <strong className="indicador-valor">{formatarIndicador(i.valor, i.formato)}</strong>
      </button>
      {aberto && (
        <div className="indicador-detalhe">
          <p>{i.explicacao}</p>
          <p className="indicador-regra">Regra: {i.regra}</p>
        </div>
      )}
    </li>
  );
}

function Historico({ historico: h }) {
  if (!h.anos.length) return null;
  const pct = (v) => (v === null || v === undefined ? "—" : percentual(v, false));
  return (
    <>
      <h2 className="titulo-secao">Histórico</h2>
      <section className="cartao">
        <h3 className="titulo-grafico">Receita e lucro</h3>
        <GraficoAnual
          anos={h.anos}
          formatar={reaisCompacto}
          series={[
            { nome: "Receita", valores: h.receita, cor: "var(--serie-1)" },
            { nome: "Lucro", valores: h.lucro, cor: "var(--serie-2)" },
          ]}
        />
      </section>
      <section className="cartao">
        <h3 className="titulo-grafico">Margens</h3>
        <GraficoAnual
          anos={h.anos}
          tipo="linhas"
          formatar={pct}
          series={[
            { nome: "Bruta", valores: h.margem_bruta, cor: "var(--serie-5)" },
            { nome: "EBIT", valores: h.margem_ebit, cor: "var(--serie-1)" },
            { nome: "Líquida", valores: h.margem_liquida, cor: "var(--serie-2)" },
          ]}
        />
      </section>
      <section className="cartao">
        <h3 className="titulo-grafico">ROE (retorno sobre o patrimônio)</h3>
        <GraficoAnual anos={h.anos} tipo="linhas" formatar={pct} series={[{ nome: "ROE", valores: h.roe, cor: "var(--serie-3)" }]} />
      </section>
      {h.divida_liquida_ebitda.some((v) => v !== null) && (
        <section className="cartao">
          <h3 className="titulo-grafico">Dívida líquida / EBITDA</h3>
          <GraficoAnual
            anos={h.anos}
            formatar={(v) => vezes(v)}
            series={[{ nome: "Dívida líq./EBITDA", valores: h.divida_liquida_ebitda, cor: "var(--serie-4)" }]}
          />
        </section>
      )}
      {h.fluxo_caixa_livre.some((v) => v !== null) && (
        <section className="cartao">
          <h3 className="titulo-grafico">Caixa livre e dividendos pagos</h3>
          <GraficoAnual
            anos={h.anos}
            formatar={reaisCompacto}
            series={[
              { nome: "Caixa livre", valores: h.fluxo_caixa_livre, cor: "var(--serie-2)" },
              { nome: "Dividendos", valores: h.dividendos, cor: "var(--serie-3)" },
            ]}
          />
        </section>
      )}
    </>
  );
}
