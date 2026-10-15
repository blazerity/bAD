using BadAgent;

namespace BadAgent.Tests;

public class CollectorTests
{
    [Fact]
    public void InventoryCollector_ProducesSchemaVersion2()
    {
        var collector = new InventoryCollector();
        var snap = collector.Collect("test-device-id", "0.5.0");

        Assert.Equal(2, snap.SchemaVersion);
        Assert.Equal("test-device-id", snap.DeviceId);
        Assert.Equal("0.5.0", snap.AgentVersion);
        Assert.False(string.IsNullOrWhiteSpace(snap.CollectedAt));
        Assert.NotNull(snap.Host);
        Assert.False(string.IsNullOrWhiteSpace(snap.Host!.Hostname));
        Assert.NotNull(snap.Hardware);
        Assert.NotNull(snap.Network);
        Assert.NotNull(snap.Users);
        Assert.Null(snap.Software); // collect_software default false
        Assert.NotNull(snap.CollectorErrors);
    }

    [Fact]
    public void InventoryCollector_SkipsDisabledSectionsWithoutErrors()
    {
        var collector = new InventoryCollector();
        var snap = collector.Collect(
            "dev-skip",
            "0.5.0",
            new CollectorOptions
            {
                CollectHardware = false,
                CollectUsers = false,
                CollectSoftware = false,
            });

        Assert.Equal(2, snap.SchemaVersion);
        Assert.NotNull(snap.Host);
        Assert.NotNull(snap.Network);
        Assert.Null(snap.Hardware);
        Assert.Null(snap.Users);
        Assert.Null(snap.Software);
        Assert.DoesNotContain(snap.CollectorErrors, e => e.Section is "hardware" or "users" or "software");
    }

    [Fact]
    public void InventoryCollector_SoftwareOptIn_LeavesNullOnNonWindows()
    {
        if (OperatingSystem.IsWindows())
        {
            var collector = new InventoryCollector();
            var snap = collector.Collect(
                "dev-sw",
                "0.5.0",
                new CollectorOptions { CollectSoftware = true });
            // On Windows we may get a list (or empty after filters); must not crash.
            Assert.NotNull(snap.Software);
            if (snap.Software!.Programs is not null)
            {
                Assert.True(snap.Software.Programs.Count <= InventoryCollector.MaxSoftwarePrograms);
                Assert.All(snap.Software.Programs, p => Assert.False(string.IsNullOrWhiteSpace(p.Name)));
            }
            return;
        }

        var linuxSnap = new InventoryCollector().Collect(
            "dev-sw",
            "0.5.0",
            new CollectorOptions { CollectSoftware = true });
        Assert.NotNull(linuxSnap.Software);
        Assert.Null(linuxSnap.Software!.Programs);
        Assert.DoesNotContain(linuxSnap.CollectorErrors, e => e.Section == "software");
    }

    [Fact]
    public void MockCollector_CanBeInjected()
    {
        IInventoryCollector mock = new FakeCollector();
        var snap = mock.Collect("id-1", "1.2.3");
        Assert.Equal(2, snap.SchemaVersion);
        Assert.Equal("fake-host", snap.Host!.Hostname);
        Assert.Empty(snap.CollectorErrors);
    }

    [Fact]
    public void BadApiClient_RejectsCleartextHttp()
    {
        Assert.Throws<InvalidOperationException>(() => new BadApiClient("http://evil.example.com", "0.5.0"));
    }

    [Fact]
    public void ConfigStore_RoundTrip()
    {
        var dir = Path.Combine(Path.GetTempPath(), "bad-test-" + Guid.NewGuid().ToString("N"));
        Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", dir);
        try
        {
            var cfg = new AgentConfig
            {
                ServerUrl = "https://bad.example.com",
                ApiKey = "bad_ak_test",
                DeviceId = "dev-1",
                InventoryIntervalHours = 6,
                HeartbeatIntervalMinutes = 15,
                CollectHardware = true,
                CollectUsers = true,
                CollectSoftware = false,
            };
            ConfigStore.Save(cfg);
            Environment.SetEnvironmentVariable("BAD_SERVER_URL", null);
            Environment.SetEnvironmentVariable("SERVERURL", null);
            var loaded = ConfigStore.LoadOrCreate();
            Assert.Equal("https://bad.example.com", loaded.ServerUrl);
            Assert.Equal("bad_ak_test", loaded.ApiKey);
            Assert.Equal("dev-1", loaded.DeviceId);
            Assert.True(loaded.CollectHardware);
            Assert.True(loaded.CollectUsers);
            Assert.False(loaded.CollectSoftware);
        }
        finally
        {
            Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", null);
            if (Directory.Exists(dir))
            {
                Directory.Delete(dir, recursive: true);
            }
        }
    }

