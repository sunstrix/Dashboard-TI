import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
import pytz

import config
import drive_client
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

# Injeção de CSS Customizado (Tema Escuro TI Premium)
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
    /* Cards de Métricas (KPIs) */
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR: CONTROLES E FILTROS
# ==============================================================================
with st.sidebar:
    st.title(f"🛠️ {config.NOME_SISTEMA}")
    st.markdown(f"**{config.NOME_EMPRESA}**")
    st.markdown("---")
    
    if st.button("🔄 Forçar Atualização dos Dados"):
        drive_client.carregar_snapshots_drive.clear()
        st.rerun()
        
    st.markdown("### 🔍 Filtros")
    
# Carregamento e Processamento dos Dados
snapshots_brutos = drive_client.carregar_snapshots_drive()

if not snapshots_brutos:
    st.warning("⚠️ Nenhum dado carregado. Verifique a conexão com o Google Drive ou a API Key.")
    st.stop()

df_inventario, log_duplicatas = parser.processar_todos_snapshots(snapshots_brutos)

if df_inventario.empty:
    st.warning("⚠️ Nenhum snapshot válido encontrado após o processamento.")
    st.stop()

# População dos Filtros na Sidebar (após ter o dataframe)
with st.sidebar:
    locais = sorted(df_inventario['Local'].dropna().unique().tolist())
    filtro_local = st.multiselect("Local", options=locais, default=locais)
    
    usuarios = sorted(df_inventario['Usuario'].dropna().unique().tolist())
    filtro_usuario = st.multiselect("Usuário", options=usuarios, default=usuarios)
    
    windows = sorted(df_inventario['Windows'].dropna().unique().tolist())
    filtro_windows = st.multiselect("Sistema Operacional", options=windows, default=windows)
    
    filtro_processador = st.text_input("Buscar no Processador (ex: Ryzen, Intel)")
    busca_geral = st.text_input("🔎 Busca Livre (Nome, ID, AnyDesk, TV)")
    
    st.markdown("---")
    st.markdown("### 📊 Auditoria de Dados")
    with st.expander(f"Ver {len(log_duplicatas)} duplicatas descartadas"):
        if log_duplicatas:
            for log in log_duplicatas:
                st.caption(f"🗑️ {log}")
        else:
            st.caption("✅ Nenhuma duplicata encontrada nesta varredura.")

# ==============================================================================
# APLICAÇÃO DOS FILTROS
# ==============================================================================
df_filtrado = df_inventario[
    (df_inventario['Local'].isin(filtro_local)) &
    (df_inventario['Usuario'].isin(filtro_usuario)) &
    (df_inventario['Windows'].isin(filtro_windows))
]

if filtro_processador:
    df_filtrado = df_filtrado[df_filtrado['Processador'].str.contains(filtro_processador, case=False, na=False)]
    
if busca_geral:
    mask_busca = (
        df_filtrado['Nome_Computador'].str.contains(busca_geral, case=False, na=False) |
        df_filtrado['ID'].str.contains(busca_geral, case=False, na=False) |
        df_filtrado['AnyDesk'].str.contains(busca_geral, case=False, na=False) |
        df_filtrado['TeamViewer'].str.contains(busca_geral, case=False, na=False)
    )
    df_filtrado = df_filtrado[mask_busca]

# ==============================================================================
# KPIs (INDICADORES PRINCIPAIS)
# ==============================================================================
st.title(f"📊 Painel de Inventário de TI")
st.markdown(f"*Atualizado em: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')} (Horário de Brasília)*")

col1, col2, col3, col4, col5 = st.columns(5)

total_maquinas = len(df_filtrado)
maquinas_ram_baixa = len(df_filtrado[(df_filtrado['Memoria_RAM_GB'] < 8.0) & (df_filtrado['Memoria_RAM_GB'] > 0)])

amd_count = len(df_filtrado[df_filtrado['Processador'].str.contains('AMD', case=False, na=False)])
intel_count = len(df_filtrado[df_filtrado['Processador'].str.contains('Intel', case=False, na=False)])

if not df_filtrado.empty:
    data_mais_antiga = df_filtrado['Data_Snapshot'].min().strftime('%d/%m/%Y')
else:
    data_mais_antiga = "N/A"

col1.metric("Total de Máquinas", total_maquinas)
col2.metric("RAM < 8GB (Alerta)", maquinas_ram_baixa, delta_color="inverse")
col3.metric("Processadores AMD", amd_count)
col4.metric("Processadores Intel", intel_count)
col5.metric("Snapshot + Antigo", data_mais_antiga)

st.markdown("---")

# ==============================================================================
# GRÁFICOS INTERATIVOS (PLOTLY)
# ==============================================================================
st.subheader("📈 Distribuição do Parque de Máquinas")
col_g1, col_g2, col_g3 = st.columns(3)

with col_g1:
    if not df_filtrado.empty:
        fig_local = px.bar(df_filtrado, x='Local', title='Máquinas por Local', color_discrete_sequence=[config.CORES['ciano_destaque']])
        fig_local.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
        st.plotly_chart(fig_local, use_container_width=True)

with col_g2:
    if not df_filtrado.empty:
        top_proc = df_filtrado['Processador'].value_counts().head(10).reset_index()
        top_proc.columns = ['Processador', 'Quantidade']
        fig_proc = px.bar(top_proc, x='Quantidade', y='Processador', orientation='h', title='Top 10 Processadores', color_discrete_sequence=[config.CORES['azul_petroleo']])
        fig_proc.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
        st.plotly_chart(fig_proc, use_container_width=True)

with col_g3:
    if not df_filtrado.empty:
        fig_win = px.pie(df_filtrado, names='Windows', title='Distribuição Windows', hole=0.4, color_discrete_sequence=px.colors.sequential.Viridis)
        fig_win.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
        fig_win.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_win, use_container_width=True)

st.markdown("---")

# ==============================================================================
# TABELA DETALHADA E EXPORTAÇÃO
# ==============================================================================
st.subheader("💻 Inventário Detalhado")

# Cálculo de Status para a Tabela
limite_data = datetime.now(pytz.timezone('America/Sao_Paulo')) - timedelta(days=config.DIAS_LIMITE_ATRASO)
df_filtrado['Status'] = df_filtrado['Data_Snapshot'].apply(
    lambda x: '🔴 Desatualizada' if x < limite_data else '🟢 OK'
)
df_filtrado['Alerta_RAM'] = df_filtrado['Memoria_RAM_GB'].apply(
    lambda x: '⚠️ Baixa' if x < 8.0 and x > 0 else '✅ OK'
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

col_exp1, col_exp2, _ = st.columns([1, 1, 4])

with col_exp1:
    csv = df_display.to_csv(index=False, sep=';', decimal=',').encode('latin-1') # latin-1 para abrir direto no Excel PT-BR
    st.download_button(
        label="📄 Baixar CSV",
        data=csv,
        file_name=f"inventario_ti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

with col_exp2:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_display.to_excel(writer, index=False, sheet_name='Inventario_TI')
    excel_data = output.getvalue()
    
    st.download_button(
        label="📊 Baixar Excel",
        data=excel_data,
        file_name=f"inventario_ti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )