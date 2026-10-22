# Релизные заметки — сервер 1.8.0, агент 1.2.0

## Панель: принудительное обновление политики и проверка MSI

- На карточке устройства (admin): кнопка **«Обновить политику и версию»** — одноразовый запрос к агенту при следующем heartbeat (pull-only: флаги в `devices.meta`, без push с сервера).
- Сервер в ответе heartbeat отдаёт полный remote `config` (даже если `config_version` не менялся) и `actions`: `inventory`, `update_check` — по флагам запроса.
- Admin API: `POST /v1/devices/{device_id}/request-refresh`.

## Агент 1.2.0

- Обработка `actions` в ответе heartbeat (принудительный inventory и проверка обновления MSI).
- CLI **`bad push`** / **`bad push --update`** — локально то же на машине (очередь → inventory → heartbeat; опционально update), без кнопки в панели.
