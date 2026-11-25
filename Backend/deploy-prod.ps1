<#
.SYNOPSIS
    Script de Validación y Despliegue en Producción — Backend eSports "La Copa Eterna"
#>
param(
    [ValidateSet("Native", "Docker")]
    [string]$Mode = "Native",
    [string]$Port = "8088"
)

$ErrorActionPreference = "Stop"
$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BackendDir

Write-Host "=== [1/3] Ejecutando Suite Completa de Seguridad, Glicko-2 y Anti-Cheat ===" -ForegroundColor Cyan
go test -v -count=1 ./...

Write-Host "`n=== [2/3] Compilando Binario de Producción (arbitration-server.exe) ===" -ForegroundColor Cyan
go build -trimpath -ldflags="-s -w" -o arbitration-server.exe ./cmd/arbitration-server

if ($Mode -eq "Docker") {
    Write-Host "`n=== [3/3] Levantando Stack Docker (Go + PostgreSQL + Redis) ===" -ForegroundColor Cyan
    docker compose up -d --build
    docker compose ps
} else {
    Write-Host "`n=== [3/3] Listo para Ejecutar en Modo Nativo con Persistencia JSON ===" -ForegroundColor Green
    if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
    $env:PORT = $Port
    if (-not $env:SAF_HMAC_SECRET) { $env:SAF_HMAC_SECRET = "LA_COPA_ETERNA_CONMEBOL_DEFAULT_KEY_2026" }
    if (-not $env:SAF_STATE_FILE) { $env:SAF_STATE_FILE = "$BackendDir\data\arbitration_snapshot.json" }
    Write-Host "Iniciando servidor en http://127.0.0.1:$Port (StateFile=$($env:SAF_STATE_FILE))"
    & "$BackendDir\arbitration-server.exe"
}
