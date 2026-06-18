@echo off
cd /d "%~dp0"
title Instalador Dashboard-TI v4.0 (Com Logs)
color 0A

REM Cria a pasta de logs se nao existir
if not exist "logs" mkdir logs

REM Redireciona toda saida (stdout e stderr) para o log
set LOGFILE=logs\instalar.log
echo ============================================================ > %LOGFILE%
echo INSTALADOR DASHBOARD-TI - Log de Execucao >> %LOGFILE%
echo Data/Hora: %date% %time% >> %LOGFILE%
echo ============================================================ >> %LOGFILE%
echo. >> %LOGFILE%

echo ============================================================
echo    INSTALADOR AUTOMATIZADO - DASHBOARD TI (GRUPO NSF)
echo    Versao 4.0 - Com sistema de logs completo
echo ============================================================
echo.
echo [INFO] O log detalhado esta sendo salvo em: logs\instalar.log
echo [INFO] Nao feche esta janela ate o fim da instalacao.
echo.
pause

echo [1/7] Verificando privilegios de administrador... >> %LOGFILE%
echo [1/7] Verificando privilegios de administrador...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Este script precisa ser executado como Administrador. >> %LOGFILE%
    echo [AVISO] Clique com o botao direito e selecione "Executar como administrador". >> %LOGFILE%
    echo.
    echo [ERRO] Execute este script como Administrador!
    echo Clique com o botao direito no instalar.bat e escolha "Executar como administrador".
    echo.
    pause
    exit /b 1
)
echo [OK] Privilegios de administrador confirmados. >> %LOGFILE%

echo.
echo [2/7] Verificando presenca do Python...
echo [2/7] Verificando presenca do Python... >> %LOGFILE%
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nao encontrado. Tentando instalar via winget... >> %LOGFILE%
    echo Python nao encontrado. Tentando instalar via winget...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Nao foi possivel instalar o Python via winget. >> %LOGFILE%
        echo [ERRO] Nao foi possivel instalar o Python.
        echo Por favor, baixe e instale o Python 3.11 manualmente em: https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    echo Python instalado com sucesso! >> %LOGFILE%
    
    REM Atualiza PATH na sessao atual
    set "PATH=%PATH%;C:\Program Files\Python311;C:\Program Files\Python311\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\Scripts"
    
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [AVISO] Python instalado, mas nao acessivel no PATH atual. >> %LOGFILE%
        echo [AVISO] Python instalado, mas ainda nao acessivel no PATH.
        echo Tente reiniciar o computador e executar este script novamente.
        echo.
        pause
        exit /b 1
    )
) else (
    echo Python ja esta instalado. >> %LOGFILE%
    python --version >> %LOGFILE% 2>&1
)

echo.
echo [3/7] Verificando arquivo requirements.txt...
echo [3/7] Verificando arquivo requirements.txt... >> %LOGFILE%
if not exist "requirements.txt" (
    echo [ERRO] Arquivo requirements.txt nao encontrado! >> %LOGFILE%
    echo [ERRO] Arquivo requirements.txt nao encontrado!
    echo Certifique-se de que voce esta executando este script na pasta do projeto.
    echo Pasta atual: %CD% >> %LOGFILE%
    echo.
    pause
    exit /b 1
)
echo [OK] Arquivo requirements.txt encontrado. >> %LOGFILE%

echo.
echo [4/7] Criando Ambiente Virtual Isolado (venv)...
echo [4/7] Criando Ambiente Virtual Isolado (venv)... >> %LOGFILE%
if not exist "venv\Scripts\python.exe" (
    echo Criando venv... >> %LOGFILE%
    echo Criando venv...
    python -m venv venv >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar venv com python. Tentando py -3.11... >> %LOGFILE%
        echo [ERRO] Falha ao criar ambiente virtual. Tentando com Python Launcher...
        py -3.11 -m venv venv >> %LOGFILE% 2>&1
        if %errorlevel% neq 0 (
            echo [ERRO] Nao foi possivel criar o ambiente virtual. >> %LOGFILE%
            echo [ERRO] Nao foi possivel criar o ambiente virtual.
            echo Verifique o log em: logs\instalar.log
            echo.
            pause
            exit /b 1
        )
    )
    echo [OK] Ambiente virtual criado com sucesso. >> %LOGFILE%
) else (
    echo [OK] Ambiente virtual ja existe. >> %LOGFILE%
    echo Ambiente virtual ja existe.
)

echo.
echo [5/7] Atualizando pip dentro do venv...
echo [5/7] Atualizando pip dentro do venv... >> %LOGFILE%
venv\Scripts\python.exe -m pip install --upgrade pip >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao atualizar o pip. >> %LOGFILE%
    echo [ERRO] Falha ao atualizar o pip.
    echo Verifique o log em: logs\instalar.log
    echo.
    pause
    exit /b 1
)
echo [OK] Pip atualizado com sucesso. >> %LOGFILE%

echo.
echo [6/7] Instalando dependencias do projeto...
echo [6/7] Instalando dependencias do projeto... >> %LOGFILE%
venv\Scripts\python.exe -m pip install -r requirements.txt >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias. >> %LOGFILE%
    echo [ERRO] Falha ao instalar dependencias.
    echo Verifique o log em: logs\instalar.log para detalhes.
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas com sucesso. >> %LOGFILE%

echo.
echo [7/7] Criando atalho de execucao (executar.bat)...
echo [7/7] Criando atalho de execucao (executar.bat)... >> %LOGFILE%
(
echo @echo off
echo cd /d "%%~dp0"
echo title Dashboard TI - Grupo NSF
echo color 0B
echo cls
echo if not exist "logs" mkdir logs
echo set LOGFILE=logs\executar.log
echo echo ============================================================ %%LOGFILE%%
echo echo EXECUTOR DASHBOARD-TI - Log de Execucao %%LOGFILE%%
echo echo Data/Hora: %%date%% %%time%% %%LOGFILE%%
echo echo ============================================================ %%LOGFILE%%
echo echo. %%LOGFILE%%
echo echo ============================================================
echo echo    INICIANDO DASHBOARD TI - GRUPO NSF
echo echo ============================================================
echo echo.
echo echo O navegador abrira em instantes em: http://localhost:8501
echo echo.
echo echo Para encerrar o servidor:
echo echo   - Feche esta janela, OU
echo echo   - Pressione Ctrl+C aqui e confirme com S
echo echo.
echo echo ============================================================
echo echo.
echo if not exist "venv\Scripts\python.exe" ^(
echo     echo [ERRO] Ambiente virtual nao encontrado!
echo     echo Por favor, execute o instalar.bat primeiro.
echo     echo [ERRO] Ambiente virtual nao encontrado! %%LOGFILE%%
echo     pause
echo     exit /b 1
echo ^)
echo echo [OK] Ambiente virtual encontrado. Iniciando servidor... %%LOGFILE%%
echo echo. %%LOGFILE%%
echo venv\Scripts\python.exe -m streamlit run app.py %%LOGFILE%% 2%%^>%%1
echo echo. %%LOGFILE%%
echo echo ============================================================ %%LOGFILE%%
echo echo SERVIDOR ENCERRADO %%LOGFILE%%
echo echo ============================================================ %%LOGFILE%%
echo pause
) > executar.bat
echo [OK] Arquivo executar.bat criado com sucesso. >> %LOGFILE%

echo.
echo ============================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo Log detalhado salvo em: logs\instalar.log
echo.
echo Para iniciar o dashboard, de um duplo clique no arquivo "executar.bat".
echo.
pause