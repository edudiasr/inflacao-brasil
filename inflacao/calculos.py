"""Contas de inflação. Funções pequenas e puras, cada uma com teste em tests/test_calculos.py.

O IPCA é divulgado como variação percentual de cada mês. Pra saber quanto os preços subiram num
período, não dá pra somar as variações: elas se multiplicam (juros sobre juros). Ex.: 1% e depois
2% dá 1,01 x 1,02 = 1,0302, ou seja 3,02%, e não 3%.
"""

from __future__ import annotations

import pandas as pd


def indice(variacoes_pct: pd.Series, base: float = 100.0) -> pd.Series:
    """Transforma variações mensais (%) num índice que começa em `base` no primeiro mês.

    O primeiro valor já inclui a variação do primeiro mês, então o índice representa o preço
    no fim de cada mês, partindo de `base` no fim do mês anterior ao primeiro.
    """
    return base * (1 + variacoes_pct / 100).cumprod()


def acumulada(variacoes_pct: pd.Series) -> float:
    """Variação total (%) de um conjunto de meses."""
    return float(((1 + variacoes_pct / 100).prod() - 1) * 100)


def em_12_meses(variacoes_pct: pd.Series) -> pd.Series:
    """Inflação acumulada nos últimos 12 meses, mês a mês (o número que sai no jornal)."""
    return ((1 + variacoes_pct / 100).rolling(12).apply(lambda janela: janela.prod(), raw=True) - 1) * 100


def por_ano(variacoes_pct: pd.Series) -> pd.Series:
    """Inflação de cada ano fechado (só anos com os 12 meses)."""
    agrupado = variacoes_pct.groupby(variacoes_pct.index.year)
    anos_completos = agrupado.count() == 12
    return agrupado.apply(acumulada)[anos_completos]


def valor_corrigido(valor: float, variacoes_pct: pd.Series) -> float:
    """Quanto `valor` do início do período precisaria ser hoje pra comprar a mesma coisa."""
    return valor * (1 + acumulada(variacoes_pct) / 100)


def ganho_real(variacao_nominal_pct: float, inflacao_pct: float) -> float:
    """Quanto algo subiu acima da inflação (%). Também é multiplicação, não subtração.

    Ex.: salário subiu 10% com inflação de 5% -> 1,10 / 1,05 = 1,0476 -> ganho real de 4,76%.
    """
    return ((1 + variacao_nominal_pct / 100) / (1 + inflacao_pct / 100) - 1) * 100


def juro_real(selic_pct_ano: pd.Series, inflacao_12m_pct: pd.Series) -> pd.Series:
    """Juro real aproximado: Selic do período descontada da inflação de 12 meses do mesmo período."""
    return ((1 + selic_pct_ano / 100) / (1 + inflacao_12m_pct / 100) - 1) * 100
