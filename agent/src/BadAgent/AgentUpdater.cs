using System.Diagnostics;
using System.Globalization;
using System.Text.Json;

namespace BadAgent;

/// <summary>
/// Проверяет на сервере bAD целевой MSI (upgrade / downgrade / pin / latest),
/// сверяет sha256, запускает silent msiexec и выходит для MajorUpgrade.
/// Агенты не ходят на GitHub напрямую. Download — только same-origin (SEC-009).
/// </summary>
public sealed class AgentUpdater
{
    /// <summary>Не долбить msiexec той же целевой версией чаще этого интервала.</summary>
    public static readonly TimeSpan PendingCooldown = TimeSpan.FromHours(2);

    private readonly ILogger _logger;
    private readonly string _agentVersion;

    public AgentUpdater(ILogger logger, string agentVersion)
    {
        _logger = logger;
        _agentVersion = agentVersion;
    }

    public async Task<bool> CheckAndApplyAsync(BadApiClient client, AgentConfig config, CancellationToken ct)
    {
        if (!config.UpdateEnabled)
        {
            _logger.LogDebug("Self-update disabled in config");
            return false;
        }

        if (string.IsNullOrWhiteSpace(config.ApiKey))
        {
            return false;
        }

        ClearPendingIfMatched(config);

        var desired = VersionUtil.NormalizeDesiredAgentVersion(config.DesiredAgentVersion) ?? "latest";

        UpdateCheckResponse check;
        try
        {
            check = await client.CheckUpdateAsync(config.ApiKey!, _agentVersion, desired, ct);
        }
        catch (AgentApiException ex) when (ex.IsAuthFailure)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Update check failed");
            WindowsEventLog.WriteWarning("bAD: проверка обновления не удалась", ex);
            return false;
        }

        var plan = ResolvePlan(_agentVersion, desired, check);
        if (plan.Action == UpdateAction.None)
        {
            _logger.LogDebug(
                "No agent version change (local={Local}, desired={Desired}, mirrored={Mirrored}, reason={Reason})",
                _agentVersion,
                desired,
                check.Version ?? "(none)",
                plan.Reason);
            return false;
        }

        if (string.IsNullOrWhiteSpace(plan.TargetVersion)
            || string.IsNullOrWhiteSpace(plan.Sha256)
            || string.IsNullOrWhiteSpace(plan.Url))
        {
            _logger.LogWarning(
                "Update plan {Action} incomplete (version/sha/url); skipping",
                plan.Action);
            return false;
        }

        if (IsPendingBlocked(config, plan.TargetVersion!))
        {
            _logger.LogInformation(
                "Pending msiexec for {Target} still within cooldown; not looping",
                plan.TargetVersion);
            return false;
        }

        if (!OperatingSystem.IsWindows())
        {
            _logger.LogWarning(
                "Version change {Action} to {Version} available but msiexec is Windows-only; skipping",
                plan.Action,
                plan.TargetVersion);
            return false;
        }

        var tempDir = Path.Combine(Path.GetTempPath(), "bad-agent-update", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);
        string msiPath;
        try
        {
            msiPath = UpdatePathUtil.ResolveSafeMsiPath(tempDir, plan.MsiName ?? check.MsiName, plan.TargetVersion);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Refusing unsafe msi_name from update check");
            WindowsEventLog.WriteError("bAD: отказ — небезопасное имя MSI в ответе update/check", ex);
            return false;
        }

