@echo off
title Instalador Dashboard-TI v2.1 (Execucao Direta)
color 0A

echo ============================================================
echo    INSTALADOR AUTOMATIZADO - DASHBOARD TI (GRUPO NSF)
echo    Versao 2.1 - Execucao direta (Sem activate.bat)
echo ============================================================
echo.

set LOGFILE=instalar.log
echo Iniciando instalacao em %date% %time% > %LOGFILE%

echo [1/5] Verificando presenca do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nao encontrado. Tentando instalar via winget...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Nao foi possivel instalar o Python.
        pause
        exit /b 1
    )
) else (
    echo Python ja esta instalado.
)

echo.
echo [2/5] Criando Ambiente Virtual Isolado (venv)...
if not exist "venv\Scripts\python.exe" (
    echo Criando venv...
    python -m venv venv >> %LOGFILE% 2>&1
) else (
    echo Ambiente virtual ja existe.
)

echo.
echo [3/5] Atualizando pip dentro do venv...
venv\Scripts\python.exe -m pip install --upgrade pip >> %LOGFILE% 2>&1

echo.
echo [4/5] Instalando dependencias do projeto...
venv\Scripts\python.exe -m pip install -r requirements.txt >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias.
    echo Por favor, abra o arquivo instalar.log, copie as ULTIMAS 10 LINHAS e me envie.
    pause
    exit /b 1
)

echo.
echo [5/5] Criando atalho de execucao (executar.bat)...
(
echo @echo off
echo cd /d "%%~dp0"
echo title Dashboard TI - Grupo NSF
echo venv\Scripts\python.exe -m streamlit run app.py
echo pause
) > executar.bat

echo.
echo ============================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo Para iniciar o dashboard, de um duplo clique no arquivo "executar.bat".
echo.
pause