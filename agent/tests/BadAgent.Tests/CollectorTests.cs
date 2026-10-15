using BadAgent;

namespace BadAgent.Tests;

public class CollectorTests
{
    [Fact]
    public void InventoryCollector_ProducesSchemaVersion1()
    {
        var collector = new InventoryCollector();
        var snap = collector.Collect("test-device-id", "0.2.0");

        Assert.Equal(1, snap.SchemaVersion);
        Assert.Equal("test-device-id", snap.DeviceId);
        Assert.Equal("0.2.0", snap.AgentVersion);
        Assert.False(string.IsNullOrWhiteSpace(snap.CollectedAt));
        Assert.NotNull(snap.Host);
        Assert.False(string.IsNullOrWhiteSpace(snap.Host!.Hostname));
        Assert.NotNull(snap.Hardware);
        Assert.NotNull(snap.Network);
        Assert.NotNull(snap.Users);
        Assert.NotNull(snap.CollectorErrors);
    }

    [Fact]
    public void MockCollector_CanBeInjected()
    {
        IInventoryCollector mock = new FakeCollector();
        var snap = mock.Collect("id-1", "1.2.3");
        Assert.Equal(1, snap.SchemaVersion);
        Assert.Equal("fake-host", snap.Host!.Hostname);
        Assert.Empty(snap.CollectorErrors);
    }

    [Fact]
    public void BadApiClient_RejectsCleartextHttp()
    {
        Assert.Throws<InvalidOperationException>(() => new BadApiClient("http://evil.example.com", "0.2.0"));
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
                HeartbeatIntervalMinutes = 15
            };
            ConfigStore.Save(cfg);
            Environment.SetEnvironmentVariable("BAD_SERVER_URL", null);
            Environment.SetEnvironmentVariable("SERVERURL", null);
            var loaded = ConfigStore.LoadOrCreate();
            Assert.Equal("https://bad.example.com", loaded.ServerUrl);
            Assert.Equal("bad_ak_test", loaded.ApiKey);
            Assert.Equal("dev-1", loaded.DeviceId);
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

    private sealed class FakeCollector : IInventoryCollector
    {
        public InventorySnapshot Collect(string deviceId, string agentVersion) => new()
        {
            SchemaVersion = 1,
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
