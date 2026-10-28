@echo off
setlocal enableextensions
title Build — Reset AnyDesk v5

echo.
echo  ============================================
echo   Reset AnyDesk v5
echo   Desenvolvido por Estevao Miguel
echo   TSCBr — Technology Solution Company — 2026
echo  ============================================
echo.

python --version >nul 2>&1
if %errorlevel%==0 goto python_ok

echo  [!] Python nao encontrado. Baixando...
set "PY_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "PY_FILE=%TEMP%\python_setup.exe"
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_FILE%' -UseBasicParsing"
"%PY_FILE%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
del /f /q "%PY_FILE%" >nul 2>&1
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [AVISO] Feche e reabra este arquivo para continuar.
    pause & exit /b 0
)
echo  [OK] Python instalado!

:python_ok
echo  [OK] Python OK.
echo.
echo  [1/3] Instalando dependencias...
python -m pip install --upgrade pip --quiet
python -m pip install customtkinter pyinstaller pillow --quiet
echo  [OK] Dependencias OK.
echo.
echo  [2/3] Gerando executavel...
echo.

python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "Reset AnyDesk" ^
    --icon=icone.ico ^
    --uac-admin ^
    --add-data "icone.ico;." ^
    anydesk_reset.py

if %errorlevel% neq 0 (
    echo  [ERRO] Falha no build.
    pause & exit /b 1
)

echo  [3/3] Copiando executavel...
if exist "dist\Reset AnyDesk.exe" (
    copy /y "dist\Reset AnyDesk.exe" "Reset AnyDesk.exe" >nul
    echo.
    echo  ============================================
    echo   CONCLUIDO! Arquivo: "Reset AnyDesk.exe"
    echo.
    echo   Na primeira execucao o app ira:
    echo   - Criar C:\Reset Anydesk\
    echo   - Baixar/instalar Python se necessario
    echo   - Instalar AnyDesk 9.6.11 se necessario
    echo   - Criar atalho na area de trabalho
    echo  ============================================
) else (
    echo  [AVISO] Verifique a pasta dist\ manualmente.
)
echo.
pause
