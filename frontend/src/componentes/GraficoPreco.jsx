import { useMemo, useRef, useState } from "react";
import { dataBR, mesAno, reais } from "../formatacao.js";

const LARGURA = 350;
const ALTURA = 200;
const MARGEM = { topo: 16, base: 22, esquerda: 4, direita: 4 };

const PERIODOS = [
  { id: "1M", dias: 31 },
  { id: "6M", dias: 183 },
  { id: "1A", dias: 365 },
  { id: "Tudo", dias: null },
];

/**
 * Gráfico de linha do preço, com:
 *  - linha tracejada no seu preço médio;
 *  - bolinhas nos dias em que você comprou;
 *  - arraste o dedo (ou o mouse) para ver o preço de cada dia.
 */
export default function GraficoPreco({ pontos, precoMedio, compras }) {
  const [periodo, setPeriodo] = useState("Tudo");
  const [indiceToque, setIndiceToque] = useState(null);
  const svgRef = useRef(null);

  // Filtra os pontos do período escolhido.
  const visiveis = useMemo(() => {
    const dias = PERIODOS.find((p) => p.id === periodo).dias;
    if (!dias || pontos.length === 0) return pontos;
    const ultimo = new Date(pontos[pontos.length - 1].data);
    const corte = new Date(ultimo.getTime() - dias * 86400000);
    return pontos.filter((p) => new Date(p.data) >= corte);
  }, [pontos, periodo]);

  if (visiveis.length < 2) {
    return <p className="vazio">Sem histórico de preços para mostrar.</p>;
  }

  // Escalas: transformam (data, preço) em (x, y) dentro do desenho.
  const precos = visiveis.map((p) => p.preco);
  let minimo = Math.min(...precos, precoMedio ?? Infinity);
  let maximo = Math.max(...precos, precoMedio ?? -Infinity);
  const folga = (maximo - minimo) * 0.08 || 1;
  minimo -= folga;
  maximo += folga;

  const largUtil = LARGURA - MARGEM.esquerda - MARGEM.direita;
  const altUtil = ALTURA - MARGEM.topo - MARGEM.base;
  const x = (i) => MARGEM.esquerda + (i / (visiveis.length - 1)) * largUtil;
  const y = (preco) => MARGEM.topo + (1 - (preco - minimo) / (maximo - minimo)) * altUtil;

  const linha = visiveis.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.preco).toFixed(1)}`).join("");
  const area = `${linha}L${x(visiveis.length - 1)},${ALTURA - MARGEM.base}L${x(0)},${ALTURA - MARGEM.base}Z`;

  const ultimoPreco = precos[precos.length - 1];
  const subiu = precoMedio == null || ultimoPreco >= precoMedio;
  const cor = subiu ? "var(--positivo)" : "var(--negativo)";

  // Bolinhas das compras: acha o dia do gráfico mais próximo de cada compra.
  const marcadores = (compras || [])
    .map((c) => visiveis.findIndex((p) => p.data >= c.data))
    .filter((i) => i >= 0);

  // Rótulos de mês no eixo de baixo (3 rótulos: começo, meio e fim).
  const rotulos = [0, Math.floor((visiveis.length - 1) / 2), visiveis.length - 1];

  function aoMover(evento) {
    const caixa = svgRef.current.getBoundingClientRect();
    const proporcao = (evento.clientX - caixa.left) / caixa.width;
    const xNoDesenho = proporcao * LARGURA;
    const i = Math.round(((xNoDesenho - MARGEM.esquerda) / largUtil) * (visiveis.length - 1));
    setIndiceToque(Math.min(Math.max(i, 0), visiveis.length - 1));
  }

  const toque = indiceToque !== null ? visiveis[indiceToque] : null;

  return (
    <div className="grafico-preco">
      <div className="grafico-leitura">
        {toque ? (
          <>
            <strong>{reais(toque.preco)}</strong>
            <span>{dataBR(toque.data)}</span>
          </>
        ) : (
          <span className="dica">Arraste no gráfico para ver cada dia</span>
        )}
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        className="grafico-svg"
        onPointerMove={aoMover}
        onPointerDown={aoMover}
        onPointerLeave={() => setIndiceToque(null)}
        role="img"
        aria-label="Gráfico do preço do ativo"
      >
        <defs>
          <linearGradient id="preenchimento" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={cor} stopOpacity="0.28" />
            <stop offset="1" stopColor={cor} stopOpacity="0" />
          </linearGradient>
        </defs>

        <path d={area} fill="url(#preenchimento)" />
        <path d={linha} fill="none" stroke={cor} strokeWidth="2.2" strokeLinejoin="round" />

        {precoMedio != null && (
          <g>
            <line
              x1={MARGEM.esquerda}
              x2={LARGURA - MARGEM.direita}
              y1={y(precoMedio)}
              y2={y(precoMedio)}
              className="linha-preco-medio"
            />
            <text x={MARGEM.esquerda + 2} y={y(precoMedio) - 5} className="rotulo-preco-medio">
              Preço médio {reais(precoMedio)}
            </text>
          </g>
        )}

        {marcadores.map((i, n) => (
          <circle key={n} cx={x(i)} cy={y(visiveis[i].preco)} r="4.5" className="marcador-compra" />
        ))}

        {toque && (
          <g>
            <line x1={x(indiceToque)} x2={x(indiceToque)} y1={MARGEM.topo - 6} y2={ALTURA - MARGEM.base} className="linha-toque" />
            <circle cx={x(indiceToque)} cy={y(toque.preco)} r="5" fill={cor} stroke="var(--cartao)" strokeWidth="2" />
          </g>
        )}

        {rotulos.map((i, n) => (
          <text
            key={n}
            x={x(i)}
            y={ALTURA - 5}
            textAnchor={n === 0 ? "start" : n === 2 ? "end" : "middle"}
            className="rotulo-eixo"
          >
            {mesAno(visiveis[i].data)}
          </text>
        ))}
      </svg>

      <div className="segmentado pequeno" role="tablist">
        {PERIODOS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={periodo === p.id ? "ativo" : ""}
            onClick={() => setPeriodo(p.id)}
          >
            {p.id}
          </button>
        ))}
      </div>

      <p className="legenda-grafico">
        <span className="bolinha-compra" /> suas compras
        <span className="traco-medio" /> seu preço médio
      </p>
    </div>
  );
}