        try
        {
            _logger.LogInformation(
                "Downloading agent package for {Action}: {From} → {To}",
                plan.Action,
                _agentVersion,
                plan.TargetVersion);
            await client.DownloadUpdateMsiAsync(config.ApiKey!, plan.Url!, msiPath, ct);

            if (!VersionUtil.VerifySha256File(msiPath, plan.Sha256!))
            {
                _logger.LogError(
                    "Update MSI sha256 mismatch for {Version}; refusing to install",
                    plan.TargetVersion);
                WindowsEventLog.WriteError(
                    $"bAD: sha256 MSI {plan.TargetVersion} не совпал — установка отменена.");
                return false;
            }

            MarkPending(config, plan.TargetVersion!);

            var kind = plan.Action == UpdateAction.Downgrade ? "downgrade" : "upgrade";
            var logPath = Path.Combine(ConfigStore.LogsDir, $"msiexec-{kind}-{plan.TargetVersion}.log");
            var psi = new ProcessStartInfo
            {
                FileName = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.System),
                    "msiexec.exe"),
                Arguments = $"/i \"{msiPath}\" /qn /l*v \"{logPath}\"",
                UseShellExecute = false,
                CreateNoWindow = true
            };

            _logger.LogInformation(
                "Starting silent msiexec {Action} {From} → {To}; agent will exit for file replace (log {Log})",
                plan.Action,
                _agentVersion,
                plan.TargetVersion,
                logPath);
            WindowsEventLog.WriteInfo(
                $"bAD: msiexec {kind} {_agentVersion} → {plan.TargetVersion}");

            if (Process.Start(psi) is null)
            {
                _logger.LogError("Failed to start msiexec");
                ClearPending(config);
                return false;
            }

            try
            {
                await Task.Delay(TimeSpan.FromSeconds(2), ct);
            }
            catch (OperationCanceledException)
            {
                // всё равно выходим, чтобы разблокировать файлы
            }

            return true;
        }
        catch (AgentApiException ex) when (ex.IsAuthFailure)
        {
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to download/apply {Action} to {Version}", plan.Action, plan.TargetVersion);
            WindowsEventLog.WriteError($"bAD: сбой {plan.Action} → {plan.TargetVersion}", ex);
            try
            {
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, recursive: true);
                }
            }
            catch
            {
                // best-effort очистка
            }

            return false;
        }
    }

    /// <summary>Решение upgrade / downgrade / none по local + desired + ответу check.</summary>
    public static UpdatePlan ResolvePlan(string localVersion, string desired, UpdateCheckResponse check)
    {
        var mirrored = check.Version;
        var actionHint = NormalizeAction(check.Action);

        // Сервер явно сказал none.
        if (actionHint == UpdateAction.None)
        {
            return UpdatePlan.None("server_action_none");
        }

        // Same version as mirrored / target — всегда no-op.
        if (!string.IsNullOrWhiteSpace(mirrored) && VersionUtil.IsSameVersion(localVersion, mirrored)
            && (string.Equals(desired, "latest", StringComparison.OrdinalIgnoreCase)
                || VersionUtil.IsSameVersion(localVersion, desired)))
        {
            return UpdatePlan.None("same");
        }

        if (string.Equals(desired, "latest", StringComparison.OrdinalIgnoreCase))
        {
            // latest: только upgrade; никогда авто-downgrade на более старое зеркало.
            if (actionHint == UpdateAction.Downgrade)
            {
                return UpdatePlan.None("latest_ignores_downgrade");
            }

            if (!check.UpdateAvailable && actionHint is null)
            {
                return UpdatePlan.None("latest_no_update");
            }

            if (string.IsNullOrWhiteSpace(mirrored) || !VersionUtil.IsNewer(mirrored, localVersion))
            {
                return UpdatePlan.None("latest_not_newer");
            }

            var url = check.Url;
            if (string.IsNullOrWhiteSpace(url) && check.UpdateAvailable)
            {
                url = "/v1/agent/update/msi";
            }

            if (string.IsNullOrWhiteSpace(check.Sha256) || string.IsNullOrWhiteSpace(url))
            {
                return UpdatePlan.None("latest_missing_assets");
            }

            return new UpdatePlan(UpdateAction.Upgrade, mirrored, check.Sha256, url, check.MsiName, "latest_upgrade");
        }

        // Pin to semver.
        if (!VersionUtil.TryParseSemVer(desired, out _))
        {
            return UpdatePlan.None("bad_desired");
        }

        if (VersionUtil.IsSameVersion(localVersion, desired))
        {
            return UpdatePlan.None("same");
        }

        // Пакет на зеркале должен совпасть с pin (single-mirror модель).
        if (string.IsNullOrWhiteSpace(mirrored) || !VersionUtil.IsSameVersion(mirrored, desired))
        {
            return UpdatePlan.None("pin_not_on_mirror");
        }

        var pinUrl = check.Url;
        if (string.IsNullOrWhiteSpace(pinUrl))
        {
            // Сервер 0.9.x мог не отдать url для non-newer — для pin всё равно бьём same-origin MSI.
            pinUrl = "/v1/agent/update/msi";
        }

        if (string.IsNullOrWhiteSpace(check.Sha256))
        {
            return UpdatePlan.None("pin_missing_sha");
        }

        if (VersionUtil.IsNewer(desired, localVersion))
        {
            return new UpdatePlan(UpdateAction.Upgrade, desired, check.Sha256, pinUrl, check.MsiName, "pin_upgrade");
        }

        if (VersionUtil.IsOlder(desired, localVersion))
        {
            return new UpdatePlan(UpdateAction.Downgrade, desired, check.Sha256, pinUrl, check.MsiName, "pin_downgrade");
        }

        return UpdatePlan.None("same");
    }

    private static UpdateAction? NormalizeAction(string? action)
    {
        if (string.IsNullOrWhiteSpace(action))
        {
            return null;
        }

        return action.Trim().ToLowerInvariant() switch
        {
            "upgrade" => UpdateAction.Upgrade,
            "downgrade" => UpdateAction.Downgrade,
            "none" or "noop" or "same" => UpdateAction.None,
            _ => null
        };
    }

    private void ClearPendingIfMatched(AgentConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.PendingUpdateVersion))
        {
            return;
        }

        if (VersionUtil.IsSameVersion(_agentVersion, config.PendingUpdateVersion))
        {
            _logger.LogInformation(
                "Pending update {Pending} matches running version; clearing pending",
                config.PendingUpdateVersion);
            ClearPending(config);
        }
    }

    private static bool IsPendingBlocked(AgentConfig config, string targetVersion)
    {
        if (!VersionUtil.IsSameVersion(config.PendingUpdateVersion, targetVersion))
        {
            return false;
        }

        if (!DateTime.TryParse(
                config.PendingUpdateStartedAt,
                CultureInfo.InvariantCulture,
                DateTimeStyles.RoundtripKind,
                out var started))
        {
            return false;
        }

        return DateTime.UtcNow - started.ToUniversalTime() < PendingCooldown;
    }

    private static void MarkPending(AgentConfig config, string targetVersion)
    {
        config.PendingUpdateVersion = targetVersion;
        config.PendingUpdateStartedAt = DateTime.UtcNow.ToString("O");
        ConfigStore.Save(config);
    }

    private static void ClearPending(AgentConfig config)
    {
        if (config.PendingUpdateVersion is null && config.PendingUpdateStartedAt is null)
        {
            return;
        }

        config.PendingUpdateVersion = null;
        config.PendingUpdateStartedAt = null;
        ConfigStore.Save(config);
    }
}

