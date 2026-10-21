import { useState } from "react";
import { percentual, reais } from "../formatacao.js";

// Cores das fatias (na mesma ordem dos itens, do maior para o menor).
export const CORES = [
  "var(--serie-1)",
  "var(--serie-2)",
  "var(--serie-3)",
  "var(--serie-4)",
  "var(--serie-5)",
  "var(--serie-6)",
];

const RAIO = 78;
const CIRCUNFERENCIA = 2 * Math.PI * RAIO;

/**
 * Gráfico de rosca da alocação.
 * Cada fatia é um círculo com o contorno "tracejado": um traço do tamanho da
 * fatia e um espaço do tamanho do resto. Toque numa fatia para destacá-la.
 */
export default function Rosca({ itens }) {
  const [selecionado, setSelecionado] = useState(null);
  // Mais de 6 grupos: os menores viram "Outros".
  const fatias = agruparPequenos(itens);
  // Total do gráfico = soma das fatias (inclui ativos sem cotação pelo valor investido).
  const total = itens.reduce((soma, item) => soma + item.valor, 0);
  const espaco = fatias.length > 1 ? 3 : 0;

  let inicio = 0;
  const desenhos = fatias.map((item, i) => {
    const tamanho = item.pct * CIRCUNFERENCIA;
    const desenho = {
      ...item,
      cor: CORES[i % CORES.length],
      traco: Math.max(tamanho - espaco, 0.01),
      deslocamento: -inicio,
    };
    inicio += tamanho;
    return desenho;
  });

  const destaque = selecionado !== null ? desenhos[selecionado] : null;

  return (
    <div className="rosca">
      <div className="rosca-grafico">
        <svg viewBox="0 0 200 200" role="img" aria-label="Gráfico de alocação">
          <g transform="rotate(-90 100 100)">
            {desenhos.map((d, i) => (
              <circle
                key={d.nome}
                cx="100"
                cy="100"
                r={RAIO}
                fill="none"
                stroke={d.cor}
                strokeWidth={selecionado === i ? 26 : 20}
                strokeDasharray={`${d.traco} ${CIRCUNFERENCIA}`}
                strokeDashoffset={d.deslocamento}
                opacity={selecionado === null || selecionado === i ? 1 : 0.3}
                className="fatia"
                onClick={() => setSelecionado(selecionado === i ? null : i)}
              />
            ))}
          </g>
        </svg>
        <div className="rosca-centro">
          <span className="rosca-centro-rotulo">{destaque ? destaque.nome : "Total"}</span>
          <strong>{destaque ? percentual(destaque.pct, false) : reais(total)}</strong>
          {destaque && <span className="rosca-centro-rotulo">{reais(destaque.valor)}</span>}
        </div>
      </div>

      <ul className="legenda">
        {desenhos.map((d, i) => (
          <li
            key={d.nome}
            className={selecionado === i ? "selecionado" : ""}
            onClick={() => setSelecionado(selecionado === i ? null : i)}
          >
            <span className="bolinha" style={{ background: d.cor }} />
            <span className="legenda-nome">{d.nome}</span>
            <span className="legenda-pct">{percentual(d.pct, false)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function agruparPequenos(itens, maximo = 6) {
  if (itens.length <= maximo) return itens;
  const principais = itens.slice(0, maximo - 1);
  const resto = itens.slice(maximo - 1);
  return [
    ...principais,
    {
      nome: "Outros",
      valor: resto.reduce((s, i) => s + i.valor, 0),
      pct: resto.reduce((s, i) => s + i.pct, 0),
    },
  ];
}
