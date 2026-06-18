@echo off
cd /d "%~dp0"
title Dashboard TI - Grupo NSF
color 0B
cls
if not exist "logs" mkdir logs
set LOGFILE=logs\executar.log
echo ============================================================ %LOGFILE%
echo EXECUTOR DASHBOARD-TI - Log de Execucao %LOGFILE%
echo Data/Hora: %date% %time% %LOGFILE%
echo ============================================================ %LOGFILE%
echo. %LOGFILE%
echo ============================================================
echo    INICIANDO DASHBOARD TI - GRUPO NSF
echo ============================================================
echo.
echo O navegador abrira em instantes em: http://localhost:8501
echo.
echo Para encerrar o servidor:
echo   - Feche esta janela, OU
echo   - Pressione Ctrl+C aqui e confirme com S
echo.
echo ============================================================
echo.
if not exist "venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo Por favor, execute o instalar.bat primeiro.
    echo [ERRO] Ambiente virtual nao encontrado! %LOGFILE%
    pause
    exit /b 1
)
echo [OK] Ambiente virtual encontrado. Iniciando servidor... %LOGFILE%
echo. %LOGFILE%
venv\Scripts\python.exe -m streamlit run app.py %LOGFILE% 2%>%1
echo. %LOGFILE%
echo ============================================================ %LOGFILE%
echo SERVIDOR ENCERRADO %LOGFILE%
echo ============================================================ %LOGFILE%
pause
