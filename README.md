# Projeto Integrado · Etapa 2 · Diagramas Técnicos

**Fatec Ferraz de Vasconcelos | Centro Paula Souza**

Tecnologia em Análise e Desenvolvimento de Sistemas

Redes de Computadores, Sistemas Distribuídos e Inglês

Entrega em 10/11/2026

## Identificação do grupo

| Grupo | Tema |
| --- | --- |
| 01 | Monitoramento da rede do campus |

**Título da solução**

Sistema Distribuído de Monitoramento e Análise de Desempenho da Rede Universitária

| Integrante | Nome completo | RA | Função |
| --- | --- | --- | --- |
| 1 | Fernando Eric Freitas da Silva | Não informado | Integrante |
| 2 | João Pedro Chagas Slengman | Não informado | Líder |
| 3 | Kaue Boscariol Bertolino | Não informado | Integrante |
| 4 | Leonardo Quintino de Amorim | Não informado | Integrante |
| 5 | Marcus Vinicius Cardoso Ferreira | Não informado | Integrante |
| 6 | Rafael Lana dos Santos | Não informado | Gestor |

## Descrição da solução

Um agente Python verifica a conectividade dos dispositivos com ICMP (ping) e reúne disponibilidade, latência e perda de pacotes. O agente envia as medições em JSON por HTTP para uma API Flask, que grava o histórico em SQLite. O painel Streamlit consulta os resultados e mostra o estado de cada dispositivo.

O diagrama de rede propõe uma sub-rede de campus (`192.168.10.0/24`) com um switch e um ponto de acesso monitorados, o agente de coleta, o servidor central e o computador do usuário. O laboratório demonstra a coleta, a API, a gravação e a visualização usando dois endereços de loopback como alvos (`SW-LAB` em `127.0.0.1` e `AP-LAB` em `127.0.0.2`). Cada ciclo envia quatro pings por alvo. A perda parcial e a indisponibilidade de `AP-LAB` são simuladas por descarte de respostas no agente. A latência medida em loopback caracteriza somente o laboratório.

## Arquivos da Etapa 2

| Arquivo ou pasta | Conteúdo |
| --- | --- |
| [Documento em PDF](Etapa2/Grupo01_Etapa2_DiagramasTecnicos.pdf) | Diagramas, fluxo, legenda técnica, componentes, protocolos e análise de falha |
| [Documento editável em Word](Etapa2/Grupo01_Etapa2_DiagramasTecnicos.docx) | Modelo da atividade preenchido |
| Rede ([imagem](Etapa2/diagramas/rede.png), [fonte editável](Etapa2/diagramas/rede.drawio)) | Topologia proposta, endereçamento e percurso dos dados |
| Arquitetura ([imagem](Etapa2/diagramas/arquitetura.png), [fonte editável](Etapa2/diagramas/arquitetura.drawio)) | Componentes do sistema e comunicação entre eles |
| [Simulação](Etapa2/simulacao/) | Código e dependências da demonstração local |
| [Evidências](Etapa2/evidencias/) | Resultados e capturas dos testes de disponibilidade e recuperação |

## Reproduzir a demonstração

Em um terminal do Windows na raiz do repositório, com Python 3 instalado, execute:

```text
python -m pip install -r Etapa2/simulacao/requirements.txt
python Etapa2/simulacao/executar_demo.py
```

O teste registrou oito medições, duas por cenário, e confirmou pela API a gravação no SQLite. A perda de `AP-LAB` foi de 0% na operação normal, 50% na perda parcial, 100% na falha simulada e 0% na recuperação. `SW-LAB` permaneceu disponível com 0% de perda nos quatro cenários. As respostas de loopback registraram 0 ms dentro da resolução do ping. Na falha de `AP-LAB`, a medição de latência ficou sem valor. [Registro da execução](Etapa2/evidencias/execucao_demo.txt)

Para visualizar os resultados no painel depois do teste, execute cada comando em um terminal separado e mantenha os dois abertos.

```text
python Etapa2/simulacao/api.py
python -m streamlit run Etapa2/simulacao/painel.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Abra `http://127.0.0.1:8501` e selecione um cenário no painel.

## Ferramentas utilizadas

| Ferramenta ou tecnologia | Uso no projeto |
| --- | --- |
| Draw.io | Fontes editáveis dos diagramas |
| Python 3 | Executar o agente, o teste automatizado e a simulação de falha |
| `ping` / ICMP sobre IPv4 | Verificar conectividade e medir latência e perda de pacotes no laboratório |
| Flask / HTTP / JSON | Receber as medições e permitir a consulta dos resultados |
| SQLite | Armazenar o histórico das medições |
| Streamlit | Exibir o estado e as métricas dos dispositivos |
| GitHub | Disponibilizar a documentação, os diagramas e as evidências |

## Organização do Projeto Integrado

O planejamento está na pasta `01_Plano_de_Projeto`. As demais pastas do projeto acompanham o cronograma geral de diagramas (`02_Diagrama_da_Rede` e `03_Arquitetura`), implementação (`codigo`), testes (`04_Testes`), relatório (`05_Relatorio`), glossário (`06_Glossario`) e apresentação (`07_Apresentacao`). [Plano de Projeto](01_Plano_de_Projeto/Plano%20de%20Projeto%20-%20ABNT.pdf)

## Uso de inteligência artificial

| Informação solicitada | Registro |
| --- | --- |
| Ferramenta utilizada e data de uso | ChatGPT (Codex, OpenAI), 10/11/2026 |
| Para que a ferramenta foi utilizada | Interpretar o modelo, estruturar a documentação e os diagramas, preparar a demonstração local e verificar os arquivos da entrega. |
| O que o grupo revisou, corrigiu ou alterou | A revisão pelos integrantes ainda precisa ser registrada pelo grupo. |
