import re
from datetime import datetime
import pytz
import pandas as pd
import streamlit as st
import config

# Fuso horário de Brasília
TZ_BR = pytz.timezone("America/Sao_Paulo")

# ==============================================================================
# PARSER DE SNAPSHOTS DO DRIVE (LÓGICA ORIGINAL PRESERVADA)
# ==============================================================================

def arredondar_ram(memoria_ram_texto):
    """
    Converte texto de memória RAM (ex: "7,7 GB", "31,4 GB") para float arredondado para cima.
    Regra: 7,7GB → 8GB, 3,2GB → 4GB, 15,1GB → 16GB
    """
    if not memoria_ram_texto or pd.isna(memoria_ram_texto):
        return 0.0
    
    try:
        memoria_str = str(memoria_ram_texto).replace("GB", "").replace("gb", "").strip()
        memoria_str = memoria_str.replace(",", ".")
        memoria_float = float(memoria_str)
        import math
        return math.ceil(memoria_float)
    except (ValueError, AttributeError):
        return 0.0

def parsear_data_geracao(texto, data_fallback_drive):
    """
    Extrai a data 'Gerado em:' do cabeçalho.
    Se não encontrar ou falhar, usa a data de modificação do Drive.
    Retorna um objeto datetime timezone-aware (UTC-3).
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
            
    return datetime.now(TZ_BR)

def parsear_snapshot(conteudo, nome_arquivo, data_modificacao_drive):
    """
    Faz o parsing de um único arquivo de snapshot.
    Retorna um dicionário com os dados estruturados.
    Tolerante a ausências de campos e variações de espaçamento.
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
        "Memoria_RAM_GB": 0.0,
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
            
            if secao_atual == "ID":
                if chave_normalizada == "LOCAL":
                    dados["Local"] = valor
                elif chave_normalizada in ("USUARIO", "USUÁRIO"):
                    dados["Usuario"] = valor
                    
            elif secao_atual == "HARDWARE":
                if chave_normalizada == "NOME_COMPUTADOR":
                    dados["Nome_Computador"] = valor
                elif chave_normalizada == "MODELO_SISTEMA":
                    dados["Modelo_Sistema"] = valor
                elif chave_normalizada == "PROCESSADOR":
                    dados["Processador"] = valor
                elif chave_normalizada == "MEMORIA_RAM":
                    dados["Memoria_RAM"] = valor
                    dados["Memoria_RAM_GB"] = arredondar_ram(valor)
                elif chave_normalizada == "WINDOWS":
                    dados["Windows"] = valor
                elif chave_normalizada == "ID":
                    dados["ID"] = valor
                    
            elif secao_atual == "SUPORTE":
                if chave_normalizada == "ANYDESK":
                    dados["AnyDesk"] = valor
                elif chave_normalizada == "TEAMVIEWER":
                    dados["TeamViewer"] = valor

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
            log_duplicatas.append(
                f"Descartado: {row['Nome_Arquivo']} (ID: {row['ID']}) - "
                f"Data: {row['Data_Snapshot'].strftime('%d/%m/%Y %H:%M')}"
            )
            
    df_final["Data_Snapshot_Str"] = df_final["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M")
    
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
        
        if modelo:
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
    FILTRA: Apenas impressoras com número de série (ignora as sem serial).
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
        
        serial_match = re.search(r'Serial\s*\(?SNMP\)?\s*:\s*(.+)', bloco_impressora)
        serial = serial_match.group(1).strip() if serial_match else ""
        
        modelo_match = re.search(r'Modelo\s*\(?SNMP\)?\s*:\s*(.+)', bloco_impressora)
        modelo = modelo_match.group(1).strip() if modelo_match else ""
        
        ip_match = re.search(r'IP\s*:\s*(.+)', bloco_impressora)
        ip = ip_match.group(1).strip() if ip_match else ""
        
        # FILTRO CRÍTICO: Ignora impressoras sem número de série
        if not serial:
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
            df_monitores["Data_Snapshot_Str"] = df_monitores["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M")
            df_monitores = df_monitores.reset_index(drop=True)
    
    # Processa Impressoras com proteção
    df_impressoras = pd.DataFrame()
    if todas_impressoras:
        df_impressoras = pd.DataFrame(todas_impressoras)
        if not df_impressoras.empty and 'Data_Snapshot' in df_impressoras.columns:
            df_impressoras = df_impressoras.sort_values(by="Data_Snapshot", ascending=False)
            if 'Serial_Impressora' in df_impressoras.columns:
                df_impressoras = df_impressoras.drop_duplicates(subset=["Serial_Impressora"], keep="first")
            df_impressoras["Data_Snapshot_Str"] = df_impressoras["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M")
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
    df['Data_Garantia_Str'] = df['Data_Garantia'].dt.strftime('%d/%m/%Y')
    
    return df