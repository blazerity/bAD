using System.Globalization;
using System.Text;

namespace BadAgent;

/// <summary>
/// ASCII inventory-отчёт (рамки/колонки, без emoji). Подписи на русском.
/// Разделы в логике Speccy: ОС → CPU → MB → Memory → GPU → Storage → …
/// </summary>
public static class AsciiReportWriter
{
    private const int Width = 72;
    private const int SoftwarePreviewCount = 20;

    public static string Write(InventorySnapshot snap, AgentConfig? config = null)
    {
        var sb = new StringBuilder();
        var hostname = snap.Host?.Hostname ?? "(неизвестно)";
        var title = $" bAD inventory — {hostname} ";

        sb.AppendLine(BoxTop(title));
        Row(sb, "device_id", snap.DeviceId);
        Row(sb, "Собрано", snap.CollectedAt);
        Row(sb, "Агент", snap.AgentVersion);
        Row(sb, "Schema", snap.SchemaVersion.ToString(CultureInfo.InvariantCulture));
        if (config is not null && !string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            Row(sb, "server_url", config.ServerUrl + " (локальный отчёт; сервер не вызывался)");
        }
        else
        {
            Row(sb, "server_url", "(не задан — только локально)");
        }

        // --- Speccy: Operating System ---
        sb.AppendLine(BoxMid("Операционная система"));
        Row(sb, "Имя узла", snap.Host?.Hostname);
        Row(sb, "Домен", snap.Host?.Domain);
        Row(sb, "AD OU", snap.Host?.AdOu);
        Row(sb, "AD DN", snap.Host?.AdDistinguishedName);
        Row(sb, "ОС", ReportFormat.FormatOs(snap.Host?.Os));

        if (snap.Hardware is null)
        {
            sb.AppendLine(BoxMid("Оборудование"));
            Row(sb, "Статус", "пропущено (collect_hardware=false)");
        }
        else
        {
            var hw = snap.Hardware;

            // --- CPU ---
            sb.AppendLine(BoxMid("Процессор"));
            Row(sb, "Имя", hw.Cpu?.Name);
            Row(sb, "Ядра", ReportFormat.FormatCores(hw.Cpu));

            // --- Motherboard ---
            sb.AppendLine(BoxMid("Материнская плата"));
            Row(sb, "Производитель", hw.Manufacturer);
            Row(sb, "Модель", hw.Model);
            Row(sb, "Серийный №", hw.SerialNumber);
            Row(sb, "BIOS", hw.BiosVersion);
            Row(sb, "Произв. BIOS", hw.BiosManufacturer);
            Row(sb, "Дата BIOS", hw.BiosReleaseDate);

            // --- Memory ---
            sb.AppendLine(BoxMid("Память"));
            Row(sb, "ОЗУ", ReportFormat.FormatBytes(hw.RamBytes));
            Row(sb, "Тип ОЗУ", hw.RamMemoryType);
            if (hw.RamModules is { Count: > 0 })
            {
                Row(sb, "Планки", hw.RamModules.Count.ToString(CultureInfo.InvariantCulture));
                foreach (var m in hw.RamModules)
                {
                    var part = m.PartNumber ?? m.Manufacturer ?? "module";
                    var type = string.IsNullOrWhiteSpace(m.MemoryType) ? "" : $" {m.MemoryType}";
                    var speed = m.SpeedMhz is null ? "" : $" {m.SpeedMhz} MHz";
                    var channel = string.IsNullOrWhiteSpace(m.Channel) ? "" : $" {m.Channel}";
                    Row(
                        sb,
                        Trunc(part, 28),
                        $"{ReportFormat.FormatBytes(m.CapacityBytes)}{type}{speed}{channel}".Trim());
                }
            }

            // --- GPU ---
            sb.AppendLine(BoxMid("Видео"));
            if (hw.Gpus is { Count: > 0 })
            {
                foreach (var g in hw.Gpus)
                {
                    var vendor = string.IsNullOrWhiteSpace(g.Vendor) ? "" : $"  ({g.Vendor})";
                    var vram = g.AdapterRamBytes is null
                        ? ""
                        : $"  {ReportFormat.FormatBytes(g.AdapterRamBytes)}";
                    Row(sb, Trunc(g.Name ?? "GPU", 28), (vendor + vram).Trim());
                }
            }
            else
            {
                Row(sb, "GPU", "(нет)");
            }

            // --- Storage ---
            sb.AppendLine(BoxMid("Накопители"));
            if (hw.Disks is { Count: > 0 })
            {
                foreach (var d in hw.Disks)
                {
                    Row(sb, Trunc(d.Model ?? "disk", 28), $"{ReportFormat.FormatBytes(d.SizeBytes)}  {d.MediaType}");
                }
            }
            else
            {
                Row(sb, "Диски", "(нет)");
            }

            if (hw.Volumes is { Count: > 0 })
            {
                Col(sb, "Том", "Размер", "Свободно");
                foreach (var v in hw.Volumes)
                {
                    Col(sb, v.Letter ?? "?", ReportFormat.FormatBytes(v.SizeBytes), ReportFormat.FormatBytes(v.FreeBytes));
                }
            }

            // --- Displays ---
            if (hw.Monitors is { Count: > 0 })
            {
                sb.AppendLine(BoxMid("Мониторы"));
                foreach (var m in hw.Monitors)
                {
                    var res = m.Width is null || m.Height is null ? "" : $" {m.Width}x{m.Height}";
                    Row(sb, Trunc(m.Name ?? m.Manufacturer ?? "monitor", 28),
                        $"{m.SerialNumber ?? "-"}{res}".Trim());
                }
            }

            // --- Battery ---
            if (hw.Battery is not null)
            {
                sb.AppendLine(BoxMid("Батарея"));
                var bat = hw.Battery;
                Row(sb, "Заряд", bat.ChargePercent is null ? null : $"{bat.ChargePercent}%");
                Row(sb, "Статус", bat.Status);
                Row(sb, "Осталось", bat.EstimatedRuntimeMinutes is null
                    ? null
                    : $"{bat.EstimatedRuntimeMinutes} мин");
            }
        }

        sb.AppendLine(BoxMid("Сеть"));
        if (snap.Network?.Nics is { Count: > 0 })
        {
            foreach (var nic in snap.Network.Nics)
            {
                Row(sb, Trunc(nic.Name ?? "NIC", 28), nic.Mac);
                var ipv4 = nic.Ipv4 is { Count: > 0 } ? string.Join(", ", nic.Ipv4) : "-";
                Row(sb, "  IPv4", ipv4);
            }
        }
        else
        {
            Row(sb, "NIC", "(нет)");
        }

        if (snap.Users is not null)
        {
            sb.AppendLine(BoxMid("Пользователи"));
            Row(sb, "Посл. интерак.", snap.Users.LastInteractive);
            var logged = snap.Users.LoggedOn is { Count: > 0 }
                ? string.Join(", ", snap.Users.LoggedOn)
                : "-";
            Row(sb, "В системе", logged);
        }
        else
        {
            sb.AppendLine(BoxMid("Пользователи"));
            Row(sb, "Статус", "пропущено (collect_users=false)");
        }

        if (snap.Software is not null)
        {
            sb.AppendLine(BoxMid("ПО"));
            var programs = snap.Software.Programs;
            if (programs is null)
            {
                Row(sb, "Программы", "(недоступно на платформе)");
            }
            else if (programs.Count == 0)
            {
                Row(sb, "Программы", "(пусто)");
            }
            else
            {
                Row(sb, "Программы", $"{programs.Count} (до {SoftwarePreviewCount})");
                foreach (var p in programs.Take(SoftwarePreviewCount))
                {
                    Row(sb, Trunc(p.Name ?? "?", 36), p.Version ?? "-");
                }
            }
        }
        else
        {
            sb.AppendLine(BoxMid("ПО"));
            Row(sb, "Статус", "пропущено (collect_software=false)");
        }

        if (snap.Minidumps is not null)
        {
            sb.AppendLine(BoxMid("Минидампы BSOD"));
            Row(sb, "Файлов", snap.Minidumps.Count.ToString(CultureInfo.InvariantCulture));
            Row(sb, "Memory.dmp", snap.Minidumps.MemoryDmpPresent ? "есть" : "нет");
            Row(sb, "Путь Memory.dmp", snap.Minidumps.MemoryDmpPath);
            Row(sb, "Изменён", snap.Minidumps.MemoryDmpModifiedAt);
            if (snap.Minidumps.Files is { Count: > 0 })
            {
                foreach (var f in snap.Minidumps.Files.Take(5))
                {
                    Row(sb, Trunc(f.Name ?? "?", 28), f.ModifiedAt ?? "-");
                }
            }
        }

        if (snap.CollectorErrors.Count > 0)
        {
            sb.AppendLine(BoxMid("Ошибки сбора"));
            foreach (var err in snap.CollectorErrors)
            {
                Row(sb, err.Section, Trunc(err.Error, 48));
            }
        }

        sb.AppendLine(BoxBottom());
        return sb.ToString();
    }

