"""
Valuation: quanto a empresa vale, em 3 cenários (negativo, neutro e positivo).

MÉTODO PRINCIPAL: Fluxo de Caixa Descontado (FCD, ou "DCF" em inglês)
    A ideia: uma empresa vale todo o dinheiro que ela vai gerar no futuro,
    trazido para valores de hoje (dinheiro futuro vale menos que dinheiro hoje).

    Para cada um dos próximos 5 anos:
        Receita        = receita do ano anterior × (1 + crescimento)
        EBIT           = receita × margem EBIT
        NOPAT          = EBIT × (1 − alíquota de IR)          (lucro operacional após IR)
        Caixa livre    = NOPAT + depreciação − capex − aumento do capital de giro
        Valor de hoje  = caixa livre / (1 + WACC) ^ ano

    Depois do 5º ano, supomos que a empresa cresce para sempre a uma taxa pequena
    (crescimento na perpetuidade). Esse "valor terminal" é:
        Valor terminal = caixa livre do ano 6 / (WACC − crescimento na perpetuidade)

    Valor da empresa (EV) = soma dos valores de hoje + valor terminal trazido a hoje
    Valor das ações      = EV − dívida líquida
    Preço justo          = valor das ações / quantidade de ações

    WACC = custo médio do dinheiro da empresa (dos sócios e dos bancos):
        Custo dos sócios (Ke) = taxa livre de risco + beta × prêmio de risco do mercado
        Custo da dívida (Kd)  = taxa livre de risco + spread, com desconto do IR
        WACC = Ke × peso das ações + Kd × (1 − IR) × peso da dívida

BANCOS E SEGURADORAS: o FCD não funciona (para eles, dívida é matéria-prima).
    Usamos o modelo de "P/VP justo" (Gordon):
        P/VP justo  = (ROE − g) / (Ke − g)
        Preço justo = valor patrimonial por ação × P/VP justo

IMPORTANTE: valuation é uma estimativa, muito sensível às premissas. Por isso o app
mostra as premissas, deixa você mudar todas e mostra a tabela de sensibilidade.
Não é recomendação de compra ou venda.
"""

import math
from typing import Optional

import pandas as pd

from carteira.indicadores import aliquota_efetiva, coluna

ANOS_PROJECAO = 5
PREMIO_RISCO_PADRAO = 0.05     # prêmio de risco do mercado de ações (Ke − taxa livre de risco), para beta 1
SPREAD_DIVIDA_PADRAO = 0.02    # quanto a empresa paga acima da taxa livre de risco nos empréstimos
# Crescimento nominal depois do 5º ano (≈ inflação + ~1% real). Igual nos 3 cenários:
# ninguém sabe prever o "para sempre", e variar essa taxa exagerava os cenários extremos.
# Os cenários diferem no que dá para estudar: crescimento, margem, capex e WACC.
CRESCIMENTO_PERPETUO = {"negativo": 0.04, "neutro": 0.04, "positivo": 0.04}
AJUSTE_WACC = {"negativo": 0.01, "neutro": 0.0, "positivo": -0.01}

CENARIOS = ("negativo", "neutro", "positivo")


class ErroValuation(Exception):
    """Premissas impossíveis (ex.: WACC menor que o crescimento perpétuo)."""


def _vazio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _limitar(valor, minimo, maximo):
    return min(max(valor, minimo), maximo)


def _percentil(serie: pd.Series, q: float, padrao: float) -> float:
    serie = serie.replace([math.inf, -math.inf], math.nan).dropna()
    return float(serie.quantile(q)) if len(serie) else padrao


# ---------------------------------------------------------------------------
# Base: os números de partida (hoje)
# ---------------------------------------------------------------------------

