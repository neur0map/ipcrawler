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
    pause
    exit /b 1
) else (
    echo ✅ SUCCESS: Docker daemon is running
)

echo.
echo 🔍 Step 3: Checking project structure...
echo Current directory: %cd%
echo Parent directory contents:
dir /b ..
echo.

REM Change to parent directory where Dockerfile is located
cd ..
echo Switched to IPCrawler root: %cd%

if not exist "Dockerfile" (
    echo ❌ FAILED: Dockerfile not found in IPCrawler root directory
    echo Make sure you're running this script from the IPCrawler project directory
    pause
    exit /b 1
) else (
    echo ✅ SUCCESS: Dockerfile found in IPCrawler root
)

echo.
echo 🔍 Step 4: Checking for existing Docker image...
echo Running: docker images -q ipcrawler
docker images -q ipcrawler
for /f %%i in ('docker images -q ipcrawler 2^>nul') do set "IMAGE_ID=%%i"
echo Image ID found: "%IMAGE_ID%"

if "%IMAGE_ID%"=="" (
    echo ℹ️  No existing ipcrawler image found - will build new one
    echo.
    echo 🔨 Building ipcrawler Docker image...
    echo Command: docker build -t ipcrawler .
    echo This will take several minutes on first run
    echo.
    
    REM Build with verbose output
    docker build -t ipcrawler . --progress=plain
    
    if errorlevel 1 (
        echo ❌ FAILED: Docker build failed with exit code %errorlevel%
        echo.
        echo Checking if image was partially created...
        docker images ipcrawler
        echo.
        pause
        exit /b 1
    )
    echo ✅ SUCCESS: Docker image built
    
    REM Verify the image was created
    echo Verifying image creation...
    docker images ipcrawler
    
) else (
    echo ✅ SUCCESS: Existing ipcrawler image found (ID: %IMAGE_ID%)
)

echo.
echo 🔍 Step 5: Creating results directory...
if not exist "results" (
    echo Creating results directory...
    mkdir results
) else (
    echo Results directory already exists
)
echo ✅ SUCCESS: Results directory ready

echo.
echo 🔍 Step 6: Testing container startup...
echo Testing: docker run --rm ipcrawler echo "Basic test"
docker run --rm ipcrawler echo "Basic test"
if errorlevel 1 (
    echo ❌ FAILED: Basic container test failed with exit code %errorlevel%
    echo.
    echo Trying to get more info about the image...
    docker inspect ipcrawler
    echo.
    pause
    exit /b 1
) else (
    echo ✅ SUCCESS: Basic container test passed
)

echo.
echo Testing: docker run --rm ipcrawler /show-tools.sh
docker run --rm ipcrawler /show-tools.sh
if errorlevel 1 (
    echo ⚠️  Tools script failed, but continuing...
    echo Exit code: %errorlevel%
) else (
    echo ✅ SUCCESS: Tools script works
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
echo Command: docker run -it --rm -v "%cd%\results:/scans" -w /scans --name "ipcrawler-session-%timestamp%" ipcrawler bash
echo Press Ctrl+C to exit the container, or type 'exit' and press Enter
echo.

REM Run the container with debug info
docker run -it --rm ^
    -v "%cd%\results:/scans" ^
    -w /scans ^
    --name "ipcrawler-session-%timestamp%" ^
    ipcrawler bash

echo.
echo 👋 Session ended with exit code: %errorlevel%
echo 📁 Results saved to: %cd%\results\
echo.
pause 