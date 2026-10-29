# Релизные заметки — агент 2.1.1 (MSI)

Патч упаковки после **2.1.0**.

## Каталог `bin`

- Вместо single-file / self-contained: **framework-dependent** publish (нужен **.NET 8 Runtime x64** на ПК).
- DLL разложены по папкам: **`bin\ms\`** (Microsoft / System), **`bin\lib\`** (Serilog и прочие NuGet), в корне — `BadAgent.exe`, `BadAgent.dll`, `uninstall.cmd`.
- MSI заметно легче (~единицы МБ вместо ~28 МБ self-contained).

## Требование (снято в 2.1.2)

В 2.1.1 нужен был .NET 8 Runtime на ПК. С **2.1.2** снова self-contained — runtime внутри MSI.

## Снятие / CLI

Как в **2.1.0**: `bad uninstall` / `bin\uninstall.cmd`.

## Обновление через msiexec

Отдельного флага `/upgrade` у msiexec нет. Апгрейд — это установка **нового** MSI с тем же UpgradeCode (MajorUpgrade в WiX):

```powershell
msiexec /i bad-agent-2.1.1.msi /qn /norestart
```

Свойства `SERVERURL` / `ENROLLMENTTOKEN` при апгрейде обычно **не** нужны: config в ProgramData сохраняется. Self-update агента делает то же самое (`msiexec /i … /qn`).
