import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
import pytz
import re
import config
import drive_client
import sheets_client
import parser

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E TEMA
# ==============================================================================
st.set_page_config(
    page_title=f"{config.NOME_EMPRESA} - {config.NOME_SISTEMA}",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# MELHORIA 2: TEMA PLOTLY PERSONALIZADO (FUNÇÃO CENTRALIZADORA)
# ==============================================================================
def apply_dashboard_theme(fig):
    """
    Aplica o tema premium (Azul Petróleo + Ciano) a qualquer gráfico Plotly.
    Substitui chamadas manuais repetidas de fig.update_layout().
    
    Args:
        fig: Objeto plotly Figure (px.bar, px.line, px.pie, go.Figure, etc.)
    
    Returns:
        fig: Mesmo objeto com tema aplicado
    """
    fig.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
    return fig

# ==============================================================================
# MELHORIA 3: BADGES E METRIC CARDS (IDENTIDADE VISUAL PREMIUM)
# ==============================================================================
def get_status_badge(valor, label=""):
    """
    Gera um badge HTML colorido baseado nos thresholds do config.py.
    
    Thresholds (config.THRESHOLDS_BADGES):
        - VERDE: valor < 5
        - AMARELO: 5 <= valor <= 10
        - VERMELHO: valor > 10
    
    Args:
        valor (int/float): Valor numérico para coloração
        label (str): Texto opcional antes do valor
    
    Returns:
        str: HTML do badge estilizado
    """
    thresholds = config.THRESHOLDS_BADGES
    
    if valor < thresholds['verde']:
        cor = config.CORES_BADGES['verde']
    elif valor <= thresholds['amarelo']:
        cor = config.CORES_BADGES['amarelo']
    else:
        cor = config.CORES_BADGES['vermelho']
    
    return f"""
    <span style="
        background-color: {cor['fundo']};
        color: {cor['texto']};
        border: 1px solid {cor['borda']};
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: bold;
        display: inline-block;
        margin-top: 8px;
    ">{label} {valor}</span>
    """

def render_metric_card(titulo, valor, icone=None, badge_valor=None, badge_label=""):
    """
    Renderiza um card de métrica premium com ícone e badge opcional.
    
    Args:
        titulo (str): Título da métrica
        valor: Valor principal (pode ser str ou numérico)
        icone (str): Emoji/ícone (usa config.ICONES_KPI se None)
        badge_valor (int/float): Valor para badge colorido (opcional)
        badge_label (str): Label do badge
    
    Returns:
        str: HTML do card estilizado
    """
    if icone is None:
        icone = config.ICONES_KPI.get('default', '📊')
    
    badge_html = ""
    if badge_valor is not None:
        badge_html = get_status_badge(badge_valor, badge_label)
    
    return f"""
    <div class="metric-card">
        <div style="font-size: 2.2em; margin-bottom: 10px;">{icone}</div>
        <div style="
            color: {config.CORES['texto_secundario']};
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        ">{titulo}</div>
        <div style="
            color: {config.CORES['ciano_destaque']};
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 8px;
        ">{valor}</div>
        {badge_html}
    </div>
    """

# ==============================================================================
# MELHORIA 6: SAFE LOAD DATA (SPINNERS + TRATAMENTO DE ERROS)
# ==============================================================================
def safe_load_data(loader_func, data_name, *args, **kwargs):
    """
    Carrega dados com spinner e tratamento de erros amigável em PT-BR.
    
    Args:
        loader_func: Função de carregamento a ser executada
        data_name (str): Nome amigável dos dados para mensagens
        *args, **kwargs: Argumentos passados à função
    
    Returns:
        tuple: (resultado, erro) onde erro é None se sucesso
    """
    try:
        with st.spinner(f"🔄 Carregando {data_name}..."):
            resultado = loader_func(*args, **kwargs)
        return resultado, None
    except Exception as e:
        st.error(f"❌ Erro ao carregar {data_name}: {str(e)}")
        st.warning("💡 Verifique sua conexão com a internet e as credenciais no arquivo .env")
        return None, str(e)

# ==============================================================================
# FUNÇÃO UTILITÁRIA: SANITIZAÇÃO PARA EXCEL
# ==============================================================================
def sanitizar_para_excel(df):
    """
    Remove caracteres de controle ilegais do openpyxl de todas as colunas
    de string do DataFrame. Preserva emojis e caracteres Unicode válidos.
    
    Caracteres removidos (ilegais no XML 1.0 usado pelo Excel):
    - \x00-\x08: Nulos e caracteres de controle básicos
    - \x0b-\x0c: Tabulação vertical e form feed
    - \x0e-\x1f: Caracteres de controle ASCII
    - \x7f-\x9f: DEL e caracteres C1 de controle
    
    Caracteres preservados:
    - \t (0x09), \n (0x0A), \r (0x0D): Tab, newline, carriage return
    - Emojis (🟢, 🔴, ️, etc.)
    - Caracteres Unicode válidos (acentos, símbolos, etc.)
    """
    if df is None or df.empty:
        return df
    
    df_limpo = df.copy()
    
    # Regex do openpyxl para caracteres ilegais em XML 1.0
    # Remove apenas caracteres de controle, preserva \t, \n, \r e emojis
    illegal_char_regex = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
    
    for col in df_limpo.columns:
        if df_limpo[col].dtype == 'object':
            df_limpo[col] = df_limpo[col].apply(
                lambda x: illegal_char_regex.sub('', str(x)) if pd.notna(x) and isinstance(x, str) else x
            )
    
    return df_limpo

# ==============================================================================
# FUNÇÃO UTILITÁRIA: INICIALIZAÇÃO SEGURA DE SESSION_STATE
# ==============================================================================
def _garantir_session(key, valor_padrao):
    """
    Garante que a chave exista no st.session_state sem sobrescrever valores existentes.
    CORREÇÃO FASE 1: permite que filtros persistam entre mudanças de aba e recarregamentos.
    Usa None como sentinela para multiselect (distingue 'nunca inicializado' de 'lista vazia').
    """
    if key not in st.session_state:
        st.session_state[key] = valor_padrao

# ==============================================================================
# FUNÇÃO UTILITÁRIA: DETECÇÃO SEGURA DA COLUNA DE MODELO (GB)
# ==============================================================================
def _detectar_coluna_modelo_gb(df):
    """
    CORREÇÃO FASE 2 (BUG: coluna duplicada na aba GB):
    A busca original ('modelo' ou 'equipamento' no nome da coluna) capturava
    'Tipo_Equipamento' — coluna que JÁ faz parte da lista de exibição —,
    gerando duas colunas 'Tipo' na tabela e na exportação Excel.
    Agora as colunas base são excluídas explicitamente da busca.
    """
    colunas_base = {
        'local', 'codigo_bpcs', 'nome_dispositivo', 'tipo_equipamento',
        'status_garantia', 'dias_restantes', 'data_garantia_str'
    }
    return next(
        (
            col for col in df.columns
            if col.lower() not in colunas_base
            and ('modelo' in col.lower() or 'equipamento' in col.lower())
        ),
        None
    )

# ==============================================================================
# FUNÇÃO AUXILIAR: BOTÕES DE EXPORTAÇÃO (ELIMINA DUPLICAÇÃO)
# ==============================================================================
def criar_botoes_exportacao(df_display, prefixo_nome, sheet_name, chave_unico):
    """
    Cria botões de exportação CSV e Excel padronizados.
    
    Args:
        df_display (pd.DataFrame): DataFrame já filtrado e renomeado para exibição
        prefixo_nome (str): Prefixo do nome do arquivo (ex: 'inventario_administrativo')
        sheet_name (str): Nome da aba no Excel
        chave_unico (str): Chave única para evitar conflitos de widget
    """
    col_exp1, col_exp2, _ = st.columns([1, 1, 4])
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col_exp1:
        csv = df_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button(
            label="📄 Baixar CSV",
            data=csv,
            file_name=f"{prefixo_nome}_{timestamp}.csv",
            mime="text/csv",
            key=f"csv_{chave_unico}"
        )
    
    with col_exp2:
        # SANITIZAÇÃO: Remove caracteres ilegais antes de exportar para Excel
        df_display_limpo = sanitizar_para_excel(df_display)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_display_limpo.to_excel(writer, index=False, sheet_name=sheet_name)
        excel_data = output.getvalue()
        
        st.download_button(
            label="📊 Baixar Excel",
            data=excel_data,
            file_name=f"{prefixo_nome}_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"excel_{chave_unico}"
        )

# ==============================================================================
# MELHORIA 1: CSS PREMIUM EXPANDIDO (TEMA AZUL PETRÓLEO + CIANO)
# ==============================================================================
st.markdown(f"""
<style>
    /* Fundo principal e texto */
    .stApp {{
        background-color: {config.CORES['fundo_app']};
        color: {config.CORES['texto_principal']};
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {config.CORES['fundo_sidebar']};
        border-right: 1px solid {config.CORES['borda']};
    }}
    
    /* Cards de Métricas (KPIs) - Streamlit nativo */
    div[data-testid="stMetric"] {{
        background-color: {config.CORES['fundo_card']};
        border: 1px solid {config.CORES['borda']};
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    
    div[data-testid="stMetricLabel"] {{
        color: {config.CORES['texto_secundario']};
        font-size: 0.9em;
    }}
    
    div[data-testid="stMetricValue"] {{
        color: {config.CORES['ciano_destaque']};
        font-weight: bold;
    }}
    
    /* MELHORIA 3: Metric Cards Customizados */
    .metric-card {{
        background-color: {config.CORES['fundo_card']};
        border: 1px solid {config.CORES['borda']};
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    .metric-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(5, 191, 219, 0.25);
        border-color: {config.CORES['ciano_destaque']};
    }}
    
    /* MELHORIA 1: Badges */
    .badge {{
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: bold;
        display: inline-block;
    }}
    
    /* Títulos */
    h1, h2, h3 {{
        color: {config.CORES['ciano_destaque']};
    }}
    
    /* Botões Padrão */
    .stButton>button {{
        background-color: {config.CORES['azul_petroleo']};
        color: white;
        border: none;
        border-radius: 5px;
        transition: 0.3s;
    }}
    
    .stButton>button:hover {{
        background-color: {config.CORES['ciano_destaque']};
        color: {config.CORES['fundo_app']};
    }}
    
    /* Botão de Atualização (Destaque) */
    div[data-testid="stSidebar"] .stButton>button {{
        background-color: {config.CORES['ciano_destaque']};
        color: {config.CORES['fundo_app']};
        font-weight: bold;
        width: 100%;
    }}
    
    /* Placeholders de desenvolvimento */
    .dev-placeholder {{
        background-color: {config.CORES['fundo_card']};
        border: 2px dashed {config.CORES['borda']};
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
    }}
    
    /* MELHORIA 1: Animações suaves */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 2px solid {config.CORES['borda']};
    }}
    
    .stTabs [data-baseweb="tab"] {{
        transition: all 0.3s ease;
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: rgba(5, 191, 219, 0.1);
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {config.CORES['azul_petroleo']} !important;
        border-bottom: 3px solid {config.CORES['ciano_destaque']};
    }}
    
    /* Timestamp global */
    .timestamp-global {{
        color: {config.CORES['texto_secundario']};
        font-size: 0.9em;
        font-style: italic;
        margin-bottom: 20px;
        padding: 8px 16px;
        background-color: {config.CORES['fundo_card']};
        border-radius: 6px;
        border-left: 3px solid {config.CORES['ciano_destaque']};
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# MELHORIA 3: TIMESTAMP GLOBAL DE ÚLTIMA ATUALIZAÇÃO
# ==============================================================================
timestamp_atualizacao = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')
st.markdown(f"""
<div class="timestamp-global">
    🕐 Última atualização: {timestamp_atualizacao} (Horário de Brasília)
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# MELHORIA 7: CARREGAMENTO DOS DADOS COM CACHE NO PROCESSAMENTO
# ==============================================================================
@st.cache_data(ttl=config.CACHE_TTL_CURTO, show_spinner=False)
def _processar_snapshots_cached(snapshots_brutos):
    """
    MELHORIA 7: Cache no processamento pesado dos snapshots.
    Evita reprocessar a cada interação do usuário (crítico em hardware antigo).
    """
    if not snapshots_brutos:
        return pd.DataFrame(), [], pd.DataFrame(), pd.DataFrame()
    
    df_inv, log_dup = parser.processar_todos_snapshots(snapshots_brutos)
    df_mon, df_imp = parser.processar_perifericos(snapshots_brutos)
    return df_inv, log_dup, df_mon, df_imp

@st.cache_data(ttl=config.CACHE_TTL_CURTO, show_spinner=False)
def _processar_gb_cached(df_gb_bruto):
    """MELHORIA 7: Cache no processamento da planilha GB."""
    if df_gb_bruto.empty:
        return pd.DataFrame()
    return parser.processar_planilha_gb(df_gb_bruto)

@st.cache_data(ttl=config.CACHE_TTL_CURTO, show_spinner=False)
def _processar_celulares_cached(df_cel_bruto):
    """MELHORIA 7: Cache no processamento da planilha de celulares."""
    if df_cel_bruto.empty:
        return pd.DataFrame()
    return parser.processar_planilha_celulares(df_cel_bruto)

# --- Carregamento com MELHORIA 6: safe_load_data + spinners ---
snapshots_brutos, erro_drive = safe_load_data(
    drive_client.carregar_snapshots_drive,
    "Snapshots do Google Drive"
)

if erro_drive:
    snapshots_brutos = []

# Processamento com cache (Melhoria 7)
df_inventario, log_duplicatas, df_monitores, df_impressoras = _processar_snapshots_cached(snapshots_brutos)

# CORREÇÃO FASE 1: Normalização defensiva de strings (strip) para evitar
# que variações de espaços quebrem os filtros multiselect.
# (Aplicado apenas strip para não alterar capitalização de nomes próprios.)
if not df_inventario.empty:
    for _col_norm in ['Local', 'Usuario', 'Windows', 'Nome_Computador', 'Modelo_Sistema', 'Processador']:
        if _col_norm in df_inventario.columns:
            df_inventario[_col_norm] = df_inventario[_col_norm].astype(str).str.strip()

# Inventário GB (Sheets)
df_gb_bruto, erro_gb = safe_load_data(
    sheets_client.carregar_planilha_gb,
    "Planilha GB (Google Sheets)"
)
df_gb = _processar_gb_cached(df_gb_bruto if df_gb_bruto is not None else pd.DataFrame())

# Celulares Administrativos (Sheets - Relatório_Dispositivos)
df_celulares_bruto, erro_cel = safe_load_data(
    sheets_client.carregar_planilha_celulares,
    "Planilha de Celulares (Google Sheets)"
)
df_celulares = _processar_celulares_cached(df_celulares_bruto if df_celulares_bruto is not None else pd.DataFrame())

# ==============================================================================
# INICIALIZAÇÃO DE SESSION_STATE PARA TODOS OS FILTROS
# ==============================================================================
# CORREÇÃO FASE 1: garante persistência dos filtros entre mudanças de aba
# e recarregamentos. None = sentinela para multiselect (repopula na 1ª renderização).
# --- Filtros do Inventário Administrativo (Computadores) ---
_garantir_session("filtro_local_admin", None)
_garantir_session("filtro_usuario_admin", None)
_garantir_session("filtro_windows_admin", None)
_garantir_session("filtro_processador_admin", "")
_garantir_session("busca_geral_admin", "")
# --- Filtros de Celulares ---
_garantir_session("filtro_local_cel", None)
_garantir_session("filtro_politica_cel", None)
_garantir_session("filtro_modelo_cel", None)
_garantir_session("filtro_status_cel", None)
_garantir_session("busca_cel", "")
# --- Filtros de Monitores ---
_garantir_session("filtro_local_mon", None)
_garantir_session("busca_mon", "")
# --- Filtros de Impressoras ---
_garantir_session("filtro_local_imp", None)
_garantir_session("busca_imp", "")
# --- Filtros do Inventário GB ---
_garantir_session("filtro_local_gb", None)
_garantir_session("filtro_tipo_gb", None)
_garantir_session("filtro_status_gb", None)

# ==============================================================================
# SIDEBAR: CONTROLES E FILTROS
# ==============================================================================
with st.sidebar:
    st.title(f"🛠️ {config.NOME_SISTEMA}")
    st.markdown(f"**{config.NOME_EMPRESA}**")
    st.markdown("---")
    
    if st.button("🔄 Forçar Atualização dos Dados"):
        drive_client.carregar_snapshots_drive.clear()
        sheets_client.carregar_planilha_gb.clear()
        sheets_client.carregar_planilha_celulares.clear()
        # MELHORIA 7: limpa também o cache de processamento
        _processar_snapshots_cached.clear()
        _processar_gb_cached.clear()
        _processar_celulares_cached.clear()
        st.rerun()
    
    # SELETOR DE RELATÓRIO (NOVO)
    st.markdown("### 📊 Selecionar Relatório")
    relatorio_selecionado = st.radio(
        "Relatório Ativo:",
        options=["🏢 Inventário Administrativo", "📊 Inventário GB"],
        index=0,
        key="relatorio_selecionado",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Filtros")

# ==============================================================================
# MELHORIA 4: NAVEGAÇÃO PRINCIPAL POR ABAS (REESTRUTURADA)
# ==============================================================================
# NOTA FASE 1: Streamlit NÃO suporta seleção programática de abas via st.tabs().
# A navegação real ocorre pelo clique do usuário na aba.
tab_visao_geral, tab_admin, tab_gb, tab_exportacao = st.tabs([
    f"{config.ABAS_DASHBOARD['visao_geral']['icone']} {config.ABAS_DASHBOARD['visao_geral']['titulo']}",
    f"{config.ABAS_DASHBOARD['inventario_admin']['icone']} {config.ABAS_DASHBOARD['inventario_admin']['titulo']}",
    f"{config.ABAS_DASHBOARD['inventario_gb']['icone']} {config.ABAS_DASHBOARD['inventario_gb']['titulo']}",
    f"{config.ABAS_DASHBOARD['exportacao']['icone']} {config.ABAS_DASHBOARD['exportacao']['titulo']}"
])

# ==============================================================================
# MELHORIA 4: ABA 1 — VISÃO GERAL (NOVA)
# ==============================================================================
with tab_visao_geral:
    st.title("📊 Visão Geral do Inventário de TI")
    st.markdown(f"*{config.ABAS_DASHBOARD['visao_geral']['descricao']}*")
    st.markdown("---")
    
    # KPIs consolidados de todas as fontes
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_computadores = len(df_inventario) if not df_inventario.empty else 0
    total_celulares_admin = len(df_celulares) if not df_celulares.empty else 0
    total_monitores = len(df_monitores) if not df_monitores.empty else 0
    total_impressoras = len(df_impressoras) if not df_impressoras.empty else 0
    total_gb = len(df_gb) if not df_gb.empty else 0
    
    with col1:
        st.markdown(render_metric_card(
            "Computadores",
            total_computadores,
            icone=config.ICONES_KPI['total_maquinas']
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(
            "Celulares Admin",
            total_celulares_admin,
            icone=config.ICONES_KPI['celulares']
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_metric_card(
            "Monitores",
            total_monitores,
            icone=config.ICONES_KPI['monitores']
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(render_metric_card(
            "Impressoras",
            total_impressoras,
            icone=config.ICONES_KPI['impressoras']
        ), unsafe_allow_html=True)
    
    with col5:
        st.markdown(render_metric_card(
            "Equipamentos GB",
            total_gb,
            icone=config.ICONES_KPI['garantias']
        ), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráfico resumo de distribuição por fonte
    st.subheader("📈 Distribuição Geral do Parque")
    
    dados_resumo = pd.DataFrame({
        'Categoria': ['Computadores', 'Celulares', 'Monitores', 'Impressoras', 'GB'],
        'Quantidade': [total_computadores, total_celulares_admin, total_monitores, total_impressoras, total_gb]
    })
    
    if dados_resumo['Quantidade'].sum() > 0:
        fig_resumo = px.bar(
            dados_resumo,
            x='Categoria',
            y='Quantidade',
            title='Total de Equipamentos por Categoria',
            color_discrete_sequence=[config.CORES['ciano_destaque']]
        )
        fig_resumo = apply_dashboard_theme(fig_resumo)
        st.plotly_chart(fig_resumo, use_container_width=True)
    else:
        st.info("ℹ️ Nenhum dado disponível para exibir o resumo.")

# ==============================================================================
# ABA 2: INVENTÁRIO ADMINISTRATIVO
# ==============================================================================
with tab_admin:
    # CORREÇÃO FASE 1 (Claude #1): st.stop() removido. Agora usa if/else para
    # isolar a falha do Drive sem derrubar a aba GB (fonte de dados independente).
    if df_inventario.empty:
        st.warning("⚠️ Nenhum dado carregado do Google Drive. Verifique a conexão ou a API Key.")
    else:
        # Sub-abas do Inventário Administrativo
        sub_tab_computadores, sub_tab_celulares, sub_tab_perifericos = st.tabs([
            "💻 Computadores",
            "📱 Celulares Administrativos",
            "🖨️ Periféricos"
        ])

        # ---------------------------------------------------------------------
        # SUB-ABA 1.1: COMPUTADORES (Conteúdo Original Preservado)
        # ---------------------------------------------------------------------
        with sub_tab_computadores:
            # FILTROS CONDICIONAIS: Só aparecem quando o relatório Administrativo está selecionado
            if relatorio_selecionado == "🏢 Inventário Administrativo":
                with st.sidebar:
                    locais = sorted(df_inventario['Local'].dropna().unique().tolist())
                    usuarios = sorted(df_inventario['Usuario'].dropna().unique().tolist())
                    windows = sorted(df_inventario['Windows'].dropna().unique().tolist())
                    
                    # CORREÇÃO FASE 1: popula session_state na 1ª renderização
                    if st.session_state.filtro_local_admin is None:
                        st.session_state.filtro_local_admin = locais
                    if st.session_state.filtro_usuario_admin is None:
                        st.session_state.filtro_usuario_admin = usuarios
                    if st.session_state.filtro_windows_admin is None:
                        st.session_state.filtro_windows_admin = windows
                    
                    filtro_local = st.multiselect("Local (Administrativo)", options=locais, default=st.session_state.filtro_local_admin, key="filtro_local_admin")
                    filtro_usuario = st.multiselect("Usuário", options=usuarios, default=st.session_state.filtro_usuario_admin, key="filtro_usuario_admin")
                    filtro_windows = st.multiselect("Sistema Operacional", options=windows, default=st.session_state.filtro_windows_admin, key="filtro_windows_admin")
                    filtro_processador = st.text_input("Buscar no Processador (ex: Ryzen, Intel)", key="filtro_processador_admin")
                    busca_geral = st.text_input("🔎 Busca Livre (Nome, ID, AnyDesk, TV)", key="busca_geral_admin")
                    
                    # CORREÇÃO FASE 1 (Claude #3 / Copilot #4.2): Botão Limpar Filtros
                    # CORREÇÃO FASE 2: rótulo "Resetar" (repõe todas as opções, não esvazia)
                    if st.button("🔄 Resetar Filtros (Admin)", key="limpar_filtros_admin"):
                        st.session_state.filtro_local_admin = None
                        st.session_state.filtro_usuario_admin = None
                        st.session_state.filtro_windows_admin = None
                        st.session_state.filtro_processador_admin = ""
                        st.session_state.busca_geral_admin = ""
                        st.rerun()
                    
                    st.markdown("---")
                    st.markdown("### 📊 Auditoria de Dados")
                    with st.expander(f"Ver {len(log_duplicatas)} duplicatas descartadas"):
                        if log_duplicatas:
                            for log in log_duplicatas:
                                st.caption(f"🗑️ {log}")
                        else:
                            st.caption("✅ Nenhuma duplicata encontrada nesta varredura.")
            else:
                # Valores padrão quando o filtro não está visível
                filtro_local = sorted(df_inventario['Local'].dropna().unique().tolist())
                filtro_usuario = sorted(df_inventario['Usuario'].dropna().unique().tolist())
                filtro_windows = sorted(df_inventario['Windows'].dropna().unique().tolist())
                filtro_processador = ""
                busca_geral = ""
            
            # Aplicação dos Filtros
            # FIX FASE 0: .copy() explícito evita SettingWithCopyWarning nas atribuições de Status/Alerta_RAM
            df_filtrado = df_inventario[
                (df_inventario['Local'].isin(filtro_local)) &
                (df_inventario['Usuario'].isin(filtro_usuario)) &
                (df_inventario['Windows'].isin(filtro_windows))
            ].copy()
            
            if filtro_processador:
                # CORREÇÃO FASE 1 (Copilot #1.4): re.escape evita regex injection
                filtro_proc_escaped = re.escape(filtro_processador)
                df_filtrado = df_filtrado[df_filtrado['Processador'].str.contains(filtro_proc_escaped, case=False, na=False)]
            
            if busca_geral:
                # CORREÇÃO FASE 1 (Copilot #1.4): re.escape evita regex injection
                busca_escaped = re.escape(busca_geral)
                mask_busca = (
                    df_filtrado['Nome_Computador'].str.contains(busca_escaped, case=False, na=False) |
                    df_filtrado['ID'].str.contains(busca_escaped, case=False, na=False) |
                    df_filtrado['AnyDesk'].str.contains(busca_escaped, case=False, na=False) |
                    df_filtrado['TeamViewer'].str.contains(busca_escaped, case=False, na=False)
                )
                df_filtrado = df_filtrado[mask_busca]
            
            # CORREÇÃO FASE 1 (Copilot #4.1): mensagem quando filtros não retornam resultados
            if df_filtrado.empty:
                st.info("ℹ️ Nenhum resultado encontrado com os filtros aplicados. Tente ajustar os filtros.")
            else:
                # KPIs (Indicadores Principais)
                st.title(f"📊 Painel de Inventário Administrativo")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                total_maquinas = len(df_filtrado)
                maquinas_ram_baixa = len(df_filtrado[(df_filtrado['Memoria_RAM_GB'] < 8.0) & (df_filtrado['Memoria_RAM_GB'] > 0)])
                # CORREÇÃO FASE 1 (Copilot #3.2): contabiliza máquinas com erro de parsing de RAM (-1)
                maquinas_ram_erro = len(df_filtrado[df_filtrado['Memoria_RAM_GB'] < 0])
                amd_count = len(df_filtrado[df_filtrado['Processador'].str.contains('AMD', case=False, na=False)])
                intel_count = len(df_filtrado[df_filtrado['Processador'].str.contains('Intel', case=False, na=False)])
                
                if not df_filtrado.empty:
                    data_mais_antiga = df_filtrado['Data_Snapshot'].min().strftime('%d/%m/%Y')
                else:
                    data_mais_antiga = "N/A"
                
                # MELHORIA 3: Substitui st.metric() por render_metric_card()
                with col1:
                    st.markdown(render_metric_card(
                        "Total de Máquinas",
                        total_maquinas,
                        icone=config.ICONES_KPI['total_maquinas']
                    ), unsafe_allow_html=True)
                
                with col2:
                    st.markdown(render_metric_card(
                        "RAM < 8GB (Alerta)",
                        maquinas_ram_baixa,
                        icone=config.ICONES_KPI['ram_baixa'],
                        badge_valor=maquinas_ram_baixa,
                        badge_label="⚠️"
                    ), unsafe_allow_html=True)
                
                with col3:
                    st.markdown(render_metric_card(
                        "Processadores AMD",
                        amd_count,
                        icone=config.ICONES_KPI['processadores']
                    ), unsafe_allow_html=True)
                
                with col4:
                    st.markdown(render_metric_card(
                        "Processadores Intel",
                        intel_count,
                        icone=config.ICONES_KPI['processadores']
                    ), unsafe_allow_html=True)
                
                with col5:
                    st.markdown(render_metric_card(
                        "Snapshot + Antigo",
                        data_mais_antiga,
                        icone=config.ICONES_KPI['snapshot_antigo']
                    ), unsafe_allow_html=True)
                
                # CORREÇÃO FASE 1: alerta visível para erros de parsing de RAM
                if maquinas_ram_erro > 0:
                    st.caption(f"⚠️ {maquinas_ram_erro} máquina(s) com erro de parsing de RAM. Verifique os snapshots de origem.")
                
                st.markdown("---")
                
                # Gráficos Interativos (Plotly)
                st.subheader("📈 Distribuição do Parque de Máquinas")
                col_g1, col_g2, col_g3 = st.columns(3)
                
                with col_g1:
                    if not df_filtrado.empty:
                        fig_local = px.bar(df_filtrado, x='Local', title='Máquinas por Local', color_discrete_sequence=[config.CORES['ciano_destaque']])
                        fig_local = apply_dashboard_theme(fig_local)
                        st.plotly_chart(fig_local, use_container_width=True)
                
                with col_g2:
                    if not df_filtrado.empty:
                        top_proc = df_filtrado['Processador'].value_counts().head(10).reset_index()
                        top_proc.columns = ['Processador', 'Quantidade']
                        fig_proc = px.bar(top_proc, x='Quantidade', y='Processador', orientation='h', title='Top 10 Processadores', color_discrete_sequence=[config.CORES['azul_petroleo']])
                        fig_proc = apply_dashboard_theme(fig_proc)
                        st.plotly_chart(fig_proc, use_container_width=True)
                
                with col_g3:
                    if not df_filtrado.empty:
                        fig_win = px.pie(df_filtrado, names='Windows', title='Distribuição Windows', hole=0.4, color_discrete_sequence=px.colors.sequential.Viridis)
                        fig_win = apply_dashboard_theme(fig_win)
                        fig_win.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_win, use_container_width=True)
                
                st.markdown("---")
                
                # Tabela Detalhada e Exportação
                st.subheader("💻 Inventário Detalhado")
                
                # Cálculo de Status para a Tabela
                limite_data = datetime.now(pytz.timezone('America/Sao_Paulo')) - timedelta(days=config.DIAS_LIMITE_ATRASO)
                df_filtrado['Status'] = df_filtrado['Data_Snapshot'].apply(
                    lambda x: '🔴 Desatualizada' if x < limite_data else '🟢 OK'
                )
                # CORREÇÃO FASE 1 (Copilot #3.2): trata RAM = -1 como erro de parsing
                df_filtrado['Alerta_RAM'] = df_filtrado['Memoria_RAM_GB'].apply(
                    lambda x: '🔴 Erro Parsing' if x < 0 else ('⚠️ Baixa' if 0 < x < 8.0 else '✅ OK')
                )
                
                colunas_exibir = [
                    "Status", "Local", "Usuario", "Nome_Computador", "Modelo_Sistema", 
                    "Processador", "Memoria_RAM", "Alerta_RAM", "Windows", "ID", 
                    "AnyDesk", "TeamViewer", "Data_Snapshot_Str"
                ]
                
                df_display = df_filtrado[colunas_exibir].copy()
                df_display.rename(columns={
                    "Data_Snapshot_Str": "Último Snapshot",
                    "Usuario": "Usuário",
                    "Nome_Computador": "Nome Computador",
                    "Modelo_Sistema": "Modelo Sistema",
                    "Memoria_RAM": "Memória RAM",
                    "Alerta_RAM": "Status RAM"
                }, inplace=True)
                
                st.dataframe(
                    df_display,
                    column_config={
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "AnyDesk": st.column_config.TextColumn("AnyDesk", width="small"),
                        "TeamViewer": st.column_config.TextColumn("TeamViewer", width="small"),
                        "ID": st.column_config.TextColumn("Hardware ID", width="medium")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Botões de Exportação
                st.markdown("---")
                st.subheader("📥 Exportar Dados Filtrados")
                criar_botoes_exportacao(df_display, "inventario_administrativo", "Inventario_Admin", "admin")

        # ---------------------------------------------------------------------
        # SUB-ABA 1.2: CELULARES ADMINISTRATIVOS (FUNCIONAL - Planilha Relatório_Dispositivos)
        # ---------------------------------------------------------------------
        with sub_tab_celulares:
            st.title("📱 Celulares Administrativos")
            st.markdown("---")
            
            if df_celulares.empty:
                st.info("ℹ️ Nenhum celular encontrado na planilha Relatório_Dispositivos. Verifique o compartilhamento da planilha.")
            else:
                # Filtros de Celulares (mesmo padrão visual das sub-abas de Periféricos)
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    locais_cel = sorted(df_celulares['Local'].dropna().unique().tolist())
                    politicas_cel = sorted(df_celulares['Politica'].dropna().unique().tolist())
                    modelos_cel = sorted(df_celulares['Modelo'].dropna().unique().tolist())
                    status_cel = sorted(df_celulares['Status_Comunicacao'].dropna().unique().tolist())
                    
                    # CORREÇÃO FASE 1: popula session_state na 1ª renderização
                    if st.session_state.filtro_local_cel is None:
                        st.session_state.filtro_local_cel = locais_cel
                    if st.session_state.filtro_politica_cel is None:
                        st.session_state.filtro_politica_cel = politicas_cel
                    if st.session_state.filtro_modelo_cel is None:
                        st.session_state.filtro_modelo_cel = modelos_cel
                    if st.session_state.filtro_status_cel is None:
                        st.session_state.filtro_status_cel = status_cel
                    
                    filtro_local_cel = st.multiselect("Local", options=locais_cel, default=st.session_state.filtro_local_cel, key="filtro_local_cel")
                    filtro_politica_cel = st.multiselect("Política", options=politicas_cel, default=st.session_state.filtro_politica_cel, key="filtro_politica_cel")
                    filtro_modelo_cel = st.multiselect("Modelo", options=modelos_cel, default=st.session_state.filtro_modelo_cel, key="filtro_modelo_cel")
                    filtro_status_cel = st.multiselect("Status de Comunicação", options=status_cel, default=st.session_state.filtro_status_cel, key="filtro_status_cel")
                
                with col_f2:
                    busca_cel = st.text_input("🔎 Buscar (Nome, Responsável, IMEI, Serial)", key="busca_cel")
                    
                    # CORREÇÃO FASE 1 (Claude #3 / Copilot #4.2): Botão Limpar Filtros
                    # CORREÇÃO FASE 2: rótulo "Resetar" (repõe todas as opções, não esvazia)
                    if st.button("🔄 Resetar Filtros (Celulares)", key="limpar_filtros_cel"):
                        st.session_state.filtro_local_cel = None
                        st.session_state.filtro_politica_cel = None
                        st.session_state.filtro_modelo_cel = None
                        st.session_state.filtro_status_cel = None
                        st.session_state.busca_cel = ""
                        st.rerun()
                
                # Aplicação dos Filtros
                # CORREÇÃO FASE 1 (Copilot #2.1): .copy() explícito evita SettingWithCopyWarning
                df_cel_filtrado = df_celulares[
                    (df_celulares['Local'].isin(filtro_local_cel)) &
                    (df_celulares['Politica'].isin(filtro_politica_cel)) &
                    (df_celulares['Modelo'].isin(filtro_modelo_cel)) &
                    (df_celulares['Status_Comunicacao'].isin(filtro_status_cel))
                ].copy()
                
                if busca_cel:
                    # CORREÇÃO FASE 1 (Copilot #1.4): re.escape evita regex injection
                    busca_cel_escaped = re.escape(busca_cel)
                    mask_cel = (
                        df_cel_filtrado['Nome_Dispositivo'].str.contains(busca_cel_escaped, case=False, na=False) |
                        df_cel_filtrado['Responsavel'].str.contains(busca_cel_escaped, case=False, na=False) |
                        df_cel_filtrado['IMEI'].str.contains(busca_cel_escaped, case=False, na=False) |
                        df_cel_filtrado['Serial'].str.contains(busca_cel_escaped, case=False, na=False)
                    )
                    df_cel_filtrado = df_cel_filtrado[mask_cel]
                
                # CORREÇÃO FASE 1 (Copilot #4.1): mensagem quando filtros não retornam resultados
                if df_cel_filtrado.empty:
                    st.info("ℹ️ Nenhum celular encontrado com os filtros aplicados. Tente ajustar os filtros.")
                else:
                    # KPIs de Celulares
                    st.subheader("📊 Visão Geral dos Celulares")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    total_cel = len(df_cel_filtrado)
                    cel_ok = len(df_cel_filtrado[df_cel_filtrado['Status_Comunicacao'] == '🟢 OK'])
                    cel_desat = len(df_cel_filtrado[df_cel_filtrado['Status_Comunicacao'] == '🔴 Desatualizado'])
                    
                    # MELHORIA 3: Metric cards com badges
                    with col1:
                        st.markdown(render_metric_card(
                            "Total de Celulares",
                            total_cel,
                            icone=config.ICONES_KPI['celulares']
                        ), unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(render_metric_card(
                            "🟢 Atualizados",
                            cel_ok,
                            icone=config.ICONES_KPI['resolvidos']
                        ), unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown(render_metric_card(
                            "🔴 Desatualizados",
                            cel_desat,
                            icone=config.ICONES_KPI['criticos'],
                            badge_valor=cel_desat,
                            badge_label="🔴"
                        ), unsafe_allow_html=True)
                    
                    with col4:
                        st.markdown(render_metric_card(
                            "Locais com Celulares",
                            df_cel_filtrado['Local'].nunique(),
                            icone=config.ICONES_KPI['locais']
                        ), unsafe_allow_html=True)
                    
                    with col5:
                        st.markdown(render_metric_card(
                            "Modelos Diferentes",
                            df_cel_filtrado['Modelo'].nunique(),
                            icone=config.ICONES_KPI['modelos']
                        ), unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Gráficos de Celulares
                    st.subheader("📈 Distribuição")
                    col_g1, col_g2, col_g3 = st.columns(3)
                    
                    with col_g1:
                        if not df_cel_filtrado.empty:
                            fig_cel_local = px.bar(
                                df_cel_filtrado, 
                                x='Local', 
                                title='Celulares por Local', 
                                color_discrete_sequence=[config.CORES['ciano_destaque']]
                            )
                            fig_cel_local = apply_dashboard_theme(fig_cel_local)
                            st.plotly_chart(fig_cel_local, use_container_width=True)
                    
                    with col_g2:
                        if not df_cel_filtrado.empty:
                            fig_cel_pol = px.pie(
                                df_cel_filtrado, 
                                names='Politica', 
                                title='Distribuição por Política', 
                                hole=0.4, 
                                color_discrete_sequence=[config.CORES['azul_petroleo'], config.CORES['ciano_destaque'], config.CORES['verde_sucesso'], config.CORES['amarelo_alerta']]
                            )
                            fig_cel_pol = apply_dashboard_theme(fig_cel_pol)
                            fig_cel_pol.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_cel_pol, use_container_width=True)
                    
                    with col_g3:
                        if not df_cel_filtrado.empty:
                            top_modelos_cel = df_cel_filtrado['Modelo'].value_counts().head(10).reset_index()
                            top_modelos_cel.columns = ['Modelo', 'Quantidade']
                            fig_cel_modelo = px.bar(
                                top_modelos_cel, 
                                x='Quantidade', 
                                y='Modelo', 
                                orientation='h', 
                                title='Top 10 Modelos de Celulares', 
                                color_discrete_sequence=[config.CORES['verde_sucesso']]
                            )
                            fig_cel_modelo = apply_dashboard_theme(fig_cel_modelo)
                            st.plotly_chart(fig_cel_modelo, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Tabela de Celulares
                    st.subheader("📱 Inventário de Celulares")
                    
                    colunas_cel_exibir = [
                        'Status_Comunicacao', 'Local', 'Responsavel', 'Nome_Dispositivo', 
                        'Modelo', 'IMEI', 'Serial', 'Politica', 'Versao_SO', 
                        'Dias_Sem_Comunicacao', 'Data_Ultimo_Envio_Str', 'IP_Local'
                    ]
                    
                    df_cel_display = df_cel_filtrado[colunas_cel_exibir].copy()
                    df_cel_display.rename(columns={
                        'Status_Comunicacao': 'Status',
                        'Responsavel': 'Responsável',
                        'Nome_Dispositivo': 'Nome do Dispositivo',
                        'Serial': 'Nº de Série',
                        'Politica': 'Política',
                        'Versao_SO': 'Versão SO',
                        'Dias_Sem_Comunicacao': 'Dias sem Comunicação',
                        'Data_Ultimo_Envio_Str': 'Último Envio',
                        'IP_Local': 'IP Local'
                    }, inplace=True)
                    
                    st.dataframe(
                        df_cel_display,
                        column_config={
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "Nº de Série": st.column_config.TextColumn("Nº de Série", width="medium"),
                            "IMEI": st.column_config.TextColumn("IMEI", width="medium"),
                            "Responsável": st.column_config.TextColumn("Responsável", width="small"),
                            "IP Local": st.column_config.TextColumn("IP Local", width="medium"),
                            "Dias sem Comunicação": st.column_config.NumberColumn("Dias", format="%d")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Exportação de Celulares
                    st.markdown("---")
                    st.subheader("📥 Exportar Celulares")
                    criar_botoes_exportacao(df_cel_display, "celulares", "Celulares", "cel")

        # ---------------------------------------------------------------------
        # SUB-ABA 1.3: PERIFÉRICOS (FUNCIONAL - Monitores e Impressoras)
        # ---------------------------------------------------------------------
        with sub_tab_perifericos:
            st.title("🖨️ Periféricos")
            st.markdown("---")
            
            # Sub-sub-abas: Monitores e Impressoras
            sub_tab_monitores, sub_tab_impressoras = st.tabs([
                "🖥️ Monitores",
                "🖨️ Impressoras"
            ])
            
            # ==================================================================
            # SUB-SUB-ABA: MONITORES
            # ==================================================================
            with sub_tab_monitores:
                if df_monitores.empty:
                    st.info("ℹ️ Nenhum monitor encontrado nos snapshots. Aguarde a próxima atualização dos scripts de coleta.")
                else:
                    # Filtros de Monitores
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        locais_mon = sorted(df_monitores['Local'].dropna().unique().tolist())
                        # CORREÇÃO FASE 1: popula session_state na 1ª renderização
                        if st.session_state.filtro_local_mon is None:
                            st.session_state.filtro_local_mon = locais_mon
                        filtro_local_mon = st.multiselect("Local", options=locais_mon, default=st.session_state.filtro_local_mon, key="filtro_local_mon")
                    with col_f2:
                        busca_mon = st.text_input("🔎 Buscar (Modelo, Serial, Usuário)", key="busca_mon")
                        # CORREÇÃO FASE 1 (Claude #3 / Copilot #4.2): Botão Limpar Filtros
                        # CORREÇÃO FASE 2: rótulo "Resetar" (repõe todas as opções, não esvazia)
                        if st.button("🔄 Resetar Filtros (Monitores)", key="limpar_filtros_mon"):
                            st.session_state.filtro_local_mon = None
                            st.session_state.busca_mon = ""
                            st.rerun()
                    
                    # Aplicação dos Filtros
                    # CORREÇÃO FASE 1 (Copilot #2.1): .copy() explícito evita SettingWithCopyWarning
                    df_mon_filtrado = df_monitores[df_monitores['Local'].isin(filtro_local_mon)].copy()
                    
                    if busca_mon:
                        # CORREÇÃO FASE 1 (Copilot #1.4): re.escape evita regex injection
                        busca_mon_escaped = re.escape(busca_mon)
                        mask_mon = (
                            df_mon_filtrado['Modelo_Monitor'].str.contains(busca_mon_escaped, case=False, na=False) |
                            df_mon_filtrado['Serial_Monitor'].str.contains(busca_mon_escaped, case=False, na=False) |
                            df_mon_filtrado['Usuario'].str.contains(busca_mon_escaped, case=False, na=False)
                        )
                        df_mon_filtrado = df_mon_filtrado[mask_mon]
                    
                    # CORREÇÃO FASE 1 (Copilot #4.1): mensagem quando filtros não retornam resultados
                    if df_mon_filtrado.empty:
                        st.info("ℹ️ Nenhum monitor encontrado com os filtros aplicados. Tente ajustar os filtros.")
                    else:
                        # KPIs de Monitores
                        st.subheader("📊 Visão Geral dos Monitores")
                        col1, col2, col3 = st.columns(3)
                        
                        # MELHORIA 3: Metric cards
                        with col1:
                            st.markdown(render_metric_card(
                                "Total de Monitores",
                                len(df_mon_filtrado),
                                icone=config.ICONES_KPI['monitores']
                            ), unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(render_metric_card(
                                "Locais com Monitores",
                                df_mon_filtrado['Local'].nunique(),
                                icone=config.ICONES_KPI['locais']
                            ), unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(render_metric_card(
                                "Modelos Diferentes",
                                df_mon_filtrado['Modelo_Monitor'].nunique(),
                                icone=config.ICONES_KPI['modelos']
                            ), unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Gráficos de Monitores
                        st.subheader("📈 Distribuição")
                        col_g1, col_g2 = st.columns(2)
                        
                        with col_g1:
                            if not df_mon_filtrado.empty:
                                fig_mon_local = px.bar(
                                    df_mon_filtrado, 
                                    x='Local', 
                                    title='Monitores por Local', 
                                    color_discrete_sequence=[config.CORES['ciano_destaque']]
                                )
                                fig_mon_local = apply_dashboard_theme(fig_mon_local)
                                st.plotly_chart(fig_mon_local, use_container_width=True)
                        
                        with col_g2:
                            if not df_mon_filtrado.empty:
                                top_modelos_mon = df_mon_filtrado['Modelo_Monitor'].value_counts().head(10).reset_index()
                                top_modelos_mon.columns = ['Modelo', 'Quantidade']
                                fig_mon_modelo = px.bar(
                                    top_modelos_mon, 
                                    x='Quantidade', 
                                    y='Modelo', 
                                    orientation='h', 
                                    title='Top 10 Modelos de Monitores', 
                                    color_discrete_sequence=[config.CORES['azul_petroleo']]
                                )
                                fig_mon_modelo = apply_dashboard_theme(fig_mon_modelo)
                                st.plotly_chart(fig_mon_modelo, use_container_width=True)
                        
                        st.markdown("---")
                        
                        # Tabela de Monitores
                        st.subheader("🖥️ Inventário de Monitores")
                        
                        colunas_mon_exibir = ['Local', 'Usuario', 'Modelo_Monitor', 'Serial_Monitor', 'Data_Snapshot_Str']
                        df_mon_display = df_mon_filtrado[colunas_mon_exibir].copy()
                        df_mon_display.rename(columns={
                            'Modelo_Monitor': 'Modelo',
                            'Serial_Monitor': 'Nº de Série',
                            'Usuario': 'Usuário',
                            'Data_Snapshot_Str': 'Último Snapshot'
                        }, inplace=True)
                        
                        st.dataframe(
                            df_mon_display,
                            column_config={
                                "Nº de Série": st.column_config.TextColumn("Nº de Série", width="medium"),
                                "Modelo": st.column_config.TextColumn("Modelo", width="medium"),
                                "Usuário": st.column_config.TextColumn("Usuário", width="small")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Exportação de Monitores
                        st.markdown("---")
                        st.subheader("📥 Exportar Monitores")
                        criar_botoes_exportacao(df_mon_display, "monitores", "Monitores", "mon")
            
            # ==================================================================
            # SUB-SUB-ABA: IMPRESSORAS
            # ==================================================================
            with sub_tab_impressoras:
                if df_impressoras.empty:
                    st.info("ℹ️ Nenhuma impressora com número de série encontrada nos snapshots. Aguarde a próxima atualização dos scripts de coleta.")
                else:
                    # Filtros de Impressoras
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        locais_imp = sorted(df_impressoras['Local'].dropna().unique().tolist())
                        # CORREÇÃO FASE 1: popula session_state na 1ª renderização
                        if st.session_state.filtro_local_imp is None:
                            st.session_state.filtro_local_imp = locais_imp
                        filtro_local_imp = st.multiselect("Local", options=locais_imp, default=st.session_state.filtro_local_imp, key="filtro_local_imp")
                    with col_f2:
                        busca_imp = st.text_input("🔎 Buscar (Modelo, Serial, IP, Nome)", key="busca_imp")
                        # CORREÇÃO FASE 1 (Claude #3 / Copilot #4.2): Botão Limpar Filtros
                        # CORREÇÃO FASE 2: rótulo "Resetar" (repõe todas as opções, não esvazia)
                        if st.button("🔄 Resetar Filtros (Impressoras)", key="limpar_filtros_imp"):
                            st.session_state.filtro_local_imp = None
                            st.session_state.busca_imp = ""
                            st.rerun()
                    
                    # Aplicação dos Filtros
                    # CORREÇÃO FASE 1 (Copilot #2.1): .copy() explícito evita SettingWithCopyWarning
                    df_imp_filtrado = df_impressoras[df_impressoras['Local'].isin(filtro_local_imp)].copy()
                    
                    if busca_imp:
                        # CORREÇÃO FASE 1 (Copilot #1.4): re.escape evita regex injection
                        busca_imp_escaped = re.escape(busca_imp)
                        mask_imp = (
                            df_imp_filtrado['Modelo_Impressora'].str.contains(busca_imp_escaped, case=False, na=False) |
                            df_imp_filtrado['Serial_Impressora'].str.contains(busca_imp_escaped, case=False, na=False) |
                            df_imp_filtrado['IP_Impressora'].str.contains(busca_imp_escaped, case=False, na=False) |
                            df_imp_filtrado['Nome_Impressora'].str.contains(busca_imp_escaped, case=False, na=False)
                        )
                        df_imp_filtrado = df_imp_filtrado[mask_imp]
                    
                    # CORREÇÃO FASE 1 (Copilot #4.1): mensagem quando filtros não retornam resultados
                    if df_imp_filtrado.empty:
                        st.info("ℹ️ Nenhuma impressora encontrada com os filtros aplicados. Tente ajustar os filtros.")
                    else:
                        # KPIs de Impressoras
                        st.subheader("📊 Visão Geral das Impressoras")
                        col1, col2, col3 = st.columns(3)
                        
                        # MELHORIA 3: Metric cards
                        with col1:
                            st.markdown(render_metric_card(
                                "Total de Impressoras",
                                len(df_imp_filtrado),
                                icone=config.ICONES_KPI['impressoras']
                            ), unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(render_metric_card(
                                "Locais com Impressoras",
                                df_imp_filtrado['Local'].nunique(),
                                icone=config.ICONES_KPI['locais']
                            ), unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(render_metric_card(
                                "Modelos Diferentes",
                                df_imp_filtrado['Modelo_Impressora'].nunique(),
                                icone=config.ICONES_KPI['modelos']
                            ), unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Gráficos de Impressoras
                        st.subheader("📈 Distribuição")
                        col_g1, col_g2 = st.columns(2)
                        
                        with col_g1:
                            if not df_imp_filtrado.empty:
                                fig_imp_local = px.bar(
                                    df_imp_filtrado, 
                                    x='Local', 
                                    title='Impressoras por Local', 
                                    color_discrete_sequence=[config.CORES['ciano_destaque']]
                                )
                                fig_imp_local = apply_dashboard_theme(fig_imp_local)
                                st.plotly_chart(fig_imp_local, use_container_width=True)
                        
                        with col_g2:
                            if not df_imp_filtrado.empty:
                                top_modelos_imp = df_imp_filtrado['Modelo_Impressora'].value_counts().head(10).reset_index()
                                top_modelos_imp.columns = ['Modelo', 'Quantidade']
                                fig_imp_modelo = px.bar(
                                    top_modelos_imp, 
                                    x='Quantidade', 
                                    y='Modelo', 
                                    orientation='h', 
                                    title='Top 10 Modelos de Impressoras', 
                                    color_discrete_sequence=[config.CORES['azul_petroleo']]
                                )
                                fig_imp_modelo = apply_dashboard_theme(fig_imp_modelo)
                                st.plotly_chart(fig_imp_modelo, use_container_width=True)
                        
                        st.markdown("---")
                        
                        # Tabela de Impressoras
                        st.subheader("🖨️ Inventário de Impressoras")
                        
                        colunas_imp_exibir = ['Local', 'Nome_Impressora', 'Modelo_Impressora', 'Serial_Impressora', 'IP_Impressora', 'Data_Snapshot_Str']
                        df_imp_display = df_imp_filtrado[colunas_imp_exibir].copy()
                        df_imp_display.rename(columns={
                            'Nome_Impressora': 'Nome',
                            'Modelo_Impressora': 'Modelo',
                            'Serial_Impressora': 'Nº de Série (SNMP)',
                            'IP_Impressora': 'IP',
                            'Data_Snapshot_Str': 'Último Snapshot'
                        }, inplace=True)
                        
                        st.dataframe(
                            df_imp_display,
                            column_config={
                                "Nº de Série (SNMP)": st.column_config.TextColumn("Nº de Série", width="medium"),
                                "Modelo": st.column_config.TextColumn("Modelo", width="medium"),
                                "IP": st.column_config.TextColumn("IP", width="small"),
                                "Nome": st.column_config.TextColumn("Nome", width="medium")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        # Exportação de Impressoras
                        st.markdown("---")
                        st.subheader("📥 Exportar Impressoras")
                        criar_botoes_exportacao(df_imp_display, "impressoras", "Impressoras", "imp")

# ==============================================================================
# ABA 3: INVENTÁRIO GB (GOOGLE SHEETS)
# ==============================================================================
with tab_gb:
    # CORREÇÃO FASE 1 (Claude #1): st.stop() removido. Agora usa if/else para
    # isolar a falha do Sheets sem derrubar a aba Administrativa (independente).
    if df_gb.empty:
        st.warning("⚠️ Nenhum dado encontrado na planilha GB. Verifique o compartilhamento da planilha.")
    else:
        # FILTROS CONDICIONAIS: Só aparecem quando o relatório GB está selecionado
        # CORREÇÃO FASE 1: este bloco só executa se df_gb NÃO for vazio,
        # eliminando o risco de KeyError ao acessar df_gb['Local'] na sidebar.
        if relatorio_selecionado == "📊 Inventário GB":
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🔍 Filtros GB")
            
            locais_gb = sorted(df_gb['Local'].dropna().unique().tolist())
            tipos_equip = sorted(df_gb['Tipo_Equipamento'].dropna().unique().tolist())
            status_garantia = sorted(df_gb['Status_Garantia'].dropna().unique().tolist())
            
            # CORREÇÃO FASE 1: popula session_state na 1ª renderização
            if st.session_state.filtro_local_gb is None:
                st.session_state.filtro_local_gb = locais_gb
            if st.session_state.filtro_tipo_gb is None:
                st.session_state.filtro_tipo_gb = tipos_equip
            if st.session_state.filtro_status_gb is None:
                st.session_state.filtro_status_gb = status_garantia
            
            filtro_local_gb = st.sidebar.multiselect("Local (GB)", options=locais_gb, default=st.session_state.filtro_local_gb, key="filtro_local_gb")
            filtro_tipo_gb = st.sidebar.multiselect("Tipo de Equipamento", options=tipos_equip, default=st.session_state.filtro_tipo_gb, key="filtro_tipo_gb")
            filtro_status_gb = st.sidebar.multiselect("Status de Garantia", options=status_garantia, default=st.session_state.filtro_status_gb, key="filtro_status_gb")
            
            # CORREÇÃO FASE 1 (Claude #3 / Copilot #4.2): Botão Limpar Filtros GB
            # CORREÇÃO FASE 2: rótulo "Resetar" (repõe todas as opções, não esvazia)
            if st.sidebar.button("🔄 Resetar Filtros (GB)", key="limpar_filtros_gb"):
                st.session_state.filtro_local_gb = None
                st.session_state.filtro_tipo_gb = None
                st.session_state.filtro_status_gb = None
                st.rerun()
        else:
            # Valores padrão quando o filtro não está visível
            filtro_local_gb = sorted(df_gb['Local'].dropna().unique().tolist())
            filtro_tipo_gb = sorted(df_gb['Tipo_Equipamento'].dropna().unique().tolist())
            filtro_status_gb = sorted(df_gb['Status_Garantia'].dropna().unique().tolist())
        
        # Aplicação dos Filtros GB
        # CORREÇÃO FASE 1 (Copilot #2.1): .copy() explícito evita SettingWithCopyWarning
        df_gb_filtrado = df_gb[
            (df_gb['Local'].isin(filtro_local_gb)) &
            (df_gb['Tipo_Equipamento'].isin(filtro_tipo_gb)) &
            (df_gb['Status_Garantia'].isin(filtro_status_gb))
        ].copy()
        
        # CORREÇÃO FASE 1 (Copilot #4.1): mensagem quando filtros não retornam resultados
        if df_gb_filtrado.empty:
            st.info("ℹ️ Nenhum equipamento GB encontrado com os filtros aplicados. Tente ajustar os filtros.")
        else:
            # KPIs do Inventário GB
            st.title(f"📊 Painel de Inventário GB")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            total_gb = len(df_gb_filtrado)
            total_celulares = len(df_gb_filtrado[df_gb_filtrado['Tipo_Equipamento'] == 'Celular'])
            total_computadores = len(df_gb_filtrado[df_gb_filtrado['Tipo_Equipamento'] == 'Computador'])
            garantia_proxima = len(df_gb_filtrado[df_gb_filtrado['Status_Garantia'] == '🟡 Próxima do Vencimento'])
            garantia_vencida = len(df_gb_filtrado[df_gb_filtrado['Status_Garantia'] == '🔴 Vencida'])
            
            # MELHORIA 3: Metric cards com badges para garantias
            with col1:
                st.markdown(render_metric_card(
                    "Total Equipamentos GB",
                    total_gb,
                    icone=config.ICONES_KPI['garantias']
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(render_metric_card(
                    "Celulares",
                    total_celulares,
                    icone=config.ICONES_KPI['celulares']
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(render_metric_card(
                    "Computadores",
                    total_computadores,
                    icone=config.ICONES_KPI['total_maquinas']
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(render_metric_card(
                    "Garantia Próxima",
                    garantia_proxima,
                    icone=config.ICONES_KPI['pendentes'],
                    badge_valor=garantia_proxima,
                    badge_label="🟡"
                ), unsafe_allow_html=True)
            
            with col5:
                st.markdown(render_metric_card(
                    "Garantia Vencida",
                    garantia_vencida,
                    icone=config.ICONES_KPI['criticos'],
                    badge_valor=garantia_vencida,
                    badge_label="🔴"
                ), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Gráficos do Inventário GB
            st.subheader("📈 Distribuição de Equipamentos GB")
            col_g1, col_g2, col_g3 = st.columns(3)
            
            with col_g1:
                if not df_gb_filtrado.empty:
                    fig_local_gb = px.bar(df_gb_filtrado, x='Local', title='Equipamentos por Local', color_discrete_sequence=[config.CORES['ciano_destaque']])
                    fig_local_gb = apply_dashboard_theme(fig_local_gb)
                    st.plotly_chart(fig_local_gb, use_container_width=True)
            
            with col_g2:
                if not df_gb_filtrado.empty:
                    fig_tipo_gb = px.pie(df_gb_filtrado, names='Tipo_Equipamento', title='Distribuição por Tipo', hole=0.4, color_discrete_sequence=[config.CORES['azul_petroleo'], config.CORES['ciano_destaque'], config.CORES['amarelo_alerta']])
                    fig_tipo_gb = apply_dashboard_theme(fig_tipo_gb)
                    fig_tipo_gb.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_tipo_gb, use_container_width=True)
            
            with col_g3:
                if not df_gb_filtrado.empty:
                    # CORREÇÃO FASE 2: busca coluna de modelo sem colidir com
                    # 'Tipo_Equipamento' (antes gerava gráfico/tabela duplicados)
                    modelo_col = _detectar_coluna_modelo_gb(df_gb_filtrado)
                    if modelo_col:
                        top_modelos = df_gb_filtrado[modelo_col].value_counts().head(10).reset_index()
                        top_modelos.columns = ['Modelo', 'Quantidade']
                        fig_modelos = px.bar(top_modelos, x='Quantidade', y='Modelo', orientation='h', title='Top 10 Modelos', color_discrete_sequence=[config.CORES['verde_sucesso']])
                        fig_modelos = apply_dashboard_theme(fig_modelos)
                        st.plotly_chart(fig_modelos, use_container_width=True)
            
            st.markdown("---")
            
            # Tabela Detalhada do Inventário GB
            st.subheader("📋 Inventário Detalhado GB")
            
            # Seleciona colunas para exibição - INCLUINDO Nome_Dispositivo
            colunas_gb = ['Local', 'Codigo_BPCS', 'Nome_Dispositivo', 'Tipo_Equipamento', 'Status_Garantia', 'Dias_Restantes', 'Data_Garantia_Str']
            
            # CORREÇÃO FASE 2: detecção segura da coluna de modelo (sem duplicar 'Tipo_Equipamento')
            modelo_col = _detectar_coluna_modelo_gb(df_gb_filtrado)
            if modelo_col:
                colunas_gb.insert(3, modelo_col)
            
            # Adiciona coluna de serial/IMEI se existir
            serial_col = next((col for col in df_gb_filtrado.columns if 'serial' in col.lower() or 'imei' in col.lower()), None)
            if serial_col:
                colunas_gb.insert(4, serial_col)
            
            df_gb_display = df_gb_filtrado[colunas_gb].copy()
            
            # Renomeia colunas para exibição
            rename_map = {
                'Codigo_BPCS': 'Código BPCS',
                'Nome_Dispositivo': 'Nome do Dispositivo',
                'Tipo_Equipamento': 'Tipo',
                'Status_Garantia': 'Status Garantia',
                'Dias_Restantes': 'Dias Restantes',
                'Data_Garantia_Str': 'Término Garantia'
            }
            if modelo_col:
                rename_map[modelo_col] = 'Modelo'
            if serial_col:
                rename_map[serial_col] = 'Serial/IMEI'
            
            df_gb_display.rename(columns=rename_map, inplace=True)
            
            st.dataframe(
                df_gb_display,
                column_config={
                    "Status Garantia": st.column_config.TextColumn("Status", width="small"),
                    "Dias Restantes": st.column_config.NumberColumn("Dias", format="%d"),
                    "Código BPCS": st.column_config.TextColumn("BPCS", width="small"),
                    "Nome do Dispositivo": st.column_config.TextColumn("Nome Dispositivo", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Botões de Exportação GB
            st.markdown("---")
            st.subheader("📥 Exportar Dados GB Filtrados")
            criar_botoes_exportacao(df_gb_display, "inventario_gb", "Inventario_GB", "gb")

# ==============================================================================
# MELHORIA 4: ABA 4 — EXPORTAÇÃO UNIFICADA (NOVA)
# ==============================================================================
with tab_exportacao:
    st.title("⚙️ Exportação de Dados")
    st.markdown(f"*{config.ABAS_DASHBOARD['exportacao']['descricao']}*")
    st.markdown("---")
    
    st.info("ℹ️ Use os botões de exportação disponíveis em cada aba de inventário para baixar os dados filtrados em CSV ou Excel.")
    
    st.markdown("---")
    st.subheader("📦 Resumo dos Dados Disponíveis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏢 Inventário Administrativo")
        st.markdown(f"- 💻 Computadores: **{len(df_inventario)}** registros")
        st.markdown(f"- 📱 Celulares: **{len(df_celulares)}** registros")
        st.markdown(f"- 🖥️ Monitores: **{len(df_monitores)}** registros")
        st.markdown(f"- 🖨️ Impressoras: **{len(df_impressoras)}** registros")
    
    with col2:
        st.markdown("#### 📊 Inventário GB")
        st.markdown(f"- 📦 Equipamentos: **{len(df_gb)}** registros")
    
    st.markdown("---")
    st.markdown("""
    ### 💡 Dicas de Exportação
    
    - **CSV**: Compatível com Excel PT-BR (separador `;` e UTF-8 BOM)
    - **Excel (.xlsx)**: Formatação automática com sanitização de caracteres especiais
    - Os dados exportados respeitam os **filtros aplicados** na aba de origem
    - Use o botão **"🔄 Forçar Atualização dos Dados"** na sidebar para garantir dados recentes antes de exportar
    """)