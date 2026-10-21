import { useCallback, useEffect, useRef, useState } from "react";
import { buscarCarteira, buscarEmpresas } from "./api.js";
import BarraAbas from "./componentes/BarraAbas.jsx";
import { Cabecalho, Carregando, ErroTela } from "./componentes/Comuns.jsx";
import MolduraIphone from "./componentes/MolduraIphone.jsx";
import Adicionar from "./telas/Adicionar.jsx";
import Ativos from "./telas/Ativos.jsx";
import Desempenho from "./telas/Desempenho.jsx";
import Detalhe from "./telas/Detalhe.jsx";
import Empresa from "./telas/Empresa.jsx";
import Inicio from "./telas/Inicio.jsx";
import Noticias from "./telas/Noticias.jsx";

const NOMES_ABAS = {
  inicio: "Início",
  ativos: "Ativos",
  empresas: "Empresas",
  desempenho: "Desempenho",
  adicionar: "Adicionar",
};

/**
 * O "cérebro" das telas: guarda qual aba está aberta, busca os dados no
 * servidor Python e escolhe qual tela mostrar.
 */
export default function App() {
  const [aba, setAba] = useState("inicio");
  // Pilha de telas "empurradas" por cima da aba (como no iPhone, com botão de voltar).
  // Ex.: [{ tipo: "ativo", ticker: "PETR4" }, { tipo: "empresa", ticker: "PETR4" }]
  // A última da lista é a que aparece. "Voltar" tira a última.
  const [pilha, setPilha] = useState([]);
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

  // A lista de empresas só é buscada na primeira vez que a aba Empresas abre.
  useEffect(() => {
    if (aba === "empresas" && !empresas) carregarEmpresas();
  }, [aba, empresas, carregarEmpresas]);

  // Volta a rolagem para o topo sempre que trocar de tela.
  useEffect(() => {
    rolagem.current?.scrollTo({ top: 0 });
  }, [aba, pilha.length]);

  function trocarAba(nova) {
    setPilha([]);
    setAba(nova);
  }

  const abrir = (tela) => setPilha((atual) => [...atual, tela]);
  const voltar = () => setPilha((atual) => atual.slice(0, -1));
  const abrirAtivo = (ticker) => abrir({ tipo: "ativo", ticker });
  const abrirEmpresa = (empresa) => abrir({ tipo: "empresa", ticker: empresa.ticker, empresa });

  // Nome que aparece no botão "voltar" (a tela de baixo na pilha, ou a aba).
  function rotuloVoltar() {
    const anterior = pilha[pilha.length - 2];
    if (!anterior) return NOMES_ABAS[aba];
    return anterior.ticker;
  }

  function telaAtual() {
    const topo = pilha[pilha.length - 1];
    if (topo?.tipo === "ativo") {
      return <Detalhe ticker={topo.ticker} rotuloVoltar={rotuloVoltar()} aoVoltar={voltar} aoAbrirEmpresa={abrirEmpresa} />;
    }
    if (topo?.tipo === "empresa") {
      const ehFii = topo.empresa?.setor?.startsWith("FII");
      return (
        <Empresa
          ticker={topo.ticker}
          empresa={topo.empresa}
          rotuloVoltar={rotuloVoltar()}
          aoVoltar={voltar}
          secaoInicial={ehFii ? "Notícias" : "Análise"}
        />
      );
    }
    if (aba === "empresas") {
      return <Noticias empresas={empresas} erro={erroEmpresas} aoTentarDeNovo={carregarEmpresas} abrirEmpresa={abrirEmpresa} />;
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

    const props = { carteira, abrirAtivo, irPara: trocarAba };
    if (aba === "ativos") return <Ativos {...props} />;
    if (aba === "desempenho") return <Desempenho {...props} />;
    return <Inicio {...props} atualizando={atualizando} aoAtualizar={carregar} />;
  }

  const topo = pilha[pilha.length - 1];
  const chave = topo ? `${pilha.length}-${topo.tipo}-${topo.ticker}` : aba;

  return (
    <MolduraIphone>
      <main className="conteudo" ref={rolagem}>
        <div className={"pagina" + (topo ? " empurrada" : "")} key={chave}>
          {telaAtual()}
        </div>
      </main>
      <BarraAbas abaAtual={aba} aoTrocar={trocarAba} />
    </MolduraIphone>
  );
}
