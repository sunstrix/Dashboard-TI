@echo off
cd /d "%~dp0"
title Dashboard TI - Grupo NSF
color 0B
cls

REM Cria a pasta de logs se nao existir
if not exist "logs" mkdir logs

REM Configura o arquivo de log
set LOGFILE=logs\executar.log
echo ============================================================ > %LOGFILE%
echo EXECUTOR DASHBOARD-TI - Log de Execucao >> %LOGFILE%
echo Data/Hora: %date% %time% >> %LOGFILE%
echo ============================================================ >> %LOGFILE%
echo. >> %LOGFILE%

echo ============================================================
echo    INICIANDO DASHBOARD TI - GRUPO NSF
echo ============================================================
echo.
echo [INFO] O log detalhado esta sendo salvo em: logs\executar.log
echo [INFO] Nao feche esta janela enquanto o dashboard estiver rodando.
echo.

REM Verificacao se o ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual (venv) nao encontrado!
    echo [ERRO] Ambiente virtual nao encontrado! >> %LOGFILE%
    echo Por favor, execute o arquivo "instalar.bat" primeiro para
    echo criar o ambiente virtual e instalar as dependencias.
    echo.
    pause
    exit /b 1
)

echo [OK] Ambiente virtual encontrado. Iniciando servidor Streamlit... >> %LOGFILE%
echo [OK] Ambiente virtual encontrado.
echo.
echo O navegador abrira em instantes em: http://localhost:8501
echo.
echo Para encerrar o servidor:
echo   - Feche esta janela, OU
echo   - Pressione Ctrl+C aqui e confirme com S
echo.
echo ============================================================
echo.

REM Executa o Streamlit usando o Python do ambiente virtual
REM Redireciona a saida do servidor (stdout e stderr) para o log
venv\Scripts\python.exe -m streamlit run app.py >> %LOGFILE% 2>&1

REM Se o Streamlit encerrar, pausa para o usuario ver a mensagem
echo.
echo ============================================================
echo    SERVIDOR ENCERRADO
echo ============================================================
echo O servidor foi encerrado em: %date% %time% >> %LOGFILE%
pause