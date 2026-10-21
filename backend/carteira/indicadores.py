"""
Indicadores fundamentalistas, semáforo, conclusões e sinais de alerta.

Entrada: a série anual da CVM (demonstrativos.py), os últimos 12 meses, o preço
da ação e a quantidade de ações. Saída: tudo pronto para a tela "Análise".

Como o semáforo funciona:
  - Cada indicador tem uma REGRA escrita (ex.: "Dívida líquida/EBITDA: verde até 1,5x,
    amarelo até 3x, vermelho acima"). As regras ficam na lista REGRAS, fácil de mudar.
  - Indicadores sem regra universal (ex.: margem líquida, que depende muito do setor)
    aparecem sem cor: servem para comparar e acompanhar.
  - A nota de cada categoria (0 a 10) é a média das cores: verde = 10, amarelo = 5, vermelho = 0.

O semáforo NÃO diz se a ação é boa para comprar. Ele resume a saúde da empresa
em cada aspecto, para você estudar com mais atenção o que estiver amarelo ou vermelho.
"""

import math
from typing import Optional

import pandas as pd

ALIQUOTA_IR_PADRAO = 0.34  # IR + CSLL das empresas no Brasil

CATEGORIAS = {
    "crescimento": "Crescimento",
    "rentabilidade": "Rentabilidade",
    "endividamento": "Endividamento",
    "caixa": "Geração de caixa",
    "dividendos": "Dividendos",
    "preco": "Preço",
}

# Regras do semáforo: (verde se ..., amarelo se ...). Senão, vermelho.
#   "maior": quanto maior, melhor  |  "menor": quanto menor, melhor
REGRAS = {
    "cagr_receita_5a": ("maior", 0.10, 0.04, "verde ≥ 10% a.a. · amarelo ≥ 4% (≈ inflação) · vermelho abaixo"),
    "cagr_receita_10a": ("maior", 0.10, 0.04, "verde ≥ 10% a.a. · amarelo ≥ 4% · vermelho abaixo"),
    "cagr_lucro_5a": ("maior", 0.10, 0.04, "verde ≥ 10% a.a. · amarelo ≥ 4% · vermelho abaixo"),
    "roe": ("maior", 0.15, 0.10, "verde ≥ 15% · amarelo ≥ 10% · vermelho abaixo"),
    "roic": ("maior", 0.12, 0.08, "verde ≥ 12% · amarelo ≥ 8% · vermelho abaixo"),
    "estabilidade_margem": ("menor", 0.03, 0.07, "variação da margem EBIT em 5 anos: verde ≤ 3 p.p. · amarelo ≤ 7 p.p."),
    "divida_liquida_ebitda": ("menor", 1.5, 3.0, "verde ≤ 1,5x · amarelo ≤ 3x · vermelho acima (negativo = mais caixa que dívida)"),
    "divida_liquida_pl": ("menor", 0.5, 1.0, "verde ≤ 0,5x · amarelo ≤ 1x · vermelho acima"),
    "liquidez_corrente": ("maior", 1.5, 1.0, "verde ≥ 1,5 · amarelo ≥ 1 · vermelho abaixo"),
    "cobertura_juros": ("maior", 4.0, 2.0, "EBIT / despesa financeira líquida: verde ≥ 4x · amarelo ≥ 2x"),
    "conversao_caixa": ("maior", 0.9, 0.6, "caixa das operações / lucro (5 anos): verde ≥ 90% · amarelo ≥ 60%"),
    "margem_fcl": ("maior", 0.08, 0.03, "caixa livre / receita (5 anos): verde ≥ 8% · amarelo ≥ 3%"),
    "anos_fcl_positivo": ("maior", 4, 2, "anos com caixa livre positivo (de 5): verde ≥ 4 · amarelo ≥ 2"),
    "dividendos_cobertos": ("maior", 1.2, 0.8, "caixa livre / dividendos (5 anos): verde ≥ 1,2x · amarelo ≥ 0,8x"),
    "anos_pagando": ("maior", 5, 2, "anos seguidos pagando dividendos: verde ≥ 5 · amarelo ≥ 2"),
    "dividend_yield": ("maior", 0.06, 0.03, "verde ≥ 6% · amarelo ≥ 3% · vermelho abaixo"),
    "p_l": ("menor", 10, 18, "verde ≤ 10 · amarelo ≤ 18 · vermelho acima (ou prejuízo)"),
    "p_vp": ("menor", 1.5, 3.0, "verde ≤ 1,5 · amarelo ≤ 3 · vermelho acima"),
    "ev_ebitda": ("menor", 6, 10, "verde ≤ 6x · amarelo ≤ 10x · vermelho acima"),
    "fcf_yield": ("maior", 0.08, 0.04, "caixa livre / valor de mercado: verde ≥ 8% · amarelo ≥ 4%"),
}

