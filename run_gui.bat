@echo off
chcp 65001 > nul
title CODESYS & Abak.IDE Automation Manager
cd /d "%~dp0"
"C:\Users\adm\AppData\Local\Python\pythoncore-3.14-64\python.exe" "%~dp0client\gui_manager.py"
if %errorlevel% neq 0 pause
