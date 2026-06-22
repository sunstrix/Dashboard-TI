import streamlit as st
import requests
import time
import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import config

def _get_drive_service():
    """Inicializa o cliente da API do Google Drive usando a API Key."""
    if not config.GOOGLE_API_KEY:
        raise ValueError("Google Drive API Key não configurada. Verifique o arquivo .env e o README.")
    try:
        return build('drive', 'v3', developerKey=config.GOOGLE_API_KEY)
    except Exception as e:
        raise ValueError(f"Erro ao inicializar o cliente do Google Drive: {e}")

def _listar_arquivos_drive():
    """
    Lista todos os arquivos na pasta configurada do Google Drive.
    Implementa paginação automática para suportar centenas de arquivos.
    Aplica filtros de exclusão definidos em config.EXCLUSOES_DRIVE.
    """
    service = _get_drive_service()
    arquivos = []
    page_token = None
    
    while True:
        try:
            response = service.files().list(
                q=f"'{config.DRIVE_FOLDER_ID}' in parents and trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name, modifiedTime, mimeType)',
                pageToken=page_token
            ).execute()
            
            arquivos.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        except HttpError as e:
            if e.resp.status == 403:
                raise ValueError("Erro 403: Cota da API excedida ou API Key inválida/sem permissão.")
            elif e.resp.status == 404:
                raise ValueError("Erro 404: Pasta do Google Drive não encontrada. Verifique o ID no config.py.")
            else:
                raise ValueError(f"Erro ao acessar o Google Drive: {e}")
    
    # Aplica filtros de exclusão RIGOROSOS
    arquivos_filtrados = []
    for arquivo in arquivos:
        nome = arquivo.get('name', '')
        mime_type = arquivo.get('mimeType', '')
        
        # PRIORIDADE MÁXIMA: Ignora TODAS as pastas (incluindo "Boticário")
        if mime_type == 'application/vnd.google-apps.folder':
            continue
        
        # Ignora arquivos que NÃO sejam .txt (snapshots de hardware)
        if not nome.endswith('.txt'):
            continue
        
        # Ignora arquivos na lista de exclusões do config
        if nome in config.EXCLUSOES_DRIVE.get('arquivos', []):
            continue
        
        # Ignora arquivos cujos nomes contenham palavras-chave de pastas excluídas
        pastas_excluidas = config.EXCLUSOES_DRIVE.get('pastas', [])
        if any(pasta.lower() in nome.lower() for pasta in pastas_excluidas):
            continue
        
        arquivos_filtrados.append(arquivo)
    
    return arquivos_filtrados

def _baixar_arquivo_drive(file_id, max_retries=3):
    """
    Baixa o conteúdo de um arquivo de texto do Drive usando MediaIoBaseDownload.
    Método oficial da API do Google para download de arquivos.
    Inclui retry automático com backoff exponencial em caso de falha.
    """
    service = _get_drive_service()
    
    for tentativa in range(max_retries):
        try:
            # Cria o request de download usando a API oficial
            request = service.files().get_media(fileId=file_id)
            
            # Buffer para receber o conteúdo do arquivo
            buffer = io.BytesIO()
            
            # Executa o download usando MediaIoBaseDownload
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Obtém o conteúdo do buffer
            conteudo_bytes = buffer.getvalue()
            
            # Tenta decodificar como UTF-8, fallback para latin-1 (comum em PT-BR Windows)
            try:
                return conteudo_bytes.decode('utf-8')
            except UnicodeDecodeError:
                return conteudo_bytes.decode('latin-1')
                
        except HttpError as e:
            # Erro HTTP da API do Google (403, 404, etc)
            if tentativa == max_retries - 1:
                if e.resp.status == 403:
                    raise ValueError(f"Erro 403: Permissão negada para baixar arquivo {file_id}. Verifique se o arquivo está compartilhado como 'Qualquer pessoa com o link'.")
                elif e.resp.status == 404:
                    raise ValueError(f"Erro 404: Arquivo {file_id} não encontrado.")
                else:
                    raise ValueError(f"Erro HTTP ao baixar arquivo: {e}")
            # Se ainda há tentativas, aguarda com backoff exponencial
            time.sleep(2 ** tentativa)  # Backoff exponencial: 1s, 2s, 4s...
            
        except Exception as e:
            # Qualquer outro erro (rede, timeout, etc)
            if tentativa == max_retries - 1:
                raise
            time.sleep(2 ** tentativa)  # Backoff exponencial: 1s, 2s, 4s...

@st.cache_data(ttl=config.CACHE_TTL, show_spinner="📡 Conectando ao Google Drive e baixando snapshots...")
def carregar_snapshots_drive():
    """
    Função principal orquestradora.
    Lista os arquivos na pasta pública e baixa o conteúdo de cada um.
    Retorna uma lista de dicionários com os dados brutos para o parser.
    O cache do Streamlit (1h) evita chamadas desnecessárias à API.
    """
    try:
        arquivos_drive = _listar_arquivos_drive()
    except ValueError as ve:
        st.error(f"❌ {ve}")
        return []
    except Exception as e:
        st.error(f"❌ Falha inesperada ao conectar com o Google Drive: {e}")
        return []
        
    if not arquivos_drive:
        st.warning("⚠️ Nenhum arquivo de snapshot encontrado na pasta do Google Drive.")
        return []
        
    snapshots = []
    total = len(arquivos_drive)
    
    # Barra de progresso para download dos arquivos
    progress_bar = st.progress(0, text="Iniciando download dos snapshots...")
    
    for i, arquivo in enumerate(arquivos_drive):
        file_id = arquivo['id']
        nome = arquivo['name']
        modified_time = arquivo.get('modifiedTime', '')
        
        # Atualiza barra de progresso
        progress_bar.progress((i + 1) / total, text=f"📥 Baixando {i+1}/{total}: {nome}")
        
        try:
            conteudo = _baixar_arquivo_drive(file_id)
            snapshots.append({
                "nome_arquivo": nome,
                "conteudo": conteudo,
                "data_modificacao_drive": modified_time
            })
        except Exception as e:
            st.warning(f"⚠️ Não foi possível baixar o arquivo {nome}. Erro: {e}")
            
    progress_bar.empty() # Remove a barra de progresso após concluir
    
    return snapshots