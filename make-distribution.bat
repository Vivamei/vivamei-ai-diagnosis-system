@echo off
REM ---------------------------------------------------------------------------
REM  venus-4s distribution packer (Windows, local only).
REM
REM  ASCII-only on purpose: this file used to be GBK-encoded, so any editor that
REM  re-saved it as UTF-8 turned the console output into mojibake. Keep it ASCII.
REM
REM  Packs the repo into ..\venus-4s-portable.zip so someone can unzip it and run
REM  start-dev.bat on their own Windows box. This is NOT the production path --
REM  production is infra\build.sh -> ACR -> infra\docker-compose.ecs.yml, so
REM  infra\ and config\ are deliberately kept in the zip.
REM ---------------------------------------------------------------------------
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo ============================================================
echo   venus-4s distribution packer
echo ============================================================
echo.

set "STAGING=%TEMP%\venus-4s-dist-%RANDOM%"
set "OUTPUT=%CD%\..\venus-4s-portable.zip"

if exist "%STAGING%" rmdir /s /q "%STAGING%"
mkdir "%STAGING%"

echo [1/4] copying sources, skipping heavy / machine-specific dirs ...
echo       skipped: dep caches, build output, runtime dirs, filled-in secrets
REM  _local  = local-only junk (problem screenshots, old logs, trash), ~180MB
REM  logs    = runtime logs, recreated by start-dev.bat
REM  var     = apps\api\var, local upload fallback used when OSS is off
REM
REM  The /XF list also drops every file that can hold a real credential:
REM    .env / dev.env / prod.env  filled-in configs (dev.env has live OSS+LLM keys)
REM    build.conf                 may carry ACR_USERNAME / ACR_PASSWORD
REM    *.pem *.key                TLS private keys
REM  robocopy /XF matches exact names, so the *.example templates and the
REM  miniapp's .env.development / .env.production (public domain only) still ship.
REM
REM  .npmrc and pnpm-lock.yaml are dropped too, but for a different reason: this
REM  machine resolves packages through a private Azure Artifacts feed whose tarball
REM  URLs carry a load-balanced shard hostname (ms-feed-2 / -12 / -25). pnpm 11
REM  re-checks those URLs against the registry metadata, so a lockfile written here
REM  is rejected everywhere else with ERR_PNPM_TARBALL_URL_MISMATCH. A clean .npmrc
REM  is written back below (see step 2) so the recipient keeps shamefully-hoist,
REM  which Taro needs, and resolves from their own default registry.
robocopy "%CD%" "%STAGING%\venus-4s" /MIR ^
    /XD .venv node_modules __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov ^
        dist .vite .turbo .swc .git playwright-report test-results ^
        mysql-data redis-data _local logs var problem ^
    /XF .coverage *.pyc *.pyo *.log venus-4s-portable.zip make-distribution.bat ^
        .env dev.env prod.env build.conf *.pem *.key ^
        .npmrc pnpm-lock.yaml ^
    /NFL /NDL /NJH /NJS /NC /NS /NP

REM robocopy exit codes 0-7 all mean success
if errorlevel 8 (
    echo [X] robocopy failed ^(exit=%errorlevel%^)
    rmdir /s /q "%STAGING%"
    pause
    exit /b 1
)

echo [2/4] writing a registry-neutral .npmrc ...
REM  shamefully-hoist is a build requirement (Taro); the registry line is not.
echo shamefully-hoist=true> "%STAGING%\venus-4s\.npmrc"

echo [3/4] removing previous zip if present ...
if exist "%OUTPUT%" del "%OUTPUT%"

echo [4/4] compressing to %OUTPUT% ...
powershell -NoProfile -Command "Compress-Archive -Path '%STAGING%\venus-4s' -DestinationPath '%OUTPUT%' -CompressionLevel Optimal -Force"
if errorlevel 1 (
    echo [X] compression failed
    rmdir /s /q "%STAGING%"
    pause
    exit /b 1
)

rmdir /s /q "%STAGING%"

echo.
echo ============================================================
echo   done: %OUTPUT%
for %%I in ("%OUTPUT%") do (
    set /a _kb=%%~zI/1024
    echo   size: !_kb! KB ^(%%~zI bytes^)
)
echo.
echo   Send this zip over; the recipient unzips it and follows README.md
echo ============================================================
pause
