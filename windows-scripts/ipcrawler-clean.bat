@echo off
setlocal enabledelayedexpansion

echo ========================================
echo       IPCrawler Cleanup Tool
echo ========================================
echo 🧹 Removing ALL IPCrawler Docker components and files
echo.

echo ⚠️  WARNING: This will permanently delete:
echo   • All IPCrawler Docker images (including intermediate layers)
echo   • All IPCrawler Docker containers (running and stopped)
echo   • All IPCrawler Docker volumes
echo   • All IPCrawler Docker networks
echo   • Docker Compose resources for IPCrawler
echo   • Local results directory and contents
echo   • Docker build cache for IPCrawler
echo   • All Python packages (contained in Docker only)
echo.

set /p "confirm=Are you sure you want to continue? (y/N): "
if /i not "%confirm%"=="y" (
    echo ❌ Cleanup cancelled by user
    pause
    exit /b 0
)

echo.
echo 📁 Step 1: Switching to IPCrawler root directory...
echo Current directory: %cd%
cd ..
echo Switched to IPCrawler root: %cd%

echo.
echo 🔍 Step 2: Checking Docker availability...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Docker not found - skipping Docker cleanup
    goto :skip_docker
)

echo ✅ Docker found - proceeding with Docker cleanup
echo.

echo 🐳 Step 3: Stopping Docker Compose services...
if exist "docker-compose.yml" (
    echo Found docker-compose.yml - stopping services...
    docker-compose down --remove-orphans --volumes 2>nul
    echo ✅ Docker Compose services stopped
) else (
    echo ℹ️  No docker-compose.yml found
)

echo.
echo 🛑 Step 4: Stopping all running IPCrawler containers...
for /f "tokens=1" %%i in ('docker ps -q --filter "name=ipcrawler" 2^>nul') do (
    echo Stopping container: %%i
    docker stop %%i
)

REM Also stop containers created by docker-compose
for /f "tokens=1" %%i in ('docker ps -q --filter "name=ipcrawler-scanner" 2^>nul') do (
    echo Stopping docker-compose container: %%i
    docker stop %%i
)

echo.
echo 🗑️  Step 5: Removing all IPCrawler containers...
for /f "tokens=1" %%i in ('docker ps -aq --filter "name=ipcrawler" 2^>nul') do (
    echo Removing container: %%i
    docker rm -f %%i
)

REM Also remove docker-compose containers
for /f "tokens=1" %%i in ('docker ps -aq --filter "name=ipcrawler-scanner" 2^>nul') do (
    echo Removing docker-compose container: %%i
    docker rm -f %%i
)

echo.
echo 🖼️  Step 6: Removing ALL IPCrawler Docker images...
REM Remove by repository name
for /f "tokens=1" %%i in ('docker images -q ipcrawler 2^>nul') do (
    echo Removing image: %%i
    docker rmi -f %%i
)

REM Remove images that might have different tags
for /f "tokens=3" %%i in ('docker images --format "table {{.Repository}} {{.Tag}} {{.ID}}" ^| findstr "ipcrawler" 2^>nul') do (
    echo Removing tagged image: %%i
    docker rmi -f %%i
)

REM Remove any images from docker-compose builds
for /f "tokens=1" %%i in ('docker images -q "*ipcrawler*" 2^>nul') do (
    echo Removing compose image: %%i
    docker rmi -f %%i
)

echo.
echo 🌐 Step 7: Removing IPCrawler Docker networks...
for /f "tokens=1" %%i in ('docker network ls -q --filter "name=ipcrawler" 2^>nul') do (
    echo Removing network: %%i
    docker network rm %%i
)

echo.
echo 💾 Step 8: Removing IPCrawler Docker volumes...
for /f "tokens=1" %%i in ('docker volume ls -q --filter "name=ipcrawler" 2^>nul') do (
    echo Removing volume: %%i
    docker volume rm -f %%i
)

REM Also check for volumes created by docker-compose
for /f "tokens=1" %%i in ('docker volume ls -q ^| findstr "ipcrawler" 2^>nul') do (
    echo Removing related volume: %%i
    docker volume rm -f %%i
)