public enum UpdateAction
{
    None,
    Upgrade,
    Downgrade
}

public readonly record struct UpdatePlan(
    UpdateAction Action,
    string? TargetVersion,
    string? Sha256,
    string? Url,
    string? MsiName,
    string Reason)
{
    public static UpdatePlan None(string reason) =>
        new(UpdateAction.None, null, null, null, null, reason);
}

public sealed class UpdateCheckResponse
{
    public bool UpdateAvailable { get; init; }
    public string? Version { get; init; }
    public string? Sha256 { get; init; }
    public string? Url { get; init; }
    public string? MsiName { get; init; }
    /// <summary>Опционально от сервера: upgrade / downgrade / none.</summary>
    public string? Action { get; init; }
    public string? Desired { get; init; }

    public static UpdateCheckResponse FromJson(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        return new UpdateCheckResponse
        {
            UpdateAvailable = root.TryGetProperty("update_available", out var ua)
                              && ua.ValueKind is JsonValueKind.True or JsonValueKind.False
                              && ua.GetBoolean(),
            Version = GetString(root, "version") ?? GetString(root, "target_version"),
            Sha256 = GetString(root, "sha256"),
            Url = GetString(root, "url"),
            MsiName = GetString(root, "msi_name"),
            Action = GetString(root, "action"),
            Desired = GetString(root, "desired")
        };
    }

    private static string? GetString(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var el) || el.ValueKind != JsonValueKind.String)
        {
            return null;
        }

        return el.GetString();
    }
}
