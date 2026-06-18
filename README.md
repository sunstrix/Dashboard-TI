\# 💻 Dashboard de Inventário de TI — Grupo NSF



Painel de controle interativo para \*\*inventário de hardware e suporte remoto\*\* de todas as máquinas da rede do \*\*Grupo NSF\*\*.



Este dashboard lê automaticamente os "snapshots" de hardware gerados pelo script de coleta (CPFANI Hardware Snapshot), consolida os dados em um inventário unificado e fornece visualizações em tempo real do parque de máquinas, permitindo à equipe de TI tomar decisões rápidas sobre upgrades, suporte remoto e manutenção preventiva.



\---



\## ✨ Funcionalidades



\- ✅ \*\*Inventário Consolidado\*\*: Leitura automática de todos os snapshots `.txt` de uma pasta pública do Google Drive

\- ✅ \*\*Deduplicação Inteligente\*\*: Identificação única por Hardware ID (UUID), mantendo apenas o snapshot mais recente por máquina

\- ✅ \*\*KPIs de Alerta\*\*: Total de máquinas, distribuição AMD vs Intel, alerta de RAM baixa (< 8GB) e snapshot mais antigo

\- ✅ \*\*Indicador de Máquinas Desatualizadas\*\*: Alerta visual (🔴/🟢) para máquinas sem atualização há mais de 30 dias (configurável)

\- ✅ \*\*Gráficos Interativos\*\*: Distribuição por Local, Top 10 Processadores e versões do Windows (Plotly)

\- ✅ \*\*Tabela Detalhada e Filtrável\*\*: Inventário completo com busca livre, filtros por Local, Usuário, SO e Processador

\- ✅ \*\*Dados de Suporte Remoto\*\*: AnyDesk e TeamViewer visíveis em cada linha para acesso rápido

\- ✅ \*\*Exportação\*\*: Download dos dados filtrados em CSV (compatível Excel PT-BR) ou Excel (.xlsx)

\- ✅ \*\*Auditoria de Duplicatas\*\*: Log expansível mostrando quais snapshots foram descartados e por quê

\- ✅ \*\*Dados em Tempo Real\*\*: Leitura direta do Google Drive via API v3 com cache de 1 hora

\- ✅ \*\*Interface Premium\*\*: Design moderno em modo escuro com tema TI (Azul Petróleo + Ciano)

\- ✅ \*\*Retry Automático\*\*: Downloads com até 3 tentativas automáticas em caso de falha de rede

\- ✅ \*\*Horário de Brasília\*\*: Todos os timestamps exibidos no fuso UTC-3



\---



\## 🛠️ Stack Tecnológica



\- \*\*Python 3.11+\*\* — Linguagem principal

\- \*\*Streamlit\*\* — Framework para dashboards web interativos

\- \*\*Pandas\*\* — Manipulação e análise de dados

\- \*\*Plotly\*\* — Visualizações gráficas interativas

\- \*\*OpenPyXL\*\* — Exportação para Excel

\- \*\*Requests\*\* — Download de arquivos com retry automático

\- \*\*Google Drive API v3\*\* — Fonte de dados em nuvem (pasta pública)

\- \*\*python-dotenv\*\* — Gerenciamento seguro de credenciais



\---



\## 📋 Pré-requisitos



Antes de começar, certifique-se de ter:



\- Windows 10/11

\- Conexão com a internet (para acessar a pasta do Google Drive)

\- Navegador web moderno (Chrome, Edge, Firefox)

\- Uma \*\*Google Drive API Key\*\* gratuita (veja o guia abaixo)



\*\*Nota:\*\* O script de instalação automatizada (`instalar.bat`) cuidará de instalar o Python e todas as dependências necessárias.



\---



\## 🚀 Instalação



\### Passo 1: Clone o repositório



Abra o terminal (PowerShell ou CMD) e execute:



&#x20;   git clone https://github.com/sunstrix/Dashboard-TI.git



Ou baixe o ZIP e extraia na sua Área de Trabalho.



\### Passo 2: Instale as dependências



\- Navegue até a pasta do projeto: `Desktop\\Dashboard-TI`

\- Clique com o botão direito no arquivo `instalar.bat` e selecione \*\*"Executar como administrador"\*\*

\- Aguarde a conclusão do processo. O script irá:

&#x20; - ✅ Verificar se o Python já está instalado

&#x20; - ✅ Baixar e instalar o Python 3.11 (se necessário, via winget)

&#x20; - ✅ Instalar todas as dependências do projeto

&#x20; - ✅ Gerar um arquivo de log detalhado (`instalar.log`)

&#x20; - ✅ Criar automaticamente o atalho `executar.bat`

\- Ao final, você verá a mensagem: \*\*"INSTALACAO CONCLUIDA COM SUCESSO!"\*\*



\### Passo 3: Configure a API Key



1\. Copie o arquivo `.env.example` e renomeie para `.env`

