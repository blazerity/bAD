# Установка сервера (Debian 12)

Скрипт `install.sh` ставит PostgreSQL, nginx и службу. Сертификат можно не передавать: панель сначала откроется по HTTP, файл сертификата загружается в **Параметры → Сертификат**.

Сразу с HTTPS:

```bash
BAD_DOMAIN=<домен> sudo -E bash install.sh
```

С сертификатом сразу, как в шапке `install.sh`:

```bash
BAD_DOMAIN=<домен> BAD_TLS_CERT=<fullchain.pem> BAD_TLS_KEY=<privkey.pem> sudo -E bash install.sh
```

Дальше — [docs/ste-100.md](../../docs/ste-100.md): смените пароль `admin`, включите подпись снимка.
