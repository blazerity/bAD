using System.Text.Json;
using BadAgent;

namespace BadAgent.Tests;

public class CollectorTests
{
    [Fact]
    public void InventoryCollector_ProducesSchemaVersion2()
    {
        var collector = new InventoryCollector();
        var snap = collector.Collect("test-device-id", "0.8.0");

        Assert.Equal(2, snap.SchemaVersion);
        Assert.Equal("test-device-id", snap.DeviceId);
        Assert.Equal("0.8.0", snap.AgentVersion);
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
            "0.8.0",
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
                "0.8.0",
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
            "0.8.0",
            new CollectorOptions { CollectSoftware = true });
        Assert.NotNull(linuxSnap.Software);
        Assert.Null(linuxSnap.Software!.Programs);
        Assert.DoesNotContain(linuxSnap.CollectorErrors, e => e.Section == "software");
    }

    [Fact]
    public void HardwareMaps_CleanWmiString_DropsPlaceholders()
    {
        Assert.Null(HardwareMaps.CleanWmiString("To Be Filled By O.E.M."));
        Assert.Null(HardwareMaps.CleanWmiString("  "));
        Assert.Equal("ABC1234", HardwareMaps.CleanWmiString(" ABC1234 "));
    }

    [Fact]
    public void HardwareMaps_MemoryAndFormFactor_KnownCodes()
    {
        Assert.Equal("SODIMM", HardwareMaps.FormFactorName(12));
        Assert.Equal("DDR5", HardwareMaps.MemoryTypeName(34));
        Assert.Equal("DDR4", HardwareMaps.MemoryTypeName(26));
        Assert.Equal("LPDDR4", HardwareMaps.MemoryTypeName(30));
        Assert.Equal("LPDDR5", HardwareMaps.MemoryTypeName(35));
        Assert.Equal("LPDDR5X", HardwareMaps.MemoryTypeName(37));
    }

    [Fact]
    public void HardwareMaps_ResolveMemoryType_PrefersSmbiosOverUnknownLegacy()
    {
        // Dell/Windows often leave MemoryType=0 and put DDR5 in SMBIOSMemoryType.
        Assert.Equal("DDR5", HardwareMaps.ResolveMemoryType(0, 34));
        Assert.Equal("DDR4", HardwareMaps.ResolveMemoryType(26, null));
        Assert.Equal("LPDDR5", HardwareMaps.ResolveMemoryType(null, 35));
        Assert.Null(HardwareMaps.ResolveMemoryType(0, 0));
        Assert.Null(HardwareMaps.ResolveMemoryType(null, null));
    }

    [Fact]
    public void HardwareMaps_ConsensusMemoryType_WhenSticksAgree()
    {
        Assert.Equal("DDR5", HardwareMaps.ConsensusMemoryType(new[] { "DDR5", "DDR5" }));
        Assert.Null(HardwareMaps.ConsensusMemoryType(new[] { "DDR4", "DDR5" }));
        Assert.Equal("LPDDR4", HardwareMaps.ConsensusMemoryType(new string?[] { "LPDDR4", null, "Unknown" }));
    }

    [Fact]
    public void HardwareMaps_InferChannel_FromDellLocator()
    {
        Assert.Equal("Channel A", HardwareMaps.InferChannel("ChannelA-DIMM0", null));
        Assert.Equal("Channel B", HardwareMaps.InferChannel("DIMM B", "BANK 1"));
        Assert.Null(HardwareMaps.InferChannel(null, null));
    }

    [Fact]
    public void HardwareInfo_SerializesNewFields_SnakeCase()
    {
        var hw = new HardwareInfo
        {
            SerialNumber = "SRVTAG01",
            Model = "Latitude 5440",
            Manufacturer = "Dell Inc.",
            RamBytes = 16L * 1024 * 1024 * 1024,
            RamMemoryType = "DDR4",
            Gpus = new List<GpuInfo>
            {
                new() { Name = "Intel UHD", Vendor = "Intel Corporation", DriverVersion = "31.0" },
                new() { Name = "NVIDIA RTX", Vendor = "NVIDIA", AdapterRamBytes = 6L * 1024 * 1024 * 1024 }
            },
            RamModules = new List<RamModuleInfo>
            {
                new()
                {
                    CapacityBytes = 8L * 1024 * 1024 * 1024,
                    SpeedMhz = 3200,
                    PartNumber = "M471A1K43EB1-CWE",
                    Channel = "Channel A",
                    DeviceLocator = "ChannelA-DIMM0",
                    FormFactor = "SODIMM",
                    MemoryType = "DDR4"
                }
            }
        };

        var json = JsonSerializer.Serialize(hw);
        Assert.Contains("\"serial_number\":\"SRVTAG01\"", json, StringComparison.Ordinal);
        Assert.Contains("\"model\":\"Latitude 5440\"", json, StringComparison.Ordinal);
        Assert.Contains("\"gpus\"", json, StringComparison.Ordinal);
        Assert.Contains("\"ram_modules\"", json, StringComparison.Ordinal);
        Assert.Contains("\"ram_memory_type\":\"DDR4\"", json, StringComparison.Ordinal);
        Assert.Contains("\"memory_type\":\"DDR4\"", json, StringComparison.Ordinal);
        Assert.Contains("\"part_number\":\"M471A1K43EB1-CWE\"", json, StringComparison.Ordinal);
        Assert.Contains("\"adapter_ram_bytes\"", json, StringComparison.Ordinal);

        var roundTrip = JsonSerializer.Deserialize<HardwareInfo>(json);
        Assert.NotNull(roundTrip);
        Assert.Equal("SRVTAG01", roundTrip!.SerialNumber);
        Assert.Equal("DDR4", roundTrip.RamMemoryType);
        Assert.Equal(2, roundTrip.Gpus!.Count);
        Assert.Equal("Channel A", roundTrip.RamModules![0].Channel);
        Assert.Equal("DDR4", roundTrip.RamModules[0].MemoryType);
        Assert.Equal(3200, roundTrip.RamModules[0].SpeedMhz);
    }

    [Fact]
    public void InventoryCollector_HardwareCaps_ArePositive()
    {
        Assert.True(InventoryCollector.MaxGpus > 0);
        Assert.True(InventoryCollector.MaxRamModules > 0);
        Assert.True(InventoryCollector.MaxGpus <= 64);
        Assert.True(InventoryCollector.MaxRamModules <= 128);
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
        Assert.Throws<InvalidOperationException>(() => new BadApiClient("http://evil.example.com", "0.8.0"));
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
