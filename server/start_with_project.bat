@echo off
chcp 65001 > nul
title Запуск Abak.IDE с автоматическим запуском моста

set "IDE_EXE=C:\Program Files (x86)\Abak.IDE.1.0.0\CODESYS\Common\abak.ide.exe"
set "PROFILE=Abak.IDE V1.0.0.0"
set "SCRIPT_PATH=%~dp0codesys_bridge_server.py"

if not exist "%IDE_EXE%" (
    echo [!] Исполняемый файл Abak.IDE не найден по стандартному пути:
    echo     %IDE_EXE%
    echo Пожалуйста, укажите путь к abak.ide.exe вручную в этом .bat файле.
    pause
    exit /b 1
)

if "%~1"=="" (
    echo Использование:
    echo   start_with_project.bat "C:\Путь\К\Вашему\Проекту.project"
    echo.
    echo Или просто перетащите файл .project на этот .bat файл.
    pause
    exit /b 0
)

set "PROJ_PATH=%~f1"

echo Запуск Abak.IDE...
echo Проект: %PROJ_PATH%
echo Скрипт: %SCRIPT_PATH%

start "" "%IDE_EXE%" --profile="%PROFILE%" "%PROJ_PATH%" --runscript="%SCRIPT_PATH%"
