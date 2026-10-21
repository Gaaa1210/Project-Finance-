import { useEffect, useRef, useState } from "react";
import { recalcularValuation } from "../../api.js";
import { IconeInfo } from "../../componentes/Icones.jsx";
import { corDoValor, percentual, reais, reaisCompacto, vezes } from "../../formatacao.js";

const CENARIOS = [
  { id: "negativo", nome: "Negativo" },
  { id: "neutro", nome: "Neutro" },
  { id: "positivo", nome: "Positivo" },
];

// Controles de cada premissa: nome, faixa do controle deslizante e passo.
const CAMPOS_EMPRESA = [
  { id: "crescimento", nome: "Crescimento da receita (anos 1–5)", min: -0.1, max: 0.3, passo: 0.005 },
  { id: "margem_ebit", nome: "Margem EBIT", min: -0.1, max: 0.6, passo: 0.005 },
  { id: "capex_receita", nome: "Capex / receita", min: 0, max: 0.4, passo: 0.005 },
  { id: "depreciacao_receita", nome: "Depreciação / receita", min: 0, max: 0.3, passo: 0.005 },
  { id: "capital_giro_receita", nome: "Capital de giro / receita", min: -0.3, max: 0.5, passo: 0.01 },
  { id: "aliquota_ir", nome: "Alíquota de IR", min: 0, max: 0.34, passo: 0.01 },
  { id: "wacc", nome: "WACC (taxa de desconto)", min: 0.05, max: 0.25, passo: 0.0025 },
  { id: "crescimento_perpetuo", nome: "Crescimento na perpetuidade", min: 0, max: 0.08, passo: 0.0025 },
];
const CAMPOS_FINANCEIRA = [
  { id: "roe", nome: "ROE de longo prazo", min: 0, max: 0.4, passo: 0.005 },
  { id: "custo_acionista", nome: "Custo de capital (Ke)", min: 0.05, max: 0.25, passo: 0.0025 },
  { id: "crescimento_perpetuo", nome: "Crescimento na perpetuidade", min: 0, max: 0.08, passo: 0.0025 },
];

const PESOS_PADRAO = { negativo: 25, neutro: 50, positivo: 25 };

