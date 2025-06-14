@echo off
echo ========================================
echo    Docker Registry Connection Test
echo ========================================
echo.

echo Testing Docker Hub connectivity...
echo.

echo Step 1: Test basic connectivity
ping -n 2 docker.io
echo.

echo Step 2: Try pulling hello-world (should work)
docker pull hello-world
echo Exit code: %errorlevel%
echo.

echo Step 3: Try pulling python:latest
docker pull python:latest
echo Exit code: %errorlevel%
echo.

echo Step 4: Try pulling python:3-slim
docker pull python:3-slim
echo Exit code: %errorlevel%
echo.

echo Step 5: Try pulling python:3.11-slim
docker pull python:3.11-slim
echo Exit code: %errorlevel%
echo.

echo Step 6: List available Python images locally
docker images python
echo.

echo ========================================
echo Registry test complete.
pause 