def montar_base(tabela: pd.DataFrame, ttm: Optional[dict], preco: Optional[float], acoes: Optional[float]) -> dict:
    atual = dict(ttm) if ttm else tabela.iloc[-1].to_dict()
    return {
        "receita": atual.get("receita_liquida"),
        "divida_liquida": atual.get("divida_liquida") or 0.0,
        "divida_bruta": atual.get("divida_bruta") or 0.0,
        "patrimonio_liquido": atual.get("patrimonio_liquido"),
        "lucro": atual.get("lucro_controladores") if not _vazio(atual.get("lucro_controladores")) else atual.get("lucro_liquido"),
        "preco": preco,
        "acoes": acoes,
        "valor_mercado": preco * acoes if preco and acoes else None,
        "referencia": atual.get("referencia"),
    }


def capital_de_giro(tabela: pd.DataFrame) -> pd.Series:
    """
    Capital de giro operacional = (ativo circulante − caixa − aplicações)
                                − (passivo circulante − empréstimos de curto prazo)
    É o dinheiro "preso" em estoques e contas a receber, menos o que os fornecedores financiam.
    """
    ativo = coluna(tabela, "ativo_circulante") - coluna(tabela, "caixa").fillna(0) - coluna(tabela, "aplicacoes_financeiras").fillna(0)
    passivo = coluna(tabela, "passivo_circulante") - coluna(tabela, "emprestimos_cp").fillna(0)
    return ativo - passivo


# ---------------------------------------------------------------------------
# WACC
# ---------------------------------------------------------------------------

def calcular_wacc(taxa_livre_risco: float, beta: float, premio_risco: float, spread_divida: float,
                  aliquota_ir: float, valor_acoes: Optional[float], divida_bruta: float) -> dict:
    custo_acionista = taxa_livre_risco + beta * premio_risco
    custo_divida = taxa_livre_risco + spread_divida
    divida = max(divida_bruta or 0.0, 0.0)
    acoes = valor_acoes if valor_acoes and valor_acoes > 0 else None
    peso_divida = divida / (divida + acoes) if acoes else 0.0
    wacc = custo_acionista * (1 - peso_divida) + custo_divida * (1 - aliquota_ir) * peso_divida
    return {
        "custo_acionista": custo_acionista,
        "custo_divida": custo_divida,
        "peso_divida": peso_divida,
        "wacc": wacc,
    }


# ---------------------------------------------------------------------------
# Premissas padrão (a partir do histórico da própria empresa)
# ---------------------------------------------------------------------------

