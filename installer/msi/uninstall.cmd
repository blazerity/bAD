@echo off
REM Снятие агента из каталога bin (нужны права администратора).
setlocal
"%~dp0BadAgent.exe" uninstall %*
exit /b %ERRORLEVEL%
