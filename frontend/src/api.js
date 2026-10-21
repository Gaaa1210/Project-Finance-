// Conversa com o servidor Python (FastAPI).
// O Vite repassa tudo que começa com /api para http://localhost:8000 (ver vite.config.js).

async function pedir(caminho, opcoes) {
  let resposta;
  try {
    resposta = await fetch(caminho, opcoes);
  } catch {
    throw new Error(SERVIDOR_DESLIGADO);
  }

  // Tenta ler a resposta como JSON. Se o servidor Python estiver desligado,
  // o Vite responde com uma página vazia e o JSON falha.
  let corpo = null;
  try {
    corpo = await resposta.json();
  } catch {
    corpo = null;
  }

  if (!resposta.ok) {
    if (corpo === null) throw new Error(SERVIDOR_DESLIGADO);
    const detalhe = corpo.detail;
    if (typeof detalhe === "string") throw new Error(detalhe);
    // Erro 422: o FastAPI recusou algum campo do formulário.
    throw new Error("Confira os campos: algum valor não está no formato certo.");
  }
  return corpo;
}

const SERVIDOR_DESLIGADO =
  "Não consegui falar com o servidor Python. Ele está ligado? " +
  "Rode 'python3 api.py' na pasta backend.";

export function buscarCarteira() {
  return pedir("/api/carteira");
}

export function buscarAtivo(ticker) {
  return pedir(`/api/ativos/${encodeURIComponent(ticker)}`);
}

export function enviarCompra(compra) {
  return pedir("/api/compras", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(compra),
  });
}

export function buscarEmpresas() {
  return pedir("/api/empresas");
}

export function buscarNoticias(ticker) {
  return pedir(`/api/noticias/${encodeURIComponent(ticker)}`);
}
