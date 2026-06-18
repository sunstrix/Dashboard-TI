import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

def _get_sheets_service():
    """Inicializa o cliente da API do Google Sheets usando a API Key."""
    if not config.GOOGLE_API_KEY:
        raise ValueError("Google Drive API Key não configurada. Verifique o arquivo .env e o README.")
    try:
        return build('sheets', 'v4', developerKey=config.GOOGLE_API_KEY)
    except Exception as e:
        raise ValueError(f"Erro ao inicializar o cliente do Google Sheets: {e}")

def _ler_aba_pdv():
    """
    Lê todos os dados da aba PDV da planilha configurada.
    Retorna uma lista de listas (dados brutos) ou lista vazia se falhar.
    """
    service = _get_sheets_service()
    
    try:
        # Lê todos os valores da aba PDV
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SHEETS_SPREADSHEET_ID,
            range=config.SHEETS_ABA_PDV
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return []
            
        return values
        
    except HttpError as e:
        if e.resp.status == 403:
            raise ValueError("Erro 403: Cota da API excedida ou API Key inválida/sem permissão para Sheets.")
        elif e.resp.status == 404:
            raise ValueError("Erro 404: Planilha ou aba não encontrada. Verifique o ID e o nome da aba no config.py.")
        else:
            raise ValueError(f"Erro ao acessar o Google Sheets: {e}")
    except Exception as e:
        raise ValueError(f"Erro inesperado ao ler a planilha: {e}")

@st.cache_data(ttl=config.CACHE_TTL, show_spinner="📊 Conectando ao Google Sheets e lendo planilha GB...")
def carregar_planilha_gb():
    """
    Função principal orquestradora para o Inventário GB.
    Lê a aba PDV da planilha Google Sheets e retorna um DataFrame pandas.
    O cache do Streamlit (1h) evita chamadas desnecessárias à API.
    """
    try:
        dados_brutos = _ler_aba_pdv()
    except ValueError as ve:
        st.error(f"❌ {ve}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Falha inesperada ao conectar com o Google Sheets: {e}")
        return pd.DataFrame()
    
    if not dados_brutos or len(dados_brutos) < 2:
        st.warning("⚠️ Nenhum dado encontrado na planilha GB. Verifique a API Key e o compartilhamento da planilha.")
        return pd.DataFrame()
    
    # Converte lista de listas em DataFrame
    # A primeira linha são os cabeçalhos
    headers = dados_brutos[0]
    data_rows = dados_brutos[1:]
    
    df = pd.DataFrame(data_rows, columns=headers)
    
    # Remove linhas completamente vazias
    df = df.dropna(how='all')
    
    # Remove espaços em branco nos nomes das colunas
    df.columns = df.columns.str.strip()
    
    # Remove espaços em branco nos valores de todas as colunas
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    return df