    private static void Row(StringBuilder sb, string key, string? value)
    {
        var v = string.IsNullOrWhiteSpace(value) ? "-" : value;
        var line = $"│ {Pad(key, 18)} {Trunc(v, Width - 24)}";
        sb.Append(line);
        sb.Append(' ', Math.Max(0, Width - 1 - line.Length));
        sb.AppendLine("│");
    }

    private static void Col(StringBuilder sb, string a, string b, string c)
    {
        var line = $"│ {Pad(a, 10)} {Pad(b, 14)} {Pad(c, 14)}";
        sb.Append(line);
        sb.Append(' ', Math.Max(0, Width - 1 - line.Length));
        sb.AppendLine("│");
    }

    private static string BoxTop(string title)
    {
        title = Trunc(title, Width - 4);
        var side = Width - 2 - title.Length;
        var left = side / 2;
        var right = side - left;
        return "┌" + new string('─', left) + title + new string('─', right) + "┐";
    }

    private static string BoxMid(string title)
    {
        title = Trunc(" " + title + " ", Width - 4);
        var side = Width - 2 - title.Length;
        var left = Math.Max(1, side / 2);
        var right = Math.Max(1, side - left);
        while (2 + left + title.Length + right > Width)
        {
            if (right > left) right--;
            else left--;
        }

        return "├" + new string('─', left) + title + new string('─', right) + "┤";
    }

    private static string BoxBottom() => "└" + new string('─', Width - 2) + "┘";

    private static string Pad(string s, int w) => s.PadRight(w);

    private static string Trunc(string s, int max)
    {
        if (string.IsNullOrEmpty(s) || s.Length <= max) return s;
        return max <= 1 ? s[..1] : s[..(max - 1)] + "…";
    }
}
