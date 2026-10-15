using System.Diagnostics;
using System.Globalization;
using System.Text.Json;

namespace BadAgent;

/// <summary>
/// Проверяет на сервере bAD целевой MSI (upgrade / downgrade / pin / latest),
/// сверяет sha256, запускает silent msiexec и выходит для MajorUpgrade.
/// Gate (0.10): server update_available + target≠current + sha256 — не только IsNewer.
/// Download — только same-origin (SEC-009).
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

        var localTarget = VersionUtil.NormalizeDesiredAgentVersion(config.UpdateTarget) ?? "latest";

        UpdateCheckResponse check;
        try
        {
            check = await client.CheckUpdateAsync(config.ApiKey!, _agentVersion, ct);
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

        var plan = ResolvePlan(_agentVersion, localTarget, check);
        if (plan.Action == UpdateAction.None)
        {
            _logger.LogDebug(
                "No agent version change (local={Local}, update_target={Target}, server_target={ServerTarget}, reason={Reason})",
                _agentVersion,
                localTarget,
                check.TargetVersion ?? check.Version ?? "(none)",
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

    /// <summary>
    /// Решение upgrade / downgrade / none.
    /// Предпочтительно: server <c>update_available</c> + <c>target_version</c> (контракт §3–4).
    /// Fallback: локальный <c>update_target</c> + mirrored <c>version</c> (single-mirror 0.9.x).
    /// </summary>
    public static UpdatePlan ResolvePlan(string localVersion, string localUpdateTarget, UpdateCheckResponse check)
    {
        var serverTarget = FirstSemVer(check.TargetVersion, check.Version);
        var sha = check.Sha256;
        var url = check.Url;
        var msiName = check.MsiName;

        // --- Канон 0.10: сервер уже посчитал target ---
        if (check.UpdateAvailable && serverTarget is not null)
        {
            if (VersionUtil.IsSameVersion(localVersion, serverTarget))
            {
                return UpdatePlan.None("same");
            }

            if (string.IsNullOrWhiteSpace(sha))
            {
                return UpdatePlan.None("missing_sha");
            }

            if (string.IsNullOrWhiteSpace(url))
            {
                url = $"/v1/agent/update/msi?version={Uri.EscapeDataString(serverTarget)}";
            }

            if (VersionUtil.IsNewer(serverTarget, localVersion))
            {
                return new UpdatePlan(UpdateAction.Upgrade, serverTarget, sha, url, msiName, "server_upgrade");
            }

            if (VersionUtil.IsOlder(serverTarget, localVersion))
            {
                return new UpdatePlan(UpdateAction.Downgrade, serverTarget, sha, url, msiName, "server_downgrade");
            }

            return UpdatePlan.None("same");
        }

        if (!string.IsNullOrWhiteSpace(check.Reason)
            && check.Reason.Contains("broken", StringComparison.OrdinalIgnoreCase))
        {
            return UpdatePlan.None("broken_pin");
        }

        // --- Fallback single-mirror / pre-0.10 server ---
        var desired = VersionUtil.NormalizeDesiredAgentVersion(localUpdateTarget) ?? "latest";
        var mirrored = check.Version;

        if (string.Equals(desired, "latest", StringComparison.OrdinalIgnoreCase))
        {
            if (string.IsNullOrWhiteSpace(mirrored) || !VersionUtil.IsNewer(mirrored, localVersion))
            {
                return UpdatePlan.None("latest_not_newer");
            }

            if (string.IsNullOrWhiteSpace(sha))
            {
                return UpdatePlan.None("latest_missing_sha");
            }

            url = string.IsNullOrWhiteSpace(url) ? "/v1/agent/update/msi" : url;
            return new UpdatePlan(UpdateAction.Upgrade, mirrored, sha, url, msiName, "latest_upgrade");
        }

        if (!VersionUtil.TryParseSemVer(desired, out _))
        {
            return UpdatePlan.None("bad_update_target");
        }

        if (VersionUtil.IsSameVersion(localVersion, desired))
        {
            return UpdatePlan.None("same");
        }

        if (string.IsNullOrWhiteSpace(mirrored) || !VersionUtil.IsSameVersion(mirrored, desired))
        {
            return UpdatePlan.None("pin_not_on_mirror");
        }

        if (string.IsNullOrWhiteSpace(sha))
        {
            return UpdatePlan.None("pin_missing_sha");
        }

        url = string.IsNullOrWhiteSpace(url)
            ? $"/v1/agent/update/msi?version={Uri.EscapeDataString(desired)}"
            : url;

        if (VersionUtil.IsNewer(desired, localVersion))
        {
            return new UpdatePlan(UpdateAction.Upgrade, desired, sha, url, msiName, "pin_upgrade");
        }

        if (VersionUtil.IsOlder(desired, localVersion))
        {
            return new UpdatePlan(UpdateAction.Downgrade, desired, sha, url, msiName, "pin_downgrade");
        }

        return UpdatePlan.None("same");
    }

    private static string? FirstSemVer(params string?[] values)
    {
        foreach (var v in values)
        {
            if (VersionUtil.TryParseSemVer(v, out var ver))
            {
                return $"{ver.Major}.{ver.Minor}.{ver.Build}";
            }
        }

        return null;
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
    /// <summary>Канон 0.10.</summary>
    public string? TargetVersion { get; init; }
    /// <summary>Legacy / mirrored version field.</summary>
    public string? Version { get; init; }
    public string? Sha256 { get; init; }
    public string? Url { get; init; }
    public string? MsiName { get; init; }
    public string? Action { get; init; }
    public string? Desired { get; init; }
    public string? Reason { get; init; }

    public static UpdateCheckResponse FromJson(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        return new UpdateCheckResponse
        {
            UpdateAvailable = root.TryGetProperty("update_available", out var ua)
                              && ua.ValueKind is JsonValueKind.True or JsonValueKind.False
                              && ua.GetBoolean(),
            TargetVersion = GetString(root, "target_version"),
            Version = GetString(root, "version"),
            Sha256 = GetString(root, "sha256"),
            Url = GetString(root, "url"),
            MsiName = GetString(root, "msi_name"),
            Action = GetString(root, "action"),
            Desired = GetString(root, "desired") ?? GetString(root, "update_target"),
            Reason = GetString(root, "reason")
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