/** Seção "Valuation" da página da empresa. */
export default function AbaValuation({ analise }) {
  const v = analise.valuation;
  const financeira = analise.empresa.financeira;
  const campos = financeira ? CAMPOS_FINANCEIRA : CAMPOS_EMPRESA;
  const sugeridas = v.premissas.cenarios;

  const [cenarios, setCenarios] = useState(sugeridas);
  const [pesos, setPesos] = useState(PESOS_PADRAO);
  const [resultado, setResultado] = useState(v);
  const [editando, setEditando] = useState("neutro");
  const [recalculando, setRecalculando] = useState(false);
  const [erro, setErro] = useState(null);
  const pedidoAtual = useRef(0);
  const alterado = JSON.stringify(cenarios) !== JSON.stringify(sugeridas) || JSON.stringify(pesos) !== JSON.stringify(PESOS_PADRAO);

  // Recalcula no servidor 0,35 s depois da última mudança (para não pedir a cada milímetro do controle).
  useEffect(() => {
    const numero = ++pedidoAtual.current;
    if (!alterado) {
      // Premissas sugeridas: o resultado já veio pronto com a análise.
      setResultado(v);
      setRecalculando(false);
      setErro(null);
      return;
    }
    setRecalculando(true);
    const espera = setTimeout(() => {
      const pesosFracao = Object.fromEntries(Object.entries(pesos).map(([k, p]) => [k, p / 100]));
      recalcularValuation(analise.empresa.ticker, cenarios, pesosFracao)
        .then((r) => {
          if (numero !== pedidoAtual.current) return; // chegou uma resposta antiga: ignora
          setResultado({ ...v, ...r });
          setErro(null);
        })
        .catch((e) => numero === pedidoAtual.current && setErro(e.message))
        .finally(() => numero === pedidoAtual.current && setRecalculando(false));
    }, 350);
    return () => clearTimeout(espera);
  }, [cenarios, pesos]);

  function mudarPremissa(campo, valor) {
    setCenarios({ ...cenarios, [editando]: { ...cenarios[editando], [campo]: valor } });
  }

  const preco = v.base.preco;
  const res = resultado.resultados;

  return (
    <>
      <section className="cartao preco-justo">
        <div className="preco-justo-topo">
          <div>
            <p className="rotulo">Preço justo ponderado</p>
            <p className="valor-gigante">{reais(resultado.preco_ponderado)}</p>
          </div>
          {recalculando && <span className="rodinha pequena" aria-label="Recalculando" />}
        </div>
        <p className="preco-justo-linha">
          Preço atual {reais(preco)}
          {resultado.potencial_ponderado !== null && resultado.potencial_ponderado !== undefined && (
            <span className={`variacao pilula ${corDoValor(resultado.potencial_ponderado)}`}>
              {percentual(resultado.potencial_ponderado)} de potencial
            </span>
          )}
        </p>
        <Regua resultados={res} preco={preco} />
        <div className="cenarios-resumo">
          {CENARIOS.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`cenario-mini cenario-${c.id}${editando === c.id ? " ativo" : ""}`}
              onClick={() => setEditando(c.id)}
            >
              <span>{c.nome}</span>
              <strong>{reais(res[c.id]?.preco_justo)}</strong>
              <small className={corDoValor(res[c.id]?.potencial)}>{percentual(res[c.id]?.potencial)}</small>
            </button>
          ))}
        </div>
        {Object.entries(resultado.erros || {}).map(([nome, mensagem]) => (
          <p key={nome} className="mensagem erro">Cenário {nome}: {mensagem}</p>
        ))}
        {erro && <p className="mensagem erro">{erro}</p>}
        {resultado.margem_seguranca !== null && resultado.margem_seguranca !== undefined && (
          <p className="nota">
            Margem de segurança: no cenário negativo a ação valeria{" "}
            <strong className={corDoValor(resultado.margem_seguranca)}>
              {percentual(Math.abs(resultado.margem_seguranca), false)} {resultado.margem_seguranca >= 0 ? "acima" : "abaixo"}
            </strong>{" "}
            do preço atual.
          </p>
        )}
      </section>

      <Reverso reverso={resultado.reverso} financeira={financeira} analise={analise} />

      <section className="cartao">
        <div className="cartao-topo">
          <h2>Premissas</h2>
          {alterado && (
            <button type="button" className="botao-texto" onClick={() => { setCenarios(sugeridas); setPesos(PESOS_PADRAO); }}>
              Restaurar sugestões
            </button>
          )}
        </div>
        <div className="segmentado" role="tablist">
          {CENARIOS.map((c) => (
            <button key={c.id} type="button" className={editando === c.id ? "ativo" : ""} onClick={() => setEditando(c.id)}>
              {c.nome}
            </button>
          ))}
        </div>
        <div className="lista-premissas">
          {campos.map((campo) => (
            <ControlePremissa
              key={campo.id}
              campo={campo}
              valor={cenarios[editando][campo.id]}
              sugerido={sugeridas[editando][campo.id]}
              origem={v.premissas.origem[campo.id]}
              aoMudar={(valor) => mudarPremissa(campo.id, valor)}
            />
          ))}
        </div>

        <h3 className="subtitulo">Peso de cada cenário</h3>
        {CENARIOS.map((c) => (
          <label key={c.id} className="controle-peso">
            <span>{c.nome}</span>
            <input type="range" min="0" max="100" step="5" value={pesos[c.id]}
                   onChange={(e) => setPesos({ ...pesos, [c.id]: Number(e.target.value) })} />
            <strong>{pesos[c.id]}</strong>
          </label>
        ))}
        <p className="nota">Os pesos não precisam somar 100: o app divide pelo total.</p>
      </section>

      {!financeira && res[editando] && <ContaAnoAno resultado={res[editando]} base={v.base} cenario={editando} premissas={cenarios[editando]} />}
      {financeira && res[editando] && (
        <section className="cartao">
          <h2>Como chegamos ao preço ({CENARIOS.find((c) => c.id === editando).nome.toLowerCase()})</h2>
          <ul className="lista-simples">
            <li><span>P/VP justo = (ROE − g) ÷ (Ke − g)</span><strong>{vezes(res[editando].pvp_justo, 2)}</strong></li>
            <li><span>Patrimônio líquido</span><strong>{reaisCompacto(v.base.patrimonio_liquido)}</strong></li>
            <li><span>Valor justo das ações</span><strong>{reaisCompacto(res[editando].valor_acoes)}</strong></li>
            <li className="total"><span>Preço justo por ação</span><strong>{reais(res[editando].preco_justo)}</strong></li>
          </ul>
        </section>
      )}

      <Sensibilidade dados={resultado.sensibilidade} preco={preco} financeira={financeira} />
      <CustoDeCapital valuation={v} financeira={financeira} />

      <details className="cartao metodo">
        <summary>Como o valuation é calculado</summary>
        {financeira ? (
          <p>
            Para bancos e seguradoras usamos o modelo de Gordon: um banco que rende ROE sobre o
            patrimônio e cresce g para sempre vale P/VP = (ROE − g) ÷ (Ke − g), onde Ke é o retorno
            que o acionista exige. Preço justo = valor patrimonial por ação × P/VP justo.
          </p>
        ) : (
          <>
            <p>
              Fluxo de caixa descontado: projetamos 5 anos de receita, margem e investimentos; o caixa
              livre de cada ano (lucro operacional após IR + depreciação − capex − aumento do capital de
              giro) é trazido a valor de hoje pelo WACC. Depois do 5º ano, a empresa cresce para sempre na
              taxa de perpetuidade (valor terminal).
            </p>
            <p>Valor da empresa − dívida líquida = valor das ações. Dividido pela quantidade de ações = preço justo.</p>
          </>
        )}
        <p>
          As premissas sugeridas vêm do histórico da própria empresa (toque no ⓘ de cada uma). Valuation
          é uma estimativa e não é recomendação de investimento.
        </p>
      </details>
    </>
  );
}

