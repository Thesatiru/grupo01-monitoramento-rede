# Protótipo – Grupo 01 · Monitoramento da rede do campus (Etapa 3)

Cinco contêineres Docker numa rede virtual `192.168.10.0/24`, a mesma sub-rede proposta no diagrama da Etapa 2.

| Contêiner | Endereço IP | Porta | Função | Situação |
| --- | --- | --- | --- | --- |
| `sw-lab` | 192.168.10.10 | – | Representa o switch monitorado (responde ao ping) | Simulado |
| `ap-lab` | 192.168.10.11 | – | Representa o ponto de acesso monitorado (responde ao ping) | Simulado |
| `coletor` | 192.168.10.20 | – | Envia ping (ICMP) aos alvos, calcula perda e latência, envia à API; guarda em fila se a API cair | Implementado |
| `api` | 192.168.10.30 | 5000/TCP | Recebe e valida as medições, grava no SQLite, calcula disponibilidade | Implementado |
| `painel` | 192.168.10.31 | 8501/TCP | Painel Streamlit que consulta a API | Implementado |

Fluxo: `coletor → (ICMP) → sw-lab / ap-lab` · `coletor → (HTTP POST JSON) → api → SQLite` · `navegador → painel → (HTTP GET) → api`.

## 1. Pré-requisitos

- **Windows:** Docker Desktop instalado e aberto (ícone da baleia verde na bandeja). Python 3 para o roteiro de testes.
- **Linux:** Docker Engine com o plugin `docker compose` e Python 3.

Confira no terminal (PowerShell no Windows):

```
docker --version
docker compose version
python --version
```

No Linux, use `python3` no lugar de `python` se for o caso.

## 2. Subir o sistema

Na pasta `codigo/` do repositório:

```
docker compose down -v
docker compose up -d --build
docker compose ps
```

O `down -v` apaga dados de execuções anteriores, para os testes começarem do zero. A primeira execução baixa as imagens e demora alguns minutos. O `ps` deve mostrar os cinco contêineres com estado `running` (a API aparece como `healthy` depois de alguns segundos).

Abra o painel em **http://localhost:8501**. A API pode ser consultada direto em http://localhost:5000/api/resumo.

Para acompanhar o coletor ao vivo: `docker compose logs -f coletor` (Ctrl+C sai do log sem parar nada).

## 3. Executar os testes

Com o sistema rodando, na pasta `codigo/`:

```
python testes/executar_testes.py
```

O script executa T01 a T04 em sequência (cerca de 8 minutos), grava a saída de cada comando em `evidencias/T0x-y.txt` na raiz do repositório e para quando é preciso tirar um print do painel, dizendo o nome do arquivo. Dá para rodar um teste só: `python testes/executar_testes.py T03`.

| Teste | O que faz | Comandos principais |
| --- | --- | --- |
| T01 – Normal | Mede latência, perda e tempo de resposta com tudo ligado | `ping`, `medir_api.py` |
| T02 – Falha de nó | Desliga o AP-LAB por 1 min e religa | `docker stop ap-lab` / `docker start ap-lab` |
| T03 – Falha de serviço | Para a API por 1 min enquanto o coletor continua medindo, depois religa | `docker stop api` / `docker start api` |
| T04 – Integridade | Confere se todos os ciclos ficaram gravados, sem perda | `GET /api/resumo?minutos=60` |

Para o T04 fazer sentido, rode os testes até uma hora depois do `docker compose up`, sem reiniciar o coletor no meio.

## 4. Encerrar

```
docker compose down       # para e remove os contêineres (mantém os dados)
docker compose down -v    # remove também o banco e a fila
```

## Problemas comuns

- **`Pool overlaps with other one on this host`**: a rede da sua casa ou outra rede Docker já usa `192.168.10.0/24`. Rode `docker network prune` e tente de novo. Se continuar, troque `192.168.10` por `192.168.50` no `docker-compose.yml` e registre a mudança no relatório.
- **Porta 5000 ou 8501 ocupada**: feche o programa que usa a porta (o laboratório da Etapa 2, por exemplo) ou troque o lado esquerdo do mapeamento, como `"5001:5000"`.
- **Windows: `docker` não é reconhecido**: abra o Docker Desktop e espere ele terminar de iniciar.

## Arquivos

```
codigo/
├── docker-compose.yml     rede, endereços e os cinco contêineres
├── api/                   API Flask + SQLite (api.py, Dockerfile)
├── coletor/               coletor ICMP com fila (coletor.py), medidor da API (medir_api.py)
├── painel/                painel Streamlit (painel.py, Dockerfile)
└── testes/                roteiro automatizado dos testes (executar_testes.py)
```

Nenhum arquivo contém senha, token ou dado de acesso.
