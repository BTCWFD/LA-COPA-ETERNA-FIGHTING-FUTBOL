@echo off
title LA COPA ETERNA: SANGRE Y POTRERO — Launcher (60 FPS WebLab)
echo ========================================================================
echo   LA COPA ETERNA: SANGRE Y POTRERO — Edicion Renacimiento Sfumato
echo   Iniciando servidor local en http://localhost:8080/WebLab/main-menu.html
echo ========================================================================
start "" "http://localhost:8080/WebLab/main-menu.html"
python -m http.server 8080
pause
