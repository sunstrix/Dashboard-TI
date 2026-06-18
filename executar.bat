@echo off
cd /d "%~dp0"
title Dashboard TI - Grupo NSF
color 0B
cls
echo ============================================================
echo    INICIANDO DASHBOARD TI - GRUPO NSF
echo ============================================================
echo.
echo O navegador abrira em instantes.
echo Para encerrar o servidor, feche esta janela ou pressione Ctrl+C.
echo.
streamlit run app.py
pause