@echo off
setlocal enabledelayedexpansion

echo.
echo ╭───────────────────────────────────────────────╮
echo │ 🕷️  ipcrawler - Windows Docker Setup           │
echo │ v2.1.3 - Network Reconnaissance Tool          │
echo ╰───────────────────────────────────────────────╯
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed or not in PATH
    echo.
    echo 📥 Please install Docker Desktop for Windows:
    echo    https://docs.docker.com/desktop/install/windows-install/
    echo.
    pause
    exit /b 1
)

echo ✅ Docker is available
echo.

REM Check if we're in the right directory
if not exist "ipcrawler" (
    echo ❌ Please run this script from the ipcrawler root directory
    echo    (the directory containing the 'ipcrawler' folder)
    echo.
    pause
    exit /b 1
)

REM Create results directory if it doesn't exist
if not exist "results" mkdir results

echo 🔨 Building ipcrawler Docker image...
echo    This may take a few minutes on first run...
echo.

docker build -t ipcrawler . 2>nul
if errorlevel 1 (
    echo ❌ Docker build failed
    echo.
    echo 🔧 Trying to build with verbose output...
    docker build -t ipcrawler .
    if errorlevel 1 (
        echo.
        echo ❌ Build failed. Please check the error messages above.
        pause
        exit /b 1
    )
)

echo.
echo ✅ Docker image built successfully
echo.

REM Parse command line arguments
set "TARGET="
set "EXTRA_ARGS="

:parse_args
if "%~1"=="" goto :done_parsing
if "%~1"=="--help" (
    goto :show_help
)
if "%~1"=="-h" (
    goto :show_help
)

REM Check if this looks like an IP address or hostname (target)
echo %~1 | findstr /R "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if not errorlevel 1 (
    set "TARGET=%~1"
    shift
    goto :parse_args
)

REM Check for common hostnames or domain patterns
echo %~1 | findstr /R "^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$" >nul
if not errorlevel 1 (
    if "!TARGET!"=="" (
        set "TARGET=%~1"
        shift
        goto :parse_args
    )
)

REM Otherwise, it's an extra argument
set "EXTRA_ARGS=!EXTRA_ARGS! %~1"
shift
goto :parse_args

:done_parsing

if "!TARGET!"=="" (
    echo 🚀 Starting interactive ipcrawler Docker container...
    echo.
    echo 📁 Results will be saved to: %cd%\results
    echo 🔧 Available commands inside container:
    echo    /show-tools.sh           - Show installed tools
    echo    /install-extra-tools.sh  - Install additional tools
    echo    ipcrawler --help         - Show ipcrawler help
    echo    ipcrawler --list         - List available plugins
    echo.
    echo 💡 Example usage:
    echo    ipcrawler 10.10.11.55
    echo    ipcrawler --ignore-plugin-checks 192.168.1.1
    echo    ipcrawler -vvv target.htb
    echo.
    echo 🚪 Type 'exit' to leave the container
    echo.
    
    docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler
) else (
    echo 🎯 Running ipcrawler against target: !TARGET!
    echo 📁 Results will be saved to: %cd%\results
    echo.
    
    docker run -it --rm -v "%cd%\results:/scans" -w /scans ipcrawler ipcrawler !EXTRA_ARGS! !TARGET!
)

echo.
echo ✅ Scan complete! Check the results folder for output files.
goto :end

:show_help
echo.
echo 🕷️  ipcrawler Windows Docker Wrapper
echo.
echo Usage:
echo   %~nx0                           - Start interactive container
echo   %~nx0 ^<target^>                  - Scan target directly
echo   %~nx0 ^<target^> [options]        - Scan with additional options
echo.
echo Examples:
echo   %~nx0                           - Interactive mode
echo   %~nx0 10.10.11.55               - Quick scan
echo   %~nx0 192.168.1.1 -vvv          - Verbose scan
echo   %~nx0 target.htb --quick         - Quick scan mode
echo.
echo Options are passed directly to ipcrawler inside the container.
echo Run '%~nx0' without arguments for interactive mode to explore.
echo.

:end
pause 