def premissas_padrao(tabela: pd.DataFrame, base: dict, mercado: dict) -> dict:
    """
    Sugere as premissas dos 3 cenários a partir do histórico (até 10 anos):
      - crescimento: neutro = mediana do crescimento anual da receita;
                     negativo/positivo = percentil 25/75, mas a 3–6 pontos do neutro
      - margem EBIT: o mesmo raciocínio (a 10–20% de distância do neutro)
      - capex: no negativo a empresa precisa investir mais; no positivo, menos
      - depreciação, capital de giro e IR: mediana histórica (iguais nos 3)
      - WACC: calculado com os dados de mercado; ±1 ponto nos cenários
      - perpetuidade: 4% ao ano (nominal) nos 3 cenários
    Cada premissa vem com a explicação de onde saiu.
    """
    receita = coluna(tabela, "receita_liquida")
    crescimentos = receita.pct_change().tail(10)
    margens = (coluna(tabela, "ebit") / receita).tail(10)
    capex = (coluna(tabela, "capex") / receita).tail(10)
    depreciacao = (coluna(tabela, "depreciacao") / receita).tail(10)
    giro = (capital_de_giro(tabela) / receita).tail(10)
    anos = f"{int(tabela.index[max(0, len(tabela) - 10)])}–{int(tabela.index[-1])}" if len(tabela) else ""

    # Neutro = mediana. Negativo/positivo = percentis 25/75, mas com distância limitada:
    # em empresas cíclicas, os anos extremos isolados exagerariam os cenários.
    g_neutro = _limitar(_percentil(crescimentos, 0.5, 0.05), -0.05, 0.20)
    g_neg = g_neutro - _limitar(g_neutro - _percentil(crescimentos, 0.25, g_neutro), 0.03, 0.06)
    g_pos = g_neutro + _limitar(_percentil(crescimentos, 0.75, g_neutro) - g_neutro, 0.03, 0.06)

    m_neutro = _percentil(margens, 0.5, 0.10)
    base_m = abs(m_neutro) or 0.05
    m_neg = m_neutro - _limitar(m_neutro - _percentil(margens, 0.25, m_neutro), 0.10 * base_m, 0.20 * base_m)
    m_pos = m_neutro + _limitar(_percentil(margens, 0.75, m_neutro) - m_neutro, 0.10 * base_m, 0.20 * base_m)

    c_neutro = max(_percentil(capex, 0.5, 0.05), 0.0)
    base_c = c_neutro or 0.01
    c_neg = c_neutro + _limitar(_percentil(capex, 0.75, c_neutro) - c_neutro, 0.10 * base_c, 0.20 * base_c)
    c_pos = max(c_neutro - _limitar(c_neutro - _percentil(capex, 0.25, c_neutro), 0.10 * base_c, 0.20 * base_c), 0.0)

    deprec = max(_percentil(depreciacao, 0.5, c_neutro), 0.0)
    capital_giro = _limitar(_percentil(giro, 0.5, 0.0), -0.3, 0.5)
    ir = aliquota_efetiva(tabela)

    w = calcular_wacc(mercado["taxa_livre_risco"], mercado["beta"], mercado["premio_risco"],
                      mercado["spread_divida"], ir, base["valor_mercado"], base["divida_bruta"])

    def cenario(nome, crescimento, margem, capex_):
        wacc = w["wacc"] + AJUSTE_WACC[nome]
        perpetuo = min(CRESCIMENTO_PERPETUO[nome], wacc - 0.02)
        return {
            "crescimento": round(crescimento, 4),
            "margem_ebit": round(margem, 4),
            "capex_receita": round(capex_, 4),
            "depreciacao_receita": round(deprec, 4),
            "capital_giro_receita": round(capital_giro, 4),
            "aliquota_ir": round(ir, 4),
            "wacc": round(wacc, 4),
            "crescimento_perpetuo": round(perpetuo, 4),
        }

    return {
        "cenarios": {
            "negativo": cenario("negativo", g_neg, m_neg, c_neg),
            "neutro": cenario("neutro", g_neutro, m_neutro, c_neutro),
            "positivo": cenario("positivo", g_pos, m_pos, c_pos),
        },
        "wacc_detalhe": {k: round(v, 4) for k, v in w.items()},
        "origem": {
            "crescimento": f"Crescimento anual da receita {anos}: neutro = mediana; negativo/positivo = percentis 25/75, a 3–6 p.p. do neutro.",
            "margem_ebit": f"Margem EBIT {anos}: neutro = mediana; negativo/positivo = percentis 25/75, a 10–20% de distância do neutro.",
            "capex_receita": f"Capex / receita {anos}: mediana no neutro; maior no negativo e menor no positivo (10–20% de diferença). Depois do 5º ano, o capex nunca fica abaixo da depreciação.",
            "depreciacao_receita": f"Mediana da depreciação / receita {anos}.",
            "capital_giro_receita": f"Mediana do capital de giro operacional / receita {anos}.",
            "aliquota_ir": "Alíquota efetiva de IR (mediana de 5 anos, limitada a 34%).",
            "wacc": "Calculado com taxa livre de risco, beta, prêmio de risco e dívida (veja o detalhe). ±1 p.p. nos cenários.",
            "crescimento_perpetuo": "Crescimento nominal depois do 5º ano: 4% nos 3 cenários (perto da inflação + 1% real), sempre abaixo do WACC. Igual nos cenários porque ninguém sabe prever o \"para sempre\".",
        },
    }


