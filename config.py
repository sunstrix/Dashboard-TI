import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# ==============================================================================
# CONFIGURAÇÕES DO GOOGLE DRIVE
# ==============================================================================
# ID da pasta pública onde os snapshots .txt são salvos
DRIVE_FOLDER_ID = "1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d"

# A API Key é lida de variável de ambiente por segurança.
# Nunca hardcode a chave diretamente aqui.
GOOGLE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY", "")

# ==============================================================================
# CONFIGURAÇÕES DE CACHE E PERFORMANCE
# ==============================================================================
# Tempo de vida do cache do Streamlit (em segundos).
# 3600 segundos = 1 hora. Evita estouro de cota da API do Google.
CACHE_TTL = 3600

# ==============================================================================
# REGRAS DE NEGÓCIO
# ==============================================================================
# Número de dias sem atualização para considerar uma máquina "Desatualizada"
DIAS_LIMITE_ATRASO = 30

# Nome da empresa e do sistema para exibição no cabeçalho
NOME_EMPRESA = "Grupo NSF"
NOME_SISTEMA = "Inventário de Hardware & Suporte"

# ==============================================================================
# IDENTIDADE VISUAL (TEMA ESCURO TI)
# ==============================================================================
# Paleta de cores inspirada em terminais modernos e dashboards corporativos
CORES = {
    "fundo_app": "#0e1117",       # Fundo padrão Streamlit Dark
    "fundo_card": "#161b22",      # Fundo dos cards de métricas (GitHub Dark Dimmed)
    "fundo_sidebar": "#010409",   # Fundo da barra lateral
    "borda": "#30363d",           # Bordas sutis
    "texto_principal": "#f0f6fc", # Branco suave para leitura
    "texto_secundario": "#8b949e",# Cinza para labels
    "azul_petroleo": "#0A4D68",   # Cor primária (Tecnologia/Corporativo)
    "ciano_destaque": "#05BFDB",  # Cor de destaque (KPIs, Gráficos)
    "verde_sucesso": "#2ea043",   # Status OK
    "vermelho_erro": "#da3633",   # Status Crítico / Alerta
    "amarelo_alerta": "#d29922"   # Status Atenção
}

# Configuração base para gráficos Plotly (aplicada globalmente)
PLOTLY_TEMPLATE_CONFIG = {
    "layout": {
        "paper_bgcolor": CORES["fundo_app"],
        "plot_bgcolor": CORES["fundo_app"],
        "font": {"color": CORES["texto_principal"], "family": "Segoe UI, Roboto, sans-serif"},
        "title_font": {"color": CORES["ciano_destaque"], "size": 20},
        "legend_font": {"color": CORES["texto_secundario"]},
        "xaxis": {"gridcolor": CORES["borda"], "zerolinecolor": CORES["borda"]},
        "yaxis": {"gridcolor": CORES["borda"], "zerolinecolor": CORES["borda"]},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40}
    }
}

# ==============================================================================
# CONSTANTES DE PARSING
# ==============================================================================
# Palavras-chave que indicam início de seção no arquivo de snapshot
SECOES_VALIDAS = ["[ID]", "[HARDWARE]", "[SUPORTE]"]