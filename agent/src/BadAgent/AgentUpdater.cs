using System.Diagnostics;
using System.Globalization;
using System.Runtime.Versioning;
using System.ServiceProcess;
using System.Text.Json;
using Microsoft.Win32;

namespace BadAgent;

/// <summary>
/// Проверяет на сервере bAD целевой архив (upgrade / downgrade / pin / latest),
/// сверяет archive_sha256, расшифровывает и заменяет файлы в bin.
/// Gate (0.10): server update_available + target≠current + sha256 — не только IsNewer.
/// Download — только same-origin (SEC-009).
/// </summary>
public sealed class AgentUpdater
{
    /// <summary>Не повторять ту же целевую версию чаще этого интервала.</summary>
    public static readonly TimeSpan PendingCooldown = TimeSpan.FromHours(2);

    private readonly ILogger _logger;
    private readonly string _agentVersion;

    public AgentUpdater(ILogger logger, string agentVersion)
    {
        _logger = logger;
        _agentVersion = agentVersion;
    }

    /// <summary>
    /// Удаляет скачанные MSI в %TEMP%\bADagent-update. Занятый файл пропускается.
    /// </summary>
    public static void DeleteStaleDownloads(ILogger logger)
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        var root = Path.Combine(Path.GetTempPath(), "bADagent-update");
        if (!Directory.Exists(root))
        {
            return;
        }

        var removed = 0;
        var cutoff = DateTime.UtcNow.AddHours(-1);
        foreach (var path in Directory.EnumerateFileSystemEntries(root))
        {
            try
            {
                var written = Directory.Exists(path)
                    ? Directory.GetLastWriteTimeUtc(path)
                    : File.GetLastWriteTimeUtc(path);
                if (written > cutoff)
                {
                    continue;
                }

                if (Directory.Exists(path))
                {
                    Directory.Delete(path, recursive: true);
                }
                else
                {
                    File.Delete(path);
                }

                removed++;
            }
            catch (Exception ex)
            {
                logger.LogDebug(ex, "Skip locked update temp {Path}", path);
            }
        }

