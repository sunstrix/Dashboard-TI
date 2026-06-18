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
                    # Tenta converter para float para ordenação (ex: "31,4 GB" -> 31.4)
                    match_ram = re.search(r"([\d,]+)", valor.replace(".", ","))
                    if match_ram:
                        try:
                            dados["Memoria_RAM_GB"] = float(match_ram.group(1).replace(",", "."))
                        except ValueError:
                            pass
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
            st.warning(f"️ Erro ao processar o arquivo {snap.get('nome_arquivo', 'Desconhecido')}: {e}")
            
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
# PARSER DO INVENTÁRIO GB (NOVA LÓGICA ADICIONADA)
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

def inferir_tipo_equipamento(modelo):
    """
    Infere se o equipamento é um Celular ou Computador baseado no nome/modelo.
    """
    if pd.isna(modelo) or not isinstance(modelo, str):
        return "Outros"
        
    modelo_lower = modelo.lower()
    
    # Palavras-chave para Celulares
    celulares = ["iphone", "samsung", "motorola", "xiaomi", "celular", "smartphone", "galaxy", "redmi"]
    for keyword in celulares:
        if keyword in modelo_lower:
            return "Celular"
            
    # Palavras-chave para Computadores
    computadores = ["dell", "hp", "lenovo", "positivo", "acer", "asus", "notebook", "desktop", "pc", "computador", "thinkpad", "latitude", "inspiron"]
    for keyword in computadores:
        if keyword in modelo_lower:
            return "Computador"
            
    return "Outros"

def processar_planilha_gb(df_bruto):
    """
    Processa o DataFrame bruto lido da planilha Google Sheets (Aba PDV).
    Aplica mapeamento BPCS, trata datas de garantia, infere tipo de equipamento
    e calcula o status de garantia.
    """
    if df_bruto.empty:
        return pd.DataFrame()
        
    df = df_bruto.copy()
    
    # 1. Mapeamento BPCS -> Local
    # Busca coluna que contenha 'bpcs' no nome
    bpcs_col = next((col for col in df.columns if 'bpcs' in col.lower()), None)
    if bpcs_col:
        df['Codigo_BPCS'] = df[bpcs_col].astype(str).str.strip()
        df['Local'] = df['Codigo_BPCS'].map(config.MAPEAMENTO_BPCS_LOCAL).fillna('Desconhecido')
    else:
        df['Codigo_BPCS'] = ''
        df['Local'] = 'Desconhecido'
        
    # 2. Tratamento de Datas (Termino de Garantia)
    # Busca coluna que contenha 'garantia' e 'termino' (ou apenas 'garantia')
    data_col = next((col for col in df.columns if 'garantia' in col.lower() and 'termino' in col.lower()), None)
    if not data_col:
        data_col = next((col for col in df.columns if 'garantia' in col.lower()), None)
        
    if data_col:
        df['Data_Garantia'] = df[data_col].apply(parsear_data_iso)
        # Calcula dias restantes (usando timezone aware para bater com o fuso do sistema se necessário, 
        # mas como a planilha só tem data, usamos now() sem tz ou com tz para comparação segura)
        hoje = pd.Timestamp.now(tz=TZ_BR).normalize()
        # Remove tz da Data_Garantia para comparação direta se ela não tiver, ou adiciona
        if df['Data_Garantia'].dt.tz is None:
            df['Data_Garantia'] = df['Data_Garantia'].dt.tz_localize(TZ_BR)
            
        df['Dias_Restantes'] = (df['Data_Garantia'] - hoje).dt.days
    else:
        df['Data_Garantia'] = pd.NaT
        df['Dias_Restantes'] = -1
        
    # 3. Status de Garantia
    def get_status_garantia(dias):
        if pd.isna(dias):
            return "⚪ Sem Info"
        if dias < 0:
            return "🔴 Vencida"
        if dias <= config.DIAS_LIMITE_GARANTIA_PROXIMA:
            return "🟡 Próxima do Vencimento"
        return " Válida"
        
    df['Status_Garantia'] = df['Dias_Restantes'].apply(get_status_garantia)
    
    # 4. Inferência de Tipo de Equipamento
    modelo_col = next((col for col in df.columns if 'modelo' in col.lower() or 'equipamento' in col.lower()), None)
    if modelo_col:
        df['Tipo_Equipamento'] = df[modelo_col].apply(inferir_tipo_equipamento)
    else:
        df['Tipo_Equipamento'] = 'Outros'
        
    # Formatação de data para exibição amigável
    df['Data_Garantia_Str'] = df['Data_Garantia'].dt.strftime('%d/%m/%Y')
    
    return df