import { useEffect, useState } from "react";

// Tela do iPhone 17: 402 x 874 pontos (6,3 polegadas).
const LARGURA = 402;
const ALTURA = 874;
const BORDA = 12; // espessura da moldura preta em volta da tela

/**
 * No computador: desenha um iPhone 17 em volta do app.
 * No iPhone de verdade (tela estreita): a moldura some e o app ocupa a tela toda.
 */
export default function MolduraIphone({ children }) {
  const escala = useEscalaParaCaber();
  const hora = useHoraAtual();

  return (
    <div className="palco">
      <div
        className="iphone"
        style={{
          width: LARGURA + BORDA * 2,
          height: ALTURA + BORDA * 2,
          transform: `scale(${escala})`,
        }}
      >
        <span className="botao-lateral acao" />
        <span className="botao-lateral volume-mais" />
        <span className="botao-lateral volume-menos" />
        <span className="botao-lateral energia" />

        <div className="tela" style={{ width: LARGURA, height: ALTURA }}>
          <div className="protecao-topo" aria-hidden="true" />
          <div className="barra-status" aria-hidden="true">
            <span className="hora">{hora}</span>
            <span className="icones-status">
              <SinalCelular />
              <Wifi />
              <Bateria />
            </span>
          </div>
          <div className="ilha-dinamica" aria-hidden="true" />
          {children}
          <div className="indicador-home" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

// Diminui o iPhone se a janela do navegador for mais baixa que ele.
function useEscalaParaCaber() {
  const calcular = () => {
    if (typeof window === "undefined") return 1;
    const altura = window.innerHeight - 48;
    const largura = window.innerWidth - 48;
    return Math.min(1, altura / (ALTURA + BORDA * 2), largura / (LARGURA + BORDA * 2));
  };
  const [escala, setEscala] = useState(calcular);
  useEffect(() => {
    const aoRedimensionar = () => setEscala(calcular());
    window.addEventListener("resize", aoRedimensionar);
    return () => window.removeEventListener("resize", aoRedimensionar);
  }, []);
  return escala;
}

// Relógio da barra de status (atualiza a cada 20 segundos).
function useHoraAtual() {
  const formatar = () =>
    new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const [hora, setHora] = useState(formatar);
  useEffect(() => {
    const id = setInterval(() => setHora(formatar()), 20000);
    return () => clearInterval(id);
  }, []);
  return hora;
}

function SinalCelular() {
  return (
    <svg width="19" height="12" viewBox="0 0 19 12" fill="currentColor">
      <rect x="0" y="8" width="3.2" height="4" rx="0.8" />
      <rect x="5" y="5.5" width="3.2" height="6.5" rx="0.8" />
      <rect x="10" y="3" width="3.2" height="9" rx="0.8" />
      <rect x="15" y="0" width="3.2" height="12" rx="0.8" />
    </svg>
  );
}

function Wifi() {
  return (
    <svg width="17" height="12" viewBox="0 0 17 12" fill="currentColor">
      <path d="M8.5 2.3c2.4 0 4.6.9 6.3 2.5l1.2-1.2A10.6 10.6 0 0 0 8.5.6 10.6 10.6 0 0 0 1 3.6l1.2 1.2a8.9 8.9 0 0 1 6.3-2.5Z" />
      <path d="M8.5 5.6c1.5 0 2.9.6 4 1.6l1.2-1.2a7.4 7.4 0 0 0-10.4 0l1.2 1.2c1.1-1 2.5-1.6 4-1.6Z" />
      <path d="M8.5 8.9c.7 0 1.3.3 1.8.7L8.5 11.4 6.7 9.6c.5-.4 1.1-.7 1.8-.7Z" />
    </svg>
  );
}

function Bateria() {
  return (
    <svg width="27" height="13" viewBox="0 0 27 13" fill="none">
      <rect x="0.5" y="0.5" width="23" height="12" rx="3.8" stroke="currentColor" opacity="0.4" />
      <rect x="2" y="2" width="17" height="9" rx="2.5" fill="currentColor" />
      <path d="M25 4.5v4c.8-.3 1.4-1.1 1.4-2s-.6-1.7-1.4-2Z" fill="currentColor" opacity="0.45" />
    </svg>
  );
}