PONTOS = {"verde": 2, "amarelo": 1, "vermelho": 0}


# ---------------------------------------------------------------------------
# Contas auxiliares
# ---------------------------------------------------------------------------

def dividir(a, b) -> Optional[float]:
    """a / b, ou None se faltar algum número ou b for zero."""
    if a is None or b is None or _vazio(a) or _vazio(b) or b == 0:
        return None
    return float(a) / float(b)


def _vazio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def cagr(inicial, final, anos: int) -> Optional[float]:
    """
    Crescimento médio anual composto. Ex.: de 100 para 161 em 5 anos = 10% a.a.
    Só faz sentido com os dois valores positivos.
    """
    if _vazio(inicial) or _vazio(final) or inicial <= 0 or final <= 0 or anos <= 0:
        return None
    return (final / inicial) ** (1 / anos) - 1


def classificar(chave: str, valor) -> Optional[str]:
    """Aplica a regra do semáforo: 'verde', 'amarelo', 'vermelho' ou None (sem regra/sem valor)."""
    if chave not in REGRAS or _vazio(valor):
        return None
    sentido, limite_verde, limite_amarelo, _ = REGRAS[chave]
    if sentido == "maior":
        return "verde" if valor >= limite_verde else "amarelo" if valor >= limite_amarelo else "vermelho"
    return "verde" if valor <= limite_verde else "amarelo" if valor <= limite_amarelo else "vermelho"


def coluna(tabela: pd.DataFrame, nome: str) -> pd.Series:
    """Uma coluna da série anual, com None virando NaN (para fazer contas)."""
    return pd.to_numeric(tabela[nome], errors="coerce") if nome in tabela.columns else pd.Series(dtype=float)


def soma_ultimos(serie: pd.Series, anos: int) -> Optional[float]:
    valores = serie.dropna().tail(anos)
    return float(valores.sum()) if len(valores) else None


def aliquota_efetiva(tabela: pd.DataFrame) -> float:
    """IR pago / lucro antes do IR, mediana dos últimos 5 anos (entre 0% e 34%)."""
    taxas = (-coluna(tabela, "ir_csll") / coluna(tabela, "lucro_antes_ir")).replace([math.inf, -math.inf], math.nan)
    taxas = taxas[(coluna(tabela, "lucro_antes_ir") > 0)].dropna().tail(5)
    if taxas.empty:
        return ALIQUOTA_IR_PADRAO
    return float(min(max(taxas.median(), 0.0), ALIQUOTA_IR_PADRAO))


# ---------------------------------------------------------------------------
# Séries por ano (para os gráficos)
# ---------------------------------------------------------------------------

def historico(tabela: pd.DataFrame) -> dict:
    receita = coluna(tabela, "receita_liquida")
    lucro = coluna(tabela, "lucro_liquido")
    lucro_contr = coluna(tabela, "lucro_controladores").fillna(lucro)
    pl = coluna(tabela, "patrimonio_liquido")
    pl_medio = (pl + pl.shift(1)) / 2
    ebitda = coluna(tabela, "ebitda")

    def lista(serie):
        return [None if _vazio(v) else round(float(v), 6) for v in serie]

    return {
        "anos": [int(a) for a in tabela.index],
        "receita": lista(receita),
        "lucro": lista(lucro),
        "ebitda": lista(ebitda),
        "margem_bruta": lista(coluna(tabela, "lucro_bruto") / receita),
        "margem_ebit": lista(coluna(tabela, "ebit") / receita),
        "margem_liquida": lista(lucro / receita),
        "roe": lista(lucro_contr / pl_medio.fillna(pl)),
        "divida_liquida_ebitda": lista(coluna(tabela, "divida_liquida") / ebitda.where(ebitda > 0)),
        "fluxo_caixa_livre": lista(coluna(tabela, "fluxo_caixa_livre")),
        "dividendos": lista(coluna(tabela, "dividendos_pagos")),
    }


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------