        if (removed > 0)
        {
            logger.LogInformation("Removed {Count} stale agent update file(s) from {Dir}", removed, root);
        }
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
                "Pending update for {Target} still within cooldown; not looping",
                plan.TargetVersion);
            return false;
        }

        if (!OperatingSystem.IsWindows())
        {
            _logger.LogWarning(
                "Version change {Action} to {Version} available but file replace is Windows-only; skipping",
                plan.Action,
                plan.TargetVersion);
            return false;
        }

        DeleteStaleDownloads(_logger);
        var tempDir = Path.Combine(Path.GetTempPath(), "bADagent-update", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);
        string msiPath;
        try
        {
            msiPath = UpdatePathUtil.ResolveSafeMsiPath(tempDir, null, plan.TargetVersion);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Refusing unsafe archive name from update check");
            WindowsEventLog.WriteError("bAD: отказ — небезопасное имя архива в ответе update/check", ex);
            return false;
        }

        var expectedSha = string.IsNullOrWhiteSpace(check.ArchiveSha256) ? plan.Sha256 : check.ArchiveSha256;
        if (string.IsNullOrWhiteSpace(check.ArchivePassword) || string.IsNullOrWhiteSpace(expectedSha))
        {
            _logger.LogError("Update archive is missing sha256 or password for {Version}", plan.TargetVersion);
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

            if (!VersionUtil.VerifySha256File(msiPath, expectedSha))
            {
                _logger.LogError(
                    "Update archive sha256 mismatch for {Version}; refusing to install",
                    plan.TargetVersion);
                WindowsEventLog.WriteError(
                    $"bAD: sha256 архива {plan.TargetVersion} не совпал — установка отменена.");
                return false;
            }

            var stage = Path.Combine(tempDir, "stage");
            AgentArchive.DecryptToDirectory(msiPath, check.ArchivePassword, stage);
            ReplaceBin(stage);
            SetProgramsVersion(CoreVersion(plan.TargetVersion!));
            MarkPending(config, plan.TargetVersion!);
            RestartServiceHidden();
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
        var sha = string.IsNullOrWhiteSpace(check.ArchiveSha256) ? check.Sha256 : check.ArchiveSha256;
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
                url = $"/v1/agent/update/archive?version={Uri.EscapeDataString(serverTarget)}";
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

            url = string.IsNullOrWhiteSpace(url) ? "/v1/agent/update/archive" : url;
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
            ? $"/v1/agent/update/archive?version={Uri.EscapeDataString(desired)}"
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

    private const string BinDir = @"C:\Program Files\blazerity\bADagent\bin";
    private const string LinkExe = @"C:\Program Files\blazerity\bADagent\bADagent.exe";

    private static string CoreVersion(string version)
    {
        var cut = version.IndexOfAny(['-', '+']);
        if (cut >= 0)
        {
            version = version[..cut];
        }

        var parts = version.Split('.');
        if (parts.Length >= 3
            && int.TryParse(parts[0], out var major)
            && int.TryParse(parts[1], out var minor)
            && int.TryParse(parts[2], out var patch))
        {
            return $"{major}.{minor}.{patch}";
        }

        return version;
    }

    private static void ReplaceBin(string stage)
    {
        Directory.CreateDirectory(BinDir);
        var exe = Path.Combine(BinDir, "BadAgent.exe");
        var old = Path.Combine(BinDir, "BadAgent.exe.old");
        if (File.Exists(exe))
        {
            try
            {
                if (File.Exists(old))
                {
                    File.Delete(old);
                }
            }
            catch
            {
                // занятый предыдущий файл не мешает переименованию текущего
            }

            File.Move(exe, old, overwrite: true);
        }

        var root = Path.GetFullPath(BinDir);
        if (!root.EndsWith(Path.DirectorySeparatorChar))
        {
            root += Path.DirectorySeparatorChar;
        }

        foreach (var file in Directory.EnumerateFiles(stage, "*", SearchOption.AllDirectories))
        {
            var rel = Path.GetRelativePath(stage, file);
            if (rel.Contains("..", StringComparison.Ordinal))
            {
                continue;
            }

            if (string.Equals(Path.GetFileName(file), "bADagent.exe", StringComparison.Ordinal))
            {
                continue;
            }

            var dest = Path.GetFullPath(Path.Combine(BinDir, rel));
            if (!dest.StartsWith(root, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var parent = Path.GetDirectoryName(dest);
            if (!string.IsNullOrEmpty(parent))
            {
                Directory.CreateDirectory(parent);
            }

            File.Copy(file, dest, overwrite: true);
        }
    }

    [SupportedOSPlatform("windows")]
    private static void SetProgramsVersion(string displayVersion)
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        var product = FindProductCode();
        if (product is null)
        {
            return;
        }

        using var key = Registry.LocalMachine.OpenSubKey(
            $@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{product}",
            writable: true);
        key?.SetValue("DisplayName", "bADagent");
        key?.SetValue("DisplayVersion", displayVersion);
    }

    [SupportedOSPlatform("windows")]
    private static string? FindProductCode()
    {
        using var upgrade = Registry.LocalMachine.OpenSubKey(
            @"SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UpgradeCodes\{BADA0001-BADA-4B01-8BAD-00BADA000001}");
        if (upgrade is null)
        {
            return null;
        }

        foreach (var compressed in upgrade.GetValueNames())
        {
            var code = DecompressProductCode(compressed);
            if (code is not null)
            {
                return code;
            }
        }

        return null;
    }

    private static string? DecompressProductCode(string compressed)
    {
        if (string.IsNullOrEmpty(compressed) || compressed.Length != 25)
        {
            return null;
        }

        Span<char> buffer = stackalloc char[38];
        buffer[0] = '{';
        buffer[9] = '-';
        buffer[14] = '-';
        buffer[19] = '-';
        buffer[24] = '-';
        buffer[37] = '}';
        for (var i = 0; i < 20; i++)
        {
            var offset = i switch
            {
                < 8 => i + 1,
                < 12 => i + 2,
                < 16 => i + 3,
                _ => i + 4
            };
            buffer[offset] = compressed[19 - i];
        }

        for (var i = 20; i < 25; i++)
        {
            buffer[i + 9] = compressed[i];
        }

        var guidString = new string(buffer);
        return Guid.TryParse(guidString.Trim('{', '}'), out _) ? guidString : null;
    }

    private void RestartServiceHidden()
    {
        if (File.Exists(LinkExe))
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = LinkExe,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
            });
            return;
        }

        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        using var sc = new ServiceController(ServiceCli.ServiceName);
        sc.Refresh();
        if (sc.Status is not ServiceControllerStatus.Stopped and not ServiceControllerStatus.StopPending)
        {
            sc.Stop();
        }
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
    public string? ArchiveSha256 { get; init; }
    public string? ArchivePassword { get; init; }
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
            ArchiveSha256 = GetString(root, "archive_sha256"),
            ArchivePassword = GetString(root, "archive_password"),
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
