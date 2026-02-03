@echo off
setlocal enabledelayedexpansion

rem Vision project helper for Windows (Docker Compose)

set "CMD=%~1"

if "%CMD%"=="" goto :help
if /I "%CMD%"=="help" goto :help

if /I "%CMD%"=="model" goto :model

if /I "%CMD%"=="clear-input" goto :clear_input
if /I "%CMD%"=="clear-uploads" goto :clear_uploads

call :detect_compose

if /I "%CMD%"=="build" goto :build
if /I "%CMD%"=="builder" goto :builder
if /I "%CMD%"=="runner" goto :runner
if /I "%CMD%"=="full" goto :full
if /I "%CMD%"=="down" goto :down
if /I "%CMD%"=="logs" goto :logs

echo Unknown command: %CMD%
echo.
goto :help

:build
echo.
echo ===================================
echo   Vision: Building Docker images
echo ===================================
echo.

echo [1/2] Building Builder image (docker-compose.builder.yml)...
%COMPOSE% -f docker-compose.builder.yml build
if errorlevel 1 (
  echo.
  echo [ERROR] Builder image build failed.
  echo.
  echo Tips:
  echo   - Is Docker Desktop running?
  echo   - Check Dockerfile.builder for syntax errors
  echo   - Try: docker system prune -f
  echo.
  exit /b 1
)
echo [1/2] Builder image OK.
echo.

echo [2/2] Building Runner image (docker-compose.runner.yml)...
%COMPOSE% -f docker-compose.runner.yml build
if errorlevel 1 (
  echo.
  echo [ERROR] Runner image build failed.
  echo.
  echo Tips:
  echo   - Check Dockerfile.runner for syntax errors
  echo   - Try: docker system prune -f
  echo.
  exit /b 1
)
echo [2/2] Runner image OK.
echo.
echo ===================================
echo   Build complete!
echo ===================================
echo.
echo Next steps:
echo   vision.bat full    - Start Runner + UI
echo   vision.bat runner  - Start only Runner
echo.
exit /b 0

:builder
echo Starting Builder (exports standard model bundle)...
%COMPOSE% -f docker-compose.builder.yml up --build
exit /b %errorlevel%

:runner
echo Starting Runner (API on :8000, watch-folder enabled by default)...
%COMPOSE% -f docker-compose.runner.yml up --build
exit /b %errorlevel%

:full
echo Starting Full Stack (Runner :8000 + UI :3000)...
%COMPOSE% -f docker-compose.full.yml up --build
exit /b %errorlevel%

:down
echo Stopping containers...
%COMPOSE% -f docker-compose.builder.yml down
%COMPOSE% -f docker-compose.runner.yml down
%COMPOSE% -f docker-compose.full.yml down
exit /b 0

:logs
echo.
echo Builder logs:
%COMPOSE% -f docker-compose.builder.yml logs --tail 200
echo.
echo Runner logs:
%COMPOSE% -f docker-compose.runner.yml logs --tail 200
exit /b 0

:model
rem Export a YOLO model to an ONNX bundle for the runner.
rem Usage:
rem   vision.bat model [model] [imgsz] [opset]
rem Example:
rem   vision.bat model yolov8n.pt 640 20

set "ULTRA_MODEL=%~2"
if "%ULTRA_MODEL%"=="" set "ULTRA_MODEL=yolov8n.pt"

set "IMG_SZ=%~3"
if "%IMG_SZ%"=="" set "IMG_SZ=640"

set "OPSET=%~4"
if "%OPSET%"=="" set "OPSET=20"

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH. Install Python 3.10+ and try again.
  exit /b 1
)

echo.
echo Exporting %ULTRA_MODEL% to models\demo\v1\model.onnx (imgsz=%IMG_SZ%, opset=%OPSET%)...
pushd backend

if not exist .venv\Scripts\python.exe (
  echo Creating venv in backend\.venv ...
  python -m venv .venv
  if errorlevel 1 (
    popd
    exit /b 1
  )
)

echo Updating pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo Installing backend deps...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  popd
  exit /b 1
)

echo Installing ultralytics...
.venv\Scripts\python.exe -m pip install ultralytics
if errorlevel 1 (
  popd
  exit /b 1
)

echo Running ONNX export...
.venv\Scripts\python.exe .\scripts\export_ultralytics_yolo_to_onnx.py --model "%ULTRA_MODEL%" --out "..\models\demo\v1" --imgsz %IMG_SZ% --opset %OPSET%
set "RC=%errorlevel%"
popd

if not "%RC%"=="0" exit /b %RC%
echo.
echo Done. You can now run:
echo   vision.bat full
exit /b 0

:clear_input
set "TARGET=%~dp0input"
if not exist "%TARGET%\" (
  mkdir "%TARGET%" >nul 2>&1
)

echo.
echo This will delete ALL files under:
echo   %TARGET%
echo.
choice /M "Continue"
if errorlevel 2 exit /b 0

del /q /s "%TARGET%\*" >nul 2>&1
for /d %%D in ("%TARGET%\*") do rmdir /s /q "%%D" >nul 2>&1

echo.
echo Cleared %TARGET%
exit /b 0

:clear_uploads
set "TARGET=%~dp0input\_uploads"
if not exist "%TARGET%\" (
  echo.
  echo No uploads folder found at:
  echo   %TARGET%
  exit /b 0
)

echo.
echo This will delete ALL files under:
echo   %TARGET%
echo.
choice /M "Continue"
if errorlevel 2 exit /b 0

del /q /s "%TARGET%\*" >nul 2>&1
for /d %%D in ("%TARGET%\*") do rmdir /s /q "%%D" >nul 2>&1

echo.
echo Cleared %TARGET%
exit /b 0

:detect_compose
rem Prefer `docker compose`, fallback to `docker-compose` if needed
where docker >nul 2>&1
if errorlevel 1 (
  echo Docker not found on PATH. Install Docker Desktop first.
  exit /b 1
)

docker compose version >nul 2>&1
if not errorlevel 1 (
  set "COMPOSE=docker compose"
  goto :eof
)

where docker-compose >nul 2>&1
if not errorlevel 1 (
  set "COMPOSE=docker-compose"
  goto :eof
)

echo Neither `docker compose` nor `docker-compose` is available.
exit /b 1

:help
echo.
echo Usage: vision.bat ^<command^>
echo.
echo Commands:
echo   model    Export a YOLO model to ONNX (writes models\demo\v1\model.onnx)
echo   clear-input    Delete all files under .\input
echo   clear-uploads  Delete all files under .\input\_uploads
echo   build    Build builder and runner images
echo   builder  Run Builder container (port 8001)
echo   runner   Run Runner container (port 8000)
echo   full     Run Runner + UI (ports 8000 + 3000)
echo   logs     Show last logs for both
echo   down     Stop and remove containers
echo.
echo Examples:
echo   vision.bat model
echo   vision.bat model yolov8n.pt 640
echo   vision.bat clear-uploads
echo   vision.bat clear-input
echo   vision.bat build
echo   vision.bat builder
echo   vision.bat runner
echo   vision.bat full
echo.
pause
exit /b 0
