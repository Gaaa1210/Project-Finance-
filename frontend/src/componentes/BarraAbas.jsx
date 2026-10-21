import { IconeAdicionar, IconeAtivos, IconeDesempenho, IconeInicio, IconeNoticias } from "./Icones.jsx";

const ABAS = [
  { id: "inicio", nome: "Início", Icone: IconeInicio },
  { id: "ativos", nome: "Ativos", Icone: IconeAtivos },
  { id: "noticias", nome: "Notícias", Icone: IconeNoticias },
  { id: "desempenho", nome: "Desempenho", Icone: IconeDesempenho },
  { id: "adicionar", nome: "Adicionar", Icone: IconeAdicionar },
];

/** Barra de abas no rodapé, no estilo do iOS. */
export default function BarraAbas({ abaAtual, aoTrocar }) {
  return (
    <nav className="barra-abas" aria-label="Navegação">
      {ABAS.map(({ id, nome, Icone }) => (
        <button
          key={id}
          type="button"
          className={"aba" + (abaAtual === id ? " ativa" : "")}
          aria-current={abaAtual === id ? "page" : undefined}
          onClick={() => aoTrocar(id)}
        >
          <Icone />
          <span>{nome}</span>
        </button>
      ))}
    </nav>
  );
}
