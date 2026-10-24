/** Общие подсказки «Параметры» для global-search и overview-search. */
(function (w) {
  var HITS = [
    { label: "Доступ / LDAP", href: "/settings/ldap", keys: "ldap доступ домен" },
    { label: "Сертификат TLS", href: "/settings/tls", keys: "tls https сертификат" },
    { label: "Почта и уведомления", href: "/settings/mail", keys: "smtp почта mail digest" },
    { label: "Хранение и очистка", href: "/settings/retention", keys: "retention хранение очистка" },
    { label: "Резервные копии", href: "/settings/backups", keys: "backup резерв ключи" },
    { label: "Политики агента", href: "/settings/policies", keys: "политики policy агент" },
    { label: "Обновления агента", href: "/settings/updates", keys: "агент msi обновление enrollment" },
    { label: "Обновление сервера", href: "/settings/server-update", keys: "сервер обновление release" },
  ];

  w.badPanelSettingsHits = function (q) {
    var text = (q || "").trim();
    if (text.length < 2) return [];
    var ql = text.toLowerCase();
    return HITS.filter(function (s) {
      return s.label.toLowerCase().indexOf(ql) >= 0 || s.keys.indexOf(ql) >= 0;
    });
  };
})(window);