/** Régua horizontal com os 3 preços justos e o preço atual. */
function Regua({ resultados, preco }) {
  const pontos = CENARIOS.map((c) => ({ ...c, valor: resultados[c.id]?.preco_justo })).filter((p) => p.valor !== null && p.valor !== undefined);
  if (!pontos.length || !preco) return null;
  const valores = [...pontos.map((p) => p.valor), preco];
  let min = Math.min(...valores);
  let max = Math.max(...valores);
  const folga = (max - min) * 0.12 || max * 0.1 || 1;
  min -= folga;
  max += folga;
  const pos = (valor) => `${((valor - min) / (max - min)) * 100}%`;
  return (
    <div className="regua" aria-hidden="true">
      <div className="regua-trilho">
        <span className="regua-faixa" style={{ left: pos(Math.min(...pontos.map((p) => p.valor))), right: `calc(100% - ${pos(Math.max(...pontos.map((p) => p.valor)))})` }} />
        {pontos.map((p) => (
          <span key={p.id} className={`regua-marca cenario-${p.id}`} style={{ left: pos(p.valor) }} />
        ))}
        <span className="regua-preco" style={{ left: pos(preco) }}>
          <span>hoje</span>
        </span>
      </div>
    </div>
  );
}

function ControlePremissa({ campo, valor, sugerido, origem, aoMudar }) {
  const [mostrarOrigem, setMostrarOrigem] = useState(false);
  // A faixa do controle se estende se o valor sugerido estiver fora dela.
  const min = Math.min(campo.min, valor, sugerido);
  const max = Math.max(campo.max, valor, sugerido);
  const mudou = Math.abs(valor - sugerido) > 1e-9;
  return (
    <div className="controle-premissa">
      <div className="controle-topo">
        <span>
          {campo.nome}
          <button type="button" className="botao-info" onClick={() => setMostrarOrigem(!mostrarOrigem)} aria-label="De onde vem esta premissa">
            <IconeInfo />
          </button>
        </span>
        <strong className={mudou ? "alterado" : ""}>{percentual(valor, false)}</strong>
      </div>
      <input type="range" min={min} max={max} step={campo.passo} value={valor} onChange={(e) => aoMudar(Number(e.target.value))} />
      {mostrarOrigem && (
        <p className="origem-premissa">
          {origem} Sugerido: {percentual(sugerido, false)}.
          {mudou && <button type="button" className="botao-texto" onClick={() => aoMudar(sugerido)}>Voltar ao sugerido</button>}
        </p>
      )}
    </div>
  );
}

