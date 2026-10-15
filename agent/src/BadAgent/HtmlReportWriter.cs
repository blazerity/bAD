using System.Globalization;
using System.Net;
using System.Text;

namespace BadAgent;

/// <summary>
/// Self-contained HTML inventory report styled like the bAD web panel (dark theme).
/// </summary>
public static class HtmlReportWriter
{
    public static string Write(InventorySnapshot snap, AgentConfig? config = null)
    {
        var hostname = WebUtility.HtmlEncode(snap.Host?.Hostname ?? "(unknown)");
        var sb = new StringBuilder();
        sb.AppendLine("<!DOCTYPE html>");
        sb.AppendLine("<html lang=\"ru\">");
        sb.AppendLine("<head>");
        sb.AppendLine("<meta charset=\"utf-8\" />");
        sb.AppendLine("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />");
        sb.AppendLine($"<title>bAD — {hostname}</title>");
        sb.AppendLine("<style>");
        sb.AppendLine(EmbeddedCss());
        sb.AppendLine("</style>");
        sb.AppendLine("</head>");
        sb.AppendLine("<body>");
        sb.AppendLine("<header class=\"top\">");
        sb.AppendLine("<a class=\"brand\" href=\"#\">bAD</a>");
        sb.AppendLine("<span class=\"tagline\">локальный отчёт inventory</span>");
        sb.AppendLine("</header>");
        sb.AppendLine("<main>");
        sb.AppendLine($"<h1>{hostname}</h1>");
        sb.AppendLine($"<p class=\"muted\">device_id: <code>{Enc(snap.DeviceId)}</code> · agent {Enc(snap.AgentVersion)} · schema {snap.SchemaVersion}</p>");
        sb.AppendLine($"<p class=\"muted\">собрано: {Enc(snap.CollectedAt)}</p>");

        if (config is not null && !string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            sb.AppendLine($"<p class=\"note\">server_url в конфиге: <code>{Enc(config.ServerUrl)}</code> — отчёт собран локально, сервер не вызывался.</p>");
        }
        else
        {
            sb.AppendLine("<p class=\"note\">server_url не задан — только локальный сбор.</p>");
        }

        Section(sb, "Host");
        sb.AppendLine("<dl class=\"grid\">");
        Kv(sb, "Hostname", snap.Host?.Hostname);
        Kv(sb, "Domain", snap.Host?.Domain);
        Kv(sb, "OS", FormatOs(snap.Host?.Os));
        sb.AppendLine("</dl>");

        Section(sb, "Hardware");
        if (snap.Hardware is null)
        {
            sb.AppendLine("<p class=\"muted\">пропущено (collect_hardware=false)</p>");
        }
        else
        {
            sb.AppendLine("<dl class=\"grid\">");
            Kv(sb, "CPU", snap.Hardware.Cpu?.Name);
            Kv(sb, "Cores", snap.Hardware.Cpu is null ? null : $"{snap.Hardware.Cpu.Cores} / {snap.Hardware.Cpu.Logical} logical");
            Kv(sb, "RAM", FormatBytes(snap.Hardware.RamBytes));
            sb.AppendLine("</dl>");

            if (snap.Hardware.Disks is { Count: > 0 })
            {
                sb.AppendLine("<h3>Disks</h3>");
                sb.AppendLine("<table><thead><tr><th>Model</th><th>Size</th><th>Media</th></tr></thead><tbody>");
                foreach (var d in snap.Hardware.Disks)
                {
                    sb.AppendLine($"<tr><td>{Enc(d.Model)}</td><td>{Enc(FormatBytes(d.SizeBytes))}</td><td>{Enc(d.MediaType)}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }

            if (snap.Hardware.Volumes is { Count: > 0 })
            {
                sb.AppendLine("<h3>Volumes</h3>");
                sb.AppendLine("<table><thead><tr><th>Letter</th><th>Size</th><th>Free</th></tr></thead><tbody>");
                foreach (var v in snap.Hardware.Volumes)
                {
                    sb.AppendLine($"<tr><td>{Enc(v.Letter)}</td><td>{Enc(FormatBytes(v.SizeBytes))}</td><td>{Enc(FormatBytes(v.FreeBytes))}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }
        }

        Section(sb, "Network");
        if (snap.Network?.Nics is { Count: > 0 })
        {
            sb.AppendLine("<table><thead><tr><th>Name</th><th>MAC</th><th>IPv4</th><th>DHCP</th></tr></thead><tbody>");
            foreach (var n in snap.Network.Nics)
            {
                var ipv4 = n.Ipv4 is { Count: > 0 } ? string.Join(", ", n.Ipv4) : "-";
                var dhcp = n.Dhcp is null ? "-" : (n.Dhcp.Value ? "yes" : "no");
                sb.AppendLine($"<tr><td>{Enc(n.Name)}</td><td>{Enc(n.Mac)}</td><td>{Enc(ipv4)}</td><td>{Enc(dhcp)}</td></tr>");
            }

            sb.AppendLine("</tbody></table>");
        }
        else
        {
            sb.AppendLine("<p class=\"muted\">нет активных NIC</p>");
        }

        Section(sb, "Users");
        if (snap.Users is null)
        {
            sb.AppendLine("<p class=\"muted\">пропущено (collect_users=false)</p>");
        }
        else
        {
            sb.AppendLine("<dl class=\"grid\">");
            Kv(sb, "Last interactive", snap.Users.LastInteractive);
            Kv(sb, "Logged on", snap.Users.LoggedOn is { Count: > 0 } ? string.Join(", ", snap.Users.LoggedOn) : null);
            sb.AppendLine("</dl>");
        }

        Section(sb, "Software");
        if (snap.Software is null)
        {
            sb.AppendLine("<p class=\"muted\">пропущено (collect_software=false)</p>");
        }
        else if (snap.Software.Programs is null)
        {
            sb.AppendLine("<p class=\"muted\">недоступно на этой платформе</p>");
        }
        else if (snap.Software.Programs.Count == 0)
        {
            sb.AppendLine("<p class=\"muted\">пусто</p>");
        }
        else
        {
            sb.AppendLine($"<p class=\"muted\">{snap.Software.Programs.Count} программ (cap {InventoryCollector.MaxSoftwarePrograms})</p>");
            sb.AppendLine("<table><thead><tr><th>Name</th><th>Version</th><th>Publisher</th></tr></thead><tbody>");
            foreach (var p in snap.Software.Programs)
            {
                sb.AppendLine($"<tr><td>{Enc(p.Name)}</td><td>{Enc(p.Version)}</td><td>{Enc(p.Publisher)}</td></tr>");
            }

            sb.AppendLine("</tbody></table>");
        }

        if (snap.CollectorErrors.Count > 0)
        {
            Section(sb, "Collector errors");
            sb.AppendLine("<ul class=\"errors\">");
            foreach (var e in snap.CollectorErrors)
            {
                sb.AppendLine($"<li><strong>{Enc(e.Section)}</strong>: {Enc(e.Error)}</li>");
            }

            sb.AppendLine("</ul>");
        }

        sb.AppendLine("</main>");
        sb.AppendLine("<footer class=\"foot\">bAD local report · generated offline</footer>");
        sb.AppendLine("</body></html>");
        return sb.ToString();
    }

    private static void Section(StringBuilder sb, string title) =>
        sb.AppendLine($"<h2>{WebUtility.HtmlEncode(title)}</h2>");

    private static void Kv(StringBuilder sb, string key, string? value) =>
        sb.AppendLine($"<div><dt>{Enc(key)}</dt><dd>{Enc(string.IsNullOrWhiteSpace(value) ? "—" : value)}</dd></div>");

    private static string Enc(string? s) => WebUtility.HtmlEncode(s ?? "");

    private static string FormatOs(OsInfo? os)
    {
        if (os is null) return "—";
        var parts = new[] { os.Caption, os.Version, os.Arch }
            .Where(x => !string.IsNullOrWhiteSpace(x));
        var text = string.Join(" / ", parts);
        return string.IsNullOrEmpty(text) ? "—" : text;
    }

    private static string FormatBytes(long? bytes)
    {
        if (bytes is null or < 0) return "—";
        double v = bytes.Value;
        string[] units = ["B", "KiB", "MiB", "GiB", "TiB"];
        var i = 0;
        while (v >= 1024 && i < units.Length - 1)
        {
            v /= 1024;
            i++;
        }

        return i == 0
            ? $"{bytes.Value} {units[i]}"
            : string.Format(CultureInfo.InvariantCulture, "{0:0.##} {1}", v, units[i]);
    }

    private static string EmbeddedCss() => """
:root {
  --bg: #0f1419;
  --bg-elev: #1a222c;
  --fg: #e8eef4;
  --muted: #8b9aab;
  --accent: #3d9cf0;
  --border: #2a3542;
  --error: #e85d5d;
  --mono: "IBM Plex Mono", "Cascadia Code", "Consolas", monospace;
  --sans: "IBM Plex Sans", "Segoe UI", "Helvetica Neue", sans-serif;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background: radial-gradient(1200px 600px at 10% -10%, #1a2a3a 0%, var(--bg) 55%);
  color: var(--fg); font-family: var(--sans); min-height: 100%;
}
.top {
  display: flex; align-items: baseline; gap: 1rem;
  padding: 1rem 1.5rem; border-bottom: 1px solid var(--border);
  background: rgba(15, 20, 25, 0.85);
}
.brand { font-weight: 700; font-size: 1.25rem; letter-spacing: 0.04em; color: var(--fg); text-decoration: none; }
.tagline { color: var(--muted); font-size: 0.9rem; }
main { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
.foot { max-width: 960px; margin: 0 auto; padding: 0 1.5rem 2rem; color: var(--muted); font-size: 0.8rem; }
h1 { margin: 0 0 0.5rem; font-size: 1.75rem; font-weight: 650; }
h2 { margin: 2rem 0 0.75rem; font-size: 1.15rem; font-weight: 600; border-bottom: 1px solid var(--border); padding-bottom: 0.35rem; }
h3 { margin: 1.25rem 0 0.5rem; font-size: 1rem; color: var(--muted); font-weight: 600; }
.muted { color: var(--muted); margin-top: 0; }
.note { background: var(--bg-elev); border: 1px solid var(--border); padding: 0.75rem 1rem; border-radius: 4px; color: var(--muted); font-size: 0.9rem; }
code { font-family: var(--mono); font-size: 0.9em; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.75rem 1.25rem; margin: 0; }
.grid dt { color: var(--muted); font-size: 0.8rem; margin: 0; }
.grid dd { margin: 0.15rem 0 0; font-family: var(--mono); font-size: 0.95rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; margin: 0.5rem 0 1rem; }
th, td { text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 0.8rem; }
.errors { color: var(--error); }
@media (max-width: 640px) {
  main { padding: 1.25rem 1rem 2rem; }
  table { font-size: 0.85rem; }
}
""";
}
