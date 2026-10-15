using System.Diagnostics;
using System.Text.Json;

namespace BadAgent;

/// <summary>
/// Проверяет на сервере bAD более новый MSI, сверяет sha256, запускает silent msiexec
/// и выходит, чтобы WiX ServiceControl / MajorUpgrade заменил файлы.
/// Агенты не ходят на GitHub напрямую.
/// </summary>
public sealed class AgentUpdater
{
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

        if (!check.UpdateAvailable
            || string.IsNullOrWhiteSpace(check.Version)
            || string.IsNullOrWhiteSpace(check.Sha256)
            || string.IsNullOrWhiteSpace(check.Url))
        {
            _logger.LogDebug(
                "No update available (current={Current}, server={Server})",
                _agentVersion,
                check.Version ?? "(none)");
            return false;
        }

        if (!VersionUtil.IsNewer(check.Version, _agentVersion))
        {
            _logger.LogInformation(
                "Server reported update {Server} but it is not newer than local {Local}; skipping",
                check.Version,
                _agentVersion);
            return false;
        }

        if (!OperatingSystem.IsWindows())
        {
            _logger.LogWarning(
                "Update {Version} available but msiexec apply is Windows-only; skipping",
                check.Version);
            return false;
        }

        var tempDir = Path.Combine(Path.GetTempPath(), "bad-agent-update", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);
        // SEC-002: basename only, no '..', path must stay inside tempDir.
        string msiPath;
        try
        {
            msiPath = UpdatePathUtil.ResolveSafeMsiPath(tempDir, check.MsiName, check.Version);
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
                "Downloading agent update {Version} from server",
                check.Version);
            await client.DownloadUpdateMsiAsync(config.ApiKey!, check.Url!, msiPath, ct);

            if (!VersionUtil.VerifySha256File(msiPath, check.Sha256!))
            {
                _logger.LogError(
                    "Update MSI sha256 mismatch for {Version}; refusing to install",
                    check.Version);
                WindowsEventLog.WriteError(
                    $"bAD: sha256 MSI обновления {check.Version} не совпал — установка отменена.");
                return false;
            }

            var logPath = Path.Combine(ConfigStore.LogsDir, $"msiexec-upgrade-{check.Version}.log");
            // Отвязанный msiexec: WiX ServiceControl останавливает службу, меняет файлы, перезапускает.
            // Выходим сразу, чтобы снять file locks.
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
                "Starting silent msiexec upgrade to {Version}; agent will exit for file replace",
                check.Version);
            if (Process.Start(psi) is null)
            {
                _logger.LogError("Failed to start msiexec");
                return false;
            }

            // Короткая пауза, чтобы msiexec успел стартовать; затем выход (далее — остановка службы).
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
            _logger.LogError(ex, "Failed to download/apply update {Version}", check.Version);
            WindowsEventLog.WriteError($"bAD: сбой загрузки/установки обновления {check.Version}", ex);
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
}

public sealed class UpdateCheckResponse
{
    public bool UpdateAvailable { get; init; }
    public string? Version { get; init; }
    public string? Sha256 { get; init; }
    public string? Url { get; init; }
    public string? MsiName { get; init; }

    public static UpdateCheckResponse FromJson(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        return new UpdateCheckResponse
        {
            UpdateAvailable = root.TryGetProperty("update_available", out var ua) && ua.GetBoolean(),
            Version = root.TryGetProperty("version", out var v) && v.ValueKind == JsonValueKind.String
                ? v.GetString()
                : null,
            Sha256 = root.TryGetProperty("sha256", out var s) && s.ValueKind == JsonValueKind.String
                ? s.GetString()
                : null,
            Url = root.TryGetProperty("url", out var u) && u.ValueKind == JsonValueKind.String
                ? u.GetString()
                : null,
            MsiName = root.TryGetProperty("msi_name", out var m) && m.ValueKind == JsonValueKind.String
                ? m.GetString()
                : null
        };
    }
}