function Reverso({ reverso, financeira, analise }) {
  if (!reverso) return null;
  const valor = reverso.valor_implicito;
  const historico = financeira
    ? analise.valuation.premissas.cenarios.neutro.roe
    : analise.valuation.premissas.cenarios.neutro.crescimento;
  const diferenca = valor - historico;
  let leitura;
  if (reverso.fora_do_intervalo === "acima") leitura = "O preço atual exige mais que isso: o mercado está muito otimista, ou as outras premissas estão conservadoras.";
  else if (reverso.fora_do_intervalo === "abaixo") leitura = "Mesmo com receita encolhendo, a ação estaria barata pelas outras premissas.";
  else if (diferenca > 0.03) leitura = "O mercado espera mais do que a empresa costuma entregar: há otimismo no preço.";
  else if (diferenca < -0.03) leitura = "O mercado espera menos do que a empresa costuma entregar: há pessimismo no preço.";
  else leitura = "O mercado espera algo parecido com o histórico da empresa.";
  return (
    <section className="cartao reverso">
      <h2>O que o preço atual supõe?</h2>
      <p className="reverso-numero">
        {reverso.fora_do_intervalo ? (reverso.fora_do_intervalo === "acima" ? "mais de " : "menos de ") : ""}
        <strong>{percentual(valor, false)}</strong>
        <span>{financeira ? " de ROE para sempre" : " de crescimento da receita por ano, por 5 anos"}</span>
      </p>
      <p className="reverso-comparacao">
        {financeira ? "ROE histórico (mediana)" : "Histórico da empresa (mediana)"}: {percentual(historico, false)}
      </p>
      <p className="nota">{leitura} (Mantendo as demais premissas do cenário neutro.)</p>
    </section>
  );
}

