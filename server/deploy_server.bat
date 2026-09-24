@echo off
chcp 65001 > nul
title Установка и настройка Abak.IDE Automation Bridge
echo ================================================================================
echo   Abak.IDE & CODESYS Automation Bridge - Быстрая настройка сервера
echo ================================================================================
echo.

:: 1. Проверка прав администратора для брандмауэра
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Запрос прав Администратора для настройки брандмауэра Windows...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [1/3] Открытие порта 11888 TCP в брандмауэре Windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-NetFirewallRule -DisplayName 'Abak IDE Bridge Server' -ErrorAction SilentlyContinue; New-NetFirewallRule -DisplayName 'Abak IDE Bridge Server' -Direction Inbound -LocalPort 11888,11889,11890,12888 -Protocol TCP -Action Allow -Profile Any | Out-Null; Write-Host '    -> Порт 11888 открыт для входящих подключений.' -ForegroundColor Green"

echo.
echo [2/3] Определение сетевых IP-адресов этого компьютера...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object { Write-Host ('    -> IP для подключения агента: ' + $_.IPAddress + ':11888 (Интерфейс: ' + $_.InterfaceAlias + ')') -ForegroundColor Cyan }"

echo.
echo [3/3] Файл сервера моста готов:
echo     %~dp0codesys_bridge_server.py
echo.
echo ================================================================================
echo   КАК ЗАПУСТИТЬ МОСТ ВНУТРИ ABAK.IDE:
echo ================================================================================
echo   1. Откройте нужный проект в Abak.IDE.
echo   2. В главном меню выберите:
echo      Инструменты (Tools) -> Скрипты (Scripting) -> Выполнить скрипт (Run Script...)
echo   3. Выберите файл:
echo      %~dp0codesys_bridge_server.py
echo.
echo   Сервер запустится в фоновом режиме без блокировки графического интерфейса.
echo ================================================================================
echo.
pause
