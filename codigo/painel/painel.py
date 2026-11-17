"""Painel de monitoramento: consulta a API central e mostra o estado da rede."""

import json
import os
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000").rstrip("/")
ATUALIZACAO_S = 5
# Se a última coleta for mais antiga que isto, o coletor provavelmente parou.
LIMITE_ATRASO_S = 20

st.set_page_config(page_title="Monitoramento da rede | Grupo 01", layout="wide")
st.title("Monitoramento da rede do campus")
st.caption(f"Grupo 01 · API central em {API_URL} · atualização a cada {ATUALIZACAO_S} s")

janela = st.radio("Janela de cálculo da disponibilidade", [5, 10, 30, 60], index=1,
                  horizontal=True, format_func=lambda m: f"{m} min")


def consultar(caminho):
    with urlopen(f"{API_URL}{caminho}", timeout=3) as resposta:
        return json.load(resposta)


def formatar_ms(valor):
    return "—" if valor is None else f"{valor:.3f} ms"


@st.fragment(run_every=ATUALIZACAO_S)
def apresentar():
    try:
        resumo = consultar(f"/api/resumo?minutos={janela}")
        historico = consultar("/api/medicoes?limite=300")
    except (URLError, OSError) as erro:
        st.error(
            "A API central não respondeu. As medições não podem ser consultadas agora; "
            "o coletor continua medindo e guarda os dados na fila até a API voltar. "
            f"Detalhe: {getattr(erro, 'reason', erro)}"
        )
        st.caption(f"Última tentativa: {datetime.now().strftime('%H:%M:%S')}")
        return

    dispositivos = resumo["dispositivos"]
    if not dispositivos:
        st.info(f"Nenhuma medição nos últimos {janela} minutos. Verifique se o coletor está em execução.")
        return

    agora = datetime.now(timezone.utc)
    ultima = max(datetime.fromisoformat(d["ultima_coleta"]) for d in dispositivos)
    atraso = (agora - ultima).total_seconds()
    if atraso > LIMITE_ATRASO_S:
        st.warning(f"A última medição chegou há {atraso:.0f} s. O coletor pode estar parado "
                   "ou sem comunicação com a API.")

    for coluna, d in zip(st.columns(len(dispositivos)), dispositivos):
        with coluna.container(border=True):
            st.subheader(f"{d['dispositivo']} · {d['ip']}")
            if d["disponivel_agora"]:
                st.markdown(":green[**Disponível**]")
            else:
                st.markdown(":red[**Indisponível** – sem resposta ao ping]")
            c1, c2, c3 = st.columns(3)
            c1.metric("Perda (último ciclo)", f"{d['perda_atual_pct']:g}%")
            c2.metric("Latência (último ciclo)", formatar_ms(d["latencia_atual_ms"]))
            c3.metric(f"Disponibilidade ({janela} min)", f"{d['disponibilidade_pct']:g}%")
            st.caption(f"{d['ciclos_disponiveis']} de {d['ciclos']} ciclos com resposta · "
                       f"perda média {d['perda_media_pct']:g}% · latência média "
                       f"{formatar_ms(d['latencia_media_ms'])}")

    tabela = pd.DataFrame(historico)
    if tabela.empty:
        return
    tabela["instante"] = pd.to_datetime(tabela["instante"], format="ISO8601")
    tabela = tabela.sort_values("instante")

    st.subheader("Latência por ciclo (ms)")
    st.line_chart(tabela.pivot_table(index="ciclo", columns="dispositivo",
                                     values="latencia_ms", aggfunc="mean"))

    # Medições gravadas bem depois de coletadas ficaram na fila do coletor durante
    # uma falha da API. Mostradas à parte porque saem do topo da tabela geral.
    gravada = pd.to_datetime(tabela["recebido_em"], format="ISO8601")
    atraso = (gravada - tabela["instante"]).dt.total_seconds()
    reenviadas = tabela[atraso > 3]
    if not reenviadas.empty:
        st.subheader("Medições reenviadas pela fila")
        st.caption(f"{len(reenviadas)} medições foram coletadas enquanto a API estava fora do ar "
                   "e gravadas depois que ela voltou, sem perda.")
        st.dataframe(
            pd.DataFrame({
                "Coleta (UTC)": reenviadas["instante"].dt.strftime("%H:%M:%S"),
                "Gravada (UTC)": gravada[reenviadas.index].dt.strftime("%H:%M:%S"),
                "Atraso (s)": atraso[reenviadas.index].round(0).astype(int),
                "Ciclo": reenviadas["ciclo"],
                "Dispositivo": reenviadas["dispositivo"],
                "Estado": reenviadas["disponivel"].map({True: "Disponível", False: "Indisponível"}),
            }).sort_values(["Ciclo", "Dispositivo"]),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Últimas medições")
    exibicao = tabela.sort_values("instante", ascending=False).head(50)
    st.dataframe(
        pd.DataFrame({
            "Coleta (UTC)": exibicao["instante"].dt.strftime("%H:%M:%S"),
            "Gravada (UTC)": pd.to_datetime(exibicao["recebido_em"], format="ISO8601").dt.strftime("%H:%M:%S"),
            "Ciclo": exibicao["ciclo"],
            "Dispositivo": exibicao["dispositivo"],
            "Estado": exibicao["disponivel"].map({True: "Disponível", False: "Indisponível"}),
            "Respostas": exibicao["recebidos"].astype(str) + "/" + exibicao["enviados"].astype(str),
            "Perda": exibicao["perda_pct"].map(lambda v: f"{v:g}%"),
            "Latência": exibicao["latencia_ms"].map(lambda v: "—" if pd.isna(v) else f"{v:.3f} ms"),
        }),
        hide_index=True,
        width="stretch",
    )
    st.caption("Quando a coleta e a gravação têm horários diferentes, a medição ficou na fila "
               "do coletor durante uma falha da API e foi reenviada depois.")


apresentar()