def _indicador(chave, nome, valor, formato, explicacao, categoria):
    regra = REGRAS.get(chave, (None, None, None, "sem regra universal: compare com o histórico e com o setor"))[3]
    return {
        "id": chave,
        "nome": nome,
        "categoria": categoria,
        "valor": None if _vazio(valor) else round(float(valor), 6),
        "formato": formato,  # 'pct', 'x' (vezes), 'reais', 'numero'
        "status": classificar(chave, valor),
        "regra": regra,
        "explicacao": explicacao,
    }


def calcular_indicadores(tabela: pd.DataFrame, ttm: Optional[dict], preco: Optional[float],
                         acoes: Optional[float], financeira: bool = False) -> list:
    """Lista de todos os indicadores, cada um com valor, status e explicação."""
    atual = dict(ttm) if ttm else (tabela.iloc[-1].to_dict() if len(tabela) else {})
    ultimo = tabela.iloc[-1].to_dict() if len(tabela) else {}
    receita = coluna(tabela, "receita_liquida")
    lucro = coluna(tabela, "lucro_liquido")
    lucro_contr_atual = atual.get("lucro_controladores") if not _vazio(atual.get("lucro_controladores")) else atual.get("lucro_liquido")
    n = len(tabela)
    t = aliquota_efetiva(tabela)
    indicadores = []

    def add(*args):
        indicadores.append(_indicador(*args))

    # --- Crescimento -------------------------------------------------------
    def cagr_de(serie, anos):
        if len(serie.dropna()) <= anos:
            return None
        return cagr(serie.iloc[-anos - 1], serie.iloc[-1], anos)

    if not financeira:
        add("cagr_receita_5a", "Crescimento da receita (5 anos)", cagr_de(receita, 5), "pct",
            "Quanto a receita cresceu, em média, por ano nos últimos 5 anos (valores nominais, sem descontar a inflação).", "crescimento")
        anos_longo = min(10, n - 1)
        add("cagr_receita_10a", f"Crescimento da receita ({anos_longo} anos)" if n > 6 else "Crescimento da receita (10 anos)",
            cagr_de(receita, anos_longo) if n > 6 else None, "pct",
            "O mesmo, no período mais longo disponível (até 10 anos). Mostra se o crescimento é consistente.", "crescimento")
    add("cagr_lucro_5a", "Crescimento do lucro (5 anos)", cagr_de(lucro, 5), "pct",
        "Crescimento médio anual do lucro líquido. Fica vazio se houve prejuízo no início ou no fim do período.", "crescimento")

    # --- Rentabilidade -----------------------------------------------------
    pl_atual = atual.get("patrimonio_liquido")
    add("roe", "ROE (retorno sobre o patrimônio)", dividir(lucro_contr_atual, pl_atual) if pl_atual and pl_atual > 0 else None, "pct",
        "Lucro dividido pelo patrimônio dos acionistas: quanto a empresa ganha para cada R$ 100 dos sócios.", "rentabilidade")
    if not financeira:
        ebit, dl = atual.get("ebit"), atual.get("divida_liquida")
        capital = (pl_atual or 0) + (dl or 0) if pl_atual is not None else None
        roic = dividir(ebit * (1 - t), capital) if ebit is not None and capital and capital > 0 else None
        add("roic", "ROIC (retorno sobre o capital investido)", roic, "pct",
            f"Lucro operacional após IR ({t:.0%}) dividido por patrimônio + dívida líquida. Mostra se o negócio rende mais que o custo do dinheiro.", "rentabilidade")
        for chave, nome, numerador, texto in [
            ("margem_bruta", "Margem bruta", "lucro_bruto", "Quanto sobra da receita depois do custo direto dos produtos/serviços."),
            ("margem_ebit", "Margem EBIT (operacional)", "ebit", "Quanto sobra da receita depois de todas as despesas da operação."),
            ("margem_ebitda", "Margem EBITDA", "ebitda", "Margem operacional antes da depreciação. Muito usada para comparar empresas do mesmo setor."),
        ]:
            add(chave, nome, dividir(atual.get(numerador), atual.get("receita_liquida")), "pct", texto, "rentabilidade")
        margens = (coluna(tabela, "ebit") / receita).dropna().tail(5)
        add("estabilidade_margem", "Estabilidade da margem (5 anos)", float(margens.max() - margens.min()) if len(margens) >= 3 else None, "pp",
            "Diferença entre a maior e a menor margem EBIT dos últimos 5 anos. Margens estáveis = negócio mais previsível.", "rentabilidade")
    add("margem_liquida", "Margem líquida", dividir(atual.get("lucro_liquido"), atual.get("receita_liquida")), "pct",
        "Quanto da receita vira lucro no fim. Depende muito do setor (varejo tem margens baixas, software altas).", "rentabilidade")

    # --- Endividamento -----------------------------------------------------
    if not financeira:
        ebitda = atual.get("ebitda")
        dl = atual.get("divida_liquida")
        dl_ebitda = None
        if dl is not None and ebitda is not None:
            dl_ebitda = dl / ebitda if ebitda > 0 else (None if dl > 0 else -1.0)
        add("divida_liquida_ebitda", "Dívida líquida / EBITDA", dl_ebitda, "x",
            "Quantos anos de geração de caixa operacional seriam necessários para pagar a dívida. Negativo = empresa tem mais caixa que dívida.", "endividamento")
        add("divida_liquida_pl", "Dívida líquida / Patrimônio", dividir(dl, pl_atual) if pl_atual and pl_atual > 0 else None, "x",
            "Quanto a empresa deve em relação ao dinheiro dos sócios.", "endividamento")
        add("liquidez_corrente", "Liquidez corrente", dividir(atual.get("ativo_circulante"), atual.get("passivo_circulante")), "x",
            "Bens e direitos de curto prazo divididos pelas obrigações de curto prazo. Abaixo de 1 = aperto para pagar as contas do ano.", "endividamento")
        financeiro = atual.get("resultado_financeiro")
        cobertura = None
        if atual.get("ebit") is not None and financeiro is not None and financeiro < 0:
            cobertura = atual["ebit"] / -financeiro
        add("cobertura_juros", "Cobertura de juros", cobertura, "x",
            "Quantas vezes o lucro operacional paga a despesa financeira líquida. Vazio se a empresa ganha mais com juros do que paga.", "endividamento")

    # --- Geração de caixa --------------------------------------------------
    if not financeira:
        fco5 = soma_ultimos(coluna(tabela, "fluxo_operacional"), 5)
        lucro5 = soma_ultimos(lucro, 5)
        add("conversao_caixa", "Conversão de lucro em caixa (5 anos)", dividir(fco5, lucro5) if lucro5 and lucro5 > 0 else None, "pct",
            "Caixa gerado pela operação dividido pelo lucro. Lucro que não vira caixa merece desconfiança.", "caixa")
        fcl = coluna(tabela, "fluxo_caixa_livre")
        add("margem_fcl", "Margem de caixa livre (5 anos)", dividir(soma_ultimos(fcl, 5), soma_ultimos(receita, 5)), "pct",
            "Caixa que sobra depois dos investimentos, dividido pela receita. É o dinheiro que pode virar dividendo, recompra ou pagar dívida.", "caixa")
        ultimos_fcl = fcl.dropna().tail(5)
        add("anos_fcl_positivo", "Anos com caixa livre positivo", int((ultimos_fcl > 0).sum()) if len(ultimos_fcl) else None, "numero",
            f"Em quantos dos últimos {len(ultimos_fcl)} anos sobrou caixa depois dos investimentos.", "caixa")
        add("capex_receita", "Investimento (capex) / receita", dividir(atual.get("capex"), atual.get("receita_liquida")), "pct",
            "Quanto da receita é reinvestido em máquinas, obras e tecnologia. Alto pode ser crescimento ou um negócio que exige muito capital.", "caixa")

    # --- Dividendos --------------------------------------------------------
    dividendos = coluna(tabela, "dividendos_pagos")
    lucro_contr = coluna(tabela, "lucro_controladores").fillna(lucro)
    div5 = soma_ultimos(dividendos, 5)
    lucro_contr5 = soma_ultimos(lucro_contr, 5)
    add("payout", "Payout (5 anos)", dividir(div5, lucro_contr5) if lucro_contr5 and lucro_contr5 > 0 else None, "pct",
        "Quanto do lucro foi pago aos acionistas. Alto = foco em renda; baixo = empresa reinvestindo para crescer.", "dividendos")
    if not financeira:
        fcl5 = soma_ultimos(coluna(tabela, "fluxo_caixa_livre"), 5)
        add("dividendos_cobertos", "Dividendos cobertos pelo caixa livre", dividir(fcl5, div5) if div5 and div5 > 0 else None, "x",
            "Caixa livre dividido pelos dividendos pagos. Abaixo de 1 = parte dos dividendos foi paga com dívida ou caixa antigo.", "dividendos")
    anos_pagando = 0
    for valor in reversed(list(dividendos)):
        if _vazio(valor) or valor <= 0:
            break
        anos_pagando += 1
    add("anos_pagando", "Anos seguidos pagando dividendos", anos_pagando if n else None, "numero",
        "Constância dos pagamentos (contando do ano mais recente para trás).", "dividendos")

    # --- Preço (precisa de cotação e quantidade de ações) -----------------
    valor_mercado = preco * acoes if preco and acoes else None
    ev = valor_mercado + (atual.get("divida_liquida") or 0) if valor_mercado is not None and not financeira else None
    lucro_ttm = lucro_contr_atual
    dividendos_ttm = atual.get("dividendos_pagos")
    add("dividend_yield", "Dividend yield", dividir(dividendos_ttm, valor_mercado), "pct",
        "Dividendos e JCP pagos nos últimos 12 meses divididos pelo valor de mercado (valor bruto, antes do IR do JCP).", "dividendos")
    add("p_l", "P/L (preço / lucro)", dividir(valor_mercado, lucro_ttm) if lucro_ttm and lucro_ttm > 0 else None, "x",
        "Quantos anos de lucro atual seriam necessários para 'pagar' a empresa pelo preço de hoje.", "preco")
    add("p_vp", "P/VP (preço / valor patrimonial)", dividir(valor_mercado, pl_atual) if pl_atual and pl_atual > 0 else None, "x",
        "Preço de mercado dividido pelo patrimônio contábil. Faz mais sentido junto com o ROE.", "preco")
    if not financeira:
        ebitda = atual.get("ebitda")
        add("ev_ebitda", "EV / EBITDA", dividir(ev, ebitda) if ebitda and ebitda > 0 else None, "x",
            "Valor da empresa (mercado + dívida líquida) dividido pelo EBITDA. Compara empresas com dívidas diferentes.", "preco")
        add("fcf_yield", "Rendimento do caixa livre (FCF yield)", dividir(atual.get("fluxo_caixa_livre"), valor_mercado), "pct",
            "Caixa livre dos últimos 12 meses dividido pelo valor de mercado. Como um 'aluguel' que a empresa gera para os sócios.", "preco")
    add("valor_mercado", "Valor de mercado", valor_mercado, "reais",
        "Preço da ação × quantidade de ações em circulação (todas as classes pelo preço deste ticker).", "preco")
    return indicadores


