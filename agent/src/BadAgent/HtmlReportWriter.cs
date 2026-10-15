using System.Net;
using System.Text;

namespace BadAgent;

/// <summary>
/// Self-contained HTML inventory report — same Win11/Fluent light family as the web panel.
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
        sb.AppendLine("<section class=\"hero\">");
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

        sb.AppendLine("</section>");

        Section(sb, "Host");
        sb.AppendLine("<dl class=\"grid\">");
        Kv(sb, "Hostname", snap.Host?.Hostname);
        Kv(sb, "Domain", snap.Host?.Domain);
        Kv(sb, "OS", ReportFormat.FormatOs(snap.Host?.Os, "—"));
        sb.AppendLine("</dl>");

        Section(sb, "Hardware");
        if (snap.Hardware is null)
        {
            sb.AppendLine("<p class=\"muted\">пропущено (collect_hardware=false)</p>");
        }
        else
        {
            sb.AppendLine("<dl class=\"grid\">");
            Kv(sb, "Manufacturer", snap.Hardware.Manufacturer);
            Kv(sb, "Model", snap.Hardware.Model);
            Kv(sb, "Serial", snap.Hardware.SerialNumber);
            Kv(sb, "CPU", snap.Hardware.Cpu?.Name);
            Kv(sb, "Cores", snap.Hardware.Cpu is null
                ? null
                : $"{snap.Hardware.Cpu.Cores} / {snap.Hardware.Cpu.Logical} logical");
            Kv(sb, "RAM", ReportFormat.FormatBytes(snap.Hardware.RamBytes, "—"));
            Kv(sb, "RAM type", snap.Hardware.RamMemoryType);
            if (snap.Hardware.RamModules is { Count: > 0 })
            {
                Kv(sb, "RAM sticks", snap.Hardware.RamModules.Count.ToString());
            }

            sb.AppendLine("</dl>");

            if (snap.Hardware.Gpus is { Count: > 0 })
            {
                sb.AppendLine("<h3>GPUs</h3>");
                sb.AppendLine("<table><thead><tr><th>Name</th><th>Vendor</th><th>Driver</th><th>Adapter RAM</th></tr></thead><tbody>");
                foreach (var g in snap.Hardware.Gpus)
                {
                    sb.AppendLine(
                        $"<tr><td>{Enc(g.Name)}</td><td>{Enc(g.Vendor)}</td><td>{Enc(g.DriverVersion)}</td>" +
                        $"<td>{Enc(ReportFormat.FormatBytes(g.AdapterRamBytes, "—"))}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }

            if (snap.Hardware.RamModules is { Count: > 0 })
            {
                sb.AppendLine("<h3>RAM modules</h3>");
                sb.AppendLine(
                    "<table><thead><tr><th>Part</th><th>Type</th><th>Capacity</th><th>Speed</th>" +
                    "<th>Channel</th><th>Locator</th></tr></thead><tbody>");
                foreach (var m in snap.Hardware.RamModules)
                {
                    var speed = m.SpeedMhz is null ? "—" : $"{m.SpeedMhz} MHz";
                    sb.AppendLine(
                        $"<tr><td>{Enc(m.PartNumber ?? m.Manufacturer)}</td>" +
                        $"<td>{Enc(m.MemoryType)}</td>" +
                        $"<td>{Enc(ReportFormat.FormatBytes(m.CapacityBytes, "—"))}</td>" +
                        $"<td>{Enc(speed)}</td><td>{Enc(m.Channel)}</td>" +
                        $"<td>{Enc(m.DeviceLocator ?? m.BankLabel)}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }

            if (snap.Hardware.Disks is { Count: > 0 })
            {
                sb.AppendLine("<h3>Disks</h3>");
                sb.AppendLine("<table><thead><tr><th>Model</th><th>Size</th><th>Media</th></tr></thead><tbody>");
                foreach (var d in snap.Hardware.Disks)
                {
                    sb.AppendLine($"<tr><td>{Enc(d.Model)}</td><td>{Enc(ReportFormat.FormatBytes(d.SizeBytes, "—"))}</td><td>{Enc(d.MediaType)}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }

            if (snap.Hardware.Volumes is { Count: > 0 })
            {
                sb.AppendLine("<h3>Volumes</h3>");
                sb.AppendLine("<table><thead><tr><th>Letter</th><th>Size</th><th>Free</th></tr></thead><tbody>");
                foreach (var v in snap.Hardware.Volumes)
                {
                    sb.AppendLine($"<tr><td>{Enc(v.Letter)}</td><td>{Enc(ReportFormat.FormatBytes(v.SizeBytes, "—"))}</td><td>{Enc(ReportFormat.FormatBytes(v.FreeBytes, "—"))}</td></tr>");
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

    private static string EmbeddedCss() => """
:root {
  --bg: #f3f3f3;
  --bg-tint: #e8f1fb;
  --bg-elev: rgba(255, 255, 255, 0.72);
  --bg-solid: #ffffff;
  --fg: #1a1a1a;
  --muted: #5d5d5d;
  --accent: #0067c0;
  --border: rgba(0, 0, 0, 0.08);
  --border-strong: rgba(0, 0, 0, 0.14);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.06);
  --error: #c42b1c;
  --radius-control: 4px;
  --radius-surface: 8px;
  --sans: "Segoe UI Variable", "Segoe UI", "Segoe UI Web", system-ui, sans-serif;
  --mono: "Cascadia Mono", "Cascadia Code", "Consolas", "Segoe UI Mono", monospace;
  --ease: cubic-bezier(0.1, 0.9, 0.2, 1);
  --dur: 160ms;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; min-height: 100%;
  color: var(--fg); font-family: var(--sans); font-size: 14px; line-height: 1.45;
  background:
    radial-gradient(900px 480px at 12% -8%, var(--bg-tint) 0%, transparent 55%),
    linear-gradient(180deg, #f7f8fa 0%, var(--bg) 40%, #eceff3 100%);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.top {
  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
  padding: 0.65rem 1.25rem; border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(1.35);
  -webkit-backdrop-filter: blur(20px) saturate(1.35);
  box-shadow: var(--shadow-sm);
}
.brand { font-weight: 600; font-size: 1.125rem; color: var(--fg); text-decoration: none; }
.tagline { color: var(--muted); font-size: 0.875rem; }
main { max-width: 1040px; margin: 0 auto; padding: 1.75rem 1.25rem 3rem; }
.foot { max-width: 1040px; margin: 0 auto; padding: 0 1.25rem 2rem; color: var(--muted); font-size: 0.8rem; }
.hero {
  background: var(--bg-elev); border: 1px solid var(--border); border-radius: var(--radius-surface);
  padding: 1.15rem 1.25rem; box-shadow: var(--shadow-sm);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  margin-bottom: 0.5rem;
}
h1 { margin: 0 0 0.4rem; font-size: 1.75rem; font-weight: 600; letter-spacing: -0.01em; }
h2 {
  margin: 1.75rem 0 0.65rem; font-size: 1.1rem; font-weight: 600;
  border-bottom: 1px solid var(--border); padding-bottom: 0.35rem;
}
h3 { margin: 1.25rem 0 0.5rem; font-size: 1rem; color: var(--muted); font-weight: 600; }
.muted { color: var(--muted); margin-top: 0; }
.note {
  background: var(--bg-solid); border: 1px solid var(--border-strong);
  padding: 0.7rem 0.9rem; border-radius: var(--radius-control);
  color: var(--muted); font-size: 0.9rem;
}
code { font-family: var(--mono); font-size: 0.9em; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem 1.25rem; margin: 0; padding: 1rem 1.1rem;
  background: var(--bg-elev); border: 1px solid var(--border);
  border-radius: var(--radius-surface); box-shadow: var(--shadow-sm);
}
.grid dt { color: var(--muted); font-size: 0.78rem; font-weight: 600; margin: 0; }
.grid dd { margin: 0.15rem 0 0; font-family: var(--mono); font-size: 0.95rem; }
table {
  width: 100%; border-collapse: separate; border-spacing: 0;
  font-size: 0.92rem; margin: 0.5rem 0 1rem;
  background: var(--bg-elev); border: 1px solid var(--border);
  border-radius: var(--radius-surface); overflow: hidden; box-shadow: var(--shadow-sm);
}
th, td { text-align: left; padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 0.78rem; background: rgba(255,255,255,0.55); }
tr:last-child td { border-bottom: none; }
tbody tr { transition: background var(--dur) var(--ease); }
tbody tr:hover { background: rgba(0, 103, 192, 0.08); }
.errors { color: var(--error); }
@media (max-width: 640px) {
  main { padding: 1.25rem 0.85rem 2rem; }
  table { font-size: 0.85rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0.01ms !important; }
}
""";
}
