-- Local web users + optional LDAP settings (also applied by Database._init_schema)
CREATE TABLE IF NOT EXISTS local_users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL COLLATE NOCASE UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'admin',
  must_change_password INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS ldap_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  enabled INTEGER NOT NULL DEFAULT 0,
  host TEXT NOT NULL DEFAULT '',
  port INTEGER NOT NULL DEFAULT 389,
  use_ssl INTEGER NOT NULL DEFAULT 0,
  start_tls INTEGER NOT NULL DEFAULT 0,
  bind_dn TEXT NOT NULL DEFAULT '',
  bind_password_enc TEXT NOT NULL DEFAULT '',
  user_search_base TEXT NOT NULL DEFAULT '',
  user_filter_template TEXT NOT NULL DEFAULT '(uid={username})',
  display_name_attr TEXT NOT NULL DEFAULT 'cn',
  default_role TEXT NOT NULL DEFAULT 'operator',
  updated_at TEXT
);

INSERT OR IGNORE INTO ldap_settings(id) VALUES (1);
