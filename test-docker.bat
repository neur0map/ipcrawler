@echo off
echo ========================================
echo       Docker Connection Test
echo ========================================
echo.

echo 🔍 Testing Docker step by step...
echo.

echo Step 1: Docker version
docker --version
echo Exit code: %errorlevel%
echo.

echo Step 2: Docker info
docker info
echo Exit code: %errorlevel%
echo.

echo Step 3: Docker daemon test
docker ps
echo Exit code: %errorlevel%
echo.

echo Step 4: Simple container test
docker run --rm hello-world
echo Exit code: %errorlevel%
echo.

echo Step 5: Python container test
docker run --rm python:3.11-slim python --version
echo Exit code: %errorlevel%
echo.

echo ========================================
echo Test complete. Press any key to exit.
pause 