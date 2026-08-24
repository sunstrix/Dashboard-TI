import re
from datetime import datetime
import math
import pytz
import pandas as pd
import streamlit as st
import config

# Fuso horário de Brasília
TZ_BR = pytz.timezone("America/Sao_Paulo")

# ==============================================================================
# CONSTANTES DE VALIDAÇÃO DE PERIFÉRICOS (CORREÇÃO FASE 0 + CASE-INSENSITIVE)
# ==============================================================================
# Valores que invalidam um número de série (periférico é descartado).
# Antes apenas "" e "0" eram barrados; "N/A" e "-" poluíam o inventário.
# CORREÇÃO FASE 1: Agora a validação é case-insensitive (pegando "Null", "NULL", "n/A", etc.)
SERIAIS_INVALIDOS = {
    "", "0", "n/a", "na", "-", "--", "null", "none",
    "sem série", "sem serie", "sem sn", "s/n", "sn"
}

# ==============================================================================
# FUNÇÃO UTILITÁRIA: SANITIZAÇÃO DE VALORES
# ==============================================================================
def sanitizar_valor(valor):
    """
    Remove caracteres de controle ilegais do openpyxl de uma string.
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
    if not valor or not isinstance(valor, str):
        return valor

    # Regex do openpyxl para caracteres ilegais em XML 1.0
    illegal_char_regex = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
    return illegal_char_regex.sub('', valor)

# ==============================================================================
# PARSER DE SNAPSHOTS DO DRIVE (LÓGICA ORIGINAL PRESERVADA)
# ==============================================================================

def arredondar_ram(memoria_ram_texto):
    """
    Converte texto de memória RAM (ex: "7,7 GB", "31,4 GB") para float arredondado para cima.
    Regra: 7,7GB → 8GB, 3,2GB → 4GB, 15,1GB → 16GB

    CORREÇÃO FASE 1: Retorna -1 (valor sentinela) em caso de erro de parsing
    para que o app.py possa exibir '🔴 Erro Parsing' em vez de '✅ OK'.
    """
    if not memoria_ram_texto or pd.isna(memoria_ram_texto):
        return -1.0

    try:
        memoria_str = str(memoria_ram_texto).replace("GB", "").replace("gb", "").strip()
        memoria_str = memoria_str.replace(",", ".")
        memoria_float = float(memoria_str)
        if memoria_float <= 0:
            return -1.0  # Valor inválido (ex: 0GB)
        return math.ceil(memoria_float)
    except (ValueError, AttributeError):
        return -1.0

def parsear_data_geracao(texto, data_fallback_drive):
    """
    Extrai a data 'Gerado em:' do cabeçalho.
    Se não encontrar ou falhar, usa a data de modificação do Drive.
    Retorna um objeto datetime timezone-aware (UTC-3).

    CORREÇÃO DE BUG (FASE 0): quando nenhuma das duas fontes funciona,
    retorna a data sentinela 01/01/1970 em vez de datetime.now().
    Antes, snapshots corrompidos apareciam como "atualizados hoje",
    ocultando máquinas quebradas no painel. Com a data sentinela:
    1) A máquina aparece como 🔴 Desatualizada;
    2) A deduplicação por ID prioriza snapshots com data válida.
    """
    match = re.search(r"Gerado em:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", texto, re.IGNORECASE)
    if match:
        try:
            data_str = match.group(1)
            dt = datetime.strptime(data_str, "%d/%m/%Y %H:%M:%S")
            return TZ_BR.localize(dt)
        except ValueError:
            pass

    if data_fallback_drive:
        try:
            data_str = data_fallback_drive.replace('Z', '+00:00')
            dt_utc = datetime.fromisoformat(data_str)
            return dt_utc.astimezone(TZ_BR)
        except Exception:
            pass

    # Data sentinela: snapshot sem data válida nunca parece "recente"
    return TZ_BR.localize(datetime(1970, 1, 1))

def parsear_snapshot(conteudo, nome_arquivo, data_modificacao_drive):
    """
    Faz o parsing de um único arquivo de snapshot.
    Retorna um dicionário com os dados estruturados.
    Tolerante a ausências de campos e variações de espaçamento.
    Aplica sanitização em todos os valores extraídos.
    """
    linhas = conteudo.splitlines()

    dados = {
        "Nome_Arquivo": nome_arquivo,
        "Local": "",
        "Usuario": "",
        "Nome_Computador": "",
        "Modelo_Sistema": "",
        "Processador": "",
        "Memoria_RAM": "",
        "Memoria_RAM_GB": -1.0,
        "Windows": "",
        "ID": "",
        "AnyDesk": "",
        "TeamViewer": "",
        "Data_Snapshot": parsear_data_geracao(conteudo, data_modificacao_drive)
    }

    secao_atual = None

    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("="):
            continue

        linha_upper = linha.upper()
        if linha_upper == "[ID]":
            secao_atual = "ID"
            continue
        elif linha_upper == "[HARDWARE]":
            secao_atual = "HARDWARE"
            continue
        elif linha_upper == "[SUPORTE]":
            secao_atual = "SUPORTE"
            continue
        elif "PERIFÉRICOS" in linha_upper or "PERIFERICOS" in linha_upper:
            secao_atual = "PERIFERICOS"
            continue

        if ":" in linha:
            chave, valor = linha.split(":", 1)
            chave = chave.strip().replace(" ", "_").upper()
            valor = valor.strip()

            # CORREÇÃO BUG #1: Regex atualizado para remover underscores E espaços antes do parêntese
            # Transforma "ID_(MAC/PROC)" em "ID" para compatibilidade com snapshots novos
            # Também funciona com "ID (MAC/PROC)" → "ID" (caso tenha espaço em vez de underscore)
            chave_normalizada = re.sub(r'[_\s]*\([^)]*\)', '', chave).strip()

            # SANITIZAÇÃO: Remove caracteres de controle ilegais do valor
            valor_sanitizado = sanitizar_valor(valor)

            if secao_atual == "ID":
                if chave_normalizada == "LOCAL":
                    dados["Local"] = valor_sanitizado
                elif chave_normalizada in ("USUARIO", "USUÁRIO"):
                    dados["Usuario"] = valor_sanitizado

            elif secao_atual == "HARDWARE":
                if chave_normalizada == "NOME_COMPUTADOR":
                    dados["Nome_Computador"] = valor_sanitizado
                elif chave_normalizada == "MODELO_SISTEMA":
                    dados["Modelo_Sistema"] = valor_sanitizado
                elif chave_normalizada == "PROCESSADOR":
                    dados["Processador"] = valor_sanitizado
                elif chave_normalizada == "MEMORIA_RAM":
                    dados["Memoria_RAM"] = valor_sanitizado
                    dados["Memoria_RAM_GB"] = arredondar_ram(valor_sanitizado)
                elif chave_normalizada == "WINDOWS":
                    dados["Windows"] = valor_sanitizado
                elif chave_normalizada == "ID":
                    dados["ID"] = valor_sanitizado

            elif secao_atual == "SUPORTE":
                if chave_normalizada == "ANYDESK":
                    dados["AnyDesk"] = valor_sanitizado
                elif chave_normalizada == "TEAMVIEWER":
                    dados["TeamViewer"] = valor_sanitizado

    return dados

def processar_todos_snapshots(lista_snapshots_brutos):
    """
    Recebe a lista de dicionários brutos do drive_client,
    faz o parsing de cada um e aplica a REGRA DE DEDUPLICAÇÃO.
    """
    snapshots_parseados = []
    for snap in lista_snapshots_brutos:
        try:
            dados = parsear_snapshot(snap["conteudo"], snap["nome_arquivo"], snap["data_modificacao_drive"])
            if dados and dados["ID"]:
                snapshots_parseados.append(dados)
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar o arquivo {snap.get('nome_arquivo', 'Desconhecido')}: {e}")

    if not snapshots_parseados:
        return pd.DataFrame(), []

    df = pd.DataFrame(snapshots_parseados)
    df = df.sort_values(by="Data_Snapshot", ascending=False)

    log_duplicatas = []
    df_antes = len(df)
    df_final = df.drop_duplicates(subset=["ID"], keep="first")
    df_depois = len(df_final)

    if df_antes > df_depois:
        duplicatas = df[df.duplicated(subset=["ID"], keep="first")]
        for _, row in duplicatas.iterrows():
            # CORREÇÃO FASE 1: Log mais claro com contexto (motivo da exclusão)
            log_duplicatas.append(
                f"Descartado (Duplicata de ID): {row['Nome_Arquivo']} (ID: {row['ID']}) - "
                f"Data: {row['Data_Snapshot'].strftime('%d/%m/%Y %H:%M')} "
                f"(Mantido: snapshot mais recente)"
            )

    # CORREÇÃO FASE 1: fillna para evitar exibição de 'NaT' na tabela
    df_final["Data_Snapshot_Str"] = df_final["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M").fillna('Sem Info')

    colunas_ordem = [
        "Local", "Usuario", "Nome_Computador", "Modelo_Sistema", "Processador",
        "Memoria_RAM", "Memoria_RAM_GB", "Windows", "ID", "AnyDesk", "TeamViewer",
        "Data_Snapshot", "Data_Snapshot_Str", "Nome_Arquivo"
    ]

    for col in colunas_ordem:
        if col not in df_final.columns:
            df_final[col] = ""

    df_final = df_final[colunas_ordem]
    df_final = df_final.reset_index(drop=True)

    return df_final, log_duplicatas

# ==============================================================================
# PARSER DE PERIFÉRICOS (FUNÇÕES REFINADAS - MAIS TOLERANTES)
# ==============================================================================

def parsear_monitores_do_snapshot(conteudo, local, usuario, data_snapshot):
    """
    Extrai monitores da seção 'PERIFÉRICOS — MONITORES' do snapshot.
    Regex refinada para aceitar variações de travessão (— ou -).
    FILTRA: Ignora monitores com número de série inválido ("0", "N/A", "-", ...).
    Aplica sanitização em todos os valores extraídos.
    """
    monitores = []

    # Regex tolerante: aceita tanto "—" (em dash) quanto "-" (hífen)
    match_monitores = re.search(
        r'PERIF[ÉE]RICOS\s*[-—]\s*MONITORES\s*\n\s*={5,}\s*\n(.*?)(?=\n\s*={5,}\s*\n|\Z)',
        conteudo,
        re.DOTALL | re.IGNORECASE
    )

    if not match_monitores:
        return monitores

    conteudo_monitores = match_monitores.group(1)

    # Encontra todos os monitores
    monitores_matches = re.finditer(
        r'Monitor\s+\d+:\s*\n(.*?)(?=\n\s*Monitor\s+\d+:|\Z)',
        conteudo_monitores,
        re.DOTALL
    )

    for match in monitores_matches:
        bloco_monitor = match.group(1)

        modelo_match = re.search(r'Modelo\s*:\s*(.+)', bloco_monitor)
        modelo = modelo_match.group(1).strip() if modelo_match else ""

        # Regex tolerante: aceita "Nº", "N°", "N." e variações de "Série"
        serial_match = re.search(r'N[º°\.]?\s*de\s*S[ée]rie\s*:\s*(.+)', bloco_monitor)
        serial = serial_match.group(1).strip() if serial_match else ""

        # SANITIZAÇÃO: Remove caracteres de controle ilegais
        modelo = sanitizar_valor(modelo)
        serial = sanitizar_valor(serial)

        # CORREÇÃO FASE 1: Validação Case-Insensitive de seriais inválidos
        serial_normalizado = serial.strip().lower() if isinstance(serial, str) else ""

        if modelo and serial_normalizado not in SERIAIS_INVALIDOS:
            monitores.append({
                "Local": local,
                "Usuario": usuario,
                "Modelo_Monitor": modelo,
                "Serial_Monitor": serial,
                "Data_Snapshot": data_snapshot
            })

    return monitores

def parsear_impressoras_do_snapshot(conteudo, local, data_snapshot):
    """
    Extrai impressoras da seção 'PERIFÉRICOS — IMPRESSORAS' do snapshot.
    FILTRA: Apenas impressoras com número de série válido (ignora "", "0", "N/A", ...).
    Aplica sanitização em todos os valores extraídos.
    """
    impressoras = []

    match_impressoras = re.search(
        r'PERIF[ÉE]RICOS\s*[-—]\s*IMPRESSORAS\s*\n\s*={5,}\s*\n(.*?)(?=\n\s*={5,}\s*\n|\Z)',
        conteudo,
        re.DOTALL | re.IGNORECASE
    )

    if not match_impressoras:
        return impressoras

    conteudo_impressoras = match_impressoras.group(1)

    impressoras_matches = re.finditer(
        r'Impressora\s+\d+:\s*\n(.*?)(?=\n\s*Impressora\s+\d+:|\Z)',
        conteudo_impressoras,
        re.DOTALL
    )

    for match in impressoras_matches:
        bloco_impressora = match.group(1)

        nome_match = re.search(r'Nome\s*:\s*(.+)', bloco_impressora)
        nome = nome_match.group(1).strip() if nome_match else ""

        # CORREÇÃO FASE 1: Regex corrigida. Antes exigia literalmente "SNMP".
        # Agora aceita qualquer sufixo entre parênteses ou nenhum sufixo.
        # Exemplos aceitos: "Serial: ABC", "Serial (SNMP): ABC", "Serial (MAC): ABC"
        serial_match = re.search(r'Serial\s*(?:\([^)]+\))?\s*:\s*(.+)', bloco_impressora)
        serial = serial_match.group(1).strip() if serial_match else ""

        # Mesmo ajuste para o Modelo
        modelo_match = re.search(r'Modelo\s*(?:\([^)]+\))?\s*:\s*(.+)', bloco_impressora)
        modelo = modelo_match.group(1).strip() if modelo_match else ""

        ip_match = re.search(r'IP\s*:\s*(.+)', bloco_impressora)
        ip = ip_match.group(1).strip() if ip_match else ""

        # SANITIZAÇÃO: Remove caracteres de controle ilegais
        nome = sanitizar_valor(nome)
        serial = sanitizar_valor(serial)
        modelo = sanitizar_valor(modelo)
        ip = sanitizar_valor(ip)

        # CORREÇÃO FASE 1: Validação Case-Insensitive de seriais inválidos
        serial_normalizado = serial.strip().lower() if isinstance(serial, str) else ""
        if serial_normalizado in SERIAIS_INVALIDOS:
            continue

        if nome:
            impressoras.append({
                "Local": local,
                "Nome_Impressora": nome,
                "Modelo_Impressora": modelo,
                "Serial_Impressora": serial,
                "IP_Impressora": ip,
                "Data_Snapshot": data_snapshot
            })

    return impressoras

def processar_perifericos(lista_snapshots_brutos):
    """
    Processa todos os snapshots e extrai monitores e impressoras.
    Com proteções adicionais para evitar erros em DataFrames vazios.
    """
    todos_monitores = []
    todas_impressoras = []

    # Proteção: se lista estiver vazia ou None, retorna DataFrames vazios
    if not lista_snapshots_brutos:
        return pd.DataFrame(), pd.DataFrame()

    for snap in lista_snapshots_brutos:
        try:
            dados_basicos = parsear_snapshot(snap["conteudo"], snap["nome_arquivo"], snap["data_modificacao_drive"])

            if not dados_basicos or not dados_basicos["ID"]:
                continue

            local = dados_basicos["Local"]
            usuario = dados_basicos["Usuario"]
            data_snapshot = dados_basicos["Data_Snapshot"]

            monitores = parsear_monitores_do_snapshot(snap["conteudo"], local, usuario, data_snapshot)
            todos_monitores.extend(monitores)

            impressoras = parsear_impressoras_do_snapshot(snap["conteudo"], local, data_snapshot)
            todas_impressoras.extend(impressoras)

        except Exception as e:
            st.warning(f"⚠️ Erro ao processar periféricos do arquivo {snap.get('nome_arquivo', 'Desconhecido')}: {e}")

    # Processa Monitores com proteção
    df_monitores = pd.DataFrame()
    if todos_monitores:
        df_monitores = pd.DataFrame(todos_monitores)
        if not df_monitores.empty and 'Data_Snapshot' in df_monitores.columns:
            df_monitores = df_monitores.sort_values(by="Data_Snapshot", ascending=False)
            if 'Serial_Monitor' in df_monitores.columns:
                df_monitores = df_monitores.drop_duplicates(subset=["Serial_Monitor"], keep="first")
            # CORREÇÃO FASE 1: fillna para evitar 'NaT' na tabela
            df_monitores["Data_Snapshot_Str"] = df_monitores["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M").fillna('Sem Info')
            df_monitores = df_monitores.reset_index(drop=True)

    # Processa Impressoras com proteção
    df_impressoras = pd.DataFrame()
    if todas_impressoras:
        df_impressoras = pd.DataFrame(todas_impressoras)
        if not df_impressoras.empty and 'Data_Snapshot' in df_impressoras.columns:
            df_impressoras = df_impressoras.sort_values(by="Data_Snapshot", ascending=False)
            if 'Serial_Impressora' in df_impressoras.columns:
                df_impressoras = df_impressoras.drop_duplicates(subset=["Serial_Impressora"], keep="first")
            # CORREÇÃO FASE 1: fillna para evitar 'NaT' na tabela
            df_impressoras["Data_Snapshot_Str"] = df_impressoras["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M").fillna('Sem Info')
            df_impressoras = df_impressoras.reset_index(drop=True)

    return df_monitores, df_impressoras

# ==============================================================================
# PARSER DO INVENTÁRIO GB (LÓGICA ORIGINAL PRESERVADA)
# ==============================================================================

def parsear_data_iso(data_str):
    """
    Converte strings de data para objetos datetime do pandas.
    """
    if pd.isna(data_str) or not isinstance(data_str, str):
        return pd.NaT

    data_str = data_str.strip()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", data_str):
        try:
            return pd.to_datetime(data_str, format="%Y-%m-%d")
        except ValueError:
            pass

    if re.match(r"^\d{2}/\d{2}/\d{4}$", data_str):
        try:
            return pd.to_datetime(data_str, format="%d/%m/%Y")
        except ValueError:
            pass

    try:
        return pd.to_datetime(data_str, dayfirst=True)
    except Exception:
        return pd.NaT

def processar_planilha_gb(df_bruto):
    """
    Processa o DataFrame bruto lido da planilha Google Sheets (Aba PDV).
    """
    if df_bruto.empty:
        return pd.DataFrame()

    df = df_bruto.copy()

    pdv_col = next((col for col in df.columns if 'pdv' in col.lower()), None)
    if pdv_col:
        df['Codigo_BPCS'] = df[pdv_col].astype(str).str.strip()
        df['Local'] = df['Codigo_BPCS'].map(config.MAPEAMENTO_BPCS_LOCAL).fillna('Desconhecido')
    else:
        df['Codigo_BPCS'] = ''
        df['Local'] = 'Desconhecido'

    tipo_col = next((col for col in df.columns if 'tipo' in col.lower()), None)
    if tipo_col:
        df['Tipo_Equipamento'] = df[tipo_col].astype(str).str.strip()
        df['Tipo_Equipamento'] = df['Tipo_Equipamento'].replace(['', 'nan', 'NaN', 'N/A', 'n/a'], 'Outros')
    else:
        df['Tipo_Equipamento'] = 'Outros'

    nome_col = next((col for col in df.columns if 'dispositivo' in col.lower() or ('nome' in col.lower() and 'pdv' not in col.lower())), None)
    if nome_col:
        df['Nome_Dispositivo'] = df[nome_col].astype(str).str.strip()
        df['Nome_Dispositivo'] = df['Nome_Dispositivo'].replace(['', 'nan', 'NaN', 'N/A', 'n/a'], '')
    else:
        df['Nome_Dispositivo'] = ''

    data_col = next((col for col in df.columns if 'garantia' in col.lower() and 'termino' in col.lower()), None)
    if not data_col:
        data_col = next((col for col in df.columns if 'garantia' in col.lower()), None)

    if data_col:
        df['Data_Garantia'] = df[data_col].apply(parsear_data_iso)
        hoje = pd.Timestamp.now(tz=TZ_BR).normalize()
        if df['Data_Garantia'].dt.tz is None:
            df['Data_Garantia'] = df['Data_Garantia'].dt.tz_localize(TZ_BR)
        df['Dias_Restantes'] = (df['Data_Garantia'] - hoje).dt.days
    else:
        df['Data_Garantia'] = pd.NaT
        df['Dias_Restantes'] = -1

    def get_status_garantia(dias):
        if pd.isna(dias):
            return "⚪ Sem Info"
        if dias < 0:
            return "🔴 Vencida"
        if dias <= config.DIAS_LIMITE_GARANTIA_PROXIMA:
            return "🟡 Próxima do Vencimento"
        return "🟢 Válida"

    df['Status_Garantia'] = df['Dias_Restantes'].apply(get_status_garantia)

    # CORREÇÃO FASE 1: fillna para evitar exibição de 'NaT' na tabela
    df['Data_Garantia_Str'] = df['Data_Garantia'].dt.strftime('%d/%m/%Y').fillna('Sem Info')

    return df

# ==============================================================================
# PARSER DE CELULARES ADMINISTRATIVOS (NOVO)
# ==============================================================================

def _extrair_responsavel(nome_dispositivo):
    """
    Extrai o responsável (usuário ou loja) do nome do dispositivo.
    Regra: sufixo após o separador " - " (ex: "14120 - Vanusa" → "Vanusa").
    Sem separador, retorna string vazia.
    """
    if not nome_dispositivo or not isinstance(nome_dispositivo, str):
        return ""
    if " - " in nome_dispositivo:
        return nome_dispositivo.split(" - ", 1)[1].strip()
    return ""

def _extrair_ipv4(ip_local):
    """
    A planilha envia 'IP Local' no formato "IPv6,IPv4".
    Extrai apenas o IPv4 para exibição (ex: "192.168.15.197").

    CORREÇÃO FASE 1: Usa regex robusta para extrair IPv4 em qualquer contexto
    (ex: "Gateway: 192.168.1.1, DNS: 8.8.8.8" retorna o primeiro IPv4 encontrado).
    """
    if not ip_local or not isinstance(ip_local, str):
        return ""

    # Regex para validar IPv4 (4 octetos separados por ponto)
    match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', ip_local)
    return match.group(0) if match else ""

def parsear_data_envio(data_str):
    """
    Converte 'Data do Último Envio dos Dados' (ex: "14/08/2026, 14:35:55")
    para datetime timezone-aware (UTC-3). Retorna pd.NaT se inválida.
    """
    if pd.isna(data_str) or not isinstance(data_str, str):
        return pd.NaT

    data_str = data_str.strip().replace(", ", " ").replace(",", " ")

    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return TZ_BR.localize(datetime.strptime(data_str, fmt))
        except ValueError:
            continue

    return pd.NaT

def processar_planilha_celulares(df_bruto):
    """
    Processa o DataFrame bruto da planilha de Celulares Administrativos.
    Aplica a MESMA lógica de categorização do Inventário GB:
    - Local: código BPCS (coluna 'Identificação') → config.MAPEAMENTO_BPCS_LOCAL,
      com fillna('Desconhecido') para códigos ausentes (ex: linha "teste").
    - Responsável: sufixo após " - " em 'Nome do dispositivo'.
    - Status de comunicação: mesma regra de negócio dos computadores
      (config.DIAS_LIMITE_ATRASO = 30 dias) sobre a data do último envio.
    """
    if df_bruto.empty:
        return pd.DataFrame()

    df = df_bruto.copy()

    # --- LOCAL (categorização BPCS, idêntica ao GB) ---
    id_col = next((col for col in df.columns if col.strip().lower() in ('identificação', 'identificacao')), None)
    if not id_col:
        id_col = next((col for col in df.columns if 'identifica' in col.lower()), None)

    if id_col:
        df['Codigo_BPCS'] = df[id_col].astype(str).str.strip()
        df['Codigo_BPCS'] = df['Codigo_BPCS'].replace(['', 'nan', 'NaN', 'N/A', 'n/a'], '')
        df['Local'] = df['Codigo_BPCS'].map(config.MAPEAMENTO_BPCS_LOCAL).fillna('Desconhecido')
    else:
        df['Codigo_BPCS'] = ''
        df['Local'] = 'Desconhecido'

    # --- NOME DO DISPOSITIVO + RESPONSÁVEL ---
    nome_col = next((col for col in df.columns if 'dispositivo' in col.lower()), None)
    if nome_col:
        df['Nome_Dispositivo'] = df[nome_col].astype(str).str.strip()
        df['Nome_Dispositivo'] = df['Nome_Dispositivo'].replace(['', 'nan', 'NaN', 'N/A', 'n/a'], '')
    else:
        df['Nome_Dispositivo'] = ''

    df['Responsavel'] = df['Nome_Dispositivo'].apply(_extrair_responsavel)

    # --- CAMPOS TÉCNICOS (sanitização Camada 2) ---
    def _coluna_texto(col, padrao=''):
        if col:
            return (
                df[col].astype(str).str.strip()
                .replace(['', 'nan', 'NaN', 'N/A', 'n/a', 'None', 'none'], padrao)
                .apply(sanitizar_valor)
            )
        return pd.Series([padrao] * len(df), index=df.index)

    modelo_col = next((col for col in df.columns if col.strip().lower() == 'modelo'), None)
    imei_col = next((col for col in df.columns if 'imei' in col.lower()), None)
    serial_col = next((col for col in df.columns if 'série' in col.lower() or 'serie' in col.lower()), None)
    politica_col = next((col for col in df.columns if 'politic' in col.lower() or 'polític' in col.lower()), None)
    versao_col = next((col for col in df.columns if 'versão' in col.lower() or 'versao' in col.lower()), None)
    status_inv_col = next((col for col in df.columns if 'status' in col.lower() and 'invent' in col.lower()), None)
    ip_col = next((col for col in df.columns if 'ip local' in col.lower()), None)
    hostname_col = next((col for col in df.columns if 'hostname' in col.lower()), None)

    df['Modelo'] = _coluna_texto(modelo_col)
    df['IMEI'] = _coluna_texto(imei_col)
    df['Serial'] = _coluna_texto(serial_col)
    df['Politica'] = _coluna_texto(politica_col, 'Sem Política')
    df['Versao_SO'] = _coluna_texto(versao_col)
    df['Status_Inventario'] = _coluna_texto(status_inv_col, 'Sem Info')
    df['IP_Local'] = _coluna_texto(ip_col).apply(_extrair_ipv4)
    df['Hostname'] = _coluna_texto(hostname_col)

    # --- DATA DO ÚLTIMO ENVIO + STATUS (mesma regra dos 30 dias) ---
    data_col = next((col for col in df.columns if 'ultimo envio' in col.lower() or 'último envio' in col.lower()), None)
    if data_col:
        df['Data_Ultimo_Envio'] = df[data_col].apply(parsear_data_envio)
    else:
        df['Data_Ultimo_Envio'] = pd.to_datetime(pd.Series([pd.NaT] * len(df), index=df.index))

    # CORREÇÃO FASE 2 (BUG CRÍTICO - TypeError tz-naive vs tz-aware):
    # O novo formato da planilha NÃO tem a coluna de data, então o fallback
    # acima cria uma Série datetime tz-NAIVE. Subtrair dela o `hoje` (tz-aware)
    # derruba o app no pandas 3.x com:
    # "TypeError: Cannot subtract tz-naive and tz-aware datetime-like objects".
    # Normaliza o dtype e garante tz-aware (mesmo padrão de processar_planilha_gb).
    df['Data_Ultimo_Envio'] = pd.to_datetime(df['Data_Ultimo_Envio'], errors='coerce')
    if df['Data_Ultimo_Envio'].dt.tz is None:
        df['Data_Ultimo_Envio'] = df['Data_Ultimo_Envio'].dt.tz_localize(TZ_BR)

    hoje = pd.Timestamp.now(tz=TZ_BR).normalize()
    df['Dias_Sem_Comunicacao'] = (hoje - df['Data_Ultimo_Envio']).dt.days

    # CORREÇÃO FASE 2 (FALLBACK DE DADOS): sem coluna de data, todos os dias
    # seriam NaN ("⚪ Sem Info"). O novo formato da planilha já traz a coluna
    # "Dias sem comunicação" calculada — usa ela quando a data não existe.
    # A lógica original (cálculo pela data) é preservada quando a coluna existe.
    if not data_col:
        dias_col = next((col for col in df.columns if 'dias sem comunica' in col.lower()), None)
        if dias_col:
            df['Dias_Sem_Comunicacao'] = pd.to_numeric(df[dias_col], errors='coerce')

    def get_status_comunicacao(dias):
        if pd.isna(dias):
            return "⚪ Sem Info"
        if dias > config.DIAS_LIMITE_ATRASO:
            return "🔴 Desatualizado"
        return "🟢 OK"

    df['Status_Comunicacao'] = df['Dias_Sem_Comunicacao'].apply(get_status_comunicacao)

    # CORREÇÃO FASE 1: fillna('Sem Info') em vez de fillna('') para melhor UX na tabela
    df['Data_Ultimo_Envio_Str'] = df['Data_Ultimo_Envio'].dt.strftime('%d/%m/%Y %H:%M').fillna('Sem Info')

    # --- ORDENAÇÃO (mais recentes primeiro, como nas demais abas) ---
    df = df.sort_values(by="Data_Ultimo_Envio", ascending=False, na_position='last')

    colunas_ordem = [
        "Status_Comunicacao", "Local", "Codigo_BPCS", "Responsavel",
        "Nome_Dispositivo", "Modelo", "IMEI", "Serial", "Politica",
        "Versao_SO", "Status_Inventario", "Dias_Sem_Comunicacao",
        "Data_Ultimo_Envio", "Data_Ultimo_Envio_Str", "IP_Local", "Hostname"
    ]

    for col in colunas_ordem:
        if col not in df.columns:
            df[col] = ""

    df = df[colunas_ordem]

    return df.reset_index(drop=True)