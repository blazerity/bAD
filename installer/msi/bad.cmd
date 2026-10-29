@echo off
REM Thin shim: PATH `bad` → bin\BadAgent.exe (не переименовываем exe).
REM Self-update/uninstall: агент 2.1.3+ сам откладывает msiexec вне этой консоли,
REM иначе Restart Manager → «Завершить выполнение пакетного файла (Y/N)?».
setlocal
"%~dp0bin\BadAgent.exe" %*
exit /b %ERRORLEVEL%