    [Fact]
    public void ConfigStore_ApplyRemoteSettings_UpdatesSafeKnobsOnly()
    {
        var dir = Path.Combine(Path.GetTempPath(), "bad-test-" + Guid.NewGuid().ToString("N"));
        Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", dir);
        Environment.SetEnvironmentVariable("BAD_SERVER_URL", null);
        Environment.SetEnvironmentVariable("SERVERURL", null);
        try
        {
            var cfg = new AgentConfig
            {
                ServerUrl = "https://bad.example.com",
                ApiKey = "bad_ak_keep",
                DeviceId = "dev-keep",
                EnrollmentToken = "enroll-keep",
                InventoryIntervalHours = 6,
                HeartbeatIntervalMinutes = 15,
                UpdateCheckIntervalHours = 24,
                UpdateEnabled = true,
                CollectHardware = true,
                CollectUsers = true,
                CollectSoftware = false,
            };

            var remoteJson = """
                {"version":"abc123","settings":{
                  "inventory_interval_hours":2,
                  "heartbeat_interval_minutes":5,
                  "update_check_interval_hours":12,
                  "update_enabled":false,
                  "collect_hardware":false,
                  "collect_users":false,
                  "collect_software":true,
                  "server_url":"https://evil.example",
                  "api_key":"stolen"
                }}
                """;
            var remote = RemoteAgentConfigResponse.FromJson(remoteJson);
            Assert.NotNull(remote);
            Assert.NotNull(remote!.Settings);

            var changed = ConfigStore.ApplyRemoteSettings(cfg, remote.Settings!);
            Assert.True(changed);
            cfg.RemoteConfigVersion = remote.Version;
            ConfigStore.Save(cfg);

            var loaded = ConfigStore.LoadOrCreate();
            Assert.Equal(2, loaded.InventoryIntervalHours);
            Assert.Equal(5, loaded.HeartbeatIntervalMinutes);
            Assert.Equal(12, loaded.UpdateCheckIntervalHours);
            Assert.False(loaded.UpdateEnabled);
            Assert.False(loaded.CollectHardware);
            Assert.False(loaded.CollectUsers);
            Assert.True(loaded.CollectSoftware);
            Assert.Equal("abc123", loaded.RemoteConfigVersion);
            Assert.Equal("https://bad.example.com", loaded.ServerUrl);
            Assert.Equal("bad_ak_keep", loaded.ApiKey);
            Assert.Equal("dev-keep", loaded.DeviceId);
            Assert.Equal("enroll-keep", loaded.EnrollmentToken);
        }
        finally
        {
            Environment.SetEnvironmentVariable("BAD_CONFIG_DIR", null);
            if (Directory.Exists(dir))
            {
                Directory.Delete(dir, recursive: true);
            }
        }
    }

    [Fact]
    public void Worker_TrySystemDriveFreeBytes_ReturnsNonNegativeOrNull()
    {
        var free = Worker.TrySystemDriveFreeBytes();
        if (free is not null)
        {
            Assert.True(free >= 0);
        }
    }

    private sealed class FakeCollector : IInventoryCollector
    {
        public InventorySnapshot Collect(string deviceId, string agentVersion, CollectorOptions? options = null) => new()
        {
            SchemaVersion = 2,
            DeviceId = deviceId,
            AgentVersion = agentVersion,
            CollectedAt = "2026-10-15T00:00:00Z",
            Host = new HostInfo { Hostname = "fake-host", Domain = "TEST" },
            Hardware = new HardwareInfo { RamBytes = 1024 },
            Network = new NetworkInfo { Nics = new List<NicInfo>() },
            Users = new UsersInfo(),
            CollectorErrors = new List<CollectorError>()
        };
    }
}
