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
                var uuid = WmiHelper.QueryFirst("SELECT UUID FROM Win32_ComputerSystemProduct", "UUID");
                if (!string.IsNullOrWhiteSpace(uuid) &&
                    !uuid.Equals("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", StringComparison.OrdinalIgnoreCase))
                {
                    return uuid.Trim();
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
