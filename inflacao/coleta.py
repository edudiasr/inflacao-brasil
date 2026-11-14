"""Baixa séries do Banco Central (SGS) e guarda em CSV na pasta dados/.

A API pública é https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados — sem cadastro e sem
chave. Séries diárias só vêm em janelas de até 10 anos por pedido, por isso o download é feito
em pedaços.

    python -m inflacao.coleta            baixa o que ainda não está em dados/
    python -m inflacao.coleta --atualizar baixa tudo de novo
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

PASTA = Path(__file__).resolve().parent.parent / "dados"
URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
INICIO = date(2015, 1, 1)


@dataclass(frozen=True)
class Serie:
    codigo: int
    arquivo: str
    descricao: str
    diaria: bool = False


SERIES = [
    Serie(433, "ipca", "IPCA, variação mensal (%)"),
    Serie(1619, "salario_minimo", "Salário mínimo (R$)"),
    Serie(432, "selic", "Meta da Selic definida pelo Copom (% ao ano)", diaria=True),
    Serie(1, "dolar", "Dólar comercial, venda (R$)", diaria=True),
    # IPCA por grupo de despesa, variação mensal (%)
    Serie(1635, "ipca_alimentacao", "IPCA - Alimentação e bebidas"),
    Serie(1636, "ipca_habitacao", "IPCA - Habitação"),
    Serie(1637, "ipca_artigos_residencia", "IPCA - Artigos de residência"),
    Serie(1638, "ipca_vestuario", "IPCA - Vestuário"),
    Serie(1639, "ipca_transportes", "IPCA - Transportes"),
    Serie(1640, "ipca_comunicacao", "IPCA - Comunicação"),
    Serie(1641, "ipca_saude", "IPCA - Saúde e cuidados pessoais"),
    Serie(1642, "ipca_despesas_pessoais", "IPCA - Despesas pessoais"),
    Serie(1643, "ipca_educacao", "IPCA - Educação"),
]


def _janelas(inicio: date, fim: date, anos: int = 9):
    """Períodos de até `anos` anos cobrindo de `inicio` a `fim`, sem buraco nem sobreposição."""
    atual = inicio
    while atual <= fim:
        ate = min(date(atual.year + anos - 1, 12, 31), fim)
        yield atual, ate
        atual = date(ate.year + 1, 1, 1)


def _pedir(codigo: int, de: date, ate: date, tentativas: int = 4) -> list[dict]:
    params = {"formato": "json", "dataInicial": de.strftime("%d/%m/%Y"), "dataFinal": ate.strftime("%d/%m/%Y")}
    for tentativa in range(tentativas):
        try:
            resposta = requests.get(URL.format(codigo=codigo), params=params, timeout=60)
            if resposta.status_code == 404:
                return []  # sem dado no período
            resposta.raise_for_status()
            return resposta.json()
        except requests.RequestException:
            if tentativa == tentativas - 1:
                raise
            time.sleep(2 ** tentativa)  # a API do BC às vezes demora ou recusa; espera e tenta de novo
    return []


def baixar(serie: Serie, fim: date | None = None) -> pd.DataFrame:
    fim = fim or date.today()
    linhas: list[dict] = []
    if serie.diaria:
        for de, ate in _janelas(INICIO, fim):
            linhas += _pedir(serie.codigo, de, ate)
    else:
        linhas = _pedir(serie.codigo, INICIO, fim)
    tabela = pd.DataFrame(linhas)
    tabela["data"] = pd.to_datetime(tabela["data"], format="%d/%m/%Y")
    tabela["valor"] = pd.to_numeric(tabela["valor"])
    return tabela.drop_duplicates("data").sort_values("data").reset_index(drop=True)


def carregar(nome: str) -> pd.Series:
    """Lê uma série já baixada como pd.Series indexada pela data."""
    tabela = pd.read_csv(PASTA / f"{nome}.csv", parse_dates=["data"])
    return tabela.set_index("data")["valor"].rename(nome)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atualizar", action="store_true", help="baixa de novo mesmo o que já existe")
    args = parser.parse_args()
    PASTA.mkdir(exist_ok=True)
    for serie in SERIES:
        destino = PASTA / f"{serie.arquivo}.csv"
        if destino.exists() and not args.atualizar:
            print(f"{serie.arquivo:28s} já baixada")
            continue
        tabela = baixar(serie)
        tabela.to_csv(destino, index=False, date_format="%Y-%m-%d")
        print(f"{serie.arquivo:28s} {len(tabela):6d} linhas  {tabela['data'].min():%m/%Y} a {tabela['data'].max():%m/%Y}")


if __name__ == "__main__":
    main()
