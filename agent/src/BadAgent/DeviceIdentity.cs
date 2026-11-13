namespace BadAgent;

/// <summary>MachineGuid для заявки. Номер машины отсюда не берётся.</summary>
public static class DeviceIdentity
{
    public static string ReadMachineGuid()
    {
        if (!OperatingSystem.IsWindows())
        {
            return "";
        }

        try
        {
            using var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(
                @"SOFTWARE\Microsoft\Cryptography");
            var guid = key?.GetValue("MachineGuid") as string;
            if (string.IsNullOrWhiteSpace(guid))
            {
                return "";
            }

            return guid.Trim();
        }
        catch
        {
            return "";
        }
    }
}
