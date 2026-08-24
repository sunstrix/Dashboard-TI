# 💻 Dashboard de Inventário de TI — Grupo NSF

> Painel de controle interativo para o **inventário de hardware, periféricos, celulares e garantias** de toda a rede do **Grupo NSF**.
> O dashboard lê os snapshots gerados pelo script de coleta (**CPFANI Hardware Snapshot**), consolida tudo em um inventário unificado e entrega visualizações em tempo real para decisões rápidas de upgrade, suporte remoto e manutenção preventiva.

![Versão](https://img.shields.io/badge/versão-2.0.0-05BFDB) ![Status](https://img.shields.io/badge/status-produção-2ea043) ![Streamlit](https://img.shields.io/badge/Streamlit-1.62-FF4B4B?logo=streamlit&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white) ![pandas](https://img.shields.io/badge/pandas-2.2+-150458?logo=pandas&logoColor=white) ![Plotly](https://img.shields.io/badge/Plotly-5.22+-0F5B99?logo=plotly&logoColor=white) ![Google Drive](https://img.shields.io/badge/Google%20Drive-API%20v3-4285F4?logo=googledrive&logoColor=white)

---

## 📑 Sumário

- [✨ Funcionalidades](#-funcionalidades)
- [🏗️ Arquitetura e Fluxo de Dados](#-arquitetura-e-fluxo-de-dados)
- [🛠️ Stack Tecnológica](#-stack-tecnológica)
- [📋 Pré-requisitos](#-pré-requisitos)
- [🚀 Instalação](#-instalação)
- [⚙️ Configuração (.env)](#-configuração-env)
- [▶️ Como Executar](#-como-executar)
- [📂 Estrutura do Projeto](#-estrutura-do-projeto)
- [📄 Formato do Snapshot](#-formato-do-snapshot)
- [🔁 Regra de Deduplicação](#-regra-de-deduplicação)
- [☁️ Fontes de Dados](#-fontes-de-dados)
- [🎨 Identidade Visual](#-identidade-visual)
- [🔄 Atualização dos Dados](#-atualização-dos-dados)
- [🔒 Segurança](#-segurança)
- [🧭 Changelog](#-changelog)
- [❓ Troubleshooting](#-troubleshooting)
- [🤝 Contribuições](#-contribuições)
- [📞 Contato](#-contato)

---

## ✨ Funcionalidades

### 🏢 Inventário Administrativo (Computadores)
- ✅ Leitura automática dos snapshots `.txt` da pasta pública do Google Drive
- ✅ Deduplicação inteligente por Hardware ID (UUID), mantendo o snapshot mais recente
- ✅ KPIs de alerta: total de máquinas, AMD vs Intel, RAM baixa (< 8 GB) e snapshot mais antigo
- ✅ Indicador 🔴/🟢 de máquinas desatualizadas (sem atualização há +30 dias)
- ✅ Gráficos interativos: distribuição por Local, Top 10 Processadores e versões do Windows
- ✅ Busca livre + filtros por Local, Usuário, SO e Processador
- ✅ AnyDesk e TeamViewer visíveis em cada linha para acesso remoto rápido

### 📱 Celulares Administrativos
- ✅ Leitura direta da planilha **Relatório_Dispositivos** (Google Sheets)
- ✅ Categorização automática de Local via código BPCS (coluna *Identificação*)
- ✅ Status de comunicação (🟢 OK /  Desatualizado) com base em *Dias sem comunicação*
- ✅ KPIs, gráficos e filtros por Local, Política, Modelo e Status

### 🖨️ Periféricos (Monitores e Impressoras)
- ✅ Extração automática das seções `PERIFÉRICOS` dos snapshots
- ✅ Filtro de seriais inválidos (`0`, `N/A`, `-`, `null`, `s/n`… — case-insensitive)
- ✅ Inventário dedicado com modelo, nº de série, IP (SNMP) e usuário

### 📊 Inventário GB (Garantias)
- ✅ Leitura da planilha **PDV** com mapeamento BPCS → Local
- ✅ Status de garantia: 🟢 Válida / 🟡 Próxima do Vencimento (90 dias) / 🔴 Vencida
- ✅ KPIs e gráficos por Local, Tipo e Modelo

### 🧰 Recursos Gerais
- ✅ Exportação **CSV** (padrão Excel PT-BR: `;` + UTF-8 BOM) e **Excel (.xlsx)** em todas as abas
- ✅ Filtros persistentes entre abas/recarregamentos + botão **🔄 Resetar Filtros**
- ✅ Auditoria de duplicatas em painel expansível
- ✅ Cache de 1 hora (protege a cota das APIs do Google)
- ✅ Retry automático com backoff exponencial (3 tentativas)
- ✅ Validação de conteúdo baixado do Drive (páginas de erro/HTML são barradas com aviso visível)
- ✅ Todos os timestamps no Horário de Brasília (UTC-3)
- ✅ Interface premium em modo escuro (Azul Petróleo + Ciano)

---

## 🏗️ Arquitetura e Fluxo de Dados

```
┌──────────────────────────┐    ┌───────────────────────────┐
│  GOOGLE DRIVE (público)  │    │  GOOGLE SHEETS (públicas) │
│  Snapshots .txt          │    │  GB (PDV) · Celulares     │
└────────────┬─────────────┘    └─────────────┬─────────────┘
             ▼                                ▼
     drive_client.py                  sheets_client.py
     (API v3 + retry +                (CSV público +
      validação de conteúdo)           fallback de GID)
             └────────────┬───────────────────┘
                          ▼
                      parser.py
             (parsing, deduplicação,
           validações e sanitização)
                          ▼
                       app.py
          (Streamlit: KPIs, gráficos,
           tabelas, filtros, exports)
```

---

## 🛠️ Stack Tecnológica

| Categoria | Tecnologia |
|-----------|------------|
| **Linguagem** | Python 3.11+ |
| **Dashboard** | Streamlit |
| **Dados** | Pandas |
| **Gráficos** | Plotly |
| **Exportação Excel** | OpenPyXL |
| **HTTP / Retry** | Requests |
| **Nuvem** | Google Drive API v3 + Google Sheets (CSV público) |
| **Credenciais** | python-dotenv |

---

## 📋 Pré-requisitos

- Windows 10/11
- Conexão com a internet (acesso ao Google Drive/Sheets)
- Navegador moderno (Chrome, Edge, Firefox)
- Uma **Google Drive API Key** gratuita (guia abaixo)

> **Nota:** o script `instalar.bat` cuida de instalar o Python e todas as dependências automaticamente.

---

## 🚀 Instalação

### Passo 1 — Clone o repositório
```powershell
git clone https://github.com/sunstrix/Dashboard-TI.git
```
*Ou baixe o ZIP e extraia na sua Área de Trabalho.*

### Passo 2 — Instale as dependências
1. Navegue até `Desktop\Dashboard-TI`
2. Clique com o botão direito em **`instalar.bat`** → **"Executar como administrador"**
3. Aguarde a mensagem **"INSTALACAO CONCLUIDA COM SUCESSO!"**

O script verifica o Python, instala dependências, gera `instalar.log` e cria o atalho `executar.bat`.

### Passo 3 — Configure a API Key
1. Copie `.env.example` e renomeie para `.env`
2. Substitua o valor de `GOOGLE_DRIVE_API_KEY` pela sua chave real (guia abaixo)

---

## 🔑 Como Gerar sua Google Drive API Key (Gratuita)

<details>
<summary><b>Clique para ver o passo a passo</b></summary>

O dashboard acessa uma **pasta pública** no Google Drive. Basta uma API Key simples (sem OAuth, sem conta de serviço).

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto (ou selecione um existente)
3. Menu lateral → **"APIs e Serviços" > "Biblioteca"**
4. Pesquise por **"Google Drive API"** e clique em **"ATIVAR"**
5. Vá em **"APIs e Serviços" > "Credenciais"**
6. Clique em **"+ CRIAR CREDENCIAIS"** → **"Chave de API"**
7. Copie a chave gerada e cole no arquivo `.env`

⚠️ **Não é necessário** configurar a "Tela de permissão OAuth" (acesso apenas leitura em pasta pública).

</details>

---

## ⚙️ Configuração (.env)

| Variável | Obrigatória | Padrão (fallback) | Descrição |
|----------|:-----------:|-------------------|-----------|
| `GOOGLE_DRIVE_API_KEY` | ✅ Sim | — | Chave da API do Google Drive |
| `DRIVE_FOLDER_ID` | ❌ Não | `1EldWrM7…CsX3d` | Pasta pública dos snapshots `.txt` |
| `SHEETS_SPREADSHEET_ID` | ❌ Não | `1Vr4T1x8…KRHiA` | Planilha do Inventário GB |
| `SHEETS_GID_PDV` | ❌ Não | `1312090202` | GID da aba **PDV** |
| `SHEETS_SPREADSHEET_ID_CELULARES` | ❌ Não | `1JBJDDee…ZVct` | Planilha de Celulares Administrativos |
| `SHEETS_GID_CELULARES` | ❌ Não | `0` | GID da aba **Relatório_Dispositivos** |
| `DRIVE_FOLDER_ID_GB_PERIFERICOS` | ❌ Não | `19LF-SGi…DIGJ` | *(TODO)* Snapshots de periféricos GB |

> **Regra de ouro:** todas as variáveis opcionais já funcionam com o padrão definido no `config.py`. Defina-as apenas para apontar o dashboard para outro ambiente (ex: testes) **sem alterar código**.
> No **Streamlit Cloud**, configure em *Settings → Secrets*.

---

## ▶️ Como Executar

**Opção 1 — Duplo clique (recomendado):** execute `executar.bat`.

**Opção 2 — Terminal:**
```powershell
cd Desktop\Dashboard-TI
streamlit run app.py
```
O dashboard abre em `http://localhost:8501`.

---

## 📂 Estrutura do Projeto

```
Dashboard-TI/
│
├── app.py               # Arquivo principal do dashboard (Streamlit)
├── config.py            # Configurações centralizadas (API, cores, regras)
├── drive_client.py      # Integração com Google Drive API v3 (+ validação de conteúdo)
├── sheets_client.py     # Download das planilhas públicas via CSV (+ fallback de GID)
├── parser.py            # Parsers de snapshots/planilhas + regra de deduplicação
├── requirements.txt     # Dependências Python
├── instalar.bat         # Instalação automatizada (Windows)
├── executar.bat         # Atalho para iniciar o dashboard
├── .env                 # Variáveis de ambiente (NÃO versionado)
├── .env.example         # Template de configuração
├── .gitignore           # Arquivos ignorados pelo Git
├── .streamlit/          # Configurações do Streamlit Cloud
├── README.md            # Esta documentação
└── instalar.log         # Log da instalação (gerado automaticamente)
```

---

## 📄 Formato do Snapshot de Hardware

Cada máquina executa o script de coleta e gera um `.txt` no padrão:

```
============================================================
   SNAPSHOT CP FANI V5.9.3 (Edição Infiltrado + Self-Healing)
   Gerado em: 18/06/2026 10:59:54
============================================================
[ID]
Local : 14120 – ARPEL SBC
Usuário : Alex
[HARDWARE]
  Nome_Computador     : 14120-ALEX
  Modelo_Sistema      : A520M-D
  Processador         : AMD Ryzen 5 5600G with Radeon Graphics
  Memoria_RAM         : 31,4 GB
  Windows             : Microsoft Windows 11 Pro
  ID                  : 03000200-0400-0500-0006-000700080009
[SUPORTE]
  AnyDesk             : 1499156040
  TeamViewer          : 307448847
============================================================
PERIFÉRICOS — MONITORES
============================================================
Monitor 1:
  Modelo      : LG 24MK430
  Nº de Série : 105NTMX2A775
...
```

Arquivos nomeados no padrão: `CPFANI_Hardware_Snapshot_<ID>.txt`

---

## 🔁 Regra de Deduplicação

A pasta do Drive acumula múltiplos snapshots da mesma máquina. Regra aplicada:

| Critério | Descrição |
|----------|-----------|
| **Identificador Único** | Campo `ID` da seção `[HARDWARE]` (UUID do hardware) |
| **Critério de Seleção** | Snapshot com a data `Gerado em:` mais recente |
| **Fallback de Data** | Se `Gerado em:` ausente, usa `modifiedTime` do Drive |
| **Data Sentinela** | Sem nenhuma data válida → `01/01/1970` (máquina aparece como 🔴 Desatualizada) |
| **Resultado** | Apenas o snapshot mais recente de cada ID entra no inventário |
| **Auditoria** | Descartes registrados no expander **"📊 Auditoria de Dados"** |

⚠️ **Nome_Computador** e **nome do arquivo** NÃO são usados na deduplicação — apenas o Hardware ID é confiável.

---

## ☁️ Fontes de Dados

| Fonte | Conteúdo | Autenticação | Cache |
|-------|----------|--------------|:-----:|
| **Google Drive** | Snapshots `.txt` (computadores, monitores, impressoras) | API Key (leitura pública) | 1h |
| **Google Sheets** | Inventário GB — aba **PDV** | Link público (CSV) | 1h |
| **Google Sheets** | Celulares — aba **Relatório_Dispositivos** | Link público (CSV) | 1h |

---

## 🎨 Identidade Visual

Tema **TI Premium** (modo escuro):

| Cor | Hex | Uso |
|-----|-----|-----|
| 🔵 Azul Petróleo | `#0A4D68` | Cor primária (tecnologia/corporativo) |
| 🩵 Ciano Destaque | `#05BFDB` | KPIs, títulos, acentos |
| ⬛ Fundo Escuro | `#0e1117` | Background do app |
| ⬛ Fundo Cards | `#161b22` | Cards de métricas |
| 🟢 Verde Sucesso | `#2ea043` | Status OK |
| 🔴 Vermelho Alerta | `#da3633` | Status crítico |
| 🟡 Amarelo Atenção | `#d29922` | Status atenção |

---

## 🔄 Atualização dos Dados

- Atualização automática a cada **1 hora** (cache do Streamlit)
- Atualização imediata: botão **"🔄 Forçar Atualização dos Dados"** na sidebar, ou reinicie o app

---

## 🔒 Segurança

- ✅ `.env` no `.gitignore` — credenciais nunca são versionadas
- ✅ API Key simples (leitura pública, sem OAuth)
- ✅ IDs de infraestrutura configuráveis por variável de ambiente (fallback no `config.py`)
- ✅ Cache de 1 hora para otimizar a cota da API
- ✅ Buscas com `re.escape()` (sem regex injection)
- ✅ Sanitização de caracteres ilegais do openpyxl (exportação Excel segura)
- ✅ Retry automático com backoff exponencial
- ✅ Mensagens claras de erro (403 cota, 404 pasta, conteúdo inválido)

---

## 🧭 Changelog

### v2.0.0 — Agosto 2026 *(Fase 2)*
- 🐛 Corrigido `TypeError` tz-naive vs tz-aware em Celulares (compatível com pandas 3.x)
- 📱 Fallback para a coluna **"Dias sem comunicação"** (novo formato do relatório, sem coluna de data)
- 📊 Corrigida coluna duplicada "Tipo" na tabela/exportação do Inventário GB
- 🛡️ Downloads do Drive validados: páginas HTML/erro são barradas com aviso visível (sem falha silenciosa)
- ⚙️ IDs de infraestrutura via variáveis de ambiente (zero quebra, com fallback)
- 🔄 Botões renomeados para **"🔄 Resetar Filtros"** (UX mais clara)

### v1.1.0 — Julho 2026 *(Fase 1)*
- 🧠 Persistência de filtros entre abas e recarregamentos (`session_state`)
- 🔎 `re.escape()` em todas as buscas; `.copy()` contra `SettingWithCopyWarning`
- 🔴 RAM com erro de parsing exibida como **"🔴 Erro Parsing"** (antes aparecia como OK)
- ️ Seriais inválidos de periféricos barrados case-insensitive

### v1.0.0 — Junho 2026
- 🎉 Lançamento: inventário administrativo, deduplicação, gráficos, exportações e tema premium

---

## ❓ Troubleshooting

### "Google Drive API Key não configurada"
**Causa:** `.env` inexistente ou vazio.
**Solução:** copie `.env.example` → `.env` e insira sua chave (guia acima).

### "Erro 403: Cota da API excedida"
**Causa:** cota diária gratuita atingida.
**Solução:** aguarde algumas horas ou gere outra API Key. O cache de 1h minimiza o problema.

### "Erro 404: Pasta não encontrada"
**Causa:** `DRIVE_FOLDER_ID` incorreto ou pasta removida.
**Solução:** confira a variável no `.env`/`config.py` e o compartilhamento público da pasta.

### "⚠️ GID '0' da planilha Celulares não encontrado"
**Causa:** o GID configurado não existe na planilha; o sistema exporta a **primeira aba** como fallback automático.
**Solução (opcional):** defina `SHEETS_GID_CELULARES` no `.env`/Secrets com o GID correto da aba (número após `#gid=` na URL).

### "⚠️ Não foi possível baixar o arquivo X (página HTML)"
**Causa:** o Google Drive retornou uma página de aviso (ex: verificação de vírus) em vez do `.txt`.
**Solução:** verifique o compartilhamento/tamanho do arquivo na pasta. Ele é pulado com aviso visível **sem derrubar o painel**.

### "Nenhum arquivo de snapshot encontrado"
**Causa:** pasta do Drive vazia ou sem `.txt`.
**Solução:** execute o script de coleta em ao menos uma máquina e confirme o upload.

### "TypeError: Cannot subtract tz-naive and tz-aware…"
**Causa:** versão anterior à v2.0.0.
**Solução:** atualize o repositório (`git pull`) — corrigido na v2.0.0.

### "Python não encontrado" / "Dependências não instaladas"
**Solução:** execute `instalar.bat` como administrador e reinicie o PC; ou `pip install -r requirements.txt`.

### "Porta 8501 em uso"
**Solução:** `streamlit run app.py --server.port 8502`

---

## 🤝 Contribuições

1. Faça um fork do projeto
2. Crie uma branch (`git checkout -b feature/NovaFeature`)
3. Commit (`git commit -m 'Adiciona NovaFeature'`)
4. Push (`git push origin feature/NovaFeature`)
5. Abra um Pull Request

---

## 📞 Contato

Projeto proprietário e confidencial. Todos os direitos reservados ao **Grupo NSF**.

- **Desenvolvedor:** Alex Paulo
- **Projeto:** Dashboard de Inventário de TI — Grupo NSF
- **Versão:** 2.0.0
- **Última Atualização:** Agosto de 2026

---

**Desenvolvido com ❤️ para otimizar a gestão de infraestrutura de TI**