import streamlit as st
import pandas as pd
import requests
import io
import config

def _baixar_planilha_csv():
    """
    Baixa a planilha Google Sheets como CSV via URL de exportação pública.
    Não requer API Key - funciona para planilhas públicas.
    Retorna o conteúdo CSV como string ou None se falhar.
    """
    # URL de exportação CSV da aba específica
    url = f"https://docs.google.com/spreadsheets/d/{config.SHEETS_SPREADSHEET_ID}/export?format=csv&gid={config.SHEETS_GID_PDV}"
    
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
            raise ValueError("Erro 404: Planilha ou aba não encontrada. Verifique o ID da planilha e o GID da aba no config.py.")
        elif e.response.status_code == 403:
            raise ValueError("Erro 403: Planilha não é pública ou acesso negado. Verifique o compartilhamento da planilha.")
        else:
            raise ValueError(f"Erro HTTP ao acessar a planilha: {e}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Erro de conexão ao acessar a planilha: {e}")
    except Exception as e:
        raise ValueError(f"Erro inesperado ao baixar a planilha: {e}")

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
    
    try:
        # Converte CSV para DataFrame
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Remove espaços em branco nos nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Remove espaços em branco nos valores de todas as colunas
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.strip()
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao processar o CSV da planilha: {e}")
        return pd.DataFrame()