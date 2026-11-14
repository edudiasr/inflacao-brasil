"""Cada conta conferida com um exemplo feito à mão (ou na calculadora)."""

import math

import pandas as pd
import pytest

from inflacao.calculos import acumulada, em_12_meses, ganho_real, indice, juro_real, por_ano, valor_corrigido
from inflacao.coleta import _janelas


def mensal(valores, inicio="2024-01-01"):
    return pd.Series(valores, index=pd.date_range(inicio, periods=len(valores), freq="MS"))


def test_inflacao_se_multiplica_nao_se_soma():
    assert acumulada(mensal([1.0, 2.0])) == pytest.approx(3.02)
    assert acumulada(mensal([1.0, 2.0])) != pytest.approx(3.0)


def test_meses_com_deflacao():
    # sobe 10% e depois cai 10%: não volta pro mesmo lugar (1,1 x 0,9 = 0,99)
    assert acumulada(mensal([10.0, -10.0])) == pytest.approx(-1.0)


def test_indice_parte_da_base_e_ja_inclui_o_primeiro_mes():
    serie = indice(mensal([1.0, 2.0, -0.5]))
    assert list(serie.round(4)) == [101.0, 103.02, 102.5049]


def test_doze_meses_de_1_por_cento_dao_12_68():
    serie = em_12_meses(mensal([1.0] * 14))
    assert math.isnan(serie.iloc[10])  # ainda não tem 12 meses
    assert serie.iloc[11] == pytest.approx(12.6825, abs=1e-4)
    assert serie.iloc[13] == pytest.approx(12.6825, abs=1e-4)


def test_por_ano_ignora_ano_incompleto():
    serie = mensal([0.5] * 12 + [1.0] * 3)  # 2024 inteiro e 3 meses de 2025
    anos = por_ano(serie)
    assert list(anos.index) == [2024]
    assert anos[2024] == pytest.approx((1.005 ** 12 - 1) * 100)


def test_valor_corrigido():
    assert valor_corrigido(100, mensal([10.0, 10.0])) == pytest.approx(121.0)


def test_ganho_real_divide_em_vez_de_subtrair():
    assert ganho_real(10, 5) == pytest.approx(4.7619, abs=1e-4)
    assert ganho_real(5, 5) == pytest.approx(0)
    assert ganho_real(3, 5) < 0  # subiu menos que a inflação: perdeu poder de compra


def test_juro_real():
    selic = pd.Series([13.75, 10.5])
    inflacao = pd.Series([5.0, 4.5])
    assert list(juro_real(selic, inflacao).round(2)) == [8.33, 5.74]


def test_janelas_do_download_cobrem_o_periodo_sem_buraco():
    from datetime import date
    janelas = list(_janelas(date(2015, 1, 1), date(2026, 11, 13)))
    assert janelas == [(date(2015, 1, 1), date(2023, 12, 31)), (date(2024, 1, 1), date(2026, 11, 13))]
    assert list(_janelas(date(2015, 1, 1), date(2015, 6, 1))) == [(date(2015, 1, 1), date(2015, 6, 1))]
