import { useState } from "react";
import { enviarCompra } from "../api.js";
import { Cabecalho, Rodape } from "../componentes/Comuns.jsx";
import { lerNumero, reais } from "../formatacao.js";

const TIPOS = ["Ação", "ETF", "FII"];

// Data de hoje no formato do campo de data: "2026-10-19"
function hoje() {
  const d = new Date();
  const doisDigitos = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}-${doisDigitos(d.getDate())}`;
}

const VAZIO = { ticker: "", tipo: "Ação", setor: "", quantidade: "", preco_pago: "", data_compra: hoje(), taxas: "" };

/** Tela 5 — Adicionar: formulário que grava uma compra nova na planilha. */
export default function Adicionar({ carteira, aoSalvar }) {
  const [form, setForm] = useState(VAZIO);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);

  // Setores que você já usou, para sugerir enquanto digita.
  const setores = [...new Set(carteira?.ativos.map((a) => a.setor).filter(Boolean))];

  const quantidade = lerNumero(form.quantidade);
  const preco = lerNumero(form.preco_pago);
  const taxas = form.taxas === "" ? 0 : lerNumero(form.taxas);
  const custo = quantidade * preco + taxas;
  const custoValido = Number.isFinite(custo) && quantidade > 0 && preco > 0;

  function mudar(campo) {
    return (evento) => {
      setForm({ ...form, [campo]: evento.target.value });
      setErro(null);
      setSucesso(null);
    };
  }

  async function aoEnviar(evento) {
    evento.preventDefault(); // impede o navegador de recarregar a página
    if (!form.ticker.trim()) return setErro("Digite o ticker (ex.: PETR4).");
    if (!(quantidade > 0)) return setErro("A quantidade precisa ser um número maior que zero.");
    if (!(preco > 0)) return setErro("O preço pago precisa ser um número maior que zero.");
    if (!Number.isFinite(taxas) || taxas < 0) return setErro("As taxas precisam ser um número (ou vazio).");

    setEnviando(true);
    try {
      const compra = await enviarCompra({
        ticker: form.ticker.trim().toUpperCase(),
        tipo: form.tipo,
        setor: form.setor.trim() || null,
        quantidade,
        preco_pago: preco,
        data_compra: form.data_compra,
        taxas,
      });
      setSucesso(`${compra.ticker} adicionada à planilha.`);
      setForm({ ...VAZIO, data_compra: form.data_compra });
      aoSalvar();
    } catch (e) {
      setErro(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <Cabecalho titulo="Adicionar" subtitulo="Nova compra de ação, ETF ou FII" />

      <form className="formulario" onSubmit={aoEnviar} noValidate>
        <section className="cartao campos">
          <label>
            <span>Ticker</span>
            <input
              value={form.ticker}
              onChange={mudar("ticker")}
              placeholder="PETR4"
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck="false"
              maxLength={12}
            />
          </label>

          <div className="campo">
            <span>Tipo</span>
            <div className="segmentado">
              {TIPOS.map((tipo) => (
                <button
                  key={tipo}
                  type="button"
                  className={form.tipo === tipo ? "ativo" : ""}
                  onClick={() => setForm({ ...form, tipo })}
                >
                  {tipo}
                </button>
              ))}
            </div>
          </div>

          <label>
            <span>
              Setor <em>opcional</em>
            </span>
            <input value={form.setor} onChange={mudar("setor")} placeholder="Ex.: Financeiro" list="setores" />
            <datalist id="setores">
              {setores.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
          </label>
        </section>

        <section className="cartao campos">
          <div className="grade-2 sem-margem">
            <label>
              <span>Quantidade</span>
              <input value={form.quantidade} onChange={mudar("quantidade")} placeholder="100" inputMode="decimal" />
            </label>
            <label>
              <span>Preço pago</span>
              <input value={form.preco_pago} onChange={mudar("preco_pago")} placeholder="36,50" inputMode="decimal" />
            </label>
          </div>
          <div className="grade-2 sem-margem">
            <label>
              <span>Data da compra</span>
              <input type="date" value={form.data_compra} max={hoje()} onChange={mudar("data_compra")} />
            </label>
            <label>
              <span>
                Taxas <em>opcional</em>
              </span>
              <input value={form.taxas} onChange={mudar("taxas")} placeholder="0,00" inputMode="decimal" />
            </label>
          </div>
        </section>

        <section className="cartao resumo-compra">
          <span>Custo total</span>
          <strong>{custoValido ? reais(custo) : "—"}</strong>
          {custoValido && (
            <small>
              {reais(custo / quantidade)} por cota, já com as taxas (é o que entra no preço médio)
            </small>
          )}
        </section>

        {erro && <p className="mensagem erro">{erro}</p>}
        {sucesso && <p className="mensagem sucesso">✓ {sucesso}</p>}

        <button type="submit" className="botao largo" disabled={enviando}>
          {enviando ? "Salvando…" : "Salvar compra"}
        </button>
        <p className="nota centro">
          A compra é gravada como uma linha nova na aba “acoes” do seu carteira.xlsx.
        </p>
      </form>

      <Rodape />
    </>
  );
}
