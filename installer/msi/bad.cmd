@echo off
REM Thin shim: PATH `bad` → bin\BadAgent.exe (не переименовываем exe).
REM Self-update/uninstall: агент откладывает msiexec через detached wscript (не .cmd в этой консоли).
setlocal
"%~dp0bin\BadAgent.exe" %*
exit /b %ERRORLEVEL%
