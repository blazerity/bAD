namespace BadAgent;

/// <summary>Забытый номер. Очередь его больше не шлёт. Файл только retired_bad_id.</summary>
internal static class RetiredDevice
{
    private static string Path => System.IO.Path.Combine(ConfigStore.ProgramDataDir, "retired_bad_id");

    public static void Remember(string? badId)
    {
        if (string.IsNullOrWhiteSpace(badId))
        {
            return;
        }

        var id = badId.Trim();
        var known = Read();
        if (known.Any(item => string.Equals(item, id, StringComparison.OrdinalIgnoreCase)))
        {
            return;
        }

        known.Add(id);
        Directory.CreateDirectory(ConfigStore.ProgramDataDir);
        File.WriteAllLines(Path, known);
    }

    public static bool Blocks(string? badId)
    {
        if (string.IsNullOrWhiteSpace(badId))
        {
            return false;
        }

        var id = badId.Trim();
        return Read().Any(item => string.Equals(item, id, StringComparison.OrdinalIgnoreCase));
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
