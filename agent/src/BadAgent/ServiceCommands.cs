using System.Text.Json;

namespace BadAgent;

/// <summary>Команды, которые служба выполняет сама. Ответ не содержит ключ.</summary>
internal static class ServiceCommands
{
    private static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public static string Dispatch(string requestJson)
    {
        try
        {
            using var doc = JsonDocument.Parse(requestJson);
            var root = doc.RootElement;
            var op = root.TryGetProperty("op", out var opEl) ? opEl.GetString() : "";
            var outcome = op switch
            {
                "push" => PushCli.Execute(),
                "update" => UpdateCli.Execute(),
                "doctor" => DoctorCli.Execute(),
                "link" => LinkProbe.Execute(),
                "config-show" => ConfigCli.ExecuteShow(),
                "config-get" => ConfigCli.ExecuteGet(Text(root, "key")),
                "config-set" => ConfigCli.ExecuteSet(Text(root, "key"), Text(root, "value")),
                "config-unset" => ConfigCli.ExecuteUnset(Text(root, "key")),
                "config-apply" => ConfigCli.ExecuteApply(Map(root, "values")),
                "report" => ReportRelay.Execute(root),
                _ => Unknown()
            };
            return Serialize(outcome);
        }
        catch (Exception ex)
        {
            var failed = new CliOutcome { ExitCode = 1 };
            failed.Line("Ошибка", ex.Message, "ошибка");
            return Serialize(failed);
        }
    }

    private static CliOutcome Unknown()
    {
        var outcome = new CliOutcome { ExitCode = 2 };
        outcome.Line("Служба", "неизвестная команда", "ошибка");
        return outcome;
    }

    private static string Text(JsonElement root, string name) =>
        root.TryGetProperty(name, out var el) && el.ValueKind == JsonValueKind.String
            ? el.GetString() ?? ""
            : "";

    private static Dictionary<string, string> Map(JsonElement root, string name)
    {
        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        if (!root.TryGetProperty(name, out var el) || el.ValueKind != JsonValueKind.Object)
        {
            return map;
        }

        foreach (var prop in el.EnumerateObject())
        {
            if (prop.Value.ValueKind == JsonValueKind.String)
            {
                map[prop.Name] = prop.Value.GetString() ?? "";
            }
        }

        return map;
    }

    private static string Serialize(CliOutcome outcome)
    {
        var body = new Dictionary<string, object?>
        {
            ["exit"] = outcome.ExitCode,
            ["stop"] = outcome.StopAfterReply,
            ["lines"] = outcome.Lines.Select(line => new Dictionary<string, object?>
            {
                ["field"] = line.Field,
                ["value"] = line.Value,
                ["status"] = line.Status
            }).ToList(),
            ["tail"] = outcome.Tail,
            ["html"] = outcome.Html,
            ["values"] = outcome.Values
        };
        return JsonSerializer.Serialize(body, Json);
    }
}

internal static class LinkProbe
{
    public static CliOutcome Execute()
    {
        var outcome = new CliOutcome();
        if (!ConfigStore.TryLoadForRead(out var config, out _))
        {
            outcome.Line("Связь", "нет", "ошибка");
            outcome.Values = new Dictionary<string, string> { ["kind"] = "down" };
            outcome.ExitCode = 1;
            return outcome;
        }

        var kind = Check(config);
        outcome.Values = new Dictionary<string, string> { ["kind"] = kind };
        if (kind is "up" or "auth")
        {
            outcome.Line("Связь", "есть", "ok");
            outcome.ExitCode = 0;
            return outcome;
        }

        outcome.Line("Связь", "нет", "ошибка");
        outcome.ExitCode = 1;
        return outcome;
    }

    public readonly record struct LinkProbeStatus(string Kind, AgentApiException? AuthException);

    public static LinkProbeStatus Status(AgentConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            return new LinkProbeStatus("no_url", null);
        }

        if (string.IsNullOrWhiteSpace(config.ApiKey) || string.IsNullOrWhiteSpace(config.DeviceId))
        {
            return new LinkProbeStatus("down", null);
        }

        try
        {
            var version = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, version);
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            _ = client.SendHeartbeatAsync(
                config.ApiKey,
                new HeartbeatQueuePayload { DeviceId = config.DeviceId },
                cts.Token).GetAwaiter().GetResult();
            return new LinkProbeStatus("up", null);
        }
        catch (AgentApiException ex) when (ex.IsAuthFailure)
        {
            return new LinkProbeStatus("auth", ex);
        }
        catch (Exception)
        {
            return new LinkProbeStatus("down", null);
        }
    }

    public static string Check(AgentConfig config)
    {
        var status = Status(config);
        if (status.Kind == "auth"
            && status.AuthException is { } ex
            && InvalidKeyReset.IsInvalidApiKey(ex))
        {
            using var client = new BadApiClient(config.ServerUrl, VersionUtil.GetAgentVersion());
            InvalidKeyReset.Forget(config, client, CancellationToken.None);
        }

        return status.Kind;
    }
}

internal static class ReportRelay
{
    public static CliOutcome Execute(JsonElement root)
    {
        var outcome = new CliOutcome();
        if (!root.TryGetProperty("snapshot", out var snapshotEl))
        {
            outcome.ExitCode = 1;
            outcome.Line("Отчёт", "нет снимка", "ошибка");
            return outcome;
        }

        InventorySnapshot? snapshot;
        try
        {
            snapshot = JsonSerializer.Deserialize<InventorySnapshot>(
                snapshotEl.GetRawText(), AgentSigningKey.InventoryJsonOptions);
        }
        catch (JsonException)
        {
            snapshot = null;
        }

        if (snapshot is null)
        {
            outcome.ExitCode = 1;
            outcome.Line("Отчёт", "снимок не разобран", "ошибка");
            return outcome;
        }

        if (!ConfigStore.TryLoadForRead(out var config, out _)
            || string.IsNullOrWhiteSpace(config.ServerUrl)
            || string.IsNullOrWhiteSpace(config.ApiKey))
        {
            outcome.ExitCode = 0;
            return outcome;
        }

        try
        {
            var version = VersionUtil.GetAgentVersion();
            using var client = new BadApiClient(config.ServerUrl, version);
            using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(3));
            outcome.Html = client.TryPostReportHtmlAsync(config.ApiKey, snapshot, cts.Token)
                .GetAwaiter()
                .GetResult();
            outcome.ExitCode = 0;
            return outcome;
        }
        catch (AgentApiException ex) when (InvalidKeyReset.IsInvalidApiKey(ex))
        {
            using var client = new BadApiClient(config.ServerUrl, VersionUtil.GetAgentVersion());
            InvalidKeyReset.Forget(config, client, CancellationToken.None);
            outcome.ExitCode = 0;
            return outcome;
        }
        catch (InvalidOperationException ex) when (ServerUrlRules.IsCleartextRejectedException(ex))
        {
            outcome.ExitCode = 1;
            outcome.Line("Отчёт", ServerUrlRules.CleartextHttpRejectedMessage, "ошибка");
            return outcome;
        }
        catch (Exception)
        {
            outcome.ExitCode = 0;
            return outcome;
        }
    }
}
