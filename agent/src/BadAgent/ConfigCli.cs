using System.Globalization;

namespace BadAgent;

/// <summary>
/// Локальный просмотр/изменение knobs в <c>config.json</c>.
/// Основной UX: <c>bad -c</c> (интерактив). Маркеры —
/// <see cref="ConfigStore.MarkAgentLocalKey"/> / <see cref="ConfigStore.MarkServerUrlLocal"/>.
/// </summary>
public static class ConfigCli
{
    /// <summary>Порядок вопросов в <c>bad -c</c>: server_url → collect_* → интервалы.</summary>
    public static readonly string[] InteractiveKeys =
    [
        "server_url",
        "collect_hardware",
        "collect_users",
        "collect_software",
        "inventory_interval_hours",
        "heartbeat_interval_minutes",
        "update_check_interval_hours"
    ];

    /// <summary>Ключи <c>bad config set</c> для сообщений об ошибках (алфавит + server_url).</summary>
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

    private static readonly Dictionary<string, string> PromptHints = new(StringComparer.Ordinal)
    {
        ["server_url"] = "Адрес сервера (https://…)",
        ["collect_hardware"] = "Собирать оборудование (true/false)",
        ["collect_users"] = "Собирать пользователей (true/false)",
        ["collect_software"] = "Собирать список ПО (true/false)",
        ["inventory_interval_hours"] = "Интервал inventory, часы (≥ 1)",
        ["heartbeat_interval_minutes"] = "Интервал heartbeat, минуты (≥ 1)",
        ["update_check_interval_hours"] = "Интервал проверки обновлений, часы (≥ 1)"
    };

