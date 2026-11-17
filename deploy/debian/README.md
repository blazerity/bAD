# Установка сервера (Debian 12)

Скрипт `install.sh` ставит PostgreSQL, nginx и службу. Сертификат можно не передавать: панель сначала откроется по HTTP, файл сертификата загружается в **Параметры → Сертификат**.

`BAD_DOMAIN` — только DNS-имя, например `bad.stepcon.ru`. Без `https://`, без пути и без порта.

Без сертификата:

```bash
sudo -E BAD_DOMAIN=bad.stepcon.ru bash install.sh
```

С сертификатом сразу:

```bash
sudo -E BAD_DOMAIN=bad.stepcon.ru BAD_TLS_CERT=<fullchain.pem> BAD_TLS_KEY=<privkey.pem> bash install.sh
```

Дальше — [docs/ste-100.md](../../docs/ste-100.md): смените пароль `admin`, включите подпись снимка.
