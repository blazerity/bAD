using System.Security.Cryptography;
using System.Text;
using BadAgent;

namespace BadAgent.Tests;

public class UpdateAndServiceTests
{
    [Theory]
    [InlineData("0.2.0", "0.1.0", true)]
    [InlineData("0.1.0", "0.1.0", false)]
    [InlineData("0.1.0", "0.2.0", false)]
    [InlineData("v1.0.0", "0.9.9", true)]
    [InlineData("1.2.3-beta", "1.2.2", true)]
    [InlineData("not-a-version", "0.1.0", false)]
    [InlineData("0.1.0", "bogus", true)]
    public void VersionUtil_IsNewer(string candidate, string current, bool expected)
    {
        Assert.Equal(expected, VersionUtil.IsNewer(candidate, current));
    }

    [Fact]
    public void VersionUtil_VerifySha256File()
    {
        var dir = Path.Combine(Path.GetTempPath(), "bad-sha-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, "payload.bin");
        try
        {
            var bytes = Encoding.UTF8.GetBytes("hello-bad-agent");
            File.WriteAllBytes(path, bytes);
            var expected = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
            Assert.True(VersionUtil.VerifySha256File(path, expected));
            Assert.False(VersionUtil.VerifySha256File(path, new string('0', 64)));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void UpdateCheckResponse_FromJson()
    {
        var json = """
            {"update_available":true,"version":"0.2.0","sha256":"abc","url":"/v1/agent/update/msi","msi_name":"bad-agent-0.2.0.msi"}
            """;
        var parsed = UpdateCheckResponse.FromJson(json);
        Assert.True(parsed.UpdateAvailable);
        Assert.Equal("0.2.0", parsed.Version);
        Assert.Equal("abc", parsed.Sha256);
        Assert.Equal("/v1/agent/update/msi", parsed.Url);
        Assert.Equal("bad-agent-0.2.0.msi", parsed.MsiName);
    }

    [Fact]
    public void ServiceCli_UnknownCommand_Returns2()
    {
        var code = ServiceCli.Run(new[] { "nope" });
        Assert.Equal(2, code);
    }

    [Fact]
    public void ServiceCli_Help_Returns0()
    {
        Assert.Equal(0, ServiceCli.Run(new[] { "help" }));
    }

    [Fact]
    public void ServiceCli_Status_OnNonWindows_Fails()
    {
        if (OperatingSystem.IsWindows())
        {
            return; // skip assertion on Windows CI
        }

        var code = ServiceCli.Run(new[] { "status" });
        Assert.Equal(1, code);
    }

    [Fact]
    public void ServiceCli_ServiceName()
    {
        Assert.Equal("BlazerityAssetDiscovery", ServiceCli.ServiceName);
    }
}
