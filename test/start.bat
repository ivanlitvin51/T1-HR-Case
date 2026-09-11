@echo off
chcp 65001 > nul
echo ===================================================
echo   Запуск T1 HR-Case RecSys тестовой среды...
echo ===================================================
echo.

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Docker не найден!
    echo Убедитесь, что Docker Desktop установлен и запущен.
    echo Если вы только что установили Docker Desktop, перезапустите окно консоли.
    echo.
    pause
    exit /b 1
)

echo [1/2] Проверка работы Docker Daemon...
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [ВНИМАНИЕ] Docker Desktop установлен, но служба еще не запущена.
    echo Запустите приложение Docker Desktop и подождите статус "Engine running".
    echo.
    pause
    exit /b 1
)

echo [2/2] Поднятие контейнеров (Postgres+pgvector, Redis, Mongo, FastAPI, React)...
echo.
docker compose up --build

pause
