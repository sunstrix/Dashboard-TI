@echo off
cd /d "%~dp0"
title Instalador Dashboard-TI v3.1 (Corrigido)
color 0A

echo ============================================================
echo    INSTALADOR AUTOMATIZADO - DASHBOARD TI (GRUPO NSF)
echo    Versao 3.1 - Com correcao de diretorio de trabalho
echo ============================================================
echo.

REM Verificacao de privilegios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Este script precisa ser executado como Administrador.
    echo Clique com o botao direito e selecione "Executar como administrador".
    echo.
    pause
    exit /b 1
)

set LOGFILE=instalar.log
echo Iniciando instalacao em %date% %time% > %LOGFILE%

echo [1/6] Verificando presenca do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nao encontrado. Tentando instalar via winget...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Nao foi possivel instalar o Python.
        echo Por favor, baixe e instale o Python 3.11 manualmente em: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo Python instalado com sucesso!
    echo Python instalado com sucesso! >> %LOGFILE%
    
    REM Atualiza PATH na sessao atual (busca instalacao padrao do winget)
    set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\Scripts"
    
    REM Verifica se o Python agora esta acessivel
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [AVISO] Python instalado, mas ainda nao acessivel no PATH.
        echo Tente reiniciar o computador e executar este script novamente.
        echo Ou use o Python Launcher: py -3.11
        pause
        exit /b 1
    )
) else (
    echo Python ja esta instalado.
    python --version >> %LOGFILE%
)

echo.
echo [2/6] Verificando arquivo requirements.txt...
if not exist "requirements.txt" (
    echo [ERRO] Arquivo requirements.txt nao encontrado!
    echo Certifique-se de que voce esta executando este script na pasta do projeto.
    pause
    exit /b 1
)
echo Arquivo requirements.txt encontrado.

echo.
echo [3/6] Criando Ambiente Virtual Isolado (venv)...
if not exist "venv\Scripts\python.exe" (
    echo Criando venv...
    python -m venv venv >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual.
        echo Tentando com Python Launcher (py -3.11)...
        py -3.11 -m venv venv >> %LOGFILE% 2>&1
        if %errorlevel% neq 0 (
            echo [ERRO] Nao foi possivel criar o ambiente virtual.
            pause
            exit /b 1
        )
    )
    echo Ambiente virtual criado com sucesso.
) else (
    echo Ambiente virtual ja existe.
)

echo.
echo [4/6] Atualizando pip dentro do venv...
venv\Scripts\python.exe -m pip install --upgrade pip >> %LOGFILE% 2>&1

echo.
echo [5/6] Instalando dependencias do projeto...
venv\Scripts\python.exe -m pip install -r requirements.txt >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias.
    echo Por favor, abra o arquivo instalar.log, copie as ULTIMAS 10 LINHAS e me envie.
    pause
    exit /b 1
)

echo.
echo [6/6] Criando atalho de execucao (executar.bat)...
(
echo @echo off
echo cd /d "%%~dp0"
echo title Dashboard TI - Grupo NSF
echo color 0B
echo cls
echo echo ============================================================
echo echo    INICIANDO DASHBOARD TI - GRUPO NSF
echo echo ============================================================
echo echo.
echo echo O navegador abrira em instantes.
echo echo Para encerrar o servidor, feche esta janela ou pressione Ctrl+C.
echo echo.
echo if not exist "venv\Scripts\python.exe" ^(
echo     echo [ERRO] Ambiente virtual nao encontrado!
echo     echo Por favor, execute o instalar.bat primeiro.
echo     pause
echo     exit /b 1
echo ^)
echo venv\Scripts\python.exe -m streamlit run app.py
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