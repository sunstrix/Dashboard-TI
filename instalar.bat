@echo off
title Instalador Dashboard-TI
color 0A

echo ============================================================
echo    INSTALADOR AUTOMATIZADO - DASHBOARD TI (GRUPO NSF)
echo ============================================================
echo.

set LOGFILE=instalar.log
echo Iniciando instalacao em %date% %time% > %LOGFILE%

echo [1/4] Verificando presenca do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nao encontrado. Tentando instalar via winget...
    echo Python nao encontrado. Tentando instalar via winget... >> %LOGFILE%
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Nao foi possivel instalar o Python automaticamente.
        echo [ERRO] Nao foi possivel instalar o Python automaticamente. >> %LOGFILE%
        echo Por favor, baixe e instale o Python 3.11 manualmente em: https://www.python.org/downloads/
        echo Certifique-se de marcar a opcao "Add Python to PATH" durante a instalacao.
        pause
        exit /b 1
    )
    echo Python instalado com sucesso!
    echo Python instalado com sucesso! >> %LOGFILE%
    set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\Scripts"
) else (
    echo Python ja esta instalado.
    echo Python ja esta instalado. >> %LOGFILE%
    python --version >> %LOGFILE%
)

echo.
echo [2/4] Atualizando pip...
python -m pip install --upgrade pip >> %LOGFILE% 2>&1

echo.
echo [3/4] Instalando dependencias do projeto (requirements.txt)...
pip install -r requirements.txt >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias. Verifique o %LOGFILE%.
    pause
    exit /b 1
)

echo.
echo [4/4] Criando atalho de execucao (executar.bat)...
(
echo @echo off
echo cd /d "%%~dp0"
echo title Dashboard TI - Grupo NSF
echo streamlit run app.py
echo pause
) > executar.bat

echo.
echo ============================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo Log detalhado salvo em: %LOGFILE%
echo.
echo Para iniciar o dashboard, de um duplo clique no arquivo "executar.bat".
echo.
pause