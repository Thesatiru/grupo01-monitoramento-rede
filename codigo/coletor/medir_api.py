"""Mede o tempo de resposta e a disponibilidade da API por amostragem.

Faz uma requisição GET /api/saude a cada INTERVALO segundos durante DURACAO segundos
e imprime cada tentativa e um resumo no final. Usado nos testes T01 e T03.

Uso (dentro do contêiner do coletor):
  docker compose exec coletor python medir_api.py --duracao 60
"""

import argparse
import os
import statistics
import time
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("API_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--duracao", type=float, default=60, help="segundos de observação")
    parser.add_argument("--intervalo", type=float, default=1, help="segundos entre tentativas")
    args = parser.parse_args()
    url = args.url.rstrip("/") + "/api/saude"

    tempos, falhas, total = [], 0, 0
    fim = time.monotonic() + args.duracao
    print(f"Medindo {url} por {args.duracao:g} s, uma tentativa a cada {args.intervalo:g} s")
    while time.monotonic() < fim:
        total += 1
        hora = datetime.now(timezone.utc).strftime("%H:%M:%S")
        inicio = time.perf_counter()
        try:
            with urlopen(url, timeout=2) as resposta:
                resposta.read()
            ms = (time.perf_counter() - inicio) * 1000
            tempos.append(ms)
            print(f"{hora} #{total:03d} OK    {ms:7.2f} ms")
        except (URLError, OSError) as erro:
            falhas += 1
            print(f"{hora} #{total:03d} FALHA {getattr(erro, 'reason', erro)}")
        time.sleep(args.intervalo)

    print("\nResumo")
    print(f"  tentativas: {total} | respostas: {len(tempos)} | falhas: {falhas}")
    print(f"  disponibilidade: {100 * len(tempos) / total:.1f}%")
    if tempos:
        print(f"  tempo de resposta: médio {statistics.mean(tempos):.2f} ms | "
              f"mínimo {min(tempos):.2f} ms | máximo {max(tempos):.2f} ms")


if __name__ == "__main__":
    main()
