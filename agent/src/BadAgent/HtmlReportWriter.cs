using System.Net;
using System.Text;

namespace BadAgent;

/// <summary>
/// Self-contained HTML inventory report — Win11/Fluent light family, Russian labels, section icons.
/// </summary>
public static class HtmlReportWriter
{
    public static string Write(InventorySnapshot snap, AgentConfig? config = null)
    {
        var hostname = WebUtility.HtmlEncode(snap.Host?.Hostname ?? "(неизвестно)");
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
        sb.AppendLine($"<h1 class=\"with-icon\">{Icon("host")}{hostname}</h1>");
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

        Section(sb, "host", "Система");
        sb.AppendLine("<dl class=\"grid\">");
        Kv(sb, "Имя узла", snap.Host?.Hostname);
        Kv(sb, "Домен", snap.Host?.Domain);
        Kv(sb, "ОС", ReportFormat.FormatOs(snap.Host?.Os, "—"));
        sb.AppendLine("</dl>");

        Section(sb, "cpu", "Оборудование");
        if (snap.Hardware is null)
        {
            sb.AppendLine("<p class=\"muted\">пропущено (collect_hardware=false)</p>");
        }
        else
        {
            sb.AppendLine("<dl class=\"grid\">");
            Kv(sb, "Производитель", snap.Hardware.Manufacturer, "model");
            Kv(sb, "Модель", snap.Hardware.Model, "model");
            Kv(sb, "Серийный номер", snap.Hardware.SerialNumber, "serial");
            Kv(sb, "Процессор", snap.Hardware.Cpu?.Name, "cpu");
            Kv(sb, "Ядра", snap.Hardware.Cpu is null
                ? null
                : $"{snap.Hardware.Cpu.Cores} / {snap.Hardware.Cpu.Logical} логических", "cpu");
            Kv(sb, "ОЗУ", ReportFormat.FormatBytes(snap.Hardware.RamBytes, "—"), "ram");
            Kv(sb, "Тип ОЗУ", snap.Hardware.RamMemoryType, "ram");
            if (snap.Hardware.RamModules is { Count: > 0 })
            {
                Kv(sb, "Планки ОЗУ", snap.Hardware.RamModules.Count.ToString(), "ram");
            }

            sb.AppendLine("</dl>");

            if (snap.Hardware.Gpus is { Count: > 0 })
            {
                SubHead(sb, "gpu", "Видеоадаптеры");
                sb.AppendLine("<table><thead><tr><th>Имя</th><th>Вендор</th><th>Драйвер</th><th>Память адаптера</th></tr></thead><tbody>");
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
                SubHead(sb, "ram", "Модули ОЗУ");
                sb.AppendLine(
                    "<table><thead><tr><th>Part</th><th>Тип</th><th>Ёмкость</th><th>Частота</th>" +
                    "<th>Канал</th><th>Locator</th></tr></thead><tbody>");
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
                SubHead(sb, "disk", "Диски");
                sb.AppendLine("<table><thead><tr><th>Модель</th><th>Размер</th><th>Носитель</th></tr></thead><tbody>");
                foreach (var d in snap.Hardware.Disks)
                {
                    sb.AppendLine($"<tr><td>{Enc(d.Model)}</td><td>{Enc(ReportFormat.FormatBytes(d.SizeBytes, "—"))}</td><td>{Enc(d.MediaType)}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }

            if (snap.Hardware.Volumes is { Count: > 0 })
            {
                SubHead(sb, "volume", "Тома");
                sb.AppendLine("<table><thead><tr><th>Буква</th><th>Размер</th><th>Свободно</th></tr></thead><tbody>");
                foreach (var v in snap.Hardware.Volumes)
                {
                    sb.AppendLine($"<tr><td>{Enc(v.Letter)}</td><td>{Enc(ReportFormat.FormatBytes(v.SizeBytes, "—"))}</td><td>{Enc(ReportFormat.FormatBytes(v.FreeBytes, "—"))}</td></tr>");
                }

                sb.AppendLine("</tbody></table>");
            }
        }

        Section(sb, "network", "Сеть");
        if (snap.Network?.Nics is { Count: > 0 })
        {
            sb.AppendLine("<table><thead><tr><th>Имя</th><th>MAC</th><th>IPv4</th><th>DHCP</th></tr></thead><tbody>");
            foreach (var n in snap.Network.Nics)
            {
                var ipv4 = n.Ipv4 is { Count: > 0 } ? string.Join(", ", n.Ipv4) : "-";
                var dhcp = n.Dhcp is null ? "-" : (n.Dhcp.Value ? "да" : "нет");
                sb.AppendLine($"<tr><td>{Enc(n.Name)}</td><td>{Enc(n.Mac)}</td><td>{Enc(ipv4)}</td><td>{Enc(dhcp)}</td></tr>");
            }

            sb.AppendLine("</tbody></table>");
        }
        else
        {
            sb.AppendLine("<p class=\"muted\">нет активных NIC</p>");
        }

        Section(sb, "users", "Пользователи");
        if (snap.Users is null)
        {
            sb.AppendLine("<p class=\"muted\">пропущено (collect_users=false)</p>");
        }
        else
        {
            sb.AppendLine("<dl class=\"grid\">");
            Kv(sb, "Последний интерактивный", snap.Users.LastInteractive, "users");
            Kv(sb, "В системе", snap.Users.LoggedOn is { Count: > 0 } ? string.Join(", ", snap.Users.LoggedOn) : null, "users");
            sb.AppendLine("</dl>");
        }

        Section(sb, "software", "ПО");
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
            sb.AppendLine("<table><thead><tr><th>Имя</th><th>Version</th><th>Издатель</th></tr></thead><tbody>");
            foreach (var p in snap.Software.Programs)
            {
                sb.AppendLine($"<tr><td>{Enc(p.Name)}</td><td>{Enc(p.Version)}</td><td>{Enc(p.Publisher)}</td></tr>");
            }

            sb.AppendLine("</tbody></table>");
        }

        if (snap.CollectorErrors.Count > 0)
        {
            Section(sb, "events", "Ошибки сбора");
            sb.AppendLine("<ul class=\"errors\">");
            foreach (var e in snap.CollectorErrors)
            {
                sb.AppendLine($"<li><strong>{Enc(e.Section)}</strong>: {Enc(e.Error)}</li>");
            }

            sb.AppendLine("</ul>");
        }

        sb.AppendLine("</main>");
        sb.AppendLine("<footer class=\"foot\">bAD · локальный отчёт · offline</footer>");
        sb.AppendLine("</body></html>");
        return sb.ToString();
    }

    private static void Section(StringBuilder sb, string icon, string title) =>
        sb.AppendLine($"<h2 class=\"with-icon\">{Icon(icon)}{WebUtility.HtmlEncode(title)}</h2>");

    private static void SubHead(StringBuilder sb, string icon, string title) =>
        sb.AppendLine($"<h3 class=\"with-icon\">{Icon(icon)}{WebUtility.HtmlEncode(title)}</h3>");

    private static void Kv(StringBuilder sb, string key, string? value, string? icon = null)
    {
        var label = icon is null
            ? Enc(key)
            : $"<span class=\"lbl-icon\">{Icon(icon)}{Enc(key)}</span>";
        sb.AppendLine($"<div><dt>{label}</dt><dd>{Enc(string.IsNullOrWhiteSpace(value) ? "—" : value)}</dd></div>");
    }

    private static string Enc(string? s) => WebUtility.HtmlEncode(s ?? "");

    private static string Icon(string name)
    {
        var path = name switch
        {
            "host" => "<rect x=\"2.5\" y=\"3.5\" width=\"15\" height=\"10\" rx=\"1.75\"/><path d=\"M7 16.5h6M10 13.5v3\"/>",
            "cpu" => "<rect x=\"5\" y=\"5\" width=\"10\" height=\"10\" rx=\"1.5\"/><rect x=\"7.5\" y=\"7.5\" width=\"5\" height=\"5\" rx=\"0.75\"/><path d=\"M8 2.75v2.25M12 2.75v2.25M8 15v2.25M12 15v2.25M2.75 8h2.25M2.75 12h2.25M15 8h2.25M15 12h2.25\"/>",
            "ram" => "<rect x=\"2.5\" y=\"6\" width=\"15\" height=\"8\" rx=\"1.25\"/><path d=\"M5.5 6V4.25M8.5 6V4.25M11.5 6V4.25M14.5 6V4.25M6.5 10.25h2M11.5 10.25h2\"/>",
            "disk" => "<ellipse cx=\"10\" cy=\"5.5\" rx=\"6.5\" ry=\"2.4\"/><path d=\"M3.5 5.5v8.5c0 1.35 2.9 2.45 6.5 2.45s6.5-1.1 6.5-2.45V5.5\"/><path d=\"M3.5 10c0 1.35 2.9 2.45 6.5 2.45s6.5-1.1 6.5-2.45\"/>",
            "gpu" => "<rect x=\"2.5\" y=\"5\" width=\"15\" height=\"10\" rx=\"1.5\"/><rect x=\"5\" y=\"7.5\" width=\"6\" height=\"5\" rx=\"0.75\"/><path d=\"M13.5 8.5h2M13.5 11.5h2\"/>",
            "network" => "<circle cx=\"10\" cy=\"10\" r=\"6.5\"/><path d=\"M3.5 10h13M10 3.5c2.2 2.2 2.2 10.8 0 13M10 3.5c-2.2 2.2-2.2 10.8 0 13\"/>",
            "users" => "<circle cx=\"10\" cy=\"6.5\" r=\"2.75\"/><path d=\"M4.25 16.25c.7-2.85 2.7-4.25 5.75-4.25s5.05 1.4 5.75 4.25\"/>",
            "software" => "<rect x=\"3.5\" y=\"3.5\" width=\"13\" height=\"13\" rx=\"2\"/><path d=\"M3.5 7.5h13M7.5 3.5v4\"/>",
            "serial" => "<rect x=\"3.5\" y=\"5\" width=\"13\" height=\"10\" rx=\"1.5\"/><path d=\"M6.5 8v4M9 8v4M11.5 8v4M14 8v4\"/>",
            "model" => "<rect x=\"2.5\" y=\"4.5\" width=\"15\" height=\"10\" rx=\"1.75\"/><path d=\"M8 14.5h4\"/>",
            "volume" => "<path d=\"M3.5 6.5 10 3.5l6.5 3v7L10 16.5 3.5 13.5v-7z\"/><path d=\"M3.5 6.5 10 9.5l6.5-3M10 9.5v7\"/>",
            "events" => "<path d=\"M10 3.5v2M10 14.5v2M3.5 10h2M14.5 10h2\"/><circle cx=\"10\" cy=\"10\" r=\"3.25\"/>",
            _ => "<circle cx=\"10\" cy=\"10\" r=\"6\"/>",
        };
        return $"<svg class=\"icon\" viewBox=\"0 0 20 20\" aria-hidden=\"true\" focusable=\"false\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\">{path}</svg>";
    }

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
.with-icon { display: flex; align-items: center; }
.icon {
  width: 1.15em; height: 1.15em; display: inline-block; vertical-align: -0.2em;
  margin-right: 0.45rem; color: var(--accent); flex-shrink: 0;
}
.lbl-icon { display: inline-flex; align-items: center; gap: 0.3rem; }
.lbl-icon .icon { margin-right: 0; width: 1em; height: 1em; }
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
