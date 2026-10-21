// Números e datas no formato brasileiro.
// Lembrete: percentuais chegam do Python como fração (0.10 = 10%).

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function valido(valor) {
  return typeof valor === "number" && Number.isFinite(valor);
}

// 1234.5 -> "R$ 1.234,50"
export function reais(valor) {
  return valido(valor) ? moeda.format(valor).replace(/ /g, " ") : "—";
}

// 120.3 -> "+R$ 120,30" (com sinal, para lucro e variação)
export function reaisComSinal(valor) {
  if (!valido(valor)) return "—";
  const sinal = valor > 0 ? "+" : valor < 0 ? "−" : "";
  return sinal + reais(Math.abs(valor));
}

// 0.1234 -> "+12,34%"
export function percentual(valor, comSinal = true) {
  if (!valido(valor)) return "—";
  const sinal = comSinal && valor > 0 ? "+" : valor < 0 ? "−" : "";
  return sinal + (Math.abs(valor) * 100).toFixed(2).replace(".", ",") + "%";
}

// 150 -> "150" | 10.5 -> "10,5"
export function numero(valor) {
  if (!valido(valor)) return "—";
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

// "2025-03-10" -> "10/03/2025"
export function dataBR(iso) {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

// "2025-03-10" -> "mar. 2025"
export function mesAno(iso) {
  const data = new Date(iso + "T12:00:00");
  return data.toLocaleDateString("pt-BR", { month: "short", year: "numeric" });
}

// Classe CSS para pintar de verde (positivo) ou vermelho (negativo).
export function corDoValor(valor) {
  if (!valido(valor) || valor === 0) return "neutro";
  return valor > 0 ? "positivo" : "negativo";
}

// Aceita "36,50", "36.50" ou "1.234,56" digitados no formulário.
export function lerNumero(texto) {
  if (texto === null || texto === undefined) return NaN;
  let limpo = String(texto).trim().replace(/R\$|\s/g, "");
  if (limpo.includes(",")) limpo = limpo.replace(/\./g, "").replace(",", ".");
  return limpo === "" ? NaN : Number(limpo);
}

export const NOMES_TIPOS = { "Ação": "Ações", ETF: "ETFs", FII: "FIIs" };

// "2026-10-20T10:00:00+00:00" -> "há 2 h" / "ontem" / "há 3 dias" / "12/10/2026"
export function tempoAtras(iso, agora = new Date()) {
  const data = new Date(iso);
  const minutos = Math.max(0, Math.round((agora - data) / 60000));
  if (minutos < 1) return "agora";
  if (minutos < 60) return `há ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `há ${horas} h`;
  const dias = Math.round(horas / 24);
  if (dias === 1) return "ontem";
  if (dias < 7) return `há ${dias} dias`;
  return data.toLocaleDateString("pt-BR");
}

// Mesmo formato de ticker que o Python aceita: 4 letras/números + 1 ou 2 números.
export function pareceTicker(texto) {
  return /^[A-Z0-9]{4}\d{1,2}$/.test(texto.trim().toUpperCase());
}
