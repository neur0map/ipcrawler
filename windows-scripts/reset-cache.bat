@echo off
setlocal enabledelayedexpansion

REM ========================================
REM ipcrawler Cache Reset Script (Windows)
REM ========================================
REM Clears all Python cache, ipcrawler cache, and rebuilds application
REM Usage: windows-scripts\reset-cache.bat

echo 🔄 ipcrawler Cache Reset - Clearing all static cache and rebuilding...
echo.

REM ========================================
REM OS Detection
REM ========================================
echo 📋 Detecting Windows environment...

set "OS_TYPE=windows"
set "WSL_DETECTED=no"

REM Check if running in WSL
if defined WSL_DISTRO_NAME (
    set "WSL_DETECTED=yes"
    echo ✅ Detected WSL environment: %WSL_DISTRO_NAME%
) else (
    echo ✅ Detected native Windows environment
)

REM Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set "WIN_VERSION=%%i.%%j"
echo ℹ️  Windows version: %WIN_VERSION%

echo.

REM ========================================
REM 1. Clear Python Cache
REM ========================================
echo 📁 Clearing Python bytecode cache...

REM Remove __pycache__ directories
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo Removing: %%d
        rmdir /s /q "%%d" 2>nul
    )
)

REM Remove .pyc files
for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        del /q "%%f" 2>nul
    )
)

REM Remove .pyo files
for /r . %%f in (*.pyo) do (
    if exist "%%f" (
        del /q "%%f" 2>nul
    )
)

REM Remove .pyd files (Windows Python extensions)
for /r . %%f in (*.pyd) do (
    if exist "%%f" (
        del /q "%%f" 2>nul
    )
)

echo ✅ Cleared Python bytecode cache

echo.

REM ========================================
REM 2. Clear ipcrawler Application Cache (Windows-specific)
REM ========================================
echo 📁 Clearing ipcrawler application cache for Windows...

REM Clear user AppData cache
if exist "%LOCALAPPDATA%\ipcrawler" (
    echo Removing Windows AppData cache...
    rmdir /s /q "%LOCALAPPDATA%\ipcrawler" 2>nul
    echo ✅ Removed Windows AppData cache
)

REM Clear temp cache
if exist "%TEMP%\ipcrawler" (
    echo Removing Windows Temp cache...
    rmdir /s /q "%TEMP%\ipcrawler" 2>nul
    echo ✅ Removed Windows Temp cache
)

REM Clear user profile cache
if exist "%USERPROFILE%\.cache\ipcrawler" (
    echo Removing user profile cache...
    rmdir /s /q "%USERPROFILE%\.cache\ipcrawler" 2>nul
    echo ✅ Removed user profile cache
)

REM Clear ProgramData cache (system-wide)
if exist "%PROGRAMDATA%\ipcrawler" (
    echo Removing ProgramData cache...
    rmdir /s /q "%PROGRAMDATA%\ipcrawler" 2>nul
    echo ✅ Removed ProgramData cache
)

REM WSL-specific cache clearing
if "%WSL_DETECTED%"=="yes" (
    echo 🐧 WSL detected - clearing Linux-style cache paths...
    
    REM Try to clear Linux cache paths if accessible
    if exist "%USERPROFILE%\.cache\ipcrawler" (
        rmdir /s /q "%USERPROFILE%\.cache\ipcrawler" 2>nul
        echo ✅ Cleared WSL Linux-style cache
    )
)

REM Clear pip cache
echo Clearing pip cache...
pip cache purge >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Cleared pip cache
) else (
    echo ⚠️  Could not clear pip cache (pip may not be available)
)

echo.

REM ========================================
REM 3. Clear Virtual Environment Cache
REM ========================================
echo 📁 Clearing virtual environment cache...

REM Remove existing virtual environment
if exist "venv" (
    echo Removing existing virtual environment...
    rmdir /s /q "venv" 2>nul
    echo ✅ Removed existing virtual environment
)

if exist ".venv" (
    echo Removing existing .venv directory...
    rmdir /s /q ".venv" 2>nul
    echo ✅ Removed existing .venv directory
)

echo.

REM ========================================
REM 4. Clear Build Artifacts
REM ========================================
echo 📁 Clearing build artifacts...

REM Remove build directories
if exist "build" (
    rmdir /s /q "build" 2>nul
)
if exist "dist" (
    rmdir /s /q "dist" 2>nul
)

