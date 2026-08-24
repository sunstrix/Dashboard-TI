import streamlit as st
import requests
import time
import io
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import config

# ==============================================================================
# FUNÇÃO UTILITÁRIA: SANITIZAÇÃO DE CONTEÚDO
# ==============================================================================
def _sanitizar_conteudo(conteudo):
    """
    Remove caracteres de controle ilegais do openpyxl do conteúdo bruto.
    Preserva emojis e caracteres Unicode válidos.
    
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
    if not conteudo:
        return conteudo
    
    # Regex do openpyxl para caracteres ilegais em XML 1.0
    illegal_char_regex = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
    return illegal_char_regex.sub('', conteudo)

# ==============================================================================
# FUNÇÃO UTILITÁRIA: VALIDAÇÃO DE CONTEÚDO DO SNAPSHOT (CORREÇÃO FASE 2)
# ==============================================================================
def _validar_conteudo_snapshot(conteudo):
    """
    CORREÇÃO FASE 2 (ROBUSTEZ): valida se o conteúdo baixado é realmente um
    snapshot de hardware, e NÃO uma página HTML de erro/aviso do Google Drive
    (ex: "aviso de verificação de vírus" para arquivos grandes, página de
    login, erro de compartilhamento).
    
    Antes, o HTML era decodificado e repassado ao parser, que falhava
    SILENCIOSAMENTE (sem seção [ID] → registro descartado sem nenhum aviso).
    Agora o arquivo inválido lança ValueError, que vira st.warning visível
    no carregar_snapshots_drive().
    
    Lança ValueError se o conteúdo for inválido.
    """
    if not conteudo or not conteudo.strip():
        raise ValueError("Conteúdo vazio retornado pelo Google Drive.")
    
    # Detecta páginas HTML de erro/aviso do Drive (virus scan, login, etc.)
    inicio = conteudo.lstrip()[:200].lower()
    if '<!doctype html' in inicio or '<html' in inicio:
        raise ValueError(
            "O Google Drive retornou uma página HTML (aviso de vírus/login) "
            "em vez do arquivo .txt. Verifique o tamanho/compartilhamento do arquivo."
        )
    
    # Um snapshot válido precisa ter pelo menos uma seção conhecida ou o
    # cabeçalho de data; sem isso o parser descartaria o arquivo em silêncio.
    conteudo_upper = conteudo.upper()
    tem_secao = any(secao in conteudo_upper for secao in config.SECOES_VALIDAS)
    tem_gerado_em = "GERADO EM:" in conteudo_upper
    
    if not tem_secao and not tem_gerado_em:
        raise ValueError(
            "Conteúdo não parece ser um snapshot válido "
            "(seções [ID]/[HARDWARE]/[SUPORTE] não encontradas)."
        )

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
        
        # Ignora arquivos na lista de exclusões do config (match exato)
        if nome in config.EXCLUSOES_DRIVE.get('arquivos', []):
            continue
        
        # CORREÇÃO FASE 1: Removido o filtro 'any(pasta.lower() in nome.lower() ...)'.
        # A query da API ('{DRIVE_FOLDER_ID}' in parents) já garante que apenas arquivos
        # DIRETOS da pasta raiz sejam listados (a API do Drive não é recursiva por padrão).
        # Manter o filtro de substring causava falso positivo, excluindo arquivos válidos
        # na raiz que por acaso tinham o nome da loja no título (ex: 'inventario_boticario.txt').
        
        arquivos_filtrados.append(arquivo)
    
    return arquivos_filtrados

def _baixar_arquivo_drive(file_id, max_retries=3):
    """
    Baixa o conteúdo de um arquivo de texto do Drive via URL de export público.
    Funciona para arquivos compartilhados como 'Qualquer pessoa com o link'.
    Inclui retry automático com backoff exponencial em caso de falha.
    Aplica sanitização no conteúdo bruto para remover caracteres ilegais.
    """
    url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    
    for tentativa in range(max_retries):
        try:
            response = requests.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Tenta decodificar como UTF-8, fallback para latin-1 (comum em PT-BR Windows)
            try:
                conteudo = response.content.decode('utf-8')
            except UnicodeDecodeError:
                conteudo = response.content.decode('latin-1')
            
            # SANITIZAÇÃO: Remove caracteres de controle ilegais do conteúdo bruto
            conteudo_sanitizado = _sanitizar_conteudo(conteudo)
            
            # CORREÇÃO FASE 2 (ROBUSTEZ): barra HTML/páginas de erro do Drive e
            # conteúdo sem as seções esperadas ANTES de entregar ao parser.
            # ValueError NÃO é RequestException → não entra no loop de retry
            # (retry não resolve página de aviso) e propaga para o
            # carregar_snapshots_drive(), que exibe st.warning por arquivo.
            _validar_conteudo_snapshot(conteudo_sanitizado)
            
            return conteudo_sanitizado
                
        except requests.exceptions.RequestException as e:
            if tentativa == max_retries - 1:
                raise
            
            # CORREÇÃO FASE 1: Feedback visual de retry para o usuário não achar que travou
            st.warning(f"⚠️ Falha no download (tentativa {tentativa + 1}/{max_retries}). Tentando novamente em {2 ** tentativa}s...")
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