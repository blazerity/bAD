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
    /// <summary>При меньшей ширине рамка даёт артефакты — печатаем plain.</summary>
    private const int MinWidthForBox = 40;
    private const int SoftwarePreviewCount = 20;

    public static string Write(InventorySnapshot snap, AgentConfig? config = null)
    {
        var sb = new StringBuilder();
        var useBox = Width >= MinWidthForBox;
        var hostname = snap.Host?.Hostname ?? "(неизвестно)";
        var title = $" bAD inventory — {hostname} ";

        if (useBox)
        {
            sb.AppendLine(BoxTop(title));
            Row(sb, useBox, "device_id", snap.DeviceId);
            Row(sb, useBox, "Собрано", TimeFormat.FormatForReport(snap.CollectedAt));
            Row(sb, useBox, "Агент", snap.AgentVersion);
            Row(sb, useBox, "Schema", snap.SchemaVersion.ToString(CultureInfo.InvariantCulture));
            if (config is not null && !string.IsNullOrWhiteSpace(config.ServerUrl))
            {
                var urlNote = config.ServerUrl + " (локальный отчёт; сервер не вызывался)";
                Row(sb, useBox, "server_url", urlNote);
                if (config.ServerUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
                {
                    Row(sb, useBox, "предупреждение",
                        "http:// — служба агента отклонит; нужен https:// (BAD_ALLOW_HTTP=1 только lab)");
                }
            }
            else
            {
                Row(sb, useBox, "server_url", "(не задан — только локально)");
            }
        }
        else
        {
            sb.AppendLine(title.Trim());
            PlainRow(sb, "device_id", snap.DeviceId);
            PlainRow(sb, "Собрано", TimeFormat.FormatForReport(snap.CollectedAt));
            PlainRow(sb, "Агент", snap.AgentVersion);
            PlainRow(sb, "Schema", snap.SchemaVersion.ToString(CultureInfo.InvariantCulture));
            if (config is not null && !string.IsNullOrWhiteSpace(config.ServerUrl))
            {
                var urlNote = config.ServerUrl + " (локальный отчёт; сервер не вызывался)";
                PlainRow(sb, "server_url", urlNote);
                if (config.ServerUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
                {
                    PlainRow(sb, "предупреждение",
                        "http:// — служба агента отклонит; нужен https:// (BAD_ALLOW_HTTP=1 только lab)");
                }
            }
            else
            {
                PlainRow(sb, "server_url", "(не задан — только локально)");
            }
        }

        // --- Speccy: Operating System ---
        SectionHeader(sb, useBox, "Операционная система");
        Row(sb, useBox, "Имя узла", snap.Host?.Hostname);
        Row(sb, useBox, "Домен", snap.Host?.Domain);
        Row(sb, useBox, "AD OU", snap.Host?.AdOu);
        Row(sb, useBox, "AD DN", snap.Host?.AdDistinguishedName);
        Row(sb, useBox, "ОС", ReportFormat.FormatOs(snap.Host?.Os));
        Row(sb, useBox, "Последняя загрузка", TimeFormat.FormatForReport(snap.Host?.LastBootAt));
        Row(sb, useBox, "Часовой пояс", snap.Host?.Timezone);
        if (snap.Host?.PendingReboot is bool pending)
        {
            Row(sb, useBox, "Ожидает перезагрузку", pending ? "да" : "нет");
        }

        if (snap.Hardware is null)
        {
            SectionHeader(sb, useBox, "Оборудование");
            Row(sb, useBox, "Статус", "пропущено (collect_hardware=false)");
        }
        else
        {
            var hw = snap.Hardware;

            // --- CPU ---
            SectionHeader(sb, useBox, "Процессор");
            Row(sb, useBox, "Имя", hw.Cpu?.Name);
            Row(sb, useBox, "Ядра", ReportFormat.FormatCores(hw.Cpu));

            // --- Motherboard ---
            SectionHeader(sb, useBox, "Материнская плата");
            Row(sb, useBox, "Производитель", hw.Manufacturer);
            Row(sb, useBox, "Модель", hw.Model);
            Row(sb, useBox, "Серийный №", hw.SerialNumber);
            Row(sb, useBox, "BIOS serial", hw.BiosSerial);
            Row(sb, useBox, "IdentifyingNumber", hw.IdentifyingNumber);
            Row(sb, useBox, "Baseboard serial", hw.BaseboardSerial);
            Row(sb, useBox, "SMBIOS UUID", hw.SmbiosUuid);
            Row(sb, useBox, "Корпус", hw.ChassisType);
            Row(sb, useBox, "BIOS", hw.BiosVersion);
            Row(sb, useBox, "Произв. BIOS", hw.BiosManufacturer);
            Row(sb, useBox, "Дата BIOS", TimeFormat.FormatForReport(hw.BiosReleaseDate));

            // --- Memory ---
            SectionHeader(sb, useBox, "Память");
            Row(sb, useBox, "ОЗУ", ReportFormat.FormatBytes(hw.RamBytes));
            Row(sb, useBox, "Тип ОЗУ", hw.RamMemoryType);
            if (hw.RamModules is { Count: > 0 })
            {
                Row(sb, useBox, "Планки", hw.RamModules.Count.ToString(CultureInfo.InvariantCulture));
                foreach (var m in hw.RamModules)
                {
                    var part = m.PartNumber ?? m.Manufacturer ?? "module";
                    var type = string.IsNullOrWhiteSpace(m.MemoryType) ? "" : $" {m.MemoryType}";
                    var speed = m.SpeedMhz is null ? "" : $" {m.SpeedMhz} MHz";
                    var channel = string.IsNullOrWhiteSpace(m.Channel) ? "" : $" {m.Channel}";
                    Row(
                        sb,
                        useBox,
                        part,
                        $"{ReportFormat.FormatBytes(m.CapacityBytes)}{type}{speed}{channel}".Trim());
                }
            }

            // --- GPU ---
            SectionHeader(sb, useBox, "Видео");
            if (hw.Gpus is { Count: > 0 })
            {
                foreach (var g in hw.Gpus)
                {
                    var vendor = string.IsNullOrWhiteSpace(g.Vendor) ? "" : $"  ({g.Vendor})";
                    var vram = g.AdapterRamBytes is null
                        ? ""
                        : $"  {ReportFormat.FormatBytes(g.AdapterRamBytes)}";
                    Row(sb, useBox, g.Name ?? "GPU", (vendor + vram).Trim());
                }
            }
            else
            {
                Row(sb, useBox, "GPU", "(нет)");
            }

            // --- Storage ---
            SectionHeader(sb, useBox, "Накопители");
            if (hw.Disks is { Count: > 0 })
            {
                foreach (var d in hw.Disks)
                {
                    var iface = string.IsNullOrWhiteSpace(d.InterfaceType) ? "" : $" {d.InterfaceType}";
                    var serial = string.IsNullOrWhiteSpace(d.SerialNumber) ? "" : $" [{d.SerialNumber}]";
                    Row(
                        sb,
                        useBox,
                        d.Model ?? "disk",
                        $"{ReportFormat.FormatBytes(d.SizeBytes)}  {d.MediaType}{iface}{serial}".Trim());
                }
            }
            else
            {
                Row(sb, useBox, "Диски", "(нет)");
            }

            if (hw.Volumes is { Count: > 0 })
            {
                Col(sb, useBox, "Том", "Размер", "Свободно");
                foreach (var v in hw.Volumes)
                {
                    Col(sb, useBox, v.Letter ?? "?", ReportFormat.FormatBytes(v.SizeBytes), ReportFormat.FormatBytes(v.FreeBytes));
                }
            }

            // --- Displays ---
            if (hw.Monitors is { Count: > 0 })
            {
                SectionHeader(sb, useBox, "Мониторы");
                foreach (var m in hw.Monitors)
                {
                    var res = m.Width is null || m.Height is null ? "" : $" {m.Width}x{m.Height}";
                    Row(sb, useBox, m.Name ?? m.Manufacturer ?? "monitor",
                        $"{m.SerialNumber ?? "-"}{res}".Trim());
                }
            }

            // --- Battery ---
            if (hw.Battery is not null)
            {
                SectionHeader(sb, useBox, "Батарея");
                var bat = hw.Battery;
                Row(sb, useBox, "Заряд", bat.ChargePercent is null ? null : $"{bat.ChargePercent}%");
                Row(sb, useBox, "Статус", bat.Status);
                Row(sb, useBox, "Осталось", bat.EstimatedRuntimeMinutes is null
                    ? null
                    : $"{bat.EstimatedRuntimeMinutes} мин");
            }
        }

        SectionHeader(sb, useBox, "Сеть");
        if (snap.Network?.Nics is { Count: > 0 })
        {
            foreach (var nic in snap.Network.Nics)
            {
                Row(sb, useBox, nic.Name ?? "NIC", nic.Mac);
                var ipv4 = nic.Ipv4 is { Count: > 0 } ? string.Join(", ", nic.Ipv4) : "-";
                Row(sb, useBox, "  IPv4", ipv4);
            }
        }
        else
        {
            Row(sb, useBox, "NIC", "(нет)");
        }

        if (snap.Users is not null)
        {
            SectionHeader(sb, useBox, "Пользователи");
            Row(sb, useBox, "Посл. интерак.", snap.Users.LastInteractive);
            var logged = snap.Users.LoggedOn is { Count: > 0 }
                ? string.Join(", ", snap.Users.LoggedOn)
                : "-";
            Row(sb, useBox, "В системе", logged);
        }
        else
        {
            SectionHeader(sb, useBox, "Пользователи");
            Row(sb, useBox, "Статус", "пропущено (collect_users=false)");
        }

        SectionHeader(sb, useBox, "ПО");
        if (snap.Software is not null)
        {
            var programs = snap.Software.Programs;
            if (programs is null)
            {
                Row(sb, useBox, "Программы", "(недоступно на платформе)");
            }
            else if (programs.Count == 0)
            {
                Row(sb, useBox, "Программы", "(пусто)");
            }
            else
            {
                Row(sb, useBox, "Программы", $"{programs.Count} (до {SoftwarePreviewCount})");
                foreach (var p in programs.Take(SoftwarePreviewCount))
                {
                    Row(sb, useBox, p.Name ?? "?", p.Version ?? "-");
                }
            }
        }
        else
        {
            Row(sb, useBox, "Статус", "пропущено (collect_software=false)");
        }

        if (snap.Security is not null)
        {
            SectionHeader(sb, useBox, "Безопасность");
            if (snap.Security.TpmPresent is bool tpm)
            {
                Row(sb, useBox, "TPM", tpm
                    ? (snap.Security.TpmSpecVersion is null ? "да" : $"да ({snap.Security.TpmSpecVersion})")
                    : "нет");
            }

            if (snap.Security.SecureBoot is bool secureBootOn)
            {
                Row(sb, useBox, "Secure Boot", secureBootOn ? "on" : "off");
            }

            if (snap.Security.Antivirus is { Count: > 0 })
            {
                foreach (var av in snap.Security.Antivirus)
                {
                    Row(sb, useBox, "AV", av.Name);
                }
            }
        }

        if (snap.Minidumps is not null)
        {
            SectionHeader(sb, useBox, "Минидампы BSOD");
            Row(sb, useBox, "Файлов", snap.Minidumps.Count.ToString(CultureInfo.InvariantCulture));
            Row(sb, useBox, "Memory.dmp", snap.Minidumps.MemoryDmpPresent ? "есть" : "нет");
            Row(sb, useBox, "Путь Memory.dmp", snap.Minidumps.MemoryDmpPath);
            Row(sb, useBox, "Изменён", TimeFormat.FormatForReport(snap.Minidumps.MemoryDmpModifiedAt));
            if (snap.Minidumps.Files is { Count: > 0 })
            {
                foreach (var f in snap.Minidumps.Files.Take(5))
                {
                    var bug = f.BugcheckCode is null
                        ? TimeFormat.FormatForReport(f.ModifiedAt)
                        : $"{f.BugcheckCode} {f.BugcheckMessage}".Trim();
                    Row(sb, useBox, f.Name ?? "?", bug);
                }
            }
        }

        if (snap.CollectorErrors.Count > 0)
        {
            SectionHeader(sb, useBox, "Ошибки сбора");
            foreach (var err in snap.CollectorErrors)
            {
                Row(sb, useBox, err.Section, err.Error);
            }
        }

        if (useBox)
        {
            sb.AppendLine(BoxBottom());
        }

        return sb.ToString();
    }

    private static void SectionHeader(StringBuilder sb, bool useBox, string title)
    {
        if (useBox)
        {
            sb.AppendLine(BoxMid(title));
        }
        else
        {
            sb.AppendLine(title);
        }
    }

    private static void Row(StringBuilder sb, bool useBox, string key, string? value)
    {
        if (useBox)
        {
            BoxRow(sb, key, value);
        }
        else
        {
            PlainRow(sb, key, value);
        }
    }

    private static void Col(StringBuilder sb, bool useBox, string a, string b, string c)
    {
        if (useBox)
        {
            BoxCol(sb, a, b, c);
        }
        else
        {
            PlainRow(sb, "Том", $"{a}  {b}  {c}");
        }
    }

    private static void BoxRow(StringBuilder sb, string key, string? value)
    {
        var v = string.IsNullOrWhiteSpace(value) ? "-" : value;
        var inner = Width - 4; // chars between "│ " and " │"
        const int keyCol = 18;
        const int gap = 1;
        var valueWidthFirst = Math.Max(1, inner - keyCol - gap);
        var contIndent = keyCol + gap; // value continuation aligns under first value column
        var valueWidthCont = Math.Max(1, inner - contIndent);

        var keyLines = WrapToWidth(key, keyCol);
        var valChunks = WrapToWidth(v, valueWidthFirst);

        void EmitLine(string core)
        {
            foreach (var line in WrapToWidth(core, inner))
            {
                sb.AppendLine("│ " + Pad(line, inner) + " │");
            }
        }

        if (keyLines.Count == 0)
        {
            keyLines.Add("");
        }

        if (valChunks.Count == 0)
        {
            valChunks.Add("");
        }

        EmitLine(Pad(keyLines[0], keyCol) + new string(' ', gap) + valChunks[0]);

        for (var vi = 1; vi < valChunks.Count; vi++)
        {
            var prefix = new string(' ', contIndent);
            EmitLine(prefix + valChunks[vi]);
        }

        for (var ki = 1; ki < keyLines.Count; ki++)
        {
            EmitLine(Pad(keyLines[ki], keyCol));
        }
    }

    private static void BoxCol(StringBuilder sb, string a, string b, string c)
    {
        var inner = Width - 4;
        var wA = 10;
        var wB = 14;
        var wC = Math.Max(4, inner - wA - wB - 2);

        var la = WrapToWidth(a, wA);
        var lb = WrapToWidth(b, wB);
        var lc = WrapToWidth(c, wC);
        var n = Math.Max(la.Count, Math.Max(lb.Count, lc.Count));
        if (n == 0)
        {
            sb.AppendLine("│ " + Pad("", inner) + " │");
            return;
        }

        for (var i = 0; i < n; i++)
        {
            var pa = i < la.Count ? la[i] : "";
            var pb = i < lb.Count ? lb[i] : "";
            var pc = i < lc.Count ? lc[i] : "";
            var rowInner = $"{Pad(pa, wA)} {Pad(pb, wB)} {pc}";
            if (rowInner.Length > inner)
            {
                BoxRow(sb, "Том", $"{a}  {b}  {c}");
                return;
            }

            sb.AppendLine("│ " + Pad(rowInner, inner) + " │");
        }
    }

    private static void PlainRow(StringBuilder sb, string key, string? value)
    {
        var v = string.IsNullOrWhiteSpace(value) ? "-" : value;
        sb.AppendLine($"{key}:");
        foreach (var line in WrapToWidth(v, Math.Max(16, Width)))
        {
            sb.AppendLine($"  {line}");
        }
    }

    private static List<string> WrapToWidth(string text, int maxChars)
    {
        var result = new List<string>();
        if (maxChars < 1) maxChars = 1;
        if (string.IsNullOrEmpty(text))
        {
            result.Add("");
            return result;
        }

        var remaining = text.AsSpan();
        while (remaining.Length > 0)
        {
            if (remaining.Length <= maxChars)
            {
                result.Add(remaining.ToString());
                break;
            }

            var chunk = remaining[..maxChars];
            var breakAt = -1;
            for (var i = chunk.Length - 1; i >= 0; i--)
            {
                if (char.IsWhiteSpace(chunk[i]))
                {
                    breakAt = i;
                    break;
                }
            }

            ReadOnlySpan<char> line;
            ReadOnlySpan<char> rest;
            if (breakAt > 0)
            {
                line = remaining[..breakAt];
                rest = remaining[breakAt..].TrimStart();
            }
            else
            {
                line = remaining[..maxChars];
                rest = remaining[maxChars..];
            }

            result.Add(line.ToString());
            remaining = rest;
        }

        return result;
    }

    private static string BoxTop(string title)
    {
        var sb = new StringBuilder();
        var inner = Width - 4;
        sb.AppendLine("┌" + new string('─', Width - 2) + "┐");
        foreach (var line in WrapToWidth(title.Trim(), inner))
        {
            sb.AppendLine("│ " + Pad(line, inner) + " │");
        }

        return sb.ToString();
    }

    private static string BoxMid(string title)
    {
        var sb = new StringBuilder();
        var inner = Width - 4;
        var labeled = $" {title} ";
        sb.AppendLine("├" + new string('─', Width - 2) + "┤");
        foreach (var line in WrapToWidth(labeled.Trim(), inner))
        {
            sb.AppendLine("│ " + Pad(line, inner) + " │");
        }

        return sb.ToString();
    }

    private static string BoxBottom() => "└" + new string('─', Width - 2) + "┘";

    private static string Pad(string s, int w) => s.Length >= w ? s : s.PadRight(w);
}
