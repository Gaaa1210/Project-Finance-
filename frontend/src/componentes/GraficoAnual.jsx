import { useState } from "react";

const LARGURA = 350;
const ALTURA = 160;
const MARGEM = { topo: 10, base: 20, lado: 4 };

/**
 * Gráfico de barras ou de linhas, um ponto por ano.
 *   series: [{ nome: "Receita", valores: [..], cor: "var(--serie-1)" }]
 *   formatar: função que transforma o número em texto (ex.: reaisCompacto)
 * Toque num ano para ver os valores dele na legenda.
 */
export default function GraficoAnual({ anos, series, tipo = "barras", formatar }) {
  const [selecionado, setSelecionado] = useState(anos.length - 1);
  const todos = series.flatMap((s) => s.valores).filter((v) => v !== null && v !== undefined);
  if (anos.length === 0 || todos.length === 0) {
    return <p className="vazio">Sem dados suficientes para o gráfico.</p>;
  }

  // Escala vertical sempre incluindo o zero (para barras negativas aparecerem para baixo).
  let minimo = Math.min(0, ...todos);
  let maximo = Math.max(0, ...todos);
  if (tipo === "linhas") {
    const folga = (maximo - minimo) * 0.1 || Math.abs(maximo) * 0.1 || 1;
    minimo = Math.min(...todos) >= 0 ? Math.max(0, Math.min(...todos) - folga) : Math.min(...todos) - folga;
    maximo += folga;
  }
  if (maximo === minimo) maximo = minimo + 1;

  const altUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const largGrupo = (LARGURA - MARGEM.lado * 2) / anos.length;
  const y = (v) => MARGEM.topo + (1 - (v - minimo) / (maximo - minimo)) * altUtil;
  const centro = (i) => MARGEM.lado + largGrupo * (i + 0.5);
  const zero = y(0);

  // Rótulos dos anos: todos se couberem, senão um sim, um não (sempre o último).
  const passo = anos.length > 7 ? 2 : 1;
  const mostrarAno = (i) => (anos.length - 1 - i) % passo === 0;

  return (
    <div className="grafico-anual">
      <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} role="img" aria-label={series.map((s) => s.nome).join(", ")}>
        {/* faixa do ano selecionado */}
        <rect
          x={centro(selecionado) - largGrupo / 2}
          y={MARGEM.topo - 4}
          width={largGrupo}
          height={altUtil + 8}
          rx="6"
          className="faixa-selecao"
        />
        <line x1={MARGEM.lado} x2={LARGURA - MARGEM.lado} y1={zero} y2={zero} className="linha-zero" />

        {tipo === "barras" &&
          series.map((s, k) => {
            const largBarra = (largGrupo * 0.7) / series.length;
            return s.valores.map((v, i) =>
              v === null || v === undefined ? null : (
                <rect
                  key={`${k}-${i}`}
                  x={centro(i) - (largGrupo * 0.7) / 2 + k * largBarra + 0.5}
                  y={Math.min(y(v), zero)}
                  width={Math.max(largBarra - 1, 1)}
                  height={Math.max(Math.abs(y(v) - zero), 0.5)}
                  rx="2"
                  fill={s.cor}
                  opacity={i === selecionado ? 1 : 0.75}
                />
              )
            );
          })}

        {tipo === "linhas" &&
          series.map((s, k) => {
            const pontos = s.valores.map((v, i) => (v === null || v === undefined ? null : [centro(i), y(v)]));
            let d = "";
            let caneta = false;
            for (const p of pontos) {
              if (!p) {
                caneta = false;
                continue;
              }
              d += `${caneta ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`;
              caneta = true;
            }
            return (
              <g key={k}>
                <path d={d} fill="none" stroke={s.cor} strokeWidth="2.2" strokeLinejoin="round" />
                {pontos.map((p, i) => p && <circle key={i} cx={p[0]} cy={p[1]} r={i === selecionado ? 4 : 2.5} fill={s.cor} />)}
              </g>
            );
          })}

        {anos.map((ano, i) =>
          mostrarAno(i) ? (
            <text key={ano} x={centro(i)} y={ALTURA - 5} textAnchor="middle" className={"rotulo-eixo" + (i === selecionado ? " forte" : "")}>
              {String(ano).slice(2)}
            </text>
          ) : null
        )}

        {/* áreas invisíveis para tocar em cada ano */}
        {anos.map((ano, i) => (
          <rect
            key={`toque-${ano}`}
            x={centro(i) - largGrupo / 2}
            y={0}
            width={largGrupo}
            height={ALTURA}
            fill="transparent"
            onClick={() => setSelecionado(i)}
            onPointerEnter={(e) => e.pointerType === "mouse" && setSelecionado(i)}
          />
        ))}
      </svg>

      <div className="legenda-anual">
        <span className="legenda-ano">{anos[selecionado]}</span>
        {series.map((s) => (
          <span key={s.nome} className="legenda-item">
            <span className="bolinha" style={{ background: s.cor }} />
            {s.nome} <strong>{formatar(s.valores[selecionado])}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}
