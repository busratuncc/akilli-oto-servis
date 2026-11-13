$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

docker compose exec -T backend pytest -q
docker compose exec -T frontend npm run lint
docker compose exec -T frontend npm run build

$health = Invoke-RestMethod -Uri "http://localhost:8000/api/health"
if ($health.status -ne "ok") {
    throw "API sağlık kontrolü başarısız."
}

Write-Host "Tüm kontroller başarılı."

