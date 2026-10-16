using System.Globalization;

namespace BadAgent;

/// <summary>
/// Локальный просмотр/изменение knobs в <c>config.json</c>.
/// Маркеры — через <see cref="ConfigStore.MarkAgentLocalKey"/> /
/// <see cref="ConfigStore.MarkServerUrlLocal"/> (контракт Windows Agent / API Lead).
/// </summary>
public static class ConfigCli
{
    /// <summary>Ключи <c>bad config set</c>: safe knobs + <c>server_url</c>.</summary>
    public static IReadOnlyList<string> EditableKeys { get; } =
        ConfigStore.CliManualSettingKeys
            .OrderBy(k => k, StringComparer.Ordinal)
            .Prepend("server_url")
            .ToArray();

    private static readonly HashSet<string> ForbiddenKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "api_key",
        "enrollment_token",
        "device_id",
        "pending_update_version",
        "pending_update_started_at",
        "remote_config_version",
        "agent_local_keys",
        "server_url_local",
        "update_enabled",
        "update_target",
        "desired_agent_version"
    };

    public static int Run(string[] args)
    {
        if (args.Length == 0)
        {
            return RunShow();
        }

        if (IsHelpToken(args[0]))
        {
            PrintHelp();
            return 0;
        }

        var cmd = args[0].Trim().ToLowerInvariant();
        return cmd switch
        {
            "set" => RunSet(args.AsSpan(1).ToArray()),
            "get" => RunGet(args.AsSpan(1).ToArray()),
            "unset" or "clear" => RunUnset(args.AsSpan(1).ToArray()),
            "list" or "ls" or "show" => RunShow(),
            _ => Unknown(args[0])
        };
    }

    private static int Unknown(string cmd)
    {
        Console.Error.WriteLine($"error: неизвестная подкоманда config '{cmd}'");
        PrintHelp();
        return 2;
    }

    private static int RunShow()
    {
        var cfg = ConfigStore.LoadOrCreate();
        Console.WriteLine($"Файл: {ConfigStore.ConfigPath}");
        Console.WriteLine();
        Console.WriteLine("Изменяемые параметры (bad config set <ключ> <значение>):");
        foreach (var key in EditableKeys)
        {
            var manual = IsManual(cfg, key) ? "  [вручную на агенте / agent_local]" : "";
            Console.WriteLine($"  {key}={FormatValue(GetEditable(cfg, key))}{manual}");
        }

        Console.WriteLine();
        Console.WriteLine("Только чтение / секреты (через CLI не меняются):");
        Console.WriteLine($"  device_id={MaskEmpty(cfg.DeviceId)}");
        Console.WriteLine($"  api_key={(string.IsNullOrWhiteSpace(cfg.ApiKey) ? "(нет)" : "(задан, скрыт)")}");
        Console.WriteLine(
            $"  enrollment_token={(string.IsNullOrWhiteSpace(cfg.EnrollmentToken) ? "(нет)" : "(задан, скрыт)")}");
        Console.WriteLine($"  remote_config_version={MaskEmpty(cfg.RemoteConfigVersion)}");
        Console.WriteLine();
        Console.WriteLine(
            $"Маркеры: agent_local_keys=[{string.Join(", ", cfg.AgentLocalKeys ?? [])}] " +
            $"server_url_local={cfg.ServerUrlLocal}");
        Console.WriteLine("(в heartbeat уходит config_local → meta.config_local на сервере)");
        return 0;
    }

    private static int RunGet(string[] args)
    {
        if (args.Length != 1)
        {
            Console.Error.WriteLine("error: использование: bad config get <ключ>");
            return 2;
        }

        var key = NormalizeKey(args[0]);
        if (ForbiddenKeys.Contains(key) || !IsEditable(key))
        {
            Console.Error.WriteLine(
                $"error: ключ '{args[0]}' нельзя читать через config get " +
                "(секреты/служебные) или он не в списке изменяемых. См. bad config.");
            return 2;
        }

        var cfg = ConfigStore.LoadOrCreate();
        var manual = IsManual(cfg, key) ? " [вручную на агенте / agent_local]" : "";
        Console.WriteLine($"{key}={FormatValue(GetEditable(cfg, key))}{manual}");
        return 0;
    }

    private static int RunUnset(string[] args)
    {
        if (args.Length != 1)
        {
            Console.Error.WriteLine("error: использование: bad config unset <ключ>");
            return 2;
        }

        var key = NormalizeKey(args[0]);
        if (!IsEditable(key))
        {
            Console.Error.WriteLine($"error: ключ '{args[0]}' не из списка изменяемых");
            return 2;
        }

        var cfg = ConfigStore.LoadOrCreate();
        if (key == "server_url")
        {
            if (!cfg.ServerUrlLocal)
            {
                Console.Error.WriteLine("error: у server_url нет маркера server_url_local");
                return 1;
            }

            ConfigStore.MarkServerUrlLocal(cfg, false);
            ConfigStore.Save(cfg);
            Console.WriteLine("ok: снят server_url_local (значение server_url не трогали)");
            return 0;
        }

        if (!ConfigStore.IsAgentLocalKey(cfg, key))
        {
            Console.Error.WriteLine($"error: у ключа '{key}' нет маркера agent_local");
            return 1;
        }

        ConfigStore.ClearAgentLocalKey(cfg, key);
        ConfigStore.Save(cfg);
        Console.WriteLine($"ok: снят agent_local для {key} (значение в файле не трогали)");
        Console.WriteLine("После следующего heartbeat remote policy снова сможет перезаписать этот knob.");
        return 0;
    }

    private static int RunSet(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("error: использование: bad config set <ключ> <значение>");
            return 2;
        }

        if (args.Length > 2)
        {
            Console.Error.WriteLine(
                "error: значение должно быть одним аргументом (без подстановки shell)");
            return 2;
        }

        var keyRaw = args[0];
        var valueRaw = args[1];
        var key = NormalizeKey(keyRaw);

        if (key.IndexOfAny(['|', ';', '&', '`', '$', '\n', '\r', '\0']) >= 0
            || valueRaw.IndexOfAny(['\n', '\r', '\0']) >= 0)
        {
            Console.Error.WriteLine("error: недопустимые символы в ключе или значении");
            return 2;
        }

        if (ForbiddenKeys.Contains(key))
        {
            Console.Error.WriteLine(
                $"error: ключ '{keyRaw}' запрещён для CLI (секреты и служебные поля не меняются)");
            return 2;
        }

        if (!IsEditable(key))
        {
            Console.Error.WriteLine(
                $"error: неизвестный или неразрешённый ключ '{keyRaw}'. " +
                $"Допустимо: {string.Join(", ", EditableKeys)}");
            return 2;
        }

        var cfg = ConfigStore.LoadOrCreate();
        var previousServerUrl = cfg.ServerUrl;
        if (!TryApply(cfg, key, valueRaw, out var error))
        {
            Console.Error.WriteLine($"error: {error}");
            return 1;
        }

        if (key == "server_url")
        {
            ConfigStore.MarkServerUrlLocal(cfg, true);
        }
        else if (!ConfigStore.MarkAgentLocalKey(cfg, key))
        {
            Console.Error.WriteLine($"error: не удалось пометить '{key}' как agent_local");
            return 1;
        }

        ConfigStore.Save(cfg);
        Console.WriteLine($"ok: {key}={FormatValue(GetEditable(cfg, key))} [вручную на агенте / agent_local]");
        Console.WriteLine($"Записано в {ConfigStore.ConfigPath}");

        if (key == "server_url")
        {
            PrintServerUrlWarning(previousServerUrl, cfg.ServerUrl);
        }

        return 0;
    }

    public static bool TryApply(AgentConfig config, string key, string value, out string? error)
    {
        error = null;
        key = NormalizeKey(key);

        switch (key)
        {
            case "server_url":
                return TryApplyServerUrl(config, value, out error);

            case "inventory_interval_hours":
                if (!TryParsePositiveInt(value, out var inv))
                {
                    error = "inventory_interval_hours: нужно целое число ≥ 1";
                    return false;
                }

                config.InventoryIntervalHours = inv;
                return true;

            case "heartbeat_interval_minutes":
                if (!TryParsePositiveInt(value, out var hb))
                {
                    error = "heartbeat_interval_minutes: нужно целое число ≥ 1";
                    return false;
                }

                config.HeartbeatIntervalMinutes = hb;
                return true;

            case "update_check_interval_hours":
                if (!TryParsePositiveInt(value, out var uch))
                {
                    error = "update_check_interval_hours: нужно целое число ≥ 1";
                    return false;
                }

                config.UpdateCheckIntervalHours = uch;
                return true;

            case "collect_hardware":
                if (!TryParseBool(value, out var ch))
                {
                    error = "collect_hardware: ожидается true/false (или 1/0, yes/no)";
                    return false;
                }

                config.CollectHardware = ch;
                return true;

            case "collect_users":
                if (!TryParseBool(value, out var cu))
                {
                    error = "collect_users: ожидается true/false (или 1/0, yes/no)";
                    return false;
                }

                config.CollectUsers = cu;
                return true;

            case "collect_software":
                if (!TryParseBool(value, out var cs))
                {
                    error = "collect_software: ожидается true/false (или 1/0, yes/no)";
                    return false;
                }

                config.CollectSoftware = cs;
                return true;

            default:
                error = $"ключ '{key}' не поддерживается";
                return false;
        }
    }

    private static bool TryApplyServerUrl(AgentConfig config, string value, out string? error)
    {
        error = null;
        var url = value.Trim().TrimEnd('/');
        if (string.IsNullOrWhiteSpace(url))
        {
            error = "server_url: пустое значение недопустимо";
            return false;
        }

        var allowHttp = string.Equals(
            Environment.GetEnvironmentVariable("BAD_ALLOW_HTTP"), "1", StringComparison.Ordinal);

        if (url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) && !allowHttp)
        {
            error = BadApiClient.CleartextHttpRejectedMessage;
            return false;
        }

        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase)
            && !url.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
        {
            error = "server_url: нужен абсолютный URL (https://…; http:// — только lab с BAD_ALLOW_HTTP=1)";
            return false;
        }

        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)
            || (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp))
        {
            error = "server_url: некорректный URL";
            return false;
        }

        config.ServerUrl = url;
        return true;
    }

    private static void PrintServerUrlWarning(string previous, string current)
    {
        Console.WriteLine();
        Console.WriteLine("Важно:");
        Console.WriteLine("  • В production указывайте только https:// (не http://).");
        Console.WriteLine("  • BAD_ALLOW_HTTP=1 — только lab, не для боевых агентов.");
        if (!string.Equals(previous, current, StringComparison.OrdinalIgnoreCase))
        {
            Console.WriteLine(
                "  • Смена server_url может потребовать повторный enroll на новом сервере");
            Console.WriteLine(
                "    (если api_key от другого сайта — служба получит 401/403 и очистит ключ).");
        }
    }

    private static bool IsManual(AgentConfig cfg, string key) =>
        key == "server_url"
            ? cfg.ServerUrlLocal
            : ConfigStore.IsAgentLocalKey(cfg, key);

    private static object GetEditable(AgentConfig cfg, string key) => key switch
    {
        "server_url" => cfg.ServerUrl,
        "inventory_interval_hours" => cfg.InventoryIntervalHours,
        "heartbeat_interval_minutes" => cfg.HeartbeatIntervalMinutes,
        "update_check_interval_hours" => cfg.UpdateCheckIntervalHours,
        "collect_hardware" => cfg.CollectHardware,
        "collect_users" => cfg.CollectUsers,
        "collect_software" => cfg.CollectSoftware,
        _ => ""
    };

    private static bool IsEditable(string key) =>
        key == "server_url" || ConfigStore.CliManualSettingKeys.Contains(key);

    private static string NormalizeKey(string key) => key.Trim().ToLowerInvariant();

    private static bool IsHelpToken(string s) =>
        s is "-h" or "--help" or "-?" or "/?" or "help";

    private static bool TryParsePositiveInt(string value, out int n) =>
        int.TryParse(value.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out n) && n >= 1;

    private static bool TryParseBool(string value, out bool b)
    {
        var t = value.Trim();
        if (t is "1" or "true" or "TRUE" or "True" or "yes" or "YES" or "on")
        {
            b = true;
            return true;
        }

        if (t is "0" or "false" or "FALSE" or "False" or "no" or "NO" or "off")
        {
            b = false;
            return true;
        }

        b = false;
        return false;
    }

    private static string FormatValue(object value) => value switch
    {
        bool b => b ? "true" : "false",
        IFormattable f => f.ToString(null, CultureInfo.InvariantCulture) ?? "",
        _ => value.ToString() ?? ""
    };

    private static string MaskEmpty(string? s) =>
        string.IsNullOrWhiteSpace(s) ? "(не задан)" : s;

    private static void PrintHelp()
    {
        Console.WriteLine("""
Настройки агента (локальный config.json):
  bad config                      Показать параметры
  bad config get <ключ>           Прочитать один ключ
  bad config set <ключ> <значение>
  bad config unset <ключ>         Снять маркер agent_local / server_url_local
  bad settings                    То же, что bad config

Разрешено:
  server_url                      https://… (http:// только lab + BAD_ALLOW_HTTP=1)
  inventory_interval_hours        целое ≥ 1
  heartbeat_interval_minutes      целое ≥ 1
  update_check_interval_hours     целое ≥ 1
  collect_hardware|users|software true|false

Запрещено обычным set: api_key, enrollment_token, device_id.
После set: MarkAgentLocalKey / MarkServerUrlLocal → heartbeat config_local (панель: agent_local).
""");
    }
}