# ---------------------------------------------------------------------------
# Projeção e valor de um cenário (empresas não financeiras)
# ---------------------------------------------------------------------------

def projetar(premissas: dict, base: dict) -> list:
    """Os 5 anos projetados, ano a ano (para mostrar a conta inteira na tela)."""
    p = premissas
    receita_anterior = base["receita"]
    giro_anterior = receita_anterior * p["capital_giro_receita"]
    anos = []
    for ano in range(1, ANOS_PROJECAO + 1):
        receita = receita_anterior * (1 + p["crescimento"])
        ebit = receita * p["margem_ebit"]
        nopat = ebit * (1 - p["aliquota_ir"])
        depreciacao = receita * p["depreciacao_receita"]
        capex = receita * p["capex_receita"]
        giro = receita * p["capital_giro_receita"]
        variacao_giro = giro - giro_anterior
        fcff = nopat + depreciacao - capex - variacao_giro
        fator = (1 + p["wacc"]) ** ano
        anos.append({
            "ano": ano, "receita": receita, "ebit": ebit, "nopat": nopat, "depreciacao": depreciacao,
            "capex": capex, "variacao_capital_giro": variacao_giro, "fluxo_caixa_livre": fcff,
            "fator_desconto": 1 / fator, "valor_presente": fcff / fator,
        })
        receita_anterior, giro_anterior = receita, giro
    return anos


def validar_premissas(premissas: dict) -> None:
    if premissas["wacc"] <= premissas["crescimento_perpetuo"]:
        raise ErroValuation("O WACC precisa ser maior que o crescimento na perpetuidade (senão a empresa valeria infinito).")
    if premissas["wacc"] <= 0:
        raise ErroValuation("O WACC precisa ser positivo.")


def capex_na_perpetuidade(premissas: dict) -> float:
    """Capex / receita usado depois do 5º ano: no mínimo igual à depreciação."""
    return max(premissas["capex_receita"], premissas["depreciacao_receita"])


def valor_cenario(premissas: dict, base: dict) -> dict:
    validar_premissas(premissas)
    projecao = projetar(premissas, base)
    ultimo = projecao[-1]
    g, wacc = premissas["crescimento_perpetuo"], premissas["wacc"]
    # Fluxo do ano 6: o caixa livre do ano 5 crescendo g. Dois ajustes de coerência:
    #  - na perpetuidade, a variação do capital de giro acompanha o crescimento g;
    #  - o capex nunca fica abaixo da depreciação (uma empresa que cresce para sempre
    #    não pode investir menos do que o desgaste dos seus ativos).
    receita_6 = ultimo["receita"] * (1 + g)
    capex_perpetuo = capex_na_perpetuidade(premissas)
    fcff_6 = (receita_6 * premissas["margem_ebit"] * (1 - premissas["aliquota_ir"])
              + receita_6 * premissas["depreciacao_receita"]
              - receita_6 * capex_perpetuo
              - (receita_6 - ultimo["receita"]) * premissas["capital_giro_receita"])
    valor_terminal = fcff_6 / (wacc - g)
    vp_terminal = valor_terminal * ultimo["fator_desconto"]
    soma_vp = sum(a["valor_presente"] for a in projecao)
    ev = soma_vp + vp_terminal
    valor_acoes = ev - base["divida_liquida"]
    preco_justo = valor_acoes / base["acoes"] if base.get("acoes") else None
    return {
        "projecao": projecao,
        "soma_valor_presente": soma_vp,
        "valor_terminal": valor_terminal,
        "valor_presente_terminal": vp_terminal,
        "peso_terminal": vp_terminal / ev if ev else None,
        "capex_perpetuidade": capex_perpetuo,
        "valor_empresa": ev,
        "valor_acoes": valor_acoes,
        "preco_justo": preco_justo,
        "potencial": preco_justo / base["preco"] - 1 if preco_justo is not None and base.get("preco") else None,
    }