2\. Abra o `.env` e substitua o valor de `GOOGLE\_DRIVE\_API\_KEY` pela sua chave real (veja como gerar abaixo)



\---



\## 🔑 Como Gerar sua Google Drive API Key (Gratuita)



O dashboard acessa uma \*\*pasta pública\*\* no Google Drive. Para isso, é necessária apenas uma API Key simples (não requer OAuth nem conta de serviço).



1\. Acesse o \[Google Cloud Console](https://console.cloud.google.com/)

2\. Crie um novo projeto (ou selecione um existente)

3\. No menu lateral, vá em \*\*"APIs e Serviços" > "Biblioteca"\*\*

4\. Pesquise por \*\*"Google Drive API"\*\* e clique em \*\*"ATIVAR"\*\*

5\. Vá em \*\*"APIs e Serviços" > "Credenciais"\*\*

6\. Clique em \*\*"+ CRIAR CREDENCIAIS"\*\* no topo e selecione \*\*"Chave de API"\*\*

7\. Copie a chave gerada e cole no arquivo `.env`



> ⚠️ \*\*Não é necessário\*\* configurar a "Tela de permissão OAuth" pois o acesso é apenas leitura em pasta pública.



\---



\## ▶️ Como Executar



\### Opção 1: Duplo clique (Recomendado)

Dê um duplo clique no arquivo `executar.bat` na raiz do projeto.



\### Opção 2: Via terminal



&#x20;   cd Desktop\\Dashboard-TI

&#x20;   streamlit run app.py



O dashboard abrirá automaticamente no navegador em `http://localhost:8501`



\---



\## 📂 Estrutura do Projeto



&#x20;   Dashboard-TI/

&#x20;   │

&#x20;   ├── app.py                      # Arquivo principal do dashboard (Streamlit)

&#x20;   ├── config.py                   # Configurações centralizadas (API, cores, regras)

&#x20;   ├── drive\_client.py             # Integração com Google Drive API v3

&#x20;   ├── parser.py                   # Parser de snapshots e regra de deduplicação

&#x20;   ├── requirements.txt            # Lista de dependências Python

&#x20;   ├── instalar.bat                # Script de instalação automatizada (Windows)

&#x20;   ├── executar.bat                # Atalho para iniciar o dashboard

&#x20;   ├── .env                        # Variáveis de ambiente (NÃO versionado)

&#x20;   ├── .env.example                # Template de configuração

&#x20;   ├── .gitignore                  # Arquivos ignorados pelo Git

&#x20;   ├── README.md                   # Este arquivo de documentação

&#x20;   └── instalar.log                # Log da instalação (gerado automaticamente)



\---



\## 📄 Formato do Snapshot de Hardware



Cada máquina da rede executa um script de coleta que gera um arquivo `.txt` com o seguinte formato:



&#x20;   ============================================================

&#x20;      SNAPSHOT CP FANI V5.9.3 (Edição Infiltrado + Self-Healing)

&#x20;      Gerado em: 18/06/2026 10:59:54

&#x20;   ============================================================

&#x20;   \[ID]

&#x20;   Local : 14120 – ARPEL SBC

&#x20;   Usuário : Alex



&#x20;   \[HARDWARE]

&#x20;     Nome\_Computador     : 14120-ALEX

&#x20;     Modelo\_Sistema      : A520M-D

&#x20;     Processador         : AMD Ryzen 5 5600G with Radeon Graphics

&#x20;     Memoria\_RAM         : 31,4 GB

&#x20;     Windows             : Microsoft Windows 11 Pro

&#x20;     ID         : 03000200-0400-0500-0006-000700080009



&#x20;   \[SUPORTE]

&#x20;     AnyDesk    : 1499156040

&#x20;     TeamViewer : 307448847



&#x20;   ============================================================



Os arquivos são nomeados no padrão: `CPFANI\_Hardware\_Snapshot\_<ID>.txt`



\---



\## 🔁 Regra de Deduplicação



A pasta do Google Drive acumula múltiplos snapshots da mesma máquina ao longo do tempo. O dashboard aplica a seguinte regra:



| Critério | Descrição |

|---|---|

| \*\*Identificador Único\*\* | Campo `ID` dentro da seção `\[HARDWARE]` (UUID do hardware) |

| \*\*Critério de Seleção\*\* | Snapshot com a data `Gerado em:` mais recente |

| \*\*Fallback de Data\*\* | Se `Gerado em:` estiver ausente, usa `modifiedTime` do Google Drive |

| \*\*Resultado\*\* | Apenas o snapshot mais recente de cada ID aparece no inventário |

| \*\*Auditoria\*\* | Snapshots descartados ficam registrados no expander "Auditoria de Dados" |



> ⚠️ O \*\*Nome\_Computador\*\* e o \*\*nome do arquivo\*\* NÃO são usados para deduplicação, pois podem mudar. Apenas o Hardware ID é confiável.



\---



\## ☁️ Fonte de Dados



\- \*\*Tipo\*\*: Pasta pública do Google Drive

\- \*\*ID da Pasta\*\*: `1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d`

\- \*\*URL\*\*: \[Acessar Pasta](https://drive.google.com/drive/u/1/folders/1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d)

\- \*\*Autenticação\*\*: API Key simples (leitura pública, sem OAuth)

\- \*\*Cache\*\*: Dados cacheados por 1 hora no Streamlit



\---



\## 🎨 Identidade Visual



O dashboard utiliza o tema \*\*TI Premium\*\* com as seguintes cores:



\- \*\*Azul Petróleo\*\*: `#0A4D68` (cor primária — tecnologia/corporativo)

\- \*\*Ciano Destaque\*\*: `#05BFDB` (KPIs, títulos, acentos)

\- \*\*Fundo Escuro\*\*: `#0e1117` (modo escuro premium Streamlit)

\- \*\*Fundo Cards\*\*: `#161b22` (cards de métricas)

\- \*\*Verde Sucesso\*\*: `#2ea043` (status OK)

\- \*\*Vermelho Alerta\*\*: `#da3633` (status crítico)

\- \*\*Amarelo Atenção\*\*: `#d29922` (status atenção)



\---



\## 🔄 Atualização dos Dados



Os dados são atualizados automaticamente a cada \*\*1 hora\*\* (cache do Streamlit).



Para forçar uma atualização imediata:

\- No dashboard, clique no botão \*\*"🔄 Forçar Atualização dos Dados"\*\* na barra lateral

\- Ou reinicie o aplicativo



\---



\## 🔒 Segurança



\- ✅ \*\*Dados Sensíveis\*\*: O arquivo `.env` está no `.gitignore` e nunca será versionado

\- ✅ \*\*Pasta Pública\*\*: O acesso ao Drive é apenas leitura, sem necessidade de OAuth

\- ✅ \*\*Cache de Dados\*\*: Os dados são cacheados por 1 hora para otimizar a cota da API

\- ✅ \*\*Retry Automático\*\*: Downloads com até 3 tentativas automáticas em caso de falha

\- ✅ \*\*Tratamento de Erros\*\*: Mensagens claras em caso de problemas de conexão ou cota



\---



\## ❓ Troubleshooting



\### "Google Drive API Key não configurada"

\*\*Causa\*\*: O arquivo `.env` não existe ou está vazio.

\*\*Solução\*\*:

\- Copie `.env.example` para `.env`

\- Insira sua API Key seguindo o guia acima



\### "Erro 403: Cota da API excedida"

\*\*Causa\*\*: A cota diária gratuita da API foi atingida.

\*\*Solução\*\*:

\- Aguarde algumas horas ou crie uma nova API Key

\- O cache de 1 hora ajuda a minimizar este problema



\### "Erro 404: Pasta não encontrada"

\*\*Causa\*\*: O ID da pasta no `config.py` está incorreto ou a pasta foi removida.

\*\*Solução\*\*:

\- Verifique o `DRIVE\_FOLDER\_ID` no `config.py`

\- Confirme que a pasta existe e é pública



\### "Nenhum arquivo de snapshot encontrado"

\*\*Causa\*\*: A pasta do Drive está vazia ou não contém arquivos `.txt`.

\*\*Solução\*\*:

\- Execute o script de coleta em pelo menos uma máquina

\- Verifique se os arquivos foram enviados corretamente para a pasta



\### "Python não encontrado"

\*\*Causa\*\*: O Python não foi instalado corretadamente ou não está no PATH.

\*\*Solução\*\*:

\- Execute o `instalar.bat` como administrador

\- Reinicie o computador após a instalação

\- Verifique se o Python está em: `C:\\Program Files\\Python311\\`



\### "Dependências não instaladas"

\*\*Solução\*\*:

&#x20;   pip install -r requirements.txt



\### "Porta 8501 em uso"

\*\*Solução\*\*:

&#x20;   streamlit run app.py --server.port 8502



\---



\## 🤝 Contribuições



Contribuições são bem-vindas! Para contribuir:



1\. Faça um fork do projeto

2\. Crie uma branch para sua feature (`git checkout -b feature/NovaFeature`)

3\. Commit suas mudanças (`git commit -m 'Adiciona NovaFeature'`)

4\. Push para a branch (`git push origin feature/NovaFeature`)

5\. Abra um Pull Request



\---



\## 📞 Contato



Este projeto é proprietário e confidencial. Todos os direitos reservados ao \*\*Grupo NSF\*\*.



Para dúvidas, problemas ou sugestões:



\- \*\*Desenvolvedor\*\*: Alex Paulo

\- \*\*Projeto\*\*: Dashboard de Inventário de TI — Grupo NSF

\- \*\*Versão\*\*: 1.0.0

\- \*\*Última Atualização\*\*: Junho de 2026



\---



\*\*Desenvolvido com ❤️ para otimizar a gestão de infraestrutura de TI\*\*

