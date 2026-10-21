import { useCallback, useEffect, useRef, useState } from "react";
import { buscarCarteira, buscarEmpresas } from "./api.js";
import BarraAbas from "./componentes/BarraAbas.jsx";
import { Cabecalho, Carregando, ErroTela } from "./componentes/Comuns.jsx";
import MolduraIphone from "./componentes/MolduraIphone.jsx";
import Adicionar from "./telas/Adicionar.jsx";
import Ativos from "./telas/Ativos.jsx";
import Desempenho from "./telas/Desempenho.jsx";
import Detalhe from "./telas/Detalhe.jsx";
import Inicio from "./telas/Inicio.jsx";
import Noticias from "./telas/Noticias.jsx";
import NoticiasEmpresa from "./telas/NoticiasEmpresa.jsx";

const NOMES_ABAS = {
  inicio: "Início",
  ativos: "Ativos",
  noticias: "Notícias",
  desempenho: "Desempenho",
  adicionar: "Adicionar",
};

/**
 * O "cérebro" das telas: guarda qual aba está aberta, busca os dados no
 * servidor Python e escolhe qual tela mostrar.
 */
export default function App() {
  const [aba, setAba] = useState("inicio");
  // Tela "empurrada" por cima da aba (como no iPhone, com botão de voltar):
  //   { tipo: "ativo", ticker: "PETR4" }    -> detalhe do ativo
  //   { tipo: "noticias", ticker: "PETR4" } -> notícias da empresa
  const [empurrada, setEmpurrada] = useState(null);
  const [carteira, setCarteira] = useState(null);
  const [erro, setErro] = useState(null);
  const [atualizando, setAtualizando] = useState(false);
  const [empresas, setEmpresas] = useState(null);
  const [erroEmpresas, setErroEmpresas] = useState(null);
  const rolagem = useRef(null);

  // Busca a carteira no servidor. useCallback evita recriar a função a cada desenho.
  const carregar = useCallback(async () => {
    setAtualizando(true);
    try {
      setCarteira(await buscarCarteira());
      setErro(null);
    } catch (e) {
      setErro(e.message);
    } finally {
      setAtualizando(false);
    }
  }, []);

  const carregarEmpresas = useCallback(async () => {
    try {
      setEmpresas(await buscarEmpresas());
      setErroEmpresas(null);
    } catch (e) {
      setErroEmpresas(e.message);
    }
  }, []);

  // Busca a carteira assim que o app abre.
  useEffect(() => {
    carregar();
  }, [carregar]);

  // A lista de empresas só é buscada na primeira vez que a aba Notícias abre.
  useEffect(() => {
    if (aba === "noticias" && !empresas) carregarEmpresas();
  }, [aba, empresas, carregarEmpresas]);

  // Volta a rolagem para o topo sempre que trocar de tela.
  useEffect(() => {
    rolagem.current?.scrollTo({ top: 0 });
  }, [aba, empurrada]);

  function trocarAba(nova) {
    setEmpurrada(null);
    setAba(nova);
  }

  function telaAtual() {
    if (empurrada?.tipo === "ativo") {
      return (
        <Detalhe
          ticker={empurrada.ticker}
          rotuloVoltar={NOMES_ABAS[aba]}
          aoVoltar={() => setEmpurrada(null)}
        />
      );
    }
    if (empurrada?.tipo === "noticias") {
      return <NoticiasEmpresa ticker={empurrada.ticker} aoVoltar={() => setEmpurrada(null)} />;
    }
    if (aba === "noticias") {
      return (
        <Noticias
          empresas={empresas}
          erro={erroEmpresas}
          aoTentarDeNovo={carregarEmpresas}
          abrirEmpresa={(ticker) => setEmpurrada({ tipo: "noticias", ticker })}
        />
      );
    }
    if (aba === "adicionar") {
      return <Adicionar carteira={carteira} aoSalvar={carregar} />;
    }
    if (erro && !carteira) {
      return (
        <>
          <Cabecalho titulo={NOMES_ABAS[aba]} />
          <ErroTela mensagem={erro} aoTentarDeNovo={carregar} />
        </>
      );
    }
    if (!carteira) {
      return (
        <>
          <Cabecalho titulo={NOMES_ABAS[aba]} />
          <Carregando texto="Buscando cotações…" />
        </>
      );
    }

    const props = {
      carteira,
      abrirAtivo: (ticker) => setEmpurrada({ tipo: "ativo", ticker }),
      irPara: trocarAba,
    };
    if (aba === "ativos") return <Ativos {...props} />;
    if (aba === "desempenho") return <Desempenho {...props} />;
    return <Inicio {...props} atualizando={atualizando} aoAtualizar={carregar} />;
  }

  const chave = empurrada ? `${empurrada.tipo}-${empurrada.ticker}` : aba;

  return (
    <MolduraIphone>
      <main className="conteudo" ref={rolagem}>
        <div className={"pagina" + (empurrada ? " empurrada" : "")} key={chave}>
          {telaAtual()}
        </div>
      </main>
      <BarraAbas abaAtual={aba} aoTrocar={trocarAba} />
    </MolduraIphone>
  );
}
