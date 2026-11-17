"""Coletor de monitoramento: mede os alvos com ping (ICMP) e envia as medições à API.

Tolerância a falhas: se a API não responder, a medição vai para uma fila local
gravada em disco (/dados/fila.jsonl). A cada ciclo o coletor tenta esvaziar a fila,
da medição mais antiga para a mais nova, antes de enviar as novas.

Configuração por variáveis de ambiente (veja docker-compose.yml):
  ALVOS      lista NOME=IP separada por vírgulas, ex.: SW-LAB=192.168.10.10,AP-LAB=192.168.10.11
  API_URL    endereço da API, ex.: http://192.168.10.30:5000
  INTERVALO  segundos entre o início de dois ciclos (padrão 5)
  PACOTES    pacotes ICMP por alvo em cada ciclo (padrão 4)
"""

import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000").rstrip("/")
INTERVALO = float(os.environ.get("INTERVALO", 5))
PACOTES = int(os.environ.get("PACOTES", 4))
FILA = Path(os.environ.get("FILA", "/dados/fila.jsonl"))
TIMEOUT_HTTP = 3


def ler_alvos(texto):
    alvos = {}
    for par in filter(None, (p.strip() for p in texto.split(","))):
        nome, _, ip = par.partition("=")
        if not nome or not ip:
            sys.exit(f"Alvo mal configurado: {par!r}. Use NOME=IP.")
        alvos[nome.strip()] = ip.strip()
    if not alvos:
        sys.exit("Nenhum alvo configurado na variável ALVOS.")
    return alvos


ALVOS = ler_alvos(os.environ.get("ALVOS", "SW-LAB=127.0.0.1"))


def log(mensagem):
    hora = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"{hora} {mensagem}", flush=True)


def comando_ping(ip):
    if platform.system() == "Windows":
        # Permite testar o coletor fora do Docker num computador Windows.
        return ["ping", "-n", str(PACOTES), "-w", "1000", ip]
    # Linux (contêiner): -i 0.2 envia um pacote a cada 200 ms, -W 1 espera 1 s por resposta.
    return ["ping", "-n", "-c", str(PACOTES), "-i", "0.2", "-W", "1", ip]


def medir(nome, ip, ciclo):
    instante = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    try:
        saida = subprocess.run(comando_ping(ip), capture_output=True, text=True,
                               timeout=PACOTES * 2 + 5, check=False).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as erro:
        log(f"[ciclo {ciclo}] ping para {nome} falhou: {erro}")
        saida = ""
    # Uma linha por resposta: "time=0.052 ms" (Linux) ou "tempo=1ms"/"tempo<1ms" (Windows)
    # No Windows, "tempo<1ms" significa abaixo da resolução do comando: registrado como 0.
    tempos = [0.0 if operador == "<" else float(valor.replace(",", ".")) for operador, valor in
              re.findall(r"(?:time|tempo)([=<])\s*([\d.,]+)\s*ms", saida, re.I)]
    recebidos = min(len(tempos), PACOTES)
    return {
        "instante": instante,
        "dispositivo": nome,
        "ip": ip,
        "ciclo": ciclo,
        "enviados": PACOTES,
        "recebidos": recebidos,
        "perda_pct": round(100 * (PACOTES - recebidos) / PACOTES, 2),
        "latencia_ms": round(sum(tempos[:recebidos]) / recebidos, 3) if recebidos else None,
        "disponivel": recebidos > 0,
    }


def enviar(medicao):
    """Envia uma medição. Devolve o tempo de resposta em ms, ou lança OSError."""
    requisicao = Request(f"{API_URL}/api/medicoes", data=json.dumps(medicao).encode(),
                         headers={"Content-Type": "application/json"}, method="POST")
    inicio = time.perf_counter()
    try:
        with urlopen(requisicao, timeout=TIMEOUT_HTTP) as resposta:
            resposta.read()
    except HTTPError as erro:
        if erro.code == 400:
            # Medição rejeitada pela validação: não adianta reenviar.
            log(f"API rejeitou a medição ({erro.read().decode(errors='replace')}): {medicao}")
            return None
        raise
    return (time.perf_counter() - inicio) * 1000


def ler_fila():
    if not FILA.exists():
        return []
    with FILA.open(encoding="utf-8") as arquivo:
        return [json.loads(linha) for linha in arquivo if linha.strip()]


def gravar_fila(medicoes):
    FILA.parent.mkdir(parents=True, exist_ok=True)
    temporario = FILA.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        for medicao in medicoes:
            arquivo.write(json.dumps(medicao, ensure_ascii=False) + "\n")
    temporario.replace(FILA)


def esvaziar_fila():
    """Reenvia a fila em ordem. Para no primeiro erro e mantém o restante."""
    pendentes = ler_fila()
    if not pendentes:
        return True
    enviados = 0
    inicio = time.perf_counter()
    try:
        for medicao in pendentes:
            enviar(medicao)
            enviados += 1
    except (URLError, OSError):
        pass
    if enviados:
        gravar_fila(pendentes[enviados:])
        duracao = time.perf_counter() - inicio
        log(f"FILA: {enviados} medição(ões) reenviada(s) em {duracao:.2f} s; "
            f"restam {len(pendentes) - enviados}")
    return enviados == len(pendentes)


def processar(medicao, fila_vazia):
    texto = (f"[ciclo {medicao['ciclo']}] {medicao['dispositivo']} ({medicao['ip']}): "
             f"{medicao['recebidos']}/{medicao['enviados']} respostas, "
             f"perda {medicao['perda_pct']:g}%, latência "
             + (f"{medicao['latencia_ms']} ms" if medicao["latencia_ms"] is not None else "—")
             + (", DISPONÍVEL" if medicao["disponivel"] else ", INDISPONÍVEL"))
    motivo = "fila ainda com medições antigas"
    if fila_vazia:
        try:
            tempo = enviar(medicao)
            if tempo is not None:
                log(f"{texto} | POST ok em {tempo:.1f} ms")
            return True
        except (URLError, OSError) as erro:
            motivo = f"API indisponível: {getattr(erro, 'reason', erro)}"
    # API fora do ar, ou ainda há medições antigas na fila: guarda para manter a ordem.
    fila = ler_fila()
    fila.append(medicao)
    gravar_fila(fila)
    log(f"{texto} | {motivo} | guardada na fila local ({len(fila)} pendente(s))")
    return False


def main():
    log(f"Coletor iniciado | API {API_URL} | alvos {ALVOS} | "
        f"{PACOTES} pacotes por alvo a cada {INTERVALO:g} s")
    pendentes = len(ler_fila())
    if pendentes:
        log(f"FILA: {pendentes} medição(ões) pendente(s) de execução anterior")
    ciclo = 0
    while True:
        ciclo += 1
        inicio = time.monotonic()
        fila_vazia = esvaziar_fila()
        for nome, ip in ALVOS.items():
            fila_vazia = processar(medir(nome, ip, ciclo), fila_vazia) and fila_vazia
        time.sleep(max(0.0, INTERVALO - (time.monotonic() - inicio)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Coletor encerrado.")
