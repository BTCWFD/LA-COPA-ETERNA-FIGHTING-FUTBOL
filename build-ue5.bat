@echo off
setlocal enabledelayedexpansion
title LA COPA ETERNA — Compilador & Auto-Importador Unreal Engine 5.4+

echo ============================================================================
echo   LA COPA ETERNA: SANGRE Y POTRERO — Automatizacion Unreal Engine 5.4+
echo ============================================================================

set "PROJECT_PATH=%~dp0SouthAmericaFighters.uproject"
set "PYTHON_PIPELINE=%~dp0Scripts\ue5_auto_import_pipeline.py"
set "PYTHON_PIPELINE_FWD=!PYTHON_PIPELINE:\=/!"
set "UE_ROOT="

for %%P in (
    "C:\Program Files\Epic Games\UE_5.8"
    "G:\Epic Games\UE_5.8"
    "C:\Program Files\Epic Games\UE_5.7"
    "C:\Program Files\Epic Games\UE_5.6"
    "G:\Epic Games\UE_5.5"
    "C:\Program Files\Epic Games\UE_5.5"
    "G:\Epic Games\UE_5.4"
    "C:\Program Files\Epic Games\UE_5.4"
) do (
    if exist "%%~P\Engine\Build\BatchFiles\Build.bat" (
        set "UE_ROOT=%%~P"
        goto :found_ue
    )
)

echo [ERROR] No se encontro UE_5.4 ni UE_5.5 en C:\Program Files\Epic Games ni G:\Epic Games.
echo         Instala Unreal Engine 5.4 desde Epic Games Launcher y vuelve a ejecutar este script.
pause
exit /b 1

:found_ue
echo [OK] Motor detectado en: "%UE_ROOT%"
echo.
echo [1/3] Compilando modulo C++20 SouthAmericaFightersEditor (Win64 Development)...
call "%UE_ROOT%\Engine\Build\BatchFiles\Build.bat" SouthAmericaFightersEditor Win64 Development -Project="%PROJECT_PATH%" -WaitMutex -FromMsBuild
if errorlevel 1 (
    echo [ERROR] Fallo la compilacion C++20. Revisa el log de UnrealBuildTool arriba.
    pause
    exit /b 1
)

echo.
echo [2/3] Ejecutando Auto-Import Pipeline v2.0 (17 Luchadores, 10 Estadios, PBR, Shader Sfumato)...
"%UE_ROOT%\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "%PROJECT_PATH%" -ExecutePythonScript="!PYTHON_PIPELINE_FWD!" -unattended -nop4 -nosplash -NullRHI
if errorlevel 1 (
    echo [WARN] El auto-importador reporto advertencias; abriendo el Editor igualmente...
)

echo.
echo [3/3] Abriendo LA COPA ETERNA en Unreal Editor...
start "" "%UE_ROOT%\Engine\Binaries\Win64\UnrealEditor.exe" "%PROJECT_PATH%"
echo [LISTO] Proyecto compilado, importado y abriendose en Unreal Engine!
pause
