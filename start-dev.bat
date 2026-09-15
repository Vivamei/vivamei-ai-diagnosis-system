@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%CD%"
set "LOGDIR=%ROOT%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "STARTLOG=%LOGDIR%\startup.log"
call :log "=== venus-4s dev starter ==="
call :log "Root: %ROOT%"
echo.

REM --- 0. tools ---
echo [0/4] checking toolchain ...
REM Only poetry / pnpm are invoked directly, so only those two are hard requirements.
REM Checking python / node separately caused false "missing" failures on machines
REM where poetry lives in pipx and python is not on PATH.
where poetry >nul 2>&1 || (echo   [X] poetry missing - install Python 3.11+ ^(https://www.python.org/downloads/^) then run: pip install poetry & goto :fail)
where pnpm   >nul 2>&1 || (echo   [X] pnpm missing - install Node.js LTS ^(https://nodejs.org/^) then run: npm i -g pnpm & goto :fail)
where docker >nul 2>&1 || echo   [!] Docker not found - will use local services ^(need MySQL 8 venus/devpass + db venus, and Redis on localhost:6379^)
echo   [OK] toolchain: poetry + pnpm

REM The distribution zip excludes config\dev.env (it holds real secrets), so a fresh
REM unzip has none. This must run BEFORE the Docker branch below: alembic reads
REM DATABASE_URL from config\dev.env, and a missing file fails Settings validation,
REM which surfaces as the misleading "db/migration not ready" retry loop.
if not exist "config\dev.env" (
    copy /y "config\dev.env.example" "config\dev.env" >nul || (echo   [X] config\dev.env missing, and cannot copy from config\dev.env.example & goto :fail)
    echo   [OK] created config\dev.env from template ^(all-mock defaults; edit it to use real SMS/LLM/OSS^)
)

REM --- 1. MySQL / Redis ---
echo [1/4] MySQL / Redis ...
set "_USE_DOCKER=0"
where docker >nul 2>&1 && docker info >nul 2>&1 && set "_USE_DOCKER=1"

if "!_USE_DOCKER!"=="1" (
    echo   using Docker
    docker compose -f infra\docker-compose.dev.yml up -d || goto :fail
    set /a _w=0
    :wait_mysql
    set "_hs="
    for /f "tokens=*" %%S in ('docker inspect -f "{{.State.Health.Status}}" venus-mysql 2^>nul') do set "_hs=%%S"
    if /i "!_hs!"=="healthy" goto :deps
    set /a _w+=1
    if !_w! GEQ 60 goto :deps
    timeout /t 1 /nobreak >nul
    goto :wait_mysql
) else (
    echo   using local services
    if not exist "config\dev.env" (echo [X] config\dev.env missing & goto :fail)
    call :parse_env_urls || goto :fail
    call :probe_port !MYSQL_HOST! !MYSQL_PORT! MySQL || goto :fail
    call :probe_port !REDIS_HOST! !REDIS_PORT! Redis || goto :fail
)

:deps
REM --- 2. backend deps ---
call :log "[2/4] backend deps (poetry) ..."
pushd apps\api
REM Poetry parses poetry.toml before running ANY subcommand, so a corrupt one breaks
REM every poetry call - including the "poetry config" below that would rewrite it.
REM Probe it first and delete it if unreadable; poetry then recreates it.
if exist "poetry.toml" (
    call poetry config --list >nul 2>&1 || (
        call :log "  [!] poetry.toml is not valid TOML, deleting so it gets recreated"
        del /q "poetry.toml"
    )
)
REM A .venv copied from another machine points at an interpreter path that does not
REM exist here, so it cannot run - delete and rebuild it.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "pass" >nul 2>&1 || (
        call :log "  [!] existing .venv is broken, copied from another machine? rebuilding"
        rmdir /s /q ".venv"
    )
)
if not exist ".venv" call poetry config virtualenvs.in-project true --local
call poetry install --no-root || (popd & goto :fail)
REM Never put a bare redirect character in a :log message - the echo inside :log
REM would treat it as redirection and write the whole line to a file, not the screen.
call :log "  running alembic upgrade head, full output in logs\startup.log"
set /a _m=0
:migrate_retry
call poetry run alembic upgrade head >> "%STARTLOG%" 2>&1 && (call :log "  [OK] migration" & goto :migrate_done)
set /a _m+=1
if !_m! GEQ 8 (call :log "  [!] migration failed after 8 tries - last 15 lines:" & powershell -NoProfile -Command "Get-Content -LiteralPath '%STARTLOG%' -Tail 15" & goto :migrate_done)
call :log "  [..] db/migration not ready, retry !_m!/8 in 5s"
timeout /t 5 /nobreak >nul
goto :migrate_retry
:migrate_done
popd

REM --- 3. frontend deps ---
call :log "[3/4] frontend deps (pnpm) ..."
pushd apps\web
if not exist "node_modules" (call pnpm install) else (call pnpm install --prefer-offline)
REM Check the exit code, not just the presence of node_modules: a failed lockfile
REM verification still leaves packages on disk, which used to slip through here.
if errorlevel 1 (echo   [X] pnpm install failed - see the output above & popd & goto :fail)
call pnpm approve-builds --all >nul 2>&1
popd

REM --- 4. start ---
call :log "[4/4] launching API (8080) + Web (5173) ..."
REM Each gets its own window for live output; the API also writes structured loguru
REM logs to logs\api.log
start "venus-api :8080" cmd /k "cd /d %ROOT%\apps\api && set LOG_FILE=..\..\logs\api.log&& poetry run uvicorn app.main:app --reload --port 8080"
start "venus-web :5173" cmd /k "cd /d %ROOT%\apps\web && pnpm dev"

echo.
call :log "=== ready ==="
echo   API  http://localhost:8080/docs
echo   Web  http://localhost:5173
echo   Logs %LOGDIR%
echo     - startup.log      startup / deps / migration
echo     - api.log          API structured log (loguru, rotating; has [MOCK SMS] codes)
if "!_USE_DOCKER!"=="1" echo   Stop containers: stop-dev.bat
pause
exit /b 0

:log
echo %~1
powershell -NoProfile -Command "Add-Content -LiteralPath '%STARTLOG%' -Value ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] %~1')" >nul 2>&1
exit /b 0

:parse_env_urls
for /f "usebackq tokens=1,* delims==" %%A in (`powershell -NoProfile -Command "$c=Get-Content 'config/dev.env' -Raw; if($c -match '(?m)^DATABASE_URL=.*://[^:]*:[^@]*@([^:/]+):(\d+)/'){Write-Output ('MYSQL_HOST='+$Matches[1]);Write-Output ('MYSQL_PORT='+$Matches[2])}; if($c -match '(?m)^REDIS_URL=.*://([^:/]+):(\d+)'){Write-Output ('REDIS_HOST='+$Matches[1]);Write-Output ('REDIS_PORT='+$Matches[2])}"`) do set "%%A=%%B"
if not defined MYSQL_HOST (echo [X] cannot parse DATABASE_URL & exit /b 1)
if not defined REDIS_HOST (echo [X] cannot parse REDIS_URL & exit /b 1)
exit /b 0

:probe_port
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient;try{$c.Connect('%~1',%~2);$c.Close();exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 (echo   [X] %~3 %~1:%~2 unreachable & exit /b 1)
echo   [OK] %~3 %~1:%~2
exit /b 0

:fail
echo.
echo [X] failed. see log above.
pause
exit /b 1
