"""Agente de monitoramento restrito aos dois alvos de loopback do laboratório."""

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen


ALVOS = {"SW-LAB": "127.0.0.1", "AP-LAB": "127.0.0.2"}
CENARIOS = {"normal": 0, "perda_parcial": 2, "falha": 4, "recuperacao": 0}
PACOTES = 4
ENDPOINT = "http://127.0.0.1:5000/api/medicoes"


def medir(nome, cenario):
    endereco = ALVOS[nome]
    resultado = subprocess.run(
        ["ping.exe", "-n", str(PACOTES), "-w", "1000", endereco],
        capture_output=True,
        text=True,
        encoding="ascii",
        errors="replace",
        timeout=12,
        check=False,
    )
    tempos = []
    for linha in resultado.stdout.splitlines():
        resposta = re.search(r"(?:tempo|time)([=<])\s*(\d+)\s*ms.*ttl=", linha, re.I)
        if resposta:
            operador, milissegundos = resposta.groups()
            # O ping do Windows registra valores abaixo de 1 ms como 0 ms.
            tempos.append(0 if operador == "<" else int(milissegundos))

    descartes = CENARIOS[cenario] if nome == "AP-LAB" else 0
    observados = tempos[descartes:]
    recebidos = len(observados)
    return {
        "instante": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dispositivo": nome,
        "ip": endereco,
        "cenario": cenario,
        "enviados": PACOTES,
        "recebidos_icmp": len(tempos),
        "descartados_simulados": len(tempos) - recebidos,
        "recebidos": recebidos,
        "perda_pct": 100 * (PACOTES - recebidos) / PACOTES,
        "latencia_ms": round(sum(observados) / recebidos, 2) if recebidos else None,
        "disponivel": recebidos > 0,
    }


def coletar(cenario):
    for nome in ALVOS:
        medicao = medir(nome, cenario)
        requisicao = Request(
            ENDPOINT,
            data=json.dumps(medicao).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(requisicao, timeout=5) as resposta:
            yield json.load(resposta)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cenario", choices=CENARIOS, default="normal")
    parser.add_argument("--intervalo", type=float, default=10, help="Segundos entre ciclos")
    parser.add_argument("--ciclos", type=int, default=1, help="Use 0 para coletar continuamente")
    args = parser.parse_args()
    if args.intervalo <= 0 or args.ciclos < 0:
        parser.error("informe intervalo positivo e quantidade de ciclos não negativa")
    ciclo = 0
    while args.ciclos == 0 or ciclo < args.ciclos:
        for medicao in coletar(args.cenario):
            print(json.dumps(medicao, ensure_ascii=False), flush=True)
        ciclo += 1
        if args.ciclos == 0 or ciclo < args.ciclos:
            time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
