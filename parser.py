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
        # Remove "GB" e espaços, substitui vírgula por ponto
        memoria_str = str(memoria_ram_texto).replace("GB", "").replace("gb", "").strip()
        memoria_str = memoria_str.replace(",", ".")
        
        # Converte para float
        memoria_float = float(memoria_str)
        
        # Arredonda para cima (ceil)
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
    # Tenta encontrar "Gerado em: DD/MM/AAAA HH:MM:SS"
    match = re.search(r"Gerado em:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", texto, re.IGNORECASE)
    if match:
        try:
            data_str = match.group(1)
            dt = datetime.strptime(data_str, "%d/%m/%Y %H:%M:%S")
            return TZ_BR.localize(dt)
        except ValueError:
            pass
            
    # Fallback para data do Drive (formato ISO 8601: 2026-06-18T14:59:00.000Z)
    if data_fallback_drive:
        try:
            # Remove o Z e parseia
            data_str = data_fallback_drive.replace('Z', '+00:00')
            dt_utc = datetime.fromisoformat(data_str)
            return dt_utc.astimezone(TZ_BR)
        except Exception:
            pass
            
    # Último fallback: agora
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
            
        # Identifica mudança de seção
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
        # Novas seções de periféricos (não processadas aqui, serão tratadas separadamente)
        elif "PERIFÉRICOS" in linha_upper or "PERIFERICOS" in linha_upper:
            secao_atual = "PERIFERICOS"
            continue
            
        # Extrai chave e valor (tolerante a espaçamentos, divide apenas no primeiro ":")
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            chave = chave.strip().replace(" ", "_").upper()
            valor = valor.strip()
            
            if secao_atual == "ID":
                if chave == "LOCAL":
                    dados["Local"] = valor
                elif chave in ("USUARIO", "USUÁRIO"):
                    dados["Usuario"] = valor
                    
            elif secao_atual == "HARDWARE":
                if chave == "NOME_COMPUTADOR":
                    dados["Nome_Computador"] = valor
                elif chave == "MODELO_SISTEMA":
                    dados["Modelo_Sistema"] = valor
                elif chave == "PROCESSADOR":
                    dados["Processador"] = valor
                elif chave == "MEMORIA_RAM":
                    dados["Memoria_RAM"] = valor
                    # Usa a função de arredondamento para cima
                    dados["Memoria_RAM_GB"] = arredondar_ram(valor)
                elif chave == "WINDOWS":
                    dados["Windows"] = valor
                elif chave == "ID":
                    dados["ID"] = valor
                    
            elif secao_atual == "SUPORTE":
                if chave == "ANYDESK":
                    dados["AnyDesk"] = valor
                elif chave == "TEAMVIEWER":
                    dados["TeamViewer"] = valor

    return dados

def processar_todos_snapshots(lista_snapshots_brutos):
    """
    Recebe a lista de dicionários brutos do drive_client,
    faz o parsing de cada um e aplica a REGRA DE DEDUPLICAÇÃO.
    
    Regra: Manter apenas o snapshot mais recente para cada ID de Hardware.
    Critério de data: Campo "Gerado em:" (Data_Snapshot).
    
    Retorna:
    - df_final: DataFrame com os dados únicos e deduplicados.
    - log_duplicatas: Lista de strings para auditoria de descarte.
    """
    snapshots_parseados = []
    for snap in lista_snapshots_brutos:
        try:
            dados = parsear_snapshot(snap["conteudo"], snap["nome_arquivo"], snap["data_modificacao_drive"])
            if dados and dados["ID"]: # Só considera se tiver ID de Hardware
                snapshots_parseados.append(dados)
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar o arquivo {snap.get('nome_arquivo', 'Desconhecido')}: {e}")
            
    if not snapshots_parseados:
        return pd.DataFrame(), []
        
    df = pd.DataFrame(snapshots_parseados)
    
    # Ordena por Data_Snapshot decrescente (mais recente primeiro)
    df = df.sort_values(by="Data_Snapshot", ascending=False)
    
    log_duplicatas = []
    
    # Deduplicação: mantém a primeira ocorrência (mais recente) de cada ID
    df_antes = len(df)
    df_final = df.drop_duplicates(subset=["ID"], keep="first")
    df_depois = len(df_final)
    
    if df_antes > df_depois:
        # Gera log das duplicatas descartadas
        duplicatas = df[df.duplicated(subset=["ID"], keep="first")]
        for _, row in duplicatas.iterrows():
            log_duplicatas.append(
                f"Descartado: {row['Nome_Arquivo']} (ID: {row['ID']}) - "
                f"Data: {row['Data_Snapshot'].strftime('%d/%m/%Y %H:%M')}"
            )
            
    # Formata a data para exibição amigável na tabela
    df_final["Data_Snapshot_Str"] = df_final["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M")
    
    # Reordena colunas para a tabela
    colunas_ordem = [
        "Local", "Usuario", "Nome_Computador", "Modelo_Sistema", "Processador", 
        "Memoria_RAM", "Memoria_RAM_GB", "Windows", "ID", "AnyDesk", "TeamViewer", 
        "Data_Snapshot", "Data_Snapshot_Str", "Nome_Arquivo"
    ]
    
    # Garante que todas as colunas existam (caso algum snapshot esteja incompleto)
    for col in colunas_ordem:
        if col not in df_final.columns:
            df_final[col] = ""
            
    df_final = df_final[colunas_ordem]
    df_final = df_final.reset_index(drop=True)
    
    return df_final, log_duplicatas