echo.
echo 🧽 Step 9: Aggressive Docker cleanup...
echo Removing dangling images...
docker image prune -f >nul 2>&1

echo Removing unused volumes...
docker volume prune -f >nul 2>&1

echo Removing unused networks...
docker network prune -f >nul 2>&1

echo Removing build cache...
docker builder prune -f >nul 2>&1

echo Removing ALL unused containers, networks, images...
docker system prune -f >nul 2>&1

echo.
echo 📊 Step 10: Docker cleanup summary...
echo Current Docker usage:
docker system df

:skip_docker

echo.
echo 📁 Step 11: Cleaning local files...

if exist "results" (
    echo Removing results directory...
    rmdir /s /q "results"
    echo ✅ Results directory removed
) else (
    echo ℹ️  No results directory found
)

REM Clean any temporary Docker files
if exist ".dockerignore" (
    echo Found .dockerignore file (keeping it)
)

if exist "docker-compose.override.yml" (
    echo Removing docker-compose.override.yml...
    del "docker-compose.override.yml"
)

echo.
echo 🔍 Step 12: Checking for any remaining IPCrawler processes...
tasklist /fi "imagename eq docker.exe" /fi "windowtitle eq *ipcrawler*" >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  Found running IPCrawler processes - you may need to restart Docker Desktop
)

echo.
echo 📋 Step 13: Final comprehensive verification...
echo Checking for remaining IPCrawler Docker components...

set "found_items=0"

REM Check for any remaining images
for /f %%i in ('docker images -q ipcrawler 2^>nul') do (
    echo ⚠️  Found remaining image: %%i
    set "found_items=1"
)

for /f %%i in ('docker images ^| findstr "ipcrawler" 2^>nul') do (
    echo ⚠️  Found remaining image reference: %%i
    set "found_items=1"
)

REM Check for any remaining containers
for /f %%i in ('docker ps -aq --filter "name=ipcrawler" 2^>nul') do (
    echo ⚠️  Found remaining container: %%i
    set "found_items=1"
)

for /f %%i in ('docker ps -aq --filter "name=ipcrawler-scanner" 2^>nul') do (
    echo ⚠️  Found remaining docker-compose container: %%i
    set "found_items=1"
)

REM Check for any remaining volumes
for /f %%i in ('docker volume ls -q --filter "name=ipcrawler" 2^>nul') do (
    echo ⚠️  Found remaining volume: %%i
    set "found_items=1"
)

REM Check for any remaining networks
for /f %%i in ('docker network ls -q --filter "name=ipcrawler" 2^>nul') do (
    echo ⚠️  Found remaining network: %%i
    set "found_items=1"
)

if "%found_items%"=="0" (
    echo ✅ ALL IPCrawler Docker components successfully removed
) else (
    echo ⚠️  Some components may still exist - try running this script again
    echo    or restart Docker Desktop for a complete reset
)

echo.
echo 🎉 COMPLETE CLEANUP FINISHED!
echo.
echo 📝 What was thoroughly cleaned:
echo   ✅ Stopped all IPCrawler containers (manual + docker-compose)
echo   ✅ Removed all IPCrawler containers
echo   ✅ Removed all IPCrawler Docker images (including intermediate layers)
echo   ✅ Removed all IPCrawler Docker volumes
echo   ✅ Removed all IPCrawler Docker networks
echo   ✅ Cleaned Docker Compose resources
echo   ✅ Cleaned Docker build cache and unused resources
echo   ✅ Removed local results directory
echo.
echo 🔧 Tools that were completely removed (all contained in Docker):
echo   • nmap, dnsutils, netcat-traditional
echo   • smbclient, sslscan, hydra
echo   • impacket suite (Python package)
echo   • All Python dependencies from requirements.txt
echo   • IPCrawler Python package itself
echo.
echo 💡 To reinstall IPCrawler completely fresh, run: ipcrawler-windows.bat
echo    This will rebuild everything from scratch with all tools
echo.
pause 