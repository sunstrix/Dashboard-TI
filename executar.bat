@echo off
cd /d "%~dp0"
title Dashboard TI - Grupo NSF
color 0B
cls

echo ============================================================
echo    INICIANDO DASHBOARD TI - GRUPO NSF
echo ============================================================
echo.

REM Verificacao se o ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual (venv) nao encontrado!
    echo.
    echo Por favor, execute o arquivo "instalar.bat" primeiro para
    echo criar o ambiente virtual e instalar as dependencias.
    echo.
    pause
    exit /b 1
)

echo Ambiente virtual encontrado. Iniciando servidor Streamlit...
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
venv\Scripts\python.exe -m streamlit run app.py

REM Se o Streamlit encerrar, pausa para o usuario ver a mensagem
echo.
echo ============================================================
echo    SERVIDOR ENCERRADO
echo ============================================================
pause