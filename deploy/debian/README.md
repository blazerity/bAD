# Deploy (Debian 12)

Однострочная установка: `install.sh` (см. [docs/operator-guide.md](../../docs/operator-guide.md)).

**Секреты:** `/var/lib/bad/bad.db` и daily backups = полный компромисс site secrets, пока master key не вне БД (`BAD_DATA_KEY`, файл `440`/`400`); enrollment token в msiexec argv/логах — не шарить логи, ротировать после массового деплоя. LDAP TLS без verify — только lab. Сразу сменить `admin`/`admin`; UI только за nginx HTTPS.
