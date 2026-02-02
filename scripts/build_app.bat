@echo off
REM Build script for Corall standalone application (Windows)
REM
REM Usage:
REM   scripts\build_app.bat           Build for Windows
REM   scripts\build_app.bat --clean   Clean build
REM

setlocal enabledelayedexpansion

set APP_NAME=Corall
set VERSION=1.0.0

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

echo.
echo ============================================
echo  Building %APP_NAME% v%VERSION%
echo ============================================
echo.

REM Parse arguments
set CLEAN=0
if "%1"=="--clean" set CLEAN=1
if "%1"=="-clean" set CLEAN=1

REM Clean if requested
if %CLEAN%==1 (
    echo =^> Cleaning previous builds...
    if exist "%PROJECT_ROOT%\build" rmdir /s /q "%PROJECT_ROOT%\build"
    if exist "%PROJECT_ROOT%\dist" rmdir /s /q "%PROJECT_ROOT%\dist"
    if exist "%PROJECT_ROOT%\.build_venv" rmdir /s /q "%PROJECT_ROOT%\.build_venv"
    echo    Cleaned
)

REM Check Python
echo =^> Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo    Error: Python not found. Please install Python 3.8 or higher.
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    Found Python %PYTHON_VERSION%

REM Create virtual environment
echo =^> Creating build virtual environment...
set VENV_DIR=%PROJECT_ROOT%\.build_venv

if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    echo    Created virtual environment
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
echo    Activated virtual environment

REM Install dependencies
echo =^> Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r "%PROJECT_ROOT%\requirements.txt" >nul 2>&1
echo    Installed application dependencies
pip install pyinstaller >nul 2>&1
echo    Installed PyInstaller

REM Pre-download ML model
echo =^> Pre-downloading ML model...
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
echo    ML model cached

REM Build application
echo =^> Building standalone application...
cd "%PROJECT_ROOT%"
pyinstaller --noconfirm --clean --log-level WARN "packaging\corall.spec"
if errorlevel 1 (
    echo    Error: Build failed
    exit /b 1
)
echo    Build completed

REM Summary
echo.
echo ============================================
echo  Build completed successfully!
echo ============================================
echo.
echo Output location:
echo   Folder: %PROJECT_ROOT%\dist\%APP_NAME%\
echo   EXE:    %PROJECT_ROOT%\dist\%APP_NAME%\%APP_NAME%.exe
echo.
echo Data directory (created on first run):
echo   %%APPDATA%%\Corall\
echo.

endlocal
