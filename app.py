import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
import pytz

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
    /* Placeholders de desenvolvimento */
    .dev-placeholder {{
        background-color: {config.CORES['fundo_card']};
        border: 2px dashed {config.CORES['borda']};
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
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
        sheets_client.carregar_planilha_gb.clear()
        st.rerun()
        
    st.markdown("### 🔍 Filtros")

# ==============================================================================
# CARREGAMENTO DOS DADOS (TODAS AS FONTES)
# ==============================================================================
# Inventário Administrativo (Drive - Computadores)
snapshots_brutos = drive_client.carregar_snapshots_drive()
df_inventario = pd.DataFrame()
log_duplicatas = []

if snapshots_brutos:
    df_inventario, log_duplicatas = parser.processar_todos_snapshots(snapshots_brutos)

# Periféricos (Drive - Monitores e Impressoras)
df_monitores = pd.DataFrame()
df_impressoras = pd.DataFrame()

if snapshots_brutos:
    df_monitores, df_impressoras = parser.processar_perifericos(snapshots_brutos)

# Inventário GB (Sheets)
df_gb_bruto = sheets_client.carregar_planilha_gb()
df_gb = pd.DataFrame()

if not df_gb_bruto.empty:
    df_gb = parser.processar_planilha_gb(df_gb_bruto)

# ==============================================================================
# NAVEGAÇÃO PRINCIPAL POR ABAS
# ==============================================================================
tab_admin, tab_gb = st.tabs([
    "🏢 Inventário Administrativo",
    "📊 Inventário GB"
])

# ==============================================================================
# ABA 1: INVENTÁRIO ADMINISTRATIVO
# ==============================================================================
with tab_admin:
    if df_inventario.empty:
        st.warning("⚠️ Nenhum dado carregado do Google Drive. Verifique a conexão ou a API Key.")
        st.stop()
    
    # Sub-abas do Inventário Administrativo
    sub_tab_computadores, sub_tab_celulares, sub_tab_perifericos = st.tabs([
        "💻 Computadores",
        "📱 Celulares Administrativos",
        "🖨️ Periféricos"
    ])
    
    # -------------------------------------------------------------------------
    # SUB-ABA 1.1: COMPUTADORES (Conteúdo Original Preservado)
    # -------------------------------------------------------------------------
    with sub_tab_computadores:
        # População dos Filtros na Sidebar (após ter o dataframe)
        with st.sidebar:
            locais = sorted(df_inventario['Local'].dropna().unique().tolist())
            filtro_local = st.multiselect("Local (Administrativo)", options=locais, default=locais)
            
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
        
        # Aplicação dos Filtros
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
        
        # KPIs (Indicadores Principais)
        st.title(f"📊 Painel de Inventário Administrativo")
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
        
        # Gráficos Interativos (Plotly)
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
        
        # Tabela Detalhada e Exportação
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
            csv = df_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                label="📄 Baixar CSV",
                data=csv,
                file_name=f"inventario_administrativo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col_exp2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='Inventario_Admin')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📊 Baixar Excel",
                data=excel_data,
                file_name=f"inventario_administrativo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # -------------------------------------------------------------------------
    # SUB-ABA 1.2: CELULARES ADMINISTRATIVOS (Placeholder)
    # -------------------------------------------------------------------------
    with sub_tab_celulares:
        st.title("📱 Celulares Administrativos")
        st.markdown("---")
        st.markdown("""
        <div class="dev-placeholder">
            <h2>🚧 Em Desenvolvimento</h2>
            <p>Esta seção está em desenvolvimento.</p>
            <p>Em breve, os celulares administrativos serão integrados aqui.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 **Funcionalidades planejadas:**")
        st.markdown("""
        - 📋 Inventário completo de celulares corporativos
        - 📊 KPIs: Total de dispositivos, distribuição por marca/modelo
        - 🔋 Status de bateria e saúde do dispositivo
        - 📱 Dados de suporte remoto (AnyDesk/TeamViewer Mobile)
        - 📅 Controle de troca e ciclo de vida
        - 📥 Exportação para CSV/Excel
        """)
    
    # -------------------------------------------------------------------------
    # SUB-ABA 1.3: PERIFÉRICOS (FUNCIONAL - Monitores e Impressoras)
    # -------------------------------------------------------------------------
    with sub_tab_perifericos:
        st.title("🖨️ Periféricos")
        st.markdown(f"*Atualizado em: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')} (Horário de Brasília)*")
        st.markdown("---")
        
        # Sub-sub-abas: Monitores e Impressoras
        sub_tab_monitores, sub_tab_impressoras = st.tabs([
            "🖥️ Monitores",
            "🖨️ Impressoras"
        ])
        
        # ======================================================================
        # SUB-SUB-ABA: MONITORES
        # ======================================================================
        with sub_tab_monitores:
            if df_monitores.empty:
                st.info("ℹ️ Nenhum monitor encontrado nos snapshots. Aguarde a próxima atualização dos scripts de coleta.")
            else:
                # Filtros de Monitores
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    locais_mon = sorted(df_monitores['Local'].dropna().unique().tolist())
                    filtro_local_mon = st.multiselect("Local", options=locais_mon, default=locais_mon, key="filtro_local_mon")
                with col_f2:
                    busca_mon = st.text_input("🔎 Buscar (Modelo, Serial, Usuário)", key="busca_mon")
                
                # Aplicação dos Filtros
                df_mon_filtrado = df_monitores[df_monitores['Local'].isin(filtro_local_mon)]
                
                if busca_mon:
                    mask_mon = (
                        df_mon_filtrado['Modelo_Monitor'].str.contains(busca_mon, case=False, na=False) |
                        df_mon_filtrado['Serial_Monitor'].str.contains(busca_mon, case=False, na=False) |
                        df_mon_filtrado['Usuario'].str.contains(busca_mon, case=False, na=False)
                    )
                    df_mon_filtrado = df_mon_filtrado[mask_mon]
                
                # KPIs de Monitores
                st.subheader("📊 Visão Geral dos Monitores")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Monitores", len(df_mon_filtrado))
                col2.metric("Locais com Monitores", df_mon_filtrado['Local'].nunique())
                col3.metric("Modelos Diferentes", df_mon_filtrado['Modelo_Monitor'].nunique())
                
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
                        fig_mon_local.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
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
                        fig_mon_modelo.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
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
                
                col_exp1, col_exp2, _ = st.columns([1, 1, 4])
                
                with col_exp1:
                    csv_mon = df_mon_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
                    st.download_button(
                        label="📄 Baixar CSV",
                        data=csv_mon,
                        file_name=f"monitores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="csv_mon"
                    )
                
                with col_exp2:
                    output_mon = io.BytesIO()
                    with pd.ExcelWriter(output_mon, engine='openpyxl') as writer:
                        df_mon_display.to_excel(writer, index=False, sheet_name='Monitores')
                    excel_data_mon = output_mon.getvalue()
                    
                    st.download_button(
                        label="📊 Baixar Excel",
                        data=excel_data_mon,
                        file_name=f"monitores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="excel_mon"
                    )
        
        # ======================================================================
        # SUB-SUB-ABA: IMPRESSORAS
        # ======================================================================
        with sub_tab_impressoras:
            if df_impressoras.empty:
                st.info("ℹ️ Nenhuma impressora com número de série encontrada nos snapshots. Aguarde a próxima atualização dos scripts de coleta.")
            else:
                # Filtros de Impressoras
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    locais_imp = sorted(df_impressoras['Local'].dropna().unique().tolist())
                    filtro_local_imp = st.multiselect("Local", options=locais_imp, default=locais_imp, key="filtro_local_imp")
                with col_f2:
                    busca_imp = st.text_input("🔎 Buscar (Modelo, Serial, IP, Nome)", key="busca_imp")
                
                # Aplicação dos Filtros
                df_imp_filtrado = df_impressoras[df_impressoras['Local'].isin(filtro_local_imp)]
                
                if busca_imp:
                    mask_imp = (
                        df_imp_filtrado['Modelo_Impressora'].str.contains(busca_imp, case=False, na=False) |
                        df_imp_filtrado['Serial_Impressora'].str.contains(busca_imp, case=False, na=False) |
                        df_imp_filtrado['IP_Impressora'].str.contains(busca_imp, case=False, na=False) |
                        df_imp_filtrado['Nome_Impressora'].str.contains(busca_imp, case=False, na=False)
                    )
                    df_imp_filtrado = df_imp_filtrado[mask_imp]
                
                # KPIs de Impressoras
                st.subheader("📊 Visão Geral das Impressoras")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Impressoras", len(df_imp_filtrado))
                col2.metric("Locais com Impressoras", df_imp_filtrado['Local'].nunique())
                col3.metric("Modelos Diferentes", df_imp_filtrado['Modelo_Impressora'].nunique())
                
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
                        fig_imp_local.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
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
                        fig_imp_modelo.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
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
                
                col_exp1, col_exp2, _ = st.columns([1, 1, 4])
                
                with col_exp1:
                    csv_imp = df_imp_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
                    st.download_button(
                        label="📄 Baixar CSV",
                        data=csv_imp,
                        file_name=f"impressoras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="csv_imp"
                    )
                
                with col_exp2:
                    output_imp = io.BytesIO()
                    with pd.ExcelWriter(output_imp, engine='openpyxl') as writer:
                        df_imp_display.to_excel(writer, index=False, sheet_name='Impressoras')
                    excel_data_imp = output_imp.getvalue()
                    
                    st.download_button(
                        label="📊 Baixar Excel",
                        data=excel_data_imp,
                        file_name=f"impressoras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="excel_imp"
                    )

# ==============================================================================
# ABA 2: INVENTÁRIO GB (GOOGLE SHEETS)
# ==============================================================================
with tab_gb:
    if df_gb.empty:
        st.warning("⚠️ Nenhum dado encontrado na planilha GB. Verifique o compartilhamento da planilha.")
        st.stop()
    
    # Filtros do Inventário GB
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filtros GB")
    
    locais_gb = sorted(df_gb['Local'].dropna().unique().tolist())
    filtro_local_gb = st.sidebar.multiselect("Local (GB)", options=locais_gb, default=locais_gb)
    
    tipos_equip = sorted(df_gb['Tipo_Equipamento'].dropna().unique().tolist())
    filtro_tipo_gb = st.sidebar.multiselect("Tipo de Equipamento", options=tipos_equip, default=tipos_equip)
    
    status_garantia = sorted(df_gb['Status_Garantia'].dropna().unique().tolist())
    filtro_status_gb = st.sidebar.multiselect("Status de Garantia", options=status_garantia, default=status_garantia)
    
    # Aplicação dos Filtros GB
    df_gb_filtrado = df_gb[
        (df_gb['Local'].isin(filtro_local_gb)) &
        (df_gb['Tipo_Equipamento'].isin(filtro_tipo_gb)) &
        (df_gb['Status_Garantia'].isin(filtro_status_gb))
    ]
    
    # KPIs do Inventário GB
    st.title(f"📊 Painel de Inventário GB")
    st.markdown(f"*Atualizado em: {datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')} (Horário de Brasília)*")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_gb = len(df_gb_filtrado)
    total_celulares = len(df_gb_filtrado[df_gb_filtrado['Tipo_Equipamento'] == 'Celular'])
    total_computadores = len(df_gb_filtrado[df_gb_filtrado['Tipo_Equipamento'] == 'Computador'])
    garantia_proxima = len(df_gb_filtrado[df_gb_filtrado['Status_Garantia'] == '🟡 Próxima do Vencimento'])
    garantia_vencida = len(df_gb_filtrado[df_gb_filtrado['Status_Garantia'] == '🔴 Vencida'])
    
    col1.metric("Total Equipamentos GB", total_gb)
    col2.metric("Celulares", total_celulares)
    col3.metric("Computadores", total_computadores)
    col4.metric("Garantia Próxima", garantia_proxima, delta_color="inverse")
    col5.metric("Garantia Vencida", garantia_vencida, delta_color="inverse")
    
    st.markdown("---")
    
    # Gráficos do Inventário GB
    st.subheader("📈 Distribuição de Equipamentos GB")
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        if not df_gb_filtrado.empty:
            fig_local_gb = px.bar(df_gb_filtrado, x='Local', title='Equipamentos por Local', color_discrete_sequence=[config.CORES['ciano_destaque']])
            fig_local_gb.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
            st.plotly_chart(fig_local_gb, use_container_width=True)
    
    with col_g2:
        if not df_gb_filtrado.empty:
            fig_tipo_gb = px.pie(df_gb_filtrado, names='Tipo_Equipamento', title='Distribuição por Tipo', hole=0.4, color_discrete_sequence=[config.CORES['azul_petroleo'], config.CORES['ciano_destaque'], config.CORES['amarelo_alerta']])
            fig_tipo_gb.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
            fig_tipo_gb.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_tipo_gb, use_container_width=True)
    
    with col_g3:
        if not df_gb_filtrado.empty:
            # Busca coluna de modelo dinamicamente
            modelo_col = next((col for col in df_gb_filtrado.columns if 'modelo' in col.lower() or 'equipamento' in col.lower()), None)
            if modelo_col:
                top_modelos = df_gb_filtrado[modelo_col].value_counts().head(10).reset_index()
                top_modelos.columns = ['Modelo', 'Quantidade']
                fig_modelos = px.bar(top_modelos, x='Quantidade', y='Modelo', orientation='h', title='Top 10 Modelos', color_discrete_sequence=[config.CORES['verde_sucesso']])
                fig_modelos.update_layout(config.PLOTLY_TEMPLATE_CONFIG['layout'])
                st.plotly_chart(fig_modelos, use_container_width=True)
    
    st.markdown("---")
    
    # Tabela Detalhada do Inventário GB
    st.subheader("📋 Inventário Detalhado GB")
    
    # Seleciona colunas para exibição - INCLUINDO Nome_Dispositivo
    colunas_gb = ['Local', 'Codigo_BPCS', 'Nome_Dispositivo', 'Tipo_Equipamento', 'Status_Garantia', 'Dias_Restantes', 'Data_Garantia_Str']
    
    # Adiciona coluna de modelo se existir
    modelo_col = next((col for col in df_gb_filtrado.columns if 'modelo' in col.lower() or 'equipamento' in col.lower()), None)
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
    
    col_exp1, col_exp2, _ = st.columns([1, 1, 4])
    
    with col_exp1:
        csv_gb = df_gb_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button(
            label="📄 Baixar CSV",
            data=csv_gb,
            file_name=f"inventario_gb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col_exp2:
        output_gb = io.BytesIO()
        with pd.ExcelWriter(output_gb, engine='openpyxl') as writer:
            df_gb_display.to_excel(writer, index=False, sheet_name='Inventario_GB')
        excel_data_gb = output_gb.getvalue()
        
        st.download_button(
            label="📊 Baixar Excel",
            data=excel_data_gb,
            file_name=f"inventario_gb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )