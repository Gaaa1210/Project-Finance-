import { useState } from "react";
import Rosca from "../componentes/Rosca.jsx";
import { Avisos, Cabecalho, FaixaOffline, Rodape, Variacao } from "../componentes/Comuns.jsx";
import { IconeAtualizar } from "../componentes/Icones.jsx";
import { reais, reaisComSinal, corDoValor } from "../formatacao.js";

const AGRUPAMENTOS = [
  { id: "tipo", nome: "Tipo" },
  { id: "setor", nome: "Setor" },
  { id: "ativo", nome: "Ativo" },
];

/** Tela 1 — Início: patrimônio, lucro, variação do dia e alocação. */
export default function Inicio({ carteira, atualizando, aoAtualizar, irPara }) {
  const [agrupamento, setAgrupamento] = useState("tipo");
  const { totais, alocacao, ativos } = carteira;
  const atualizadoAs = new Date(carteira.atualizado_em).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const botaoAtualizar = (
    <button
      type="button"
      className={"botao-redondo" + (atualizando ? " girando" : "")}
      onClick={aoAtualizar}
      aria-label="Atualizar cotações"
    >
      <IconeAtualizar />
    </button>
  );

  if (ativos.length === 0) {
    return (
      <>
        <Cabecalho titulo="Início" acao={botaoAtualizar} />
        <section className="cartao vazio-grande">
          <h2>Sua carteira está vazia</h2>
          <p>Registre a sua primeira compra de ação, ETF ou FII.</p>
          <button type="button" className="botao" onClick={() => irPara("adicionar")}>
            Adicionar compra
          </button>
        </section>
        <Rodape />
      </>
    );
  }

  const lucroDoDiaPct =
    totais.valor_atual - totais.variacao_dia_reais
      ? totais.variacao_dia_reais / (totais.valor_atual - totais.variacao_dia_reais)
      : 0;

  return (
    <>
      <Cabecalho titulo="Início" subtitulo={`Atualizado às ${atualizadoAs}`} acao={botaoAtualizar} />
      <FaixaOffline ativo={carteira.modo_offline} />

      <section className="cartao destaque">
        <p className="rotulo">Patrimônio em renda variável</p>
        <p className="valor-gigante">{reais(totais.valor_atual)}</p>
        <div className="linha-variacoes">
          <div>
            <p className="rotulo">Lucro total</p>
            <Variacao reais={totais.lucro_reais} pct={totais.lucro_pct} pilula />
          </div>
          <div>
            <p className="rotulo">Hoje</p>
            <Variacao reais={totais.variacao_dia_reais} pct={lucroDoDiaPct} pilula />
          </div>
        </div>
      </section>

      <div className="grade-2">
        <section className="cartao mini">
          <p className="rotulo">Total investido</p>
          <p className="valor-medio">{reais(totais.total_investido)}</p>
        </section>
        <section className="cartao mini">
          <p className="rotulo">Proventos recebidos</p>
          <p className={`valor-medio ${corDoValor(totais.dividendos_recebidos)}`}>
            {reaisComSinal(totais.dividendos_recebidos)}
          </p>
        </section>
      </div>

      <section className="cartao">
        <div className="cartao-topo">
          <h2>Alocação</h2>
          <div className="segmentado pequeno">
            {AGRUPAMENTOS.map((a) => (
              <button
                key={a.id}
                type="button"
                className={agrupamento === a.id ? "ativo" : ""}
                onClick={() => setAgrupamento(a.id)}
              >
                {a.nome}
              </button>
            ))}
          </div>
        </div>
        <Rosca key={agrupamento} itens={alocacao[agrupamento]} />
      </section>

      {totais.ativos_sem_cotacao > 0 && (
        <p className="nota">
          {totais.ativos_sem_cotacao} ativo(s) sem cotação ficaram fora do patrimônio e do lucro.
        </p>
      )}

      <section className="cartao em-breve">
        <h2>Em breve</h2>
        <p>
          Renda fixa (CDB, LCI, LCA e Tesouro) entra na Etapa 2 e fundos de investimento na
          Etapa 3. Por enquanto, o patrimônio mostra só ações, ETFs e FIIs.
        </p>
      </section>

      <Avisos avisos={carteira.avisos} />
      <Rodape />
    </>
  );
}
