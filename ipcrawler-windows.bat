@echo off
setlocal enabledelayedexpansion

echo ========================================
echo       ipcrawler Windows Launcher
echo ========================================
echo 🪟 Cross-Platform Docker Setup for Windows
echo.
echo This script provides:
echo   • Docker Desktop and WSL2 support
echo   • Comprehensive security toolkit
echo   • Cross-platform container compatibility
echo   • Windows-optimized file path handling
echo.

REM Check if Docker is installed and running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed or not in PATH
    echo.
    echo Please install Docker for Windows:
    echo.
    echo 🎯 Recommended: Docker Desktop for Windows
    echo   • Download: https://docs.docker.com/desktop/install/windows/
    echo   • Requires Windows 10/11 with WSL2
    echo.
    echo 🔧 Alternative: Docker in WSL2 only
    echo   • Install WSL2: wsl --install
    echo   • Install Docker inside WSL2 distribution
    echo.
    echo 📋 After installation, restart this script
    echo.
    pause
    exit /b 1
)

REM Check if Docker daemon is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is installed but not running
    echo.
    echo Please start Docker and try again:
    echo.
    echo 🖥️  Docker Desktop users:
    echo   • Start Docker Desktop from Start Menu
    echo   • Wait for Docker to be "Running" in system tray
    echo.
    echo 🐧 WSL2 Docker Engine users:
    echo   • Open WSL2 terminal
    echo   • Run: sudo service docker start
    echo   • Or: sudo dockerd (if installed manually)
    echo.
    pause
    exit /b 1
)

echo ✅ Docker is ready!
docker --version
echo.

REM Check if ipcrawler image exists
for /f %%i in ('docker images -q ipcrawler 2^>nul') do set "IMAGE_ID=%%i"

if "%IMAGE_ID%"=="" (
    echo ℹ️ ipcrawler Docker image not found
    echo.
    echo 🔨 Building ipcrawler Docker image (this may take a few minutes)...
    echo.
    docker build -t ipcrawler .
    if errorlevel 1 (
        echo ❌ Docker build failed
        pause
        exit /b 1
    )
    echo ✅ Docker image built successfully!
    echo.
) else (
    echo ✅ ipcrawler Docker image found
    echo 🚀 Image ready! Starting Docker terminal...
    echo.
)

REM Create results directory if it doesn't exist
if not exist "results" mkdir results

echo 🔧 Verifying all security tools are working...
echo.

REM Test key tools in a temporary container
docker run --rm ipcrawler /show-tools.sh

echo.
echo 🚀 Starting ipcrawler Docker terminal...
echo 🖥️  Platform: Windows
echo.
echo 📋 Available commands once inside:
echo   • /show-tools.sh            (List all available tools)
echo   • ipcrawler --help          (Show help)
echo   • ipcrawler 127.0.0.1       (Test scan)
echo   • ipcrawler target.com      (Scan target)
echo   • ls /scans                 (View results)
echo   • exit                      (Leave container)
echo.
echo 💾 Results will be saved to: %cd%\results\
echo.

REM Generate unique container name for Windows
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
    set "timestamp=%%a%%b%%c%%d"
)

echo 🐳 Launching cross-platform Docker container...
echo.

REM Run the container with Windows-optimized settings
docker run -it --rm ^
    -v "%cd%\results:/scans" ^
    -w /scans ^
    --name "ipcrawler-session-%timestamp%" ^
    --platform linux/amd64 ^
    ipcrawler bash

echo.
echo 👋 ipcrawler session ended
echo 📁 Check your results in: %cd%\results\
echo.
echo 💡 Windows result viewing options:
echo   • explorer %cd%\results
echo   • Open in File Explorer from current directory
echo   • Or navigate to: %cd%\results
echo.
pause 