# ---------------------------------------------------------------------------
# Bancos e seguradoras: P/VP justo (Gordon)
# ---------------------------------------------------------------------------

def premissas_padrao_financeira(tabela: pd.DataFrame, base: dict, mercado: dict) -> dict:
    lucro = coluna(tabela, "lucro_controladores").fillna(coluna(tabela, "lucro_liquido"))
    pl = coluna(tabela, "patrimonio_liquido")
    roes = (lucro / ((pl + pl.shift(1)) / 2).fillna(pl)).tail(10)
    ke = mercado["taxa_livre_risco"] + mercado["beta"] * mercado["premio_risco"]
    r_neutro = _percentil(roes, 0.5, 0.15)
    cenarios = {}
    for nome, q in (("negativo", 0.25), ("neutro", 0.5), ("positivo", 0.75)):
        roe = _percentil(roes, q, r_neutro)
        if nome == "negativo":
            roe = min(roe, r_neutro - 0.02)
        if nome == "positivo":
            roe = max(roe, r_neutro + 0.02)
        custo = ke + AJUSTE_WACC[nome]
        cenarios[nome] = {
            "roe": round(roe, 4),
            "custo_acionista": round(custo, 4),
            "crescimento_perpetuo": round(min(CRESCIMENTO_PERPETUO[nome], custo - 0.02), 4),
        }
    return {
        "cenarios": cenarios,
        "wacc_detalhe": {"custo_acionista": round(ke, 4)},
        "origem": {
            "roe": "ROE histórico (até 10 anos): percentis 25 / 50 / 75.",
            "custo_acionista": "Taxa livre de risco + beta × prêmio de risco; ±1 p.p. nos cenários.",
            "crescimento_perpetuo": "Crescimento nominal de longo prazo: 4% nos 3 cenários, abaixo do custo de capital.",
        },
    }


def valor_cenario_financeira(premissas: dict, base: dict) -> dict:
    roe, ke, g = premissas["roe"], premissas["custo_acionista"], premissas["crescimento_perpetuo"]
    if ke <= g:
        raise ErroValuation("O custo de capital precisa ser maior que o crescimento na perpetuidade.")
    pvp_justo = (roe - g) / (ke - g)
    valor_acoes = base["patrimonio_liquido"] * pvp_justo if base.get("patrimonio_liquido") else None
    preco_justo = valor_acoes / base["acoes"] if valor_acoes is not None and base.get("acoes") else None
    return {
        "pvp_justo": pvp_justo,
        "valor_acoes": valor_acoes,
        "preco_justo": preco_justo,
        "potencial": preco_justo / base["preco"] - 1 if preco_justo is not None and base.get("preco") else None,
    }


# ---------------------------------------------------------------------------
# Tudo junto: 3 cenários, média ponderada, sensibilidade e valuation reverso
# ---------------------------------------------------------------------------

def avaliar(cenarios: dict, base: dict, pesos: Optional[dict] = None, financeira: bool = False) -> dict:
    pesos = pesos or {"negativo": 0.25, "neutro": 0.5, "positivo": 0.25}
    calcular = valor_cenario_financeira if financeira else valor_cenario

    resultados, erros = {}, {}
    for nome in CENARIOS:
        try:
            resultados[nome] = calcular(cenarios[nome], base)
        except ErroValuation as erro:
            erros[nome] = str(erro)

    soma_pesos = sum(pesos.get(n, 0) for n in resultados)
    precos = {n: r["preco_justo"] for n, r in resultados.items() if r.get("preco_justo") is not None}
    ponderado = None
    if precos and soma_pesos > 0 and len(precos) == len(resultados):
        ponderado = sum(precos[n] * pesos.get(n, 0) for n in precos) / soma_pesos

    return {
        "metodo": "P/VP justo (Gordon)" if financeira else "Fluxo de caixa descontado (5 anos + perpetuidade)",
        "resultados": resultados,
        "erros": erros,
        "pesos": pesos,
        "preco_ponderado": ponderado,
        "potencial_ponderado": ponderado / base["preco"] - 1 if ponderado is not None and base.get("preco") else None,
        "margem_seguranca": (precos["negativo"] / base["preco"] - 1) if "negativo" in precos and base.get("preco") else None,
        "sensibilidade": sensibilidade(cenarios["neutro"], base, financeira) if "neutro" in resultados else None,
        "reverso": valuation_reverso(cenarios["neutro"], base, financeira),
    }


