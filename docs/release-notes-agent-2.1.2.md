# Релизные заметки — агент 2.1.2 (MSI)

Патч после **2.1.1**: снова **self-contained** MSI.

## Установка

- .NET Runtime на ПК **ставить не нужно** — runtime внутри MSI (размер снова порядка десятков МБ).
- Раскладка `bin\` как в 2.1.1: корень + **`ms\`** (Microsoft/System) + **`lib\`** (Serilog и пр.).

## Прочее

CLI `bad uninstall`, MajorUpgrade через `msiexec /i … /qn` — без изменений.