# ---------------------------------------------------------------------------
# Raio-X: nota de cada categoria + frase de conclusão
# ---------------------------------------------------------------------------

def _fmt_pct(valor) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


def _fmt_x(valor) -> str:
    return f"{valor:.1f}x".replace(".", ",")


def raio_x(indicadores: list, financeira: bool = False) -> list:
    """Uma entrada por categoria: status, nota de 0 a 10 e uma frase resumindo."""
    por_id = {i["id"]: i["valor"] for i in indicadores}
    categorias = []
    for chave, nome in CATEGORIAS.items():
        itens = [i for i in indicadores if i["categoria"] == chave]
        com_cor = [PONTOS[i["status"]] for i in itens if i["status"]]
        if com_cor:
            media = sum(com_cor) / len(com_cor)
            nota = round(media / 2 * 10, 1)
            status = "verde" if media >= 1.5 else "amarelo" if media >= 0.75 else "vermelho"
        else:
            nota, status = None, None
        aplica = not (financeira and chave in ("endividamento", "caixa"))
        categorias.append({
            "id": chave,
            "nome": nome,
            "status": status if aplica else None,
            "nota": nota if aplica else None,
            "resumo": _frase(chave, por_id, financeira) if aplica else "Não se aplica a bancos e seguradoras (o dinheiro é a 'matéria-prima' do negócio).",
        })
    return categorias


