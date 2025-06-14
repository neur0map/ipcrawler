@echo off
setlocal enabledelayedexpansion

echo ========================================
echo       ipcrawler Windows Launcher
echo ========================================
echo 🪟 Cross-Platform Docker Setup for Windows
echo.

echo 🔍 Step 1: Checking Docker installation...
echo Current directory: %cd%
echo.

REM Test Docker version first
echo Testing: docker --version
docker --version
if errorlevel 1 (
    echo ❌ FAILED: Docker command not found
    echo.
    echo This means Docker is either:
    echo   • Not installed
    echo   • Not added to PATH
    echo   • Command Prompt needs restart after Docker install
    echo.
    echo Please ensure Docker Desktop is installed and restart Command Prompt
    echo.
    pause
    exit /b 1
) else (
    echo ✅ SUCCESS: Docker command works
)

echo.
echo 🔍 Step 2: Testing Docker daemon...
echo Testing: docker ps
docker ps
if errorlevel 1 (
    echo ❌ FAILED: Docker daemon not accessible
    echo.
    echo This means Docker Desktop is either:
    echo   • Not running (check system tray for whale icon)
    echo   • Still starting up (wait a few minutes)
    echo   • Having permission issues
    echo.
    echo Please start Docker Desktop and wait for it to be ready
    echo.
    pause
    exit /b 1
) else (
    echo ✅ SUCCESS: Docker daemon is running
)

echo.
echo 🔍 Step 3: Checking current directory...
if not exist "Dockerfile" (
    echo ❌ FAILED: Dockerfile not found in current directory
    echo Current directory: %cd%
    echo.
    echo Please make sure you're running this from the ipcrawler directory
    echo The directory should contain: Dockerfile, ipcrawler-windows.bat, etc.
    echo.
    dir /b | findstr /i "dockerfile ipcrawler"
    echo.
    pause
    exit /b 1
) else (
    echo ✅ SUCCESS: Dockerfile found
)

echo.
echo 🔍 Step 4: Checking for existing Docker image...
for /f %%i in ('docker images -q ipcrawler 2^>nul') do set "IMAGE_ID=%%i"

if "%IMAGE_ID%"=="" (
    echo ℹ️  No existing ipcrawler image found - will build new one
    echo.
    echo 🔨 Building ipcrawler Docker image...
    echo This will take several minutes on first run
    echo.
    docker build -t ipcrawler .
    if errorlevel 1 (
        echo ❌ FAILED: Docker build failed
        echo.
        echo Common causes:
        echo   • No internet connection
        echo   • Insufficient disk space
        echo   • Antivirus blocking Docker
        echo.
        pause
        exit /b 1
    )
    echo ✅ SUCCESS: Docker image built
) else (
    echo ✅ SUCCESS: Existing ipcrawler image found
)

echo.
echo 🔍 Step 5: Creating results directory...
if not exist "results" mkdir results
echo ✅ SUCCESS: Results directory ready

echo.
echo 🔍 Step 6: Testing container startup...
echo Testing: docker run --rm ipcrawler /show-tools.sh
docker run --rm ipcrawler /show-tools.sh
if errorlevel 1 (
    echo ❌ FAILED: Container won't start or tools missing
    echo.
    echo Trying basic container test...
    docker run --rm ipcrawler echo "Basic container test"
    if errorlevel 1 (
        echo ❌ FAILED: Basic container startup failed
        echo This indicates a fundamental Docker issue
        echo.
        pause
        exit /b 1
    ) else (
        echo ⚠️  Container starts but tools may be missing
        echo Continuing anyway...
    )
) else (
    echo ✅ SUCCESS: Container and tools working
)

echo.
echo 🚀 All checks passed! Starting interactive session...
echo.
echo 📋 Available commands once inside:
echo   • /show-tools.sh            (List all available tools)
echo   • ipcrawler --help          (Show help)
echo   • ipcrawler 127.0.0.1       (Test scan)
echo   • exit                      (Leave container)
echo.
echo 💾 Results will be saved to: %cd%\results\
echo.

REM Generate unique container name
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
    set "timestamp=%%a%%b%%c%%d"
)

echo 🐳 Starting Docker container...
echo Press Ctrl+C if you need to exit
echo.

REM Run the container (removed --platform for better compatibility)
docker run -it --rm ^
    -v "%cd%\results:/scans" ^
    -w /scans ^
    --name "ipcrawler-session-%timestamp%" ^
    ipcrawler bash

echo.
echo 👋 Session ended
echo 📁 Results saved to: %cd%\results\
echo.
pause 