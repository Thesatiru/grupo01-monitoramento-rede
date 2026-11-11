# Laboratório local de monitoramento da rede do campus

O laboratório executa o agente Python, a API Flask, o armazenamento SQLite e o painel Streamlit no mesmo computador Windows. O switch SW-LAB e o ponto de acesso AP-LAB são representados por endereços da interface de loopback. Os pacotes ICMP são enviados somente para esses endereços.

| Componente | Endereço | Comunicação |
| --- | --- | --- |
| Switch SW-LAB simulado | `127.0.0.1` | ICMP Echo |
| Ponto de acesso AP-LAB simulado | `127.0.0.2` | ICMP Echo |
| API Flask | `127.0.0.1:5000/api/medicoes` | POST e GET HTTP com JSON |
| Banco SQLite | `.dados/monitor.db` | Arquivo local, consultado pela API com SQL |
| Painel Streamlit | `127.0.0.1:8501` | Consulta a API e exibe as métricas no navegador |

## Reproduzir a demonstração

Use Windows com Python 3.12 e mantenha livres as portas TCP 5000 e 8501. A partir da raiz do repositório, execute no PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Etapa2/simulacao/requirements.txt
.\.venv\Scripts\python.exe Etapa2/simulacao/executar_demo.py
```

O teste inicia a API, envia quatro pacotes ICMP para cada endereço em cada cenário, confere as oito gravações pelo GET da API e encerra o servidor. O histórico permanece no SQLite. Acrescente `--registro Etapa2/simulacao/.dados/execucao.txt` ao último comando para salvar a saída.

Para visualizar o histórico, inicie a API e o painel em dois terminais na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe Etapa2/simulacao/api.py
```

```powershell
.\.venv\Scripts\python.exe -m streamlit run Etapa2/simulacao/painel.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Abra [o painel](http://127.0.0.1:8501) e escolha um cenário no seletor. Com a API ativa, é possível coletar novos dados no terceiro terminal com `.\.venv\Scripts\python.exe Etapa2/simulacao/monitor.py --ciclos 0 --intervalo 10`. O intervalo é aplicado após concluir cada ciclo.

## Cenários esperados

| Cenário | SW-LAB | AP-LAB | Intervenção |
| --- | --- | --- | --- |
| Operação normal | 4/4, 0% de perda | 4/4, 0% de perda | Usa todas as respostas ICMP recebidas |
| Perda parcial | 4/4, 0% de perda | 2/4, 50% de perda | Coletor desconsidera duas respostas reais de AP-LAB |
| Falha de conectividade | 4/4, 0% de perda | 0/4, 100% de perda | Coletor desconsidera quatro respostas reais de AP-LAB |
| Recuperação | 4/4, 0% de perda | 4/4, 0% de perda | Coletor volta a usar todas as respostas |

O coletor calcula a perda pela fração de pacotes sem resposta aproveitada, marca como indisponível o equipamento com zero respostas e calcula a latência média somente entre as respostas aproveitadas. O ping do Windows mede a latência em milissegundos inteiros. A indicação `<1 ms` é registrada como `0 ms`, conforme a resolução desse comando. Com zero respostas aproveitadas, a latência fica sem valor.

A simulação verifica o tratamento das métricas e a exibição do estado. A intervenção é feita no coletor e os alvos continuam respondendo ao ping do Windows. Todos os serviços ficam no loopback. A medição não representa a latência real do campus.
