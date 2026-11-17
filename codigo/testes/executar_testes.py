"""Executa os testes T01 a T04 e salva as saídas dos comandos na pasta evidencias/.

Uso, na pasta codigo/ com o sistema já iniciado (docker compose up -d --build):
  python testes/executar_testes.py            todos os testes
  python testes/executar_testes.py T02        só um teste

O script para nos momentos em que é preciso tirar um print do painel
(http://localhost:8501). Tire o print, salve com o nome indicado e aperte Enter.
Funciona no Windows (PowerShell) e no Linux; precisa só do Python 3 e do Docker.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

RAIZ = Path(__file__).resolve().parents[2]          # raiz do repositório
EVIDENCIAS = RAIZ / "evidencias"
PASTA_CODIGO = Path(__file__).resolve().parents[1]  # pasta codigo/
API_HOST = "http://localhost:5000"


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def rodar(evidencia, descricao, comando):
    """Roda um comando, mostra a saída e grava em evidencias/<evidencia>.txt."""
    print(f"\n>>> [{evidencia}] {descricao}\n$ {' '.join(comando)}")
    resultado = subprocess.run(comando, cwd=PASTA_CODIGO, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    saida = (resultado.stdout + resultado.stderr).strip()
    print(saida)
    EVIDENCIAS.mkdir(exist_ok=True)
    texto = (f"Evidência {evidencia} – {descricao}\nData e hora: {agora()}\n"
             f"Comando: {' '.join(comando)}\n{'-' * 70}\n{saida}\n")
    (EVIDENCIAS / f"{evidencia}.txt").write_text(texto, encoding="utf-8")
    return saida


def resumo_api(evidencia, minutos, descricao):
    print(f"\n>>> [{evidencia}] {descricao}\n$ GET {API_HOST}/api/resumo?minutos={minutos}")
    with urlopen(f"{API_HOST}/api/resumo?minutos={minutos}", timeout=5) as resposta:
        dados = json.load(resposta)
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    print(texto)
    (EVIDENCIAS / f"{evidencia}.txt").write_text(
        f"Evidência {evidencia} – {descricao}\nData e hora: {agora()}\n"
        f"Requisição: GET {API_HOST}/api/resumo?minutos={minutos}\n{'-' * 70}\n{texto}\n",
        encoding="utf-8")


def print_painel(evidencia, o_que_mostrar):
    input(f"\n*** [{evidencia}] Abra http://localhost:8501 e tire um print mostrando "
          f"{o_que_mostrar}.\n    Salve como evidencias/{evidencia}.png e aperte Enter para continuar...")


def esperar(segundos, motivo):
    print(f"\n... aguardando {segundos} s ({motivo})", flush=True)
    time.sleep(segundos)


def compose(*args):
    return ["docker", "compose", *args]


def t01():
    print("\n========== T01 – Funcionamento normal ==========")
    rodar("T01-a", "Contêineres em execução", compose("ps"))
    esperar(20, "coletor executa alguns ciclos")
    rodar("T01-b", "Log do coletor com medições enviadas à API", compose("logs", "--tail", "12", "coletor"))
    rodar("T01-c", "Latência e perda entre coletor e AP-LAB (20 pacotes ICMP)",
          compose("exec", "-T", "coletor", "ping", "-n", "-c", "20", "-i", "0.2", "192.168.10.11"))
    rodar("T01-d", "Tempo de resposta e disponibilidade da API (30 s)",
          compose("exec", "-T", "coletor", "python", "medir_api.py", "--duracao", "30"))
    print_painel("T01-e", "os dois dispositivos disponíveis e a tabela de medições")


def t02():
    print("\n========== T02 – Falha de um nó monitorado (AP-LAB desligado) ==========")
    rodar("T02-a", "Desligamento do AP-LAB", ["docker", "stop", "ap-lab"])
    esperar(60, "AP-LAB fora do ar por 1 minuto")
    rodar("T02-b", "Log do coletor durante a falha do AP-LAB", compose("logs", "--tail", "12", "coletor"))
    rodar("T02-c", "Ping manual ao AP-LAB desligado",
          compose("exec", "-T", "coletor", "ping", "-n", "-c", "4", "-W", "1", "192.168.10.11"))
    print_painel("T02-d", "o AP-LAB indisponível e o SW-LAB ainda disponível")
    rodar("T02-e", "Religamento do AP-LAB", ["docker", "start", "ap-lab"])
    esperar(15, "coletor volta a receber respostas")
    rodar("T02-f", "Log do coletor após o religamento", compose("logs", "--tail", "6", "coletor"))
    resumo_api("T02-g", 5, "Disponibilidade na janela de 5 minutos após a falha")


def t03():
    print("\n========== T03 – Falha do serviço central (API interrompida) ==========")
    print("Iniciando medição contínua da API em segundo plano (120 s)...")
    medidor = subprocess.Popen(compose("exec", "-T", "coletor", "python", "medir_api.py",
                                       "--duracao", "120"),
                               cwd=PASTA_CODIGO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace")
    esperar(20, "API funcionando normalmente antes da falha")
    rodar("T03-a", "Interrupção da API", ["docker", "stop", "api"])
    esperar(60, "API fora do ar por 1 minuto")
    rodar("T03-b", "Log do coletor guardando medições na fila", compose("logs", "--tail", "12", "coletor"))
    print_painel("T03-c", "o aviso de que a API central não respondeu")
    rodar("T03-d", "Religamento da API", ["docker", "start", "api"])
    esperar(15, "coletor reenvia a fila")
    rodar("T03-e", "Log do coletor com o reenvio da fila", compose("logs", "--tail", "15", "coletor"))
    print("Aguardando o fim da medição contínua da API...")
    saida, _ = medidor.communicate()
    (EVIDENCIAS / "T03-f.txt").write_text(
        f"Evidência T03-f – Disponibilidade e tempo de resposta da API durante a falha (120 s)\n"
        f"Data e hora: {agora()}\nComando: docker compose exec coletor python medir_api.py "
        f"--duracao 120\n{'-' * 70}\n{saida}\n", encoding="utf-8")
    print(saida[-400:])
    print_painel("T03-g", "a tabela com medições cujo horário de coleta é diferente do de gravação")


def t04():
    print("\n========== T04 – Integridade dos dados após as falhas ==========")
    rodar("T04-a", "Último ciclo executado pelo coletor", compose("logs", "--tail", "2", "coletor"))
    resumo_api("T04-b", 60, "Quantidade de ciclos gravados por dispositivo na última hora")


TESTES = {"T01": t01, "T02": t02, "T03": t03, "T04": t04}


def main():
    escolhidos = [a.upper() for a in sys.argv[1:]] or list(TESTES)
    for nome in escolhidos:
        if nome not in TESTES:
            sys.exit(f"Teste desconhecido: {nome}. Use: {', '.join(TESTES)}")
    for nome in escolhidos:
        TESTES[nome]()
    print(f"\nPronto. Evidências em texto salvas em {EVIDENCIAS}")


if __name__ == "__main__":
    main()
