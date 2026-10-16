namespace BadAgent;

public static class DeviceIdentity
{
    public static string ResolveDeviceId()
    {
        if (OperatingSystem.IsWindows())
        {
            try
            {
                using var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(
                    @"SOFTWARE\Microsoft\Cryptography");
                var guid = key?.GetValue("MachineGuid") as string;
                if (!string.IsNullOrWhiteSpace(guid))
                {
                    return guid.Trim();
                }
            }
            catch
            {
                // дальше
            }

            try
            {
                // Fallback id только если нет MachineGuid. Placeholder all-F / all-zero — отсев.
                var uuid = HardwareMaps.CleanSmbiosUuid(
                    WmiHelper.QueryFirst("SELECT UUID FROM Win32_ComputerSystemProduct", "UUID"));
                if (uuid is not null)
                {
                    return uuid;
                }
            }
            catch
            {
                // дальше
            }
        }

        // Non-Windows / fallback для unit-тестов и Linux CI
        var host = Environment.MachineName;
        return $"fallback-{host}-{Environment.UserName}".ToLowerInvariant();
    }
}
