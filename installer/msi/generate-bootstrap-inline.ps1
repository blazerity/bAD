# Раньше генерировал bootstrap-inline.wxi (PowerShell ExeCommand).
# С 2.1.10 bootstrap — installer/msi/bootstrap-schedule.vbs (ScriptSourceFile), генерация не нужна.
# Скрипт оставлен, чтобы release-msi.yml не ломался.
Write-Host "bootstrap-inline generation skipped (VBScript CA bootstrap-schedule.vbs)"
