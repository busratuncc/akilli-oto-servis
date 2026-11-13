$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

docker compose up --build -d
docker compose ps

Write-Host ""
Write-Host "Arayüz: http://localhost:5174"
Write-Host "API dokümantasyonu: http://localhost:8000/docs"

