"""API central: recebe as medições do coletor, grava no SQLite e atende ao painel.

Rotas
  POST /api/medicoes        grava uma medição enviada pelo coletor
  GET  /api/medicoes        últimas medições (parâmetro opcional ?limite=N)
  GET  /api/resumo          disponibilidade, perda e latência por dispositivo (?minutos=N)
  GET  /api/saude           verificação simples de que o serviço está no ar
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, jsonify, request

BANCO = Path(os.environ.get("MONITOR_DB", "/dados/monitor.db"))

CAMPOS = {
    "instante": str,       # momento da coleta (UTC, ISO 8601)
    "dispositivo": str,    # nome do alvo, ex.: AP-LAB
    "ip": str,             # endereço IPv4 do alvo
    "ciclo": int,          # número do ciclo do coletor
    "enviados": int,       # pacotes ICMP enviados
    "recebidos": int,      # respostas ICMP recebidas
    "perda_pct": (int, float),
    "latencia_ms": (int, float, type(None)),  # RTT médio; vazio quando não houve resposta
    "disponivel": bool,
}


def agora():
    return datetime.now(timezone.utc)


def conectar(banco):
    conexao = sqlite3.connect(banco, timeout=5)
    conexao.row_factory = sqlite3.Row
    return conexao


def validar(medicao):
    """Devolve uma mensagem de erro ou None se a medição for coerente."""
    if not isinstance(medicao, dict):
        return "Envie a medição como um objeto JSON."
    faltando = [campo for campo in CAMPOS if campo not in medicao]
    if faltando:
        return f"Campos ausentes: {', '.join(faltando)}."
    for campo, tipo in CAMPOS.items():
        valor = medicao[campo]
        # bool é subclasse de int em Python; evita aceitar true/false como número
        if tipo is int and isinstance(valor, bool):
            return f"Campo {campo} com tipo inválido."
        if not isinstance(valor, tipo):
            return f"Campo {campo} com tipo inválido."
    enviados, recebidos = medicao["enviados"], medicao["recebidos"]
    if enviados <= 0 or not 0 <= recebidos <= enviados:
        return "Quantidade de pacotes incoerente."
    if abs(medicao["perda_pct"] - (enviados - recebidos) * 100 / enviados) > 0.01:
        return "Percentual de perda não corresponde aos pacotes."
    if medicao["disponivel"] != (recebidos > 0):
        return "Estado de disponibilidade não corresponde às respostas."
    if recebidos == 0 and medicao["latencia_ms"] is not None:
        return "Latência informada sem nenhuma resposta."
    try:
        datetime.fromisoformat(medicao["instante"])
    except ValueError:
        return "Instante fora do formato ISO 8601."
    return None


def criar_app(banco=BANCO):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    banco = Path(banco)
    banco.parent.mkdir(parents=True, exist_ok=True)
    with closing(conectar(banco)) as conexao, conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS medicoes (
                id INTEGER PRIMARY KEY,
                instante TEXT NOT NULL,
                recebido_em TEXT NOT NULL,
                dispositivo TEXT NOT NULL,
                ip TEXT NOT NULL,
                ciclo INTEGER NOT NULL,
                enviados INTEGER NOT NULL,
                recebidos INTEGER NOT NULL,
                perda_pct REAL NOT NULL,
                latencia_ms REAL,
                disponivel INTEGER NOT NULL,
                UNIQUE (dispositivo, instante)
            )
            """
        )

    @app.get("/api/saude")
    def saude():
        return jsonify(status="ok", instante=agora().isoformat(timespec="seconds"))

    @app.post("/api/medicoes")
    def gravar():
        medicao = request.get_json(silent=True)
        erro = validar(medicao)
        if erro:
            return jsonify(erro=erro), 400
        dados = {campo: medicao[campo] for campo in CAMPOS}
        dados["recebido_em"] = agora().isoformat(timespec="seconds")
        colunas = ", ".join(dados)
        marcadores = ", ".join("?" for _ in dados)
        with closing(conectar(banco)) as conexao, conexao:
            # INSERT OR IGNORE: se o coletor reenviar a mesma medição depois de uma
            # falha (resposta perdida), ela não é gravada duas vezes.
            cursor = conexao.execute(
                f"INSERT OR IGNORE INTO medicoes ({colunas}) VALUES ({marcadores})",
                tuple(dados.values()),
            )
        if cursor.rowcount == 0:
            return jsonify(duplicada=True, **dados), 200
        return jsonify(id=cursor.lastrowid, **dados), 201

    @app.get("/api/medicoes")
    def listar():
        limite = min(max(request.args.get("limite", 100, type=int), 1), 1000)
        with closing(conectar(banco)) as conexao:
            linhas = conexao.execute(
                "SELECT * FROM medicoes ORDER BY instante DESC, id DESC LIMIT ?", (limite,)
            ).fetchall()
        medicoes = [dict(linha) for linha in linhas]
        for medicao in medicoes:
            medicao["disponivel"] = bool(medicao["disponivel"])
        return jsonify(medicoes)

    @app.get("/api/resumo")
    def resumo():
        minutos = min(max(request.args.get("minutos", 10, type=int), 1), 1440)
        inicio = (agora() - timedelta(minutes=minutos)).isoformat(timespec="seconds")
        with closing(conectar(banco)) as conexao:
            linhas = conexao.execute(
                """
                SELECT dispositivo, ip,
                       COUNT(*)                        AS ciclos,
                       SUM(disponivel)                 AS ciclos_disponiveis,
                       ROUND(100.0 * SUM(disponivel) / COUNT(*), 1) AS disponibilidade_pct,
                       ROUND(AVG(perda_pct), 1)        AS perda_media_pct,
                       ROUND(AVG(latencia_ms), 3)      AS latencia_media_ms,
                       MAX(instante)                   AS ultima_coleta
                FROM medicoes
                WHERE instante >= ?
                GROUP BY dispositivo, ip
                ORDER BY dispositivo
                """,
                (inicio,),
            ).fetchall()
            dispositivos = []
            for linha in linhas:
                item = dict(linha)
                ultima = conexao.execute(
                    "SELECT disponivel, perda_pct, latencia_ms FROM medicoes "
                    "WHERE dispositivo = ? ORDER BY instante DESC LIMIT 1",
                    (item["dispositivo"],),
                ).fetchone()
                item["disponivel_agora"] = bool(ultima["disponivel"])
                item["perda_atual_pct"] = ultima["perda_pct"]
                item["latencia_atual_ms"] = ultima["latencia_ms"]
                dispositivos.append(item)
        return jsonify(janela_minutos=minutos, gerado_em=agora().isoformat(timespec="seconds"),
                       dispositivos=dispositivos)

    return app


if __name__ == "__main__":
    criar_app().run(host="0.0.0.0", port=int(os.environ.get("PORTA", 5000)))
