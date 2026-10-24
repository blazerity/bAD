using System.Diagnostics;
using System.Runtime.Versioning;
using Microsoft.Win32;

namespace BadAgent;

/// <summary>
/// Снятие MSI по команде панели (<c>actions.uninstall</c> в heartbeat).
/// </summary>
public static class AgentUninstaller
{
    public const string MsiDisplayName = "blazerity Asset Discovery Agent";
    public const string MsiUpgradeCode = "BADA0001-BADA-4B01-8BAD-00BADA000001";

    /// <summary>
    /// Запускает <c>msiexec /x</c> без ожидания. Возвращает false, если ProductCode не найден или старт не удался.
    /// </summary>
    public static bool TryStartSilentUninstall(ILogger logger)
    {
        if (!OperatingSystem.IsWindows())
        {
            logger.LogWarning("Снятие агента: только Windows");
            return false;
        }

        var productCode = TryFindInstalledProductCode();
        if (productCode is null)
        {
            logger.LogWarning(
                "Снятие агента: ProductCode MSI не найден (DisplayName «{DisplayName}» / UpgradeCode {UpgradeCode})",
                MsiDisplayName,
                MsiUpgradeCode);
            WindowsEventLog.WriteWarning(
                "bAD: команда снятия — установка MSI не найдена в реестре, служба не останавливается");
            return false;
        }

        var msiexec = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.System),
            "msiexec.exe");
        if (!File.Exists(msiexec))
        {
            logger.LogError("Снятие агента: msiexec.exe не найден");
            WindowsEventLog.WriteError("bAD: команда снятия — msiexec.exe не найден");
            return false;
        }

        var args = $"/x {productCode} /qn /norestart";
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = msiexec,
                Arguments = args,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            if (Process.Start(psi) is null)
            {
                logger.LogError("Снятие агента: не удалось запустить msiexec");
                return false;
            }

            logger.LogInformation("Снятие агента: запущен msiexec {Args}", args);
            WindowsEventLog.WriteInfo($"bAD: запущено снятие MSI (ProductCode {productCode})");
            return true;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Снятие агента: ошибка запуска msiexec");
            WindowsEventLog.WriteError("bAD: ошибка запуска msiexec для снятия", ex);
            return false;
        }
    }

    [SupportedOSPlatform("windows")]
    public static string? TryFindInstalledProductCode()
    {
        var fromName = ScanUninstallByDisplayName(RegistryView.Registry64)
                       ?? ScanUninstallByDisplayName(RegistryView.Registry32);
        if (fromName is not null)
        {
            return fromName;
        }

        return TryFindProductCodeByUpgradeCode();
    }

    [SupportedOSPlatform("windows")]
    private static string? ScanUninstallByDisplayName(RegistryView view)
    {
        using var baseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view);
        using var uninstall = baseKey.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall");
        if (uninstall is null)
        {
            return null;
        }

        foreach (var subName in uninstall.GetSubKeyNames())
        {
            using var sub = uninstall.OpenSubKey(subName);
            if (sub is null)
            {
                continue;
            }

            var displayName = sub.GetValue("DisplayName") as string;
            if (!string.Equals(displayName?.Trim(), MsiDisplayName, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var code = NormalizeProductCode(subName);
            if (code is not null)
            {
                return code;
            }
        }

        return null;
    }

    [SupportedOSPlatform("windows")]
    private static string? TryFindProductCodeByUpgradeCode()
    {
        var upgradePath = $@"SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UpgradeCodes\{{{MsiUpgradeCode}}}";
        using var upgradeKey = Registry.LocalMachine.OpenSubKey(upgradePath);
        if (upgradeKey is null)
        {
            return null;
        }

        foreach (var compressed in upgradeKey.GetValueNames())
        {
            var code = DecompressMsiProductCode(compressed);
            if (code is not null)
            {
                return code;
            }
        }

        return null;
    }

    /// <summary>Ключ Uninstall — ProductCode; для msiexec — в фигурных скобках.</summary>
    private static string? NormalizeProductCode(string subKeyName)
    {
        var trimmed = subKeyName.Trim();
        if (trimmed.StartsWith("{", StringComparison.Ordinal))
        {
            return Guid.TryParse(trimmed.Trim('{', '}'), out _) ? trimmed : null;
        }

        return Guid.TryParse(trimmed, out var g) ? $"{{{g}}}" : null;
    }

    /// <summary>Имя значения под UpgradeCodes → ProductCode GUID (формат Windows Installer).</summary>
    private static string? DecompressMsiProductCode(string compressed)
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
}
