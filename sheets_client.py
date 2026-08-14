import streamlit as st
import pandas as pd
import requests
import io
import config


# ==============================================================================
# FUNÇÃO GENÉRICA DE DOWNLOAD DE PLANILHAS (DRY)
# ==============================================================================
def _baixar_csv_de_planilha(spreadsheet_id, gid, nome_log):
    """
    Baixa uma planilha Google Sheets como CSV via URL de exportação pública.
    Não requer API Key - funciona para planilhas públicas.
    Retorna o conteúdo CSV como string ou lança ValueError em caso de falha.
    
    Parâmetros:
        spreadsheet_id: ID da planilha
        gid: ID da aba (0 para a primeira aba)
        nome_log: Nome usado em mensagens de erro para debugging
    """
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Tenta decodificar como UTF-8
        try:
            return response.content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback para latin-1 (comum em planilhas PT-BR)
            return response.content.decode('latin-1')
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(
                f"Erro 404: Planilha {nome_log} ou aba não encontrada. "
                f"Verifique o ID da planilha e o GID da aba no config.py."
            )
        elif e.response.status_code == 403:
            raise ValueError(
                f"Erro 403: Planilha {nome_log} não é pública ou acesso negado. "
                f"Verifique o compartilhamento da planilha."
            )
        else:
            raise ValueError(f"Erro HTTP ao acessar a planilha {nome_log}: {e}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Erro de conexão ao acessar a planilha {nome_log}: {e}")
    except Exception as e:
        raise ValueError(f"Erro inesperado ao baixar a planilha {nome_log}: {e}")


# ==============================================================================
# WRAPPERS DE DOWNLOAD (preservam a interface interna original)
# ==============================================================================
def _baixar_planilha_csv():
    """
    Wrapper para download da planilha GB (Inventário GB - PDV).
    Preserva a interface original para compatibilidade.
    """
    return _baixar_csv_de_planilha(
        config.SHEETS_SPREADSHEET_ID,
        config.SHEETS_GID_PDV,
        "GB (PDV)"
    )


def _baixar_planilha_celulares_csv():
    """
    Wrapper para download da planilha de Celulares Administrativos.
    """
    return _baixar_csv_de_planilha(
        config.SHEETS_SPREADSHEET_ID_CELULARES,
        config.SHEETS_GID_CELULARES,
        "Celulares Administrativos"
    )


# ==============================================================================
# CARREGAMENTO E PARSE DO CSV (reutilizável)
# ==============================================================================
def _csv_para_dataframe(csv_content, nome_planilha):
    """
    Converte string CSV em DataFrame pandas com sanitização padrão.
    Remove linhas vazias, espaços em colunas e em valores.
    """
    try:
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Remove espaços em branco nos nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Remove espaços em branco nos valores de todas as colunas de string
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.strip()
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao processar o CSV da planilha {nome_planilha}: {e}")
        return pd.DataFrame()


# ==============================================================================
# FUNÇÕES PÚBLICAS COM CACHE (Streamlit)
# ==============================================================================
@st.cache_data(ttl=config.CACHE_TTL, show_spinner="📊 Conectando ao Google Sheets e lendo planilha GB...")
def carregar_planilha_gb():
    """
    Função principal orquestradora para o Inventário GB.
    Baixa a planilha como CSV via URL pública e retorna um DataFrame pandas.
    O cache do Streamlit (1h) evita downloads desnecessários.
    """
    try:
        csv_content = _baixar_planilha_csv()
    except ValueError as ve:
        st.error(f"❌ {ve}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Falha inesperada ao conectar com o Google Sheets: {e}")
        return pd.DataFrame()
    
    if not csv_content or len(csv_content.strip()) == 0:
        st.warning("⚠️ Nenhum dado encontrado na planilha GB. Verifique o compartilhamento da planilha.")
        return pd.DataFrame()
    
    return _csv_para_dataframe(csv_content, "GB (PDV)")


@st.cache_data(ttl=config.CACHE_TTL, show_spinner="📱 Conectando ao Google Sheets e lendo planilha de Celulares...")
def carregar_planilha_celulares():
    """
    Função principal orquestradora para Celulares Administrativos.
    Baixa a planilha como CSV via URL pública e retorna um DataFrame pandas.
    O cache do Streamlit (1h) evita downloads desnecessários.
    """
    try:
        csv_content = _baixar_planilha_celulares_csv()
    except ValueError as ve:
        st.error(f"❌ {ve}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Falha inesperada ao conectar com o Google Sheets (Celulares): {e}")
        return pd.DataFrame()
    
    if not csv_content or len(csv_content.strip()) == 0:
        st.warning(
            "⚠️ Nenhum dado encontrado na planilha de Celulares Administrativos. "
            "Verifique o compartilhamento da planilha."
        )
        return pd.DataFrame()
    
    return _csv_para_dataframe(csv_content, "Celulares Administrativos")