# ==============================================================================
# PARSER DE PERIFÉRICOS (NOVAS FUNÇÕES ADICIONADAS)
# ==============================================================================

def parsear_monitores_do_snapshot(conteudo, local, usuario, data_snapshot):
    """
    Extrai monitores da seção 'PERIFÉRICOS — MONITORES' do snapshot.
    Retorna lista de dicionários com dados dos monitores.
    """
    monitores = []
    
    # Busca a seção de monitores
    match_monitores = re.search(
        r'PERIFÉRICOS\s*—\s*MONITORES\s*\n\s*={5,}\s*\n(.*?)(?=\n\s*={5,}\s*\n\s*PERIFÉRICOS|\Z)',
        conteudo,
        re.DOTALL | re.IGNORECASE
    )
    
    if not match_monitores:
        return monitores
    
    conteudo_monitores = match_monitores.group(1)
    
    # Encontra todos os monitores (Monitor 1:, Monitor 2:, etc.)
    monitores_matches = re.finditer(
        r'Monitor\s+\d+:\s*\n(.*?)(?=\n\s*Monitor\s+\d+:|\Z)',
        conteudo_monitores,
        re.DOTALL
    )
    
    for match in monitores_matches:
        bloco_monitor = match.group(1)
        
        # Extrai modelo
        modelo_match = re.search(r'Modelo\s*:\s*(.+)', bloco_monitor)
        modelo = modelo_match.group(1).strip() if modelo_match else ""
        
        # Extrai número de série
        serial_match = re.search(r'N[º°]\s*de\s*S[ée]rie\s*:\s*(.+)', bloco_monitor)
        serial = serial_match.group(1).strip() if serial_match else ""
        
        if modelo:  # Só adiciona se tiver modelo
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
    Retorna lista de dicionários com dados das impressoras.
    FILTRA: Apenas impressoras com número de série (ignora as sem serial).
    """
    impressoras = []
    
    # Busca a seção de impressoras
    match_impressoras = re.search(
        r'PERIFÉRICOS\s*—\s*IMPRESSORAS\s*\n\s*={5,}\s*\n(.*?)(?=\n\s*={5,}\s*\n|\Z)',
        conteudo,
        re.DOTALL | re.IGNORECASE
    )
    
    if not match_impressoras:
        return impressoras
    
    conteudo_impressoras = match_impressoras.group(1)
    
    # Encontra todas as impressoras (Impressora 1:, Impressora 2:, etc.)
    impressoras_matches = re.finditer(
        r'Impressora\s+\d+:\s*\n(.*?)(?=\n\s*Impressora\s+\d+:|\Z)',
        conteudo_impressoras,
        re.DOTALL
    )
    
    for match in impressoras_matches:
        bloco_impressora = match.group(1)
        
        # Extrai nome
        nome_match = re.search(r'Nome\s*:\s*(.+)', bloco_impressora)
        nome = nome_match.group(1).strip() if nome_match else ""
        
        # Extrai número de série (Serial SNMP)
        serial_match = re.search(r'Serial\s*\(SNMP\)\s*:\s*(.+)', bloco_impressora)
        serial = serial_match.group(1).strip() if serial_match else ""
        
        # Extrai modelo (Modelo SNMP)
        modelo_match = re.search(r'Modelo\s*\(SNMP\)\s*:\s*(.+)', bloco_impressora)
        modelo = modelo_match.group(1).strip() if modelo_match else ""
        
        # Extrai IP
        ip_match = re.search(r'IP\s*:\s*(.+)', bloco_impressora)
        ip = ip_match.group(1).strip() if ip_match else ""
        
        # FILTRO CRÍTICO: Ignora impressoras sem número de série
        if not serial:
            continue
        
        if nome:  # Só adiciona se tiver nome
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
    Aplica deduplicação:
    - Monitores: por Serial_Monitor (mantém o mais recente)
    - Impressoras: por Serial_Impressora (mantém o mais recente)
    
    Retorna:
    - df_monitores: DataFrame com monitores únicos
    - df_impressoras: DataFrame com impressoras únicas
    """
    todos_monitores = []
    todas_impressoras = []
    
    for snap in lista_snapshots_brutos:
        try:
            # Primeiro, parseia o snapshot completo para obter Local, Usuário e Data
            dados_basicos = parsear_snapshot(snap["conteudo"], snap["nome_arquivo"], snap["data_modificacao_drive"])
            
            if not dados_basicos or not dados_basicos["ID"]:
                continue
            
            local = dados_basicos["Local"]
            usuario = dados_basicos["Usuario"]
            data_snapshot = dados_basicos["Data_Snapshot"]
            
            # Extrai monitores
            monitores = parsear_monitores_do_snapshot(snap["conteudo"], local, usuario, data_snapshot)
            todos_monitores.extend(monitores)
            
            # Extrai impressoras
            impressoras = parsear_impressoras_do_snapshot(snap["conteudo"], local, data_snapshot)
            todas_impressoras.extend(impressoras)
            
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar periféricos do arquivo {snap.get('nome_arquivo', 'Desconhecido')}: {e}")
    
    # Processa Monitores
    df_monitores = pd.DataFrame()
    if todos_monitores:
        df_monitores = pd.DataFrame(todos_monitores)
        df_monitores = df_monitores.sort_values(by="Data_Snapshot", ascending=False)
        # Deduplica por Serial_Monitor (mantém o mais recente)
        df_monitores = df_monitores.drop_duplicates(subset=["Serial_Monitor"], keep="first")
        df_monitores["Data_Snapshot_Str"] = df_monitores["Data_Snapshot"].dt.strftime("%d/%m/%Y %H:%M")
        df_monitores = df_monitores.reset_index(drop=True)
    
    # Processa Impressoras
    df_impressoras = pd.DataFrame()
    if todas_impressoras:
        df_impressoras = pd.DataFrame(todas_impressoras)
        df_impressoras = df_impressoras.sort_values(by="Data_Snapshot", ascending=False)
        # Deduplica por Serial_Impressora (mantém o mais recente)
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
    Suporta formatos ISO (YYYY-MM-DD) e Brasileiro (DD/MM/YYYY).
    Retorna NaT se a conversão falhar.
    """
    if pd.isna(data_str) or not isinstance(data_str, str):
        return pd.NaT
        
    data_str = data_str.strip()
    
    # Formato ISO: YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", data_str):
        try:
            return pd.to_datetime(data_str, format="%Y-%m-%d")
        except ValueError:
            pass
            
    # Formato Brasileiro: DD/MM/YYYY
    if re.match(r"^\d{2}/\d{2}/\d{4}$", data_str):
        try:
            return pd.to_datetime(data_str, format="%d/%m/%Y")
        except ValueError:
            pass
            
    # Fallback genérico do pandas
    try:
        return pd.to_datetime(data_str, dayfirst=True)
    except Exception:
        return pd.NaT

def processar_planilha_gb(df_bruto):
    """
    Processa o DataFrame bruto lido da planilha Google Sheets (Aba PDV).
    Aplica mapeamento BPCS (coluna B), lê Tipo (coluna C), Nome do Dispositivo (coluna E),
    trata datas de garantia e calcula o status de garantia.
    """
    if df_bruto.empty:
        return pd.DataFrame()
        
    df = df_bruto.copy()
    
    # 1. BPCS - Coluna B (PDV)
    pdv_col = next((col for col in df.columns if 'pdv' in col.lower()), None)
    if pdv_col:
        df['Codigo_BPCS'] = df[pdv_col].astype(str).str.strip()
        df['Local'] = df['Codigo_BPCS'].map(config.MAPEAMENTO_BPCS_LOCAL).fillna('Desconhecido')
    else:
        df['Codigo_BPCS'] = ''
        df['Local'] = 'Desconhecido'
        
    # 2. TIPO - Coluna C (TIPO)
    tipo_col = next((col for col in df.columns if 'tipo' in col.lower()), None)
    if tipo_col:
        df['Tipo_Equipamento'] = df[tipo_col].astype(str).str.strip()
        df['Tipo_Equipamento'] = df['Tipo_Equipamento'].replace(['', 'nan', 'NaN', 'N/A', 'n/a'], 'Outros')
    else:
        df['Tipo_Equipamento'] = 'Outros'
        
    # 3. NOME DO DISPOSITIVO - Coluna E
    nome_col = next((col for col in df.columns if 'dispositivo' in col.lower() or ('nome' in col.lower() and 'pdv' not in col.lower())), None)
    if nome_col:
        df['Nome_Dispositivo'] = df[nome_col].astype(str).str.strip()
        df['Nome_Dispositivo'] = df['Nome_Dispositivo'].replace(['', 'nan', 'NaN', 'N/A', 'n/a'], '')
    else:
        df['Nome_Dispositivo'] = ''
        
    # 4. Tratamento de Datas (Termino de Garantia)
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
        
    # 5. Status de Garantia
    def get_status_garantia(dias):
        if pd.isna(dias):
            return "⚪ Sem Info"
        if dias < 0:
            return "🔴 Vencida"
        if dias <= config.DIAS_LIMITE_GARANTIA_PROXIMA:
            return "🟡 Próxima do Vencimento"
        return "🟢 Válida"
        
    df['Status_Garantia'] = df['Dias_Restantes'].apply(get_status_garantia)
    
    # Formatação de data para exibição amigável
    df['Data_Garantia_Str'] = df['Data_Garantia'].dt.strftime('%d/%m/%Y')
    
    return df