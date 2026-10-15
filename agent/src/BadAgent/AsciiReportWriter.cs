using System.Globalization;
using System.Text;

namespace BadAgent;

/// <summary>Pretty ASCII inventory report for terminal (boxes/columns, no emojis).</summary>
public static class AsciiReportWriter
{
    private const int Width = 72;
    private const int SoftwarePreviewCount = 20;

    public static string Write(InventorySnapshot snap, AgentConfig? config = null)
    {
        var sb = new StringBuilder();
        var hostname = snap.Host?.Hostname ?? "(unknown)";
        var title = $" bAD inventory — {hostname} ";

        sb.AppendLine(BoxTop(title));
        Row(sb, "Device ID", snap.DeviceId);
        Row(sb, "Collected", snap.CollectedAt);
        Row(sb, "Agent", snap.AgentVersion);
        Row(sb, "Schema", snap.SchemaVersion.ToString(CultureInfo.InvariantCulture));
        if (config is not null && !string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            Row(sb, "Server URL", config.ServerUrl + " (local report; server not contacted)");
        }
        else
        {
            Row(sb, "Server URL", "(not configured — local-only)");
        }

        sb.AppendLine(BoxMid("Host"));
        Row(sb, "Hostname", snap.Host?.Hostname);
        Row(sb, "Domain", snap.Host?.Domain);
        Row(sb, "OS", ReportFormat.FormatOs(snap.Host?.Os));

        if (snap.Hardware is not null)
        {
            sb.AppendLine(BoxMid("Hardware"));
            var cpu = snap.Hardware.Cpu;
            Row(sb, "CPU", cpu?.Name);
            Row(sb, "Cores", ReportFormat.FormatCores(cpu));
            Row(sb, "RAM", ReportFormat.FormatBytes(snap.Hardware.RamBytes));

            if (snap.Hardware.Disks is { Count: > 0 })
            {
                sb.AppendLine(BoxMid("Disks"));
                foreach (var d in snap.Hardware.Disks)
                {
                    Row(sb, Trunc(d.Model ?? "disk", 28), $"{ReportFormat.FormatBytes(d.SizeBytes)}  {d.MediaType}");
                }
            }

            if (snap.Hardware.Volumes is { Count: > 0 })
            {
                sb.AppendLine(BoxMid("Volumes"));
                Col(sb, "Letter", "Size", "Free");
                foreach (var v in snap.Hardware.Volumes)
                {
                    Col(sb, v.Letter ?? "?", ReportFormat.FormatBytes(v.SizeBytes), ReportFormat.FormatBytes(v.FreeBytes));
                }
            }
        }
        else
        {
            sb.AppendLine(BoxMid("Hardware"));
            Row(sb, "Status", "skipped (collect_hardware=false)");
        }

        sb.AppendLine(BoxMid("Network"));
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
            Row(sb, "NICs", "(none)");
        }

        if (snap.Users is not null)
        {
            sb.AppendLine(BoxMid("Users"));
            Row(sb, "Last interactive", snap.Users.LastInteractive);
            var logged = snap.Users.LoggedOn is { Count: > 0 }
                ? string.Join(", ", snap.Users.LoggedOn)
                : "-";
            Row(sb, "Logged on", logged);
        }
        else
        {
            sb.AppendLine(BoxMid("Users"));
            Row(sb, "Status", "skipped (collect_users=false)");
        }

        if (snap.Software is not null)
        {
            sb.AppendLine(BoxMid("Software"));
            var programs = snap.Software.Programs;
            if (programs is null)
            {
                Row(sb, "Programs", "(unavailable on this platform)");
            }
            else if (programs.Count == 0)
            {
                Row(sb, "Programs", "(empty)");
            }
            else
            {
                Row(sb, "Programs", $"{programs.Count} (showing up to {SoftwarePreviewCount})");
                foreach (var p in programs.Take(SoftwarePreviewCount))
                {
                    Row(sb, Trunc(p.Name ?? "?", 36), p.Version ?? "-");
                }
            }
        }
        else
        {
            sb.AppendLine(BoxMid("Software"));
            Row(sb, "Status", "skipped (collect_software=false)");
        }

        if (snap.CollectorErrors.Count > 0)
        {
            sb.AppendLine(BoxMid("Collector errors"));
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
