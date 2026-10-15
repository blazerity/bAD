@echo off
REM Thin shim so `bad` works from PATH (cmd.exe / Win+R) without renaming BadAgent.exe.
setlocal
"%~dp0BadAgent.exe" %*
exit /b %ERRORLEVEL%