def _frase(categoria: str, v: dict, financeira: bool) -> str:
    """Frase de conclusão escrita por regras (sem IA), a partir dos números."""
    def tem(*chaves):
        return all(v.get(c) is not None for c in chaves)

    if categoria == "crescimento":
        partes = []
        if tem("cagr_receita_5a"):
            ritmo = "acima" if v["cagr_receita_5a"] > 0.045 else "abaixo"
            partes.append(f"Receita cresceu {_fmt_pct(v['cagr_receita_5a'])} ao ano em 5 anos ({ritmo} da inflação típica de ~4,5%)")
        if tem("cagr_lucro_5a"):
            partes.append(f"lucro {_fmt_pct(v['cagr_lucro_5a'])} ao ano")
        elif "cagr_lucro_5a" in v:
            partes.append("lucro sem comparação possível (houve prejuízo no período)")
        return (", ".join(partes) + ".") if partes else "Histórico insuficiente para medir o crescimento."

    if categoria == "rentabilidade":
        if not tem("roe"):
            return "Não foi possível calcular o retorno (patrimônio negativo ou sem lucro)."
        frase = f"ROE de {_fmt_pct(v['roe'])}"
        if tem("roic"):
            frase += f" e ROIC de {_fmt_pct(v['roic'])}"
        if tem("estabilidade_margem"):
            estavel = "estáveis" if v["estabilidade_margem"] <= 0.03 else "com oscilação moderada" if v["estabilidade_margem"] <= 0.07 else "instáveis"
            frase += f"; margens {estavel} nos últimos 5 anos"
        return frase + "."

    if categoria == "endividamento":
        if not tem("divida_liquida_ebitda"):
            return "Sem dados suficientes de dívida e EBITDA."
        dl = v["divida_liquida_ebitda"]
        if dl < 0:
            return "Empresa com mais caixa do que dívida (caixa líquido)."
        nivel = "baixa" if dl <= 1.5 else "moderada" if dl <= 3 else "alta"
        return f"Dívida {nivel}: {_fmt_x(dl)} o EBITDA."

    if categoria == "caixa":
        partes = []
        if tem("conversao_caixa"):
            partes.append(f"{_fmt_pct(v['conversao_caixa'])} do lucro virou caixa em 5 anos")
        if tem("anos_fcl_positivo"):
            partes.append(f"caixa livre positivo em {int(v['anos_fcl_positivo'])} dos últimos 5 anos")
        return ("; ".join(partes) + ".").capitalize() if partes else "Sem dados de fluxo de caixa suficientes."

    if categoria == "dividendos":
        if not v.get("anos_pagando"):
            return "Não pagou dividendos no último ano (pode estar reinvestindo para crescer)."
        frase = f"Paga dividendos há {int(v['anos_pagando'])} ano(s) seguido(s)"
        if tem("payout"):
            frase += f", distribuindo {_fmt_pct(v['payout'])} do lucro"
        if tem("dividend_yield"):
            frase += f"; yield de {_fmt_pct(v['dividend_yield'])}"
        return frase + "."

    if categoria == "preco":
        partes = []
        if tem("p_l"):
            partes.append(f"P/L de {_fmt_x(v['p_l']).replace('x', '')}")
        if tem("ev_ebitda"):
            partes.append(f"EV/EBITDA de {_fmt_x(v['ev_ebitda'])}")
        if tem("p_vp"):
            partes.append(f"P/VP de {_fmt_x(v['p_vp']).replace('x', '')}")
        return ("Negocia a " + ", ".join(partes) + ". Veja a aba Valuation para o preço justo.") if partes else "Sem cotação ou sem lucro para calcular os múltiplos."
    return ""


