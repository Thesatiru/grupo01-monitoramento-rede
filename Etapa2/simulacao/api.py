"""API de recepção e consulta de medições do laboratório."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, jsonify, request

from monitor import ALVOS, CENARIOS, PACOTES


BANCO = Path(os.environ.get("MONITOR_DB", Path(__file__).parent / ".dados" / "monitor.db"))
COLUNAS = (
    "instante", "dispositivo", "ip", "cenario", "enviados", "recebidos_icmp",
    "descartados_simulados", "recebidos", "perda_pct", "latencia_ms", "disponivel",
)


def criar_app(banco=BANCO):
    app = Flask(__name__)
    banco = Path(banco)
    banco.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(banco)) as conexao, conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS medicoes (
                id INTEGER PRIMARY KEY,
                instante TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                ip TEXT NOT NULL,
                cenario TEXT NOT NULL,
                enviados INTEGER NOT NULL,
                recebidos_icmp INTEGER NOT NULL,
                descartados_simulados INTEGER NOT NULL,
                recebidos INTEGER NOT NULL,
                perda_pct REAL NOT NULL,
                latencia_ms REAL,
                disponivel INTEGER NOT NULL
            )
        """)

    @app.post("/api/medicoes")
    def gravar_medicao():
        medicao = request.get_json(silent=True)
        if not isinstance(medicao, dict) or set(medicao) != set(COLUNAS):
            return jsonify(erro="Envie os campos de uma medição em JSON."), 400
        nome, cenario = medicao["dispositivo"], medicao["cenario"]
        if not isinstance(nome, str) or nome not in ALVOS or medicao["ip"] != ALVOS[nome]:
            return jsonify(erro="Dispositivo fora do laboratório."), 400
        if not isinstance(cenario, str) or cenario not in CENARIOS:
            return jsonify(erro="Cenário desconhecido."), 400
        recebidos = medicao["recebidos"]
        recebidos_icmp = medicao["recebidos_icmp"]
        descartados = medicao["descartados_simulados"]
        latencia = medicao["latencia_ms"]
        if (
            not isinstance(medicao["instante"], str)
            or medicao["enviados"] != PACOTES
            or any(type(n) is not int for n in (recebidos, recebidos_icmp, descartados))
            or not 0 <= recebidos <= recebidos_icmp <= PACOTES
            or descartados != recebidos_icmp - recebidos
            or medicao["perda_pct"] != (PACOTES - recebidos) * 100 / PACOTES
            or medicao["disponivel"] is not (recebidos > 0)
            or (recebidos and (type(latencia) not in (int, float) or not 0 <= latencia <= 1000))
            or (not recebidos and latencia is not None)
        ):
            return jsonify(erro="Métricas inconsistentes."), 400
        with closing(sqlite3.connect(banco)) as conexao, conexao:
            cursor = conexao.execute(
                f"INSERT INTO medicoes ({', '.join(COLUNAS)}) VALUES ({', '.join('?' for _ in COLUNAS)})",
                tuple(medicao[chave] for chave in COLUNAS),
            )
        return jsonify(id=cursor.lastrowid, **medicao), 201

    @app.get("/api/medicoes")
    def listar_medicoes():
        with closing(sqlite3.connect(banco)) as conexao:
            conexao.row_factory = sqlite3.Row
            linhas = conexao.execute("SELECT * FROM medicoes ORDER BY id DESC LIMIT 100")
            medicoes = [dict(linha) for linha in linhas]
        for medicao in medicoes:
            medicao["disponivel"] = bool(medicao["disponivel"])
        return jsonify(medicoes)

    return app


if __name__ == "__main__":
    criar_app().run(host="127.0.0.1", port=5000)
