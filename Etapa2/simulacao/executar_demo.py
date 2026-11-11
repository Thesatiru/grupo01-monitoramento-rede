"""Executa e verifica os quatro cenários, registrando as medições da API."""

import argparse
import json
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

from werkzeug.serving import make_server

from api import BANCO, criar_app
from monitor import CENARIOS, ENDPOINT, PACOTES, coletar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registro", type=Path, help="Caminho para salvar a saída do teste")
    args = parser.parse_args()
    servidor = make_server("127.0.0.1", 5000, criar_app())
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    linhas = ["Laboratório Grupo 01 | Python/ICMP → HTTP JSON → Flask → SQLite"]
    try:
        registros = []
        for cenario, descartes in CENARIOS.items():
            linhas.append(f"\n[{cenario}]")
            for medicao in coletar(cenario):
                esperado = descartes if medicao["dispositivo"] == "AP-LAB" else 0
                if (
                    medicao["recebidos_icmp"] != PACOTES
                    or medicao["descartados_simulados"] != esperado
                    or medicao["recebidos"] != PACOTES - esperado
                ):
                    raise RuntimeError(f"Medição inesperada: {medicao}")
                registros.append(medicao)
                linhas.append(f"POST 201 {json.dumps(medicao, ensure_ascii=False)}")

        with urlopen(ENDPOINT, timeout=5) as resposta:
            consultados = {m["id"]: m for m in json.load(resposta)}
        if any(consultados.get(m["id"]) != m for m in registros):
            raise RuntimeError("As medições lidas pelo painel não correspondem às gravadas.")
        linhas.append(f"\nGET 200 | {len(registros)} registros conferidos no SQLite pela API.")
        linhas.append(f"Banco local: {BANCO.name}")
        linhas.append("Resultado: operação normal, perda parcial, falha e recuperação verificadas.")
    finally:
        servidor.shutdown()
        thread.join()
        servidor.server_close()
        texto = "\n".join(linhas) + "\n"
        print(texto, end="")
        if args.registro:
            args.registro.parent.mkdir(parents=True, exist_ok=True)
            args.registro.write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
