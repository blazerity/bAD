using System.Text.RegularExpressions;
using BadAgent;

namespace BadAgent.Tests;

public class CliReportTests
{
    [Fact]
    public void ReportPathResolver_DesktopDefault_UsesTimestampFilename()
    {
        var utc = new DateTime(2026, 10, 15, 17, 30, 45, DateTimeKind.Utc);
        var desktop = Path.Combine(Path.GetTempPath(), "bad-desktop-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(desktop);
        try
        {
            var path = ReportPathResolver.ResolveHtmlPath(null, utc, () => desktop);
            Assert.Equal(Path.Combine(desktop, "bad_report_20261015_173045.html"), path);
        }
        finally
        {
            Directory.Delete(desktop, recursive: true);
        }
    }

    [Fact]
    public void ReportPathResolver_Directory_PutsDefaultFilenameThere()
    {
        var utc = new DateTime(2026, 3, 1, 8, 0, 0, DateTimeKind.Utc);
        var dir = Path.Combine(Path.GetTempPath(), "bad-outdir-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            var path = ReportPathResolver.ResolveHtmlPath(dir, utc);
            Assert.Equal(Path.Combine(dir, "bad_report_20260301_080000.html"), path);

            var withSlash = ReportPathResolver.ResolveHtmlPath(dir + Path.DirectorySeparatorChar, utc);
            Assert.Equal(Path.Combine(dir, "bad_report_20260301_080000.html"), withSlash);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void ReportPathResolver_FilePath_AddsHtmlWhenMissing()
    {
        var utc = DateTime.UtcNow;
        var dir = Path.Combine(Path.GetTempPath(), "bad-file-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            var noExt = Path.Combine(dir, "myreport");
            var resolved = ReportPathResolver.ResolveHtmlPath(noExt, utc);
            Assert.EndsWith("myreport.html", resolved, StringComparison.OrdinalIgnoreCase);

            var withHtml = Path.Combine(dir, "out.html");
            Assert.Equal(
                Path.GetFullPath(withHtml),
                ReportPathResolver.ResolveHtmlPath(withHtml, utc));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void HtmlReportWriter_ContainsHostname()
    {
        var snap = SampleSnapshot();
        var html = HtmlReportWriter.Write(snap);
        Assert.Contains("WORKSTATION-01", html, StringComparison.Ordinal);
        Assert.Contains("bAD", html, StringComparison.Ordinal);
        Assert.Contains("--bg: #0f1419", html, StringComparison.Ordinal);
    }

    [Fact]
    public void AsciiReportWriter_ContainsKeySections()
    {
        var snap = SampleSnapshot();
        var text = AsciiReportWriter.Write(snap, new AgentConfig { ServerUrl = "https://bad.example.com" });
        Assert.Contains("WORKSTATION-01", text, StringComparison.Ordinal);
        Assert.Contains("Host", text, StringComparison.Ordinal);
        Assert.Contains("Hardware", text, StringComparison.Ordinal);
        Assert.Contains("Network", text, StringComparison.Ordinal);
        Assert.Contains("Users", text, StringComparison.Ordinal);
        Assert.Contains("Software", text, StringComparison.Ordinal);
        Assert.Contains("local report", text, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotMatch(new Regex(@"[\u2600-\u27BF]"), text); // no emoji block
    }

    [Fact]
    public void AsciiReportWriter_MarksSkippedSections()
    {
        var snap = SampleSnapshot();
        snap.Hardware = null;
        snap.Users = null;
        snap.Software = null;
        var text = AsciiReportWriter.Write(snap);
        Assert.Contains("collect_hardware=false", text, StringComparison.Ordinal);
        Assert.Contains("collect_users=false", text, StringComparison.Ordinal);
        Assert.Contains("collect_software=false", text, StringComparison.Ordinal);
    }

    [Fact]
    public void BadCli_Help_Returns0()
    {
        Assert.Equal(0, BadCli.Run(new[] { "--help" }, new FakeCollector()));
        Assert.Equal(0, BadCli.Run(new[] { "-?" }, new FakeCollector()));
    }

    [Fact]
    public void BadCli_Unknown_Returns2()
    {
        Assert.Equal(2, BadCli.Run(new[] { "nope" }, new FakeCollector()));
    }

    [Fact]
    public void BadCli_Html_WritesFileWithHostname()
    {
        var dir = Path.Combine(Path.GetTempPath(), "bad-cli-html-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var outFile = Path.Combine(dir, "report.html");
        var configDir = Path.Combine(Path.GetTempPath(), "bad-cfg-" + Guid.NewGuid().ToString("N"));
        Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", configDir);
        try
        {
            var code = BadCli.Run(new[] { "--html", outFile }, new FakeCollector());
            Assert.Equal(0, code);
            Assert.True(File.Exists(outFile));
            var html = File.ReadAllText(outFile);
            Assert.Contains("fake-cli-host", html, StringComparison.Ordinal);
        }
        finally
        {
            Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", null);
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
            if (Directory.Exists(configDir)) Directory.Delete(configDir, recursive: true);
        }
    }

    [Fact]
    public void BadCli_Ascii_Returns0()
    {
        var configDir = Path.Combine(Path.GetTempPath(), "bad-cfg-" + Guid.NewGuid().ToString("N"));
        Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", configDir);
        try
        {
            Assert.Equal(0, BadCli.Run(new[] { "report" }, new FakeCollector()));
            Assert.Equal(0, BadCli.Run(Array.Empty<string>(), new FakeCollector()));
        }
        finally
        {
            Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", null);
            if (Directory.Exists(configDir)) Directory.Delete(configDir, recursive: true);
        }
    }

    private static InventorySnapshot SampleSnapshot() => new()
    {
        SchemaVersion = 2,
        DeviceId = "dev-sample",
        AgentVersion = "0.4.0",
        CollectedAt = "2026-10-15T17:00:00Z",
        Host = new HostInfo
        {
            Hostname = "WORKSTATION-01",
            Domain = "CORP",
            Os = new OsInfo { Caption = "Windows 11", Version = "10.0", Arch = "64-bit" }
        },
        Hardware = new HardwareInfo
        {
            Cpu = new CpuInfo { Name = "Test CPU", Cores = 4, Logical = 8 },
            RamBytes = 16L * 1024 * 1024 * 1024,
            Disks = new List<DiskInfo> { new() { Model = "SSD", SizeBytes = 512L * 1024 * 1024 * 1024, MediaType = "SSD" } },
            Volumes = new List<VolumeInfo> { new() { Letter = "C:", SizeBytes = 500L * 1024 * 1024 * 1024, FreeBytes = 100L * 1024 * 1024 * 1024 } }
        },
        Network = new NetworkInfo
        {
            Nics = new List<NicInfo>
            {
                new() { Name = "Ethernet", Mac = "AA:BB:CC:DD:EE:FF", Ipv4 = new List<string> { "10.0.0.5" }, Dhcp = true }
            }
        },
        Users = new UsersInfo { LastInteractive = "CORP\\alice", LoggedOn = new List<string> { "CORP\\alice" } },
        Software = new SoftwareInfo
        {
            Programs = new List<InstalledProgram>
            {
                new() { Name = "Example App", Version = "1.0", Publisher = "Example" }
            }
        },
        CollectorErrors = new List<CollectorError>()
    };

    private sealed class FakeCollector : IInventoryCollector
    {
        public InventorySnapshot Collect(string deviceId, string agentVersion, CollectorOptions? options = null) => new()
        {
            SchemaVersion = 2,
            DeviceId = deviceId,
            AgentVersion = agentVersion,
            CollectedAt = "2026-10-15T00:00:00Z",
            Host = new HostInfo { Hostname = "fake-cli-host", Domain = "TEST" },
            Hardware = new HardwareInfo { RamBytes = 1024 },
            Network = new NetworkInfo { Nics = new List<NicInfo>() },
            Users = new UsersInfo { LastInteractive = "tester" },
            Software = null,
            CollectorErrors = new List<CollectorError>()
        };
    }
}