def sensibilidade(premissas: dict, base: dict, financeira: bool = False) -> Optional[dict]:
    """
    Tabela: preço justo do cenário neutro mudando o custo de capital (linhas)
    e o crescimento na perpetuidade (colunas). Mostra o quanto o resultado depende das premissas.
    """
    if not base.get("acoes"):
        return None
    chave_taxa = "custo_acionista" if financeira else "wacc"
    calcular = valor_cenario_financeira if financeira else valor_cenario
    passos = (-0.01, -0.005, 0.0, 0.005, 0.01)
    taxas = [premissas[chave_taxa] + d for d in passos]
    crescimentos = [premissas["crescimento_perpetuo"] + d for d in passos]
    tabela = []
    for taxa in taxas:
        linha = []
        for g in crescimentos:
            try:
                linha.append(calcular({**premissas, chave_taxa: taxa, "crescimento_perpetuo": g}, base)["preco_justo"])
            except ErroValuation:
                linha.append(None)
        tabela.append(linha)
    return {"taxa": chave_taxa, "taxas": taxas, "crescimentos": crescimentos, "precos": tabela}


def valuation_reverso(premissas: dict, base: dict, financeira: bool = False) -> Optional[dict]:
    """
    A pergunta inversa: o que o PREÇO DE HOJE supõe sobre o futuro?
      - Empresas: qual crescimento anual da receita nos 5 anos (mantendo as outras
        premissas do cenário neutro) faz o preço justo ser igual ao preço atual.
      - Bancos: qual ROE justifica o P/VP atual.
    Resolvido por "bisseção": chutamos um valor, vemos se o preço justo ficou acima ou
    abaixo do preço atual, e cortamos o intervalo pela metade até acertar.
    """
    preco = base.get("preco")
    if not preco or not base.get("acoes"):
        return None

    if financeira:
        if not base.get("patrimonio_liquido") or base["patrimonio_liquido"] <= 0:
            return None
        pvp = preco * base["acoes"] / base["patrimonio_liquido"]
        ke, g = premissas["custo_acionista"], premissas["crescimento_perpetuo"]
        return {"variavel": "roe", "valor_implicito": pvp * (ke - g) + g, "fora_do_intervalo": False}

    def diferenca(crescimento):
        return valor_cenario({**premissas, "crescimento": crescimento}, base)["preco_justo"] - preco

    try:
        baixo, alto = -0.30, 0.60
        f_baixo, f_alto = diferenca(baixo), diferenca(alto)
        if f_baixo * f_alto > 0:
            # Nenhum crescimento entre −30% e +60% ao ano justifica o preço.
            # (Se a empresa queima caixa, crescer mais a faz valer MENOS; por isso olhamos os dois lados.)
            acima = (f_baixo < 0) if f_alto > f_baixo else (f_baixo > 0)
            return {"variavel": "crescimento", "valor_implicito": alto if acima else baixo,
                    "fora_do_intervalo": "acima" if acima else "abaixo"}
        for _ in range(60):
            meio = (baixo + alto) / 2
            f_meio = diferenca(meio)
            if f_meio * f_baixo > 0:
                baixo, f_baixo = meio, f_meio
            else:
                alto = meio
        return {"variavel": "crescimento", "valor_implicito": (baixo + alto) / 2, "fora_do_intervalo": False}
    except ErroValuation:
        return None
