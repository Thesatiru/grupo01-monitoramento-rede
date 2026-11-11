"""Painel Streamlit para visualização das medições recebidas pela API."""

import json
from datetime import datetime
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st

from monitor import ALVOS, ENDPOINT


ROTULOS = {
    "normal": "Operação normal",
    "perda_parcial": "Perda parcial simulada",
    "falha": "Falha de conectividade simulada",
    "recuperacao": "Recuperação",
}

st.set_page_config(page_title="Monitoramento da rede | Grupo 01", layout="wide")
st.title("Monitoramento da rede do campus")
st.caption("Grupo 01 · Laboratório de loopback · 4 pacotes ICMP por equipamento")
padrao = st.query_params.get("cenario")
chaves = ["todos", *ROTULOS]
cenario = st.selectbox(
    "Cenário",
    chaves,
    index=chaves.index(padrao) if padrao in ROTULOS else 0,
    format_func=lambda chave: ROTULOS.get(chave, "Todos os cenários"),
)


@st.fragment(run_every=5)
def apresentar():
    try:
        with urlopen(ENDPOINT, timeout=3) as resposta:
            medicoes = json.load(resposta)
    except (URLError, TimeoutError):
        st.error("A API de monitoramento está indisponível.")
        return
    medicoes = [m for m in medicoes if cenario == "todos" or m["cenario"] == cenario]
    if not medicoes:
        st.info("Aguardando a primeira medição.")
        return

    mais_recentes = {}
    for medicao in medicoes:
        mais_recentes.setdefault(medicao["dispositivo"], medicao)
    for coluna, nome in zip(st.columns(len(ALVOS)), ALVOS):
        medicao = mais_recentes.get(nome)
        if medicao is None:
            continue
        estado = "Disponível" if medicao["disponivel"] else "Indisponível"
        cor = "green" if medicao["disponivel"] else "red"
        latencia = medicao["latencia_ms"]
        rtt = f"{latencia:g} ms" if latencia is not None else "—"
        with coluna.container(border=True):
            st.subheader(f"{nome} · {medicao['ip']}")
            st.markdown(f":{cor}[**{estado}**]")
            perda, tempo, respostas = st.columns(3)
            perda.metric("Perda", f"{medicao['perda_pct']:g}%")
            tempo.metric("Latência média", rtt)
            respostas.metric("Respostas", f"{medicao['recebidos']}/{medicao['enviados']}")
            st.caption(f"ICMP recebidos: {medicao['recebidos_icmp']} · "
                       f"Descartes simulados: {medicao['descartados_simulados']}")

    st.subheader("Histórico das medições")
    st.dataframe(
        [
            {
                "Hora (UTC)": datetime.fromisoformat(m["instante"]).strftime("%H:%M:%S"),
                "Equipamento": m["dispositivo"],
                "Cenário": ROTULOS[m["cenario"]],
                "Estado": "Disponível" if m["disponivel"] else "Indisponível",
                "Perda": f"{m['perda_pct']:g}%",
                "Latência": f"{m['latencia_ms']:g} ms" if m["latencia_ms"] is not None else "—",
            }
            for m in medicoes
        ],
        hide_index=True,
    )


apresentar()
