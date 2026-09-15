@echo off
cd /d "%~dp0"
echo Stopping venus-4s dev containers (MySQL / Redis) ...
docker compose -f infra\docker-compose.dev.yml down
echo.
echo Done. API / Web cmd windows are separate - close them manually.
pause