    public static int Run(string[] args)
    {
        if (args.Length == 0)
        {
            return RunShow();
        }

        if (BadCli.IsHelpToken(args[0]))
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

    /// <summary>Интерактивный мастер <c>bad -c</c>. Пустой ввод — оставить текущее значение.</summary>
    public static int RunInteractive(TextReader? input = null, TextWriter? output = null)
    {
        var elev = WindowsElevation.RequireElevatedOrExit("интерактивной настройки (bad -c)");
        if (elev != 0)
        {
            return elev;
        }

        input ??= Console.In;
        output ??= Console.Out;

        var cfg = ConfigStore.LoadOrCreate();
        var previousServerUrl = cfg.ServerUrl;
        var anyChanged = false;
        var serverUrlChanged = false;
        var changedKeys = new List<string>();

        output.WriteLine("Интерактивная настройка агента (bad -c)");
        output.WriteLine($"Файл: {ConfigStore.ConfigPath}");
        output.WriteLine("Пустой ввод — оставить текущее значение. Ctrl+C — отмена.");
        output.WriteLine("server_url в бою — только https:// (http:// лишь с BAD_ALLOW_HTTP=1 для lab).");
        output.WriteLine();

        foreach (var key in InteractiveKeys)
        {
            if (!PromptOneKey(input, output, cfg, key, ref anyChanged, ref serverUrlChanged, changedKeys))
            {
                break; // EOF
            }
        }

        if (!anyChanged)
        {
            output.WriteLine();
            output.WriteLine(CliColumns.Format("Настройки", "не перезаписывали", "без изменений"));
            return 0;
        }

        ConfigStore.Save(cfg);
        output.WriteLine();
        foreach (var changed in changedKeys)
        {
            output.WriteLine(CliColumns.Format(changed, FormatValue(GetEditable(cfg, changed)), "ok"));
        }
        if (serverUrlChanged)
        {
            PrintServerUrlWarning(previousServerUrl, cfg.ServerUrl, output);
        }

        return 0;
    }

    /// <returns><c>false</c> при EOF (прервать опрос).</returns>
    private static bool PromptOneKey(
        TextReader input,
        TextWriter output,
        AgentConfig cfg,
        string key,
        ref bool anyChanged,
        ref bool serverUrlChanged,
        List<string> changedKeys)
    {
        var current = FormatValue(GetEditable(cfg, key));
        var hint = PromptHints.GetValueOrDefault(key, key);

        while (true)
        {
            output.Write($"{hint} [{current}]: ");
            output.Flush();
            var line = input.ReadLine();
            if (line is null)
            {
                output.WriteLine();
                output.WriteLine("Ввод завершён (EOF).");
                return false;
            }

            if (string.IsNullOrWhiteSpace(line))
            {
                output.WriteLine($"  → без изменений ({current})");
                return true;
            }

            var raw = line.Trim();
            if (raw.IndexOfAny(['\n', '\r', '\0']) >= 0
                || (key != "server_url" && raw.IndexOfAny(['|', ';', '&', '`', '$']) >= 0))
            {
                output.WriteLine("  error: недопустимые символы, попробуйте ещё раз");
                continue;
            }

            if (!TryApply(cfg, key, raw, out var error))
            {
                output.WriteLine($"  error: {error}");
                continue;
            }

            var next = FormatValue(GetEditable(cfg, key));
            if (string.Equals(next, current, StringComparison.Ordinal))
            {
                output.WriteLine($"  → без изменений ({current})");
            }
            else
            {
                output.WriteLine($"  → {next}");
                if (key == "server_url")
                {
                    serverUrlChanged = true;
                    ConfigStore.MarkServerUrlLocal(cfg, true);
                }
                else
                {
                    ConfigStore.MarkAgentLocalKey(cfg, key);
                }

                anyChanged = true;
                changedKeys.Add(key);
            }

            return true;
        }
    }

    private static int Unknown(string cmd)
    {
        Console.Error.WriteLine($"error: неизвестная подкоманда config '{cmd}'");
        PrintHelp();
        return 2;
    }

    private static int RunShow()
    {
        var readable = ConfigStore.TryLoadForRead(out var cfg, out var readError);
        if (!readable)
        {
            Console.Error.WriteLine(
                "Предупреждение: config.json недоступен для чтения — показаны значения по умолчанию и device_id машины.");
            if (!string.IsNullOrWhiteSpace(readError))
            {
                Console.Error.WriteLine($"Причина: {readError}");
            }

            cfg.DeviceId = DeviceIdentity.ResolveDeviceId();
        }
        Console.WriteLine(CliColumns.Format("Файл", ConfigStore.ConfigPath));
        foreach (var key in InteractiveKeys)
        {
            var manual = IsManual(cfg, key) ? " [вручную на агенте]" : "";
            CliColumns.Write(key, FormatValue(GetEditable(cfg, key)) + manual);
        }

        CliColumns.Write("device_id", cfg.DeviceId);
        CliColumns.Write("remote_config_version", cfg.RemoteConfigVersion);
        return 0;
    }

    private static int RunGet(string[] args)
    {
        if (args.Length != 1)
        {
            CliColumns.Write("Ключ", "использование: bad config get <ключ>", "ошибка");
            return 2;
        }

        var key = NormalizeKey(args[0]);
        if (key is "api_key" or "enrollment_token" or "enrollment_code")
        {
            CliColumns.Write("Ключ", "секрет CLI не печатает", "ошибка");
            return 2;
        }

        if (ForbiddenKeys.Contains(key) || !IsEditable(key))
        {
            CliColumns.Write("Ключ", $"'{key}' нельзя читать через config get", "ошибка");
            return 2;
        }

        if (!ConfigStore.TryLoadForRead(out var cfg, out var readError))
        {
            var why = string.IsNullOrWhiteSpace(readError) ? "" : $" {readError}";
            CliColumns.Write("Ключ", $"не удалось прочитать config.json.{why}", "ошибка");
            return 1;
        }

        var manual = IsManual(cfg, key) ? " [вручную на агенте]" : "";
        CliColumns.Write(key, FormatValue(GetEditable(cfg, key)) + manual);
        return 0;
    }

    private static int RunUnset(string[] args)
    {
        var elev = WindowsElevation.RequireElevatedOrExit("изменения настроек (bad config unset)");
        if (elev != 0)
        {
            return elev;
        }

        if (args.Length != 1)
        {
            CliColumns.Write("Ключ", "использование: bad config unset <ключ>", "ошибка");
            return 2;
        }

        var key = NormalizeKey(args[0]);
        if (!IsEditable(key))
        {
            CliColumns.Write("Ключ", $"'{args[0]}' не из списка изменяемых", "ошибка");
            return 2;
        }

        var cfg = ConfigStore.LoadOrCreate();
        if (key == "server_url")
        {
            if (!cfg.ServerUrlLocal)
            {
                CliColumns.Write("server_url", "нет маркера server_url_local", "ошибка");
                return 1;
            }

            ConfigStore.MarkServerUrlLocal(cfg, false);
            ConfigStore.Save(cfg);
            CliColumns.Write("server_url", "снят server_url_local", "ok");
            return 0;
        }

        if (!ConfigStore.IsAgentLocalKey(cfg, key))
        {
            CliColumns.Write(key, "нет маркера agent_local", "ошибка");
            return 1;
        }

        ConfigStore.ClearAgentLocalKey(cfg, key);
        ConfigStore.Save(cfg);
        CliColumns.Write(key, "снят agent_local", "ok");
        return 0;
    }

    private static int RunSet(string[] args)
    {
        var elev = WindowsElevation.RequireElevatedOrExit("изменения настроек (bad config set)");
        if (elev != 0)
        {
            return elev;
        }

        if (args.Length < 2)
        {
            CliColumns.Write("Ключ", "использование: bad config set <ключ> <значение>", "ошибка");
            return 2;
        }

        if (args.Length > 2)
        {
            CliColumns.Write("Ключ", "значение должно быть одним аргументом", "ошибка");
            return 2;
        }

        var keyRaw = args[0];
        var valueRaw = args[1];
        var key = NormalizeKey(keyRaw);

        if (key.IndexOfAny(['|', ';', '&', '`', '$', '\n', '\r', '\0']) >= 0
            || valueRaw.IndexOfAny(['\n', '\r', '\0']) >= 0)
        {
            CliColumns.Write("Ключ", "недопустимые символы в ключе или значении", "ошибка");
            return 2;
        }

        if (key is "api_key" or "enrollment_token" or "enrollment_code" || ForbiddenKeys.Contains(key))
        {
            // Не эхоить valueRaw — даже при попытке set секрета.
            CliColumns.Write(key, "запрещён для CLI, значение не принято", "ошибка");
            return 2;
        }

        if (!IsEditable(key))
        {
            CliColumns.Write(key, "неизвестный или неразрешённый ключ", "ошибка");
            return 2;
        }

        var cfg = ConfigStore.LoadOrCreate();
        var previousServerUrl = cfg.ServerUrl;
        if (!TryApply(cfg, key, valueRaw, out var error))
        {
            // error — шаблон валидации (ServerUrlRules и т.п.); valueRaw не повторяем.
            CliColumns.Write(key, error, "ошибка");
            return 1;
        }

        if (key == "server_url")
        {
            ConfigStore.MarkServerUrlLocal(cfg, true);
        }
        else if (!ConfigStore.MarkAgentLocalKey(cfg, key))
        {
            CliColumns.Write(key, "не удалось пометить как agent_local", "ошибка");
            return 1;
        }

        ConfigStore.Save(cfg);
        CliColumns.Write(key, FormatValue(GetEditable(cfg, key)), "ok");

        if (key == "server_url")
        {
            PrintServerUrlWarning(previousServerUrl, cfg.ServerUrl, Console.Out);
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
                return TrySetPositiveInt(value, key, v => config.InventoryIntervalHours = v, out error);

            case "heartbeat_interval_minutes":
                return TrySetPositiveInt(value, key, v => config.HeartbeatIntervalMinutes = v, out error);

            case "update_check_interval_hours":
                return TrySetPositiveInt(value, key, v => config.UpdateCheckIntervalHours = v, out error);

            case "collect_hardware":
                return TrySetBool(value, key, v => config.CollectHardware = v, out error);

            case "collect_users":
                return TrySetBool(value, key, v => config.CollectUsers = v, out error);

            case "collect_software":
                return TrySetBool(value, key, v => config.CollectSoftware = v, out error);

            default:
                error = $"ключ '{key}' не поддерживается";
                return false;
        }
    }

    private static bool TrySetPositiveInt(string value, string key, Action<int> set, out string? error)
    {
        if (!TryParsePositiveInt(value, out var n))
        {
            error = $"{key}: нужно целое число ≥ 1";
            return false;
        }

        set(n);
        error = null;
        return true;
    }

    private static bool TrySetBool(string value, string key, Action<bool> set, out string? error)
    {
        if (!TryParseBool(value, out var b))
        {
            error = $"{key}: ожидается true/false (или 1/0, yes/no)";
            return false;
        }

        set(b);
        error = null;
        return true;
    }

    private static bool TryApplyServerUrl(AgentConfig config, string value, out string? error)
    {
        // Те же правила, что у службы (ServerUrlRules / BadApiClient) — без дрейфа сообщений.
        if (!ServerUrlRules.TryNormalize(value, out var url, out error))
        {
            return false;
        }

        config.ServerUrl = url;
        return true;
    }

    private static void PrintServerUrlWarning(string previous, string current, TextWriter output)
    {
        output.WriteLine();
        if (current.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
        {
            output.WriteLine(
                "Предупреждение: http:// принят только из‑за BAD_ALLOW_HTTP=1 (lab). " +
                "В бою укажите https:// — иначе агент без opt-in не подключится.");
        }
        else
        {
            output.WriteLine(
                "Важно: в бою оставляйте server_url на https:// " +
                "(cleartext без BAD_ALLOW_HTTP=1 служба отклонит — ServerUrlRules).");
        }

        if (!string.Equals(previous, current, StringComparison.OrdinalIgnoreCase))
        {
            output.WriteLine(
                "Смена server_url может потребовать повторный enroll на новом сервере. " +
                "При 401/403 служба api_key не удаляет.");
        }
    }

    private static bool IsManual(AgentConfig cfg, string key) =>
        key == "server_url"
            ? cfg.ServerUrlLocal
            : ConfigStore.IsAgentLocalKey(cfg, key);

    private static object GetEditable(AgentConfig cfg, string key) =>
        key == "server_url"
            ? cfg.ServerUrl
            : ConfigStore.TryGetSafeKnobValue(cfg, key) ?? "";

    private static bool IsEditable(string key) =>
        key == "server_url" || ConfigStore.CliManualSettingKeys.Contains(key);

    private static string NormalizeKey(string key) => key.Trim().ToLowerInvariant();

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

    private static void PrintHelp()
    {
        Console.WriteLine("""
Настройки агента:
  bad -c                          Интерактивная настройка
  bad config                      Показать параметры
  bad config set <ключ> <значение>   Один параметр
  bad config get|unset <ключ>

Изменяемые: server_url (в бою только https://), collect_*, интервалы.
Значения api_key / enrollment_token CLI не печатает и не принимает в set.
http:// в server_url — только lab с BAD_ALLOW_HTTP=1 (правила ServerUrlRules).
""");
    }
}
