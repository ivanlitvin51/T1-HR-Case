chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Запуск T1 HR-Case RecSys тестовой среды..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "`n[ОШИБКА] Команда 'docker' не найдена в системе!" -ForegroundColor Red
    Write-Host "1. Убедитесь, что Docker Desktop установлен." -ForegroundColor Yellow
    Write-Host "2. Если установка только что завершилась, перезапустите окно PowerShell." -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода..."
    exit 1
}

Write-Host "`n[1/2] Проверка состояния службы Docker..." -ForegroundColor Green
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ВНИМАНИЕ] Docker Desktop установлен, но сам движок еще не запущен!" -ForegroundColor Yellow
    Write-Host "Запустите приложение 'Docker Desktop' из меню Пуск и дождитесь статуса 'Engine running'." -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода..."
    exit 1
}

Write-Host "`n[2/2] Поднятие контейнеров (Postgres + pgvector, Redis, MongoDB, FastAPI, React)..." -ForegroundColor Green
docker compose up --build