# ---------------------------------------------------------------------------
# Sinais de alerta
# ---------------------------------------------------------------------------

def sinais_de_alerta(tabela: pd.DataFrame, indicadores: list, financeira: bool = False) -> list:
    """Situações que merecem atenção, cada uma com explicação."""
    alertas = []
    v = {i["id"]: i["valor"] for i in indicadores}
    receita = coluna(tabela, "receita_liquida")
    lucro = coluna(tabela, "lucro_liquido")
    pl = coluna(tabela, "patrimonio_liquido")

    def alerta(nivel, titulo, explicacao):
        alertas.append({"nivel": nivel, "titulo": titulo, "explicacao": explicacao})

    if len(pl.dropna()) and pl.dropna().iloc[-1] < 0:
        alerta("alto", "Patrimônio líquido negativo",
               "A empresa deve mais do que tem. ROE e P/VP perdem o sentido, e o risco de reestruturação é maior.")

    ultimos_lucros = lucro.dropna().tail(5)
    prejuizos = int((ultimos_lucros < 0).sum())
    if prejuizos >= 2:
        alerta("alto", f"Prejuízo em {prejuizos} dos últimos {len(ultimos_lucros)} anos",
               "Lucros inconsistentes tornam qualquer projeção mais incerta.")

    ultimas_receitas = receita.dropna().tail(4)
    if len(ultimas_receitas) == 4 and all(ultimas_receitas.diff().dropna() < 0):
        alerta("medio", "Receita caindo há 3 anos seguidos",
               "Pode ser perda de mercado, ciclo do setor ou venda de negócios. Vale entender o motivo.")

    if not financeira:
        margens = (coluna(tabela, "ebit") / receita).dropna().tail(4)
        if len(margens) == 4 and all(margens.diff().dropna() < 0):
            alerta("medio", "Margem operacional caindo há 3 anos seguidos",
                   "Custos subindo mais rápido que a receita, ou preços pressionados pela concorrência.")

        if v.get("conversao_caixa") is not None and v["conversao_caixa"] < 0.6 and (v.get("cagr_lucro_5a") or 0) > 0:
            alerta("alto", "Lucro cresce, mas o caixa não acompanha",
                   "Menos de 60% do lucro virou caixa em 5 anos. Pode ser capital preso em estoques/clientes ou lucro contábil sem dinheiro de verdade.")

        dl_ebitda = coluna(tabela, "divida_liquida") / coluna(tabela, "ebitda").where(coluna(tabela, "ebitda") > 0)
        dl_ebitda = dl_ebitda.dropna()
        if len(dl_ebitda) >= 4 and dl_ebitda.iloc[-1] > 2 and dl_ebitda.iloc[-1] - dl_ebitda.iloc[-4] >= 1:
            alerta("medio", "Dívida crescendo mais rápido que o EBITDA",
                   f"A dívida líquida passou de {_fmt_x(dl_ebitda.iloc[-4])} para {_fmt_x(dl_ebitda.iloc[-1])} o EBITDA em 3 anos.")

        if v.get("dividendos_cobertos") is not None and v["dividendos_cobertos"] < 0.8:
            alerta("medio", "Dividendos maiores que o caixa livre",
                   "Nos últimos 5 anos a empresa pagou mais dividendos do que gerou de caixa livre. Esse ritmo pode não se sustentar.")

        if v.get("liquidez_corrente") is not None and v["liquidez_corrente"] < 1:
            alerta("medio", "Liquidez corrente abaixo de 1",
                   "As obrigações de curto prazo são maiores que os recursos de curto prazo.")
    return alertas