REM Remove egg-info directories
for /d %%d in (*.egg-info) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
    )
)

REM Remove compiled extensions
for /r . %%f in (*.dll) do (
    if exist "%%f" (
        del /q "%%f" 2>nul
    )
)

echo ✅ Removed build artifacts

echo.

REM ========================================
REM 5. Clear Docker Cache (if Docker is available)
REM ========================================
echo 🐳 Checking Docker availability...

docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker found - clearing Docker cache...
    
    REM Remove ipcrawler Docker images
    for /f "tokens=1" %%i in ('docker images -q ipcrawler 2^>nul') do (
        echo Removing Docker image: %%i
        docker rmi %%i >nul 2>&1
    )
    
    REM Prune Docker build cache
    docker builder prune -f >nul 2>&1
    
    echo ✅ Cleared Docker cache
) else (
    echo ⚠️  Docker not available - skipping Docker cache cleanup
)

echo.

REM ========================================
REM 6. Clear Windows-specific Package Cache
REM ========================================
echo 📁 Clearing Windows-specific package cache...

REM Clear Chocolatey cache if available
where choco >nul 2>&1
if %errorlevel% equ 0 (
    echo Clearing Chocolatey cache...
    choco cache clean >nul 2>&1
    echo ✅ Cleared Chocolatey cache
)

REM Clear Scoop cache if available
where scoop >nul 2>&1
if %errorlevel% equ 0 (
    echo Clearing Scoop cache...
    scoop cache rm * >nul 2>&1
    echo ✅ Cleared Scoop cache
)

REM Clear Windows Package Manager cache if available
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo Clearing Windows Package Manager cache...
    REM winget doesn't have a direct cache clear, but we can note it
    echo ℹ️  Windows Package Manager detected (no cache clear needed)
)

REM Clear conda cache if available
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo Clearing Conda cache...
    conda clean --all -y >nul 2>&1
    echo ✅ Cleared Conda cache
)

echo.

REM ========================================
REM 7. Rebuild Application
REM ========================================
echo 🔧 Rebuilding ipcrawler application...

REM Check Python availability
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.7+ first.
    echo    Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Recreate virtual environment
echo Creating fresh virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)
echo ✅ Created new virtual environment

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo ⚠️  Failed to upgrade pip, continuing anyway...
) else (
    echo ✅ Upgraded pip
)

REM Install requirements
if exist "requirements.txt" (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Failed to install Python dependencies
        pause
        exit /b 1
    )
    echo ✅ Installed Python dependencies
) else (
    echo ⚠️  No requirements.txt found
)

REM Install ipcrawler in development mode
echo Installing ipcrawler in development mode...
pip install -e .
if %errorlevel% neq 0 (
    echo ❌ Failed to install ipcrawler
    pause
    exit /b 1
)
echo ✅ Installed ipcrawler

echo.

REM ========================================
REM 8. Verify Installation
REM ========================================
echo 🔍 Verifying installation...

REM Test import
python -c "import ipcrawler" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ ipcrawler module imports successfully
) else (
    echo ❌ Failed to import ipcrawler module
    pause
    exit /b 1
)

REM Test command line
python ipcrawler.py --help >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ ipcrawler command line works
) else (
    echo ❌ ipcrawler command line failed
    pause
    exit /b 1
)

echo.

REM ========================================
REM 9. Summary
REM ========================================
echo 🎉 Cache reset complete for Windows!
echo.
echo ✅ Cleared:
echo    • Python bytecode cache (__pycache__, .pyc files)
echo    • ipcrawler application cache (Windows-specific paths)
echo    • Virtual environment
echo    • Build artifacts
echo    • Docker cache (if available)
echo    • Windows package cache (Chocolatey, Scoop, etc.)
if "%WSL_DETECTED%"=="yes" (
    echo    • WSL integration cache
)
echo.
echo ✅ Rebuilt:
echo    • Fresh virtual environment
echo    • Python dependencies
echo    • ipcrawler application
echo.
echo 🚀 Ready to use! Try: python ipcrawler.py --help
echo.
echo 💡 If you still see cached behavior:
echo    1. Restart your command prompt
echo    2. Run: venv\Scripts\activate.bat
echo    3. Check: python ipcrawler.py --version
if "%WSL_DETECTED%"=="yes" (
    echo    4. WSL: Consider restarting WSL with 'wsl --shutdown'
)
echo.

pause 