namespace BadAgent;

/// <summary>Номер, который служба забыла. Снова из MachineGuid его не пишем.</summary>
internal static class RetiredDevice
{
    public const string PlaceholderId = "6f0bc3d6-87c4-4608-9c01-e6e7c7d2e6c5";

    private static string Path => System.IO.Path.Combine(ConfigStore.ProgramDataDir, "retired_device_id");

    public static void Remember(string? deviceId)
    {
        if (string.IsNullOrWhiteSpace(deviceId))
        {
            return;
        }

        var id = deviceId.Trim();
        var known = Read();
        if (known.Any(item => string.Equals(item, id, StringComparison.OrdinalIgnoreCase)))
        {
            return;
        }

        known.Add(id);
        Directory.CreateDirectory(ConfigStore.ProgramDataDir);
        File.WriteAllLines(Path, known);
    }

    public static bool Blocks(string? deviceId)
    {
        if (string.IsNullOrWhiteSpace(deviceId))
        {
            return false;
        }

        var id = deviceId.Trim();
        return Read().Any(item => string.Equals(item, id, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>Пустой device_id заполняется, только если это не забытый номер.</summary>
    public static bool TryAssign(AgentConfig config)
    {
        if (!string.IsNullOrWhiteSpace(config.DeviceId))
        {
            return false;
        }

        var resolved = DeviceIdentity.ResolveDeviceId();
        if (string.IsNullOrWhiteSpace(resolved) || Blocks(resolved))
        {
            return false;
        }

        config.DeviceId = resolved;
        return true;
    }

    private static List<string> Read()
    {
        try
        {
            if (!File.Exists(Path))
            {
                return new List<string>();
            }

            return File.ReadAllLines(Path)
                .Select(line => line.Trim())
                .Where(line => line.Length > 0)
                .ToList();
        }
        catch (IOException)
        {
            return new List<string>();
        }
        catch (UnauthorizedAccessException)
        {
            return new List<string>();
        }
    }
}