function ContaAnoAno({ resultado: r, base, cenario, premissas }) {
  const nome = CENARIOS.find((c) => c.id === cenario).nome.toLowerCase();
  return (
    <section className="cartao">
      <h2>Como chegamos ao preço ({nome})</h2>
      <div className="tabela-rolavel">
        <table className="tabela-projecao">
          <thead>
            <tr>
              <th />
              {r.projecao.map((a) => <th key={a.ano}>Ano {a.ano}</th>)}
            </tr>
          </thead>
          <tbody>
            <LinhaTabela nome="Receita" valores={r.projecao.map((a) => a.receita)} />
            <LinhaTabela nome="EBIT" valores={r.projecao.map((a) => a.ebit)} />
            <LinhaTabela nome="(−) IR" valores={r.projecao.map((a) => a.nopat - a.ebit)} />
            <LinhaTabela nome="(+) Depreciação" valores={r.projecao.map((a) => a.depreciacao)} />
            <LinhaTabela nome="(−) Capex" valores={r.projecao.map((a) => -a.capex)} />
            <LinhaTabela nome="(±) Capital de giro" valores={r.projecao.map((a) => -a.variacao_capital_giro)} />
            <LinhaTabela nome="Caixa livre" valores={r.projecao.map((a) => a.fluxo_caixa_livre)} destaque />
            <LinhaTabela nome="Valor de hoje" valores={r.projecao.map((a) => a.valor_presente)} />
          </tbody>
        </table>
      </div>
      <ul className="lista-simples">
        <li><span>Soma dos 5 anos (a valor de hoje)</span><strong>{reaisCompacto(r.soma_valor_presente)}</strong></li>
        <li><span>(+) Valor terminal a valor de hoje</span><strong>{reaisCompacto(r.valor_presente_terminal)}</strong></li>
        <li><span>= Valor da empresa (EV)</span><strong>{reaisCompacto(r.valor_empresa)}</strong></li>
        <li><span>(−) Dívida líquida</span><strong>{reaisCompacto(base.divida_liquida)}</strong></li>
        <li><span>= Valor das ações</span><strong>{reaisCompacto(r.valor_acoes)}</strong></li>
        <li><span>÷ Ações em circulação</span><strong>{base.acoes ? (base.acoes / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mi" : "—"}</strong></li>
        <li className="total"><span>Preço justo por ação</span><strong>{reais(r.preco_justo)}</strong></li>
      </ul>
      {r.capex_perpetuidade > premissas.capex_receita + 1e-9 && (
        <p className="nota">
          Depois do 5º ano, o capex usado é {percentual(r.capex_perpetuidade, false)} da receita (igual à depreciação):
          uma empresa que cresce para sempre não pode investir menos do que o desgaste dos seus ativos.
        </p>
      )}
      {r.peso_terminal > 0.75 && (
        <p className="mensagem aviso">
          {percentual(r.peso_terminal, false)} do valor vem do período depois do 5º ano. Quanto maior essa parte,
          mais o resultado depende do WACC e da perpetuidade ({percentual(premissas.crescimento_perpetuo, false)}).
        </p>
      )}
    </section>
  );
}

function LinhaTabela({ nome, valores, destaque = false }) {
  return (
    <tr className={destaque ? "destaque" : ""}>
      <th>{nome}</th>
      {valores.map((v, i) => <td key={i}>{reaisCompacto(v).replace("R$ ", "")}</td>)}
    </tr>
  );
}

function Sensibilidade({ dados, preco, financeira }) {
  if (!dados) return null;
  const nomeTaxa = financeira ? "Ke" : "WACC";
  return (
    <section className="cartao">
      <h2>Sensibilidade (cenário neutro)</h2>
      <p className="nota">
        Preço justo mudando o {nomeTaxa} (linhas) e a perpetuidade (colunas). Verde = acima do preço atual.
      </p>
      <div className="tabela-rolavel">
        <table className="tabela-sensibilidade">
          <thead>
            <tr>
              <th>{nomeTaxa} ↓ · g →</th>
              {dados.crescimentos.map((g, j) => <th key={j}>{percentual(g, false)}</th>)}
            </tr>
          </thead>
          <tbody>
            {dados.taxas.map((taxa, i) => (
              <tr key={i}>
                <th>{percentual(taxa, false)}</th>
                {dados.precos[i].map((p, j) => (
                  <td key={j} className={(i === 2 && j === 2 ? "centro " : "") + (p === null ? "" : preco && p >= preco ? "acima" : "abaixo")}>
                    {p === null ? "—" : reais(p).replace("R$ ", "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CustoDeCapital({ valuation: v, financeira }) {
  const m = v.mercado;
  const w = v.premissas.wacc_detalhe;
  return (
    <section className="cartao">
      <h2>Custo de capital</h2>
      <ul className="lista-simples custo-capital">
        <li><span>Taxa livre de risco<small>{m.fontes.taxa_livre_risco}</small></span><strong>{percentual(m.taxa_livre_risco, false)}</strong></li>
        <li><span>Beta<small>{m.fontes.beta}</small></span><strong>{m.beta.toFixed(2).replace(".", ",")}</strong></li>
        <li><span>Prêmio de risco do mercado<small>{m.fontes.premio_risco}</small></span><strong>{percentual(m.premio_risco, false)}</strong></li>
        <li><span>Custo do acionista (Ke)<small>taxa livre + beta × prêmio</small></span><strong>{percentual(w.custo_acionista, false)}</strong></li>
        {!financeira && (
          <>
            <li><span>Custo da dívida (antes do IR)<small>{m.fontes.spread_divida}</small></span><strong>{percentual(w.custo_divida, false)}</strong></li>
            <li><span>Peso da dívida<small>dívida bruta ÷ (dívida + valor de mercado)</small></span><strong>{percentual(w.peso_divida, false)}</strong></li>
            <li className="total"><span>WACC (cenário neutro)</span><strong>{percentual(w.wacc, false)}</strong></li>
          </>
        )}
      </ul>
    </section>
  );
}
