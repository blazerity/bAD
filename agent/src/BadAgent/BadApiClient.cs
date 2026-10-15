using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace BadAgent;

public sealed class BadApiClient : IDisposable
{
    private readonly HttpClient _http;
    private readonly string _baseUrl;
    private readonly string _agentVersion;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = null
    };

    public BadApiClient(string serverUrl, string agentVersion)
    {
        if (string.IsNullOrWhiteSpace(serverUrl))
        {
            throw new ArgumentException("server_url is required", nameof(serverUrl));
        }

        var allowHttp = string.Equals(
            Environment.GetEnvironmentVariable("BAD_ALLOW_HTTP"), "1", StringComparison.Ordinal);

        if (serverUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase) && !allowHttp)
        {
            throw new InvalidOperationException(
                "Cleartext http:// server URLs are not allowed; use https:// (or BAD_ALLOW_HTTP=1 for local dev)");
        }

        if (!serverUrl.StartsWith("https://", StringComparison.OrdinalIgnoreCase)
            && !serverUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("server_url must be an absolute http(s) URL");
        }

        _baseUrl = serverUrl.TrimEnd('/');
        _agentVersion = agentVersion;
        var handler = new HttpClientHandler
        {
            // Proper TLS certificate validation (do not bypass)
            ServerCertificateCustomValidationCallback = null,
            CheckCertificateRevocationList = true
        };
        _http = new HttpClient(handler)
        {
            Timeout = TimeSpan.FromSeconds(60)
        };
        _http.DefaultRequestHeaders.UserAgent.ParseAdd($"bad-agent/{agentVersion}");
    }

    public async Task<(string ApiKey, string DeviceId)> EnrollAsync(
        string enrollmentToken,
        string deviceId,
        string hostname,
        CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/enroll");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", enrollmentToken);
        req.Content = JsonContent.Create(new
        {
            device_id = deviceId,
            hostname,
            agent_version = _agentVersion
        });

        using var resp = await _http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Enroll failed: {(int)resp.StatusCode} {body}");
        }

        using var doc = JsonDocument.Parse(body);
        var apiKey = doc.RootElement.GetProperty("api_key").GetString()
                     ?? throw new InvalidOperationException("enroll response missing api_key");
        var returnedId = doc.RootElement.GetProperty("device_id").GetString() ?? deviceId;
        return (apiKey, returnedId);
    }

    public async Task SendHeartbeatAsync(
        string apiKey,
        string deviceId,
        string? lastInventoryAt,
        CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/heartbeat");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        req.Content = JsonContent.Create(new
        {
            device_id = deviceId,
            agent_version = _agentVersion,
            last_inventory_at = lastInventoryAt
        });

        using var resp = await _http.SendAsync(req, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            throw new HttpRequestException($"Heartbeat failed: {(int)resp.StatusCode} {body}");
        }
    }

    public async Task SendInventoryAsync(string apiKey, InventorySnapshot snapshot, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/inventory");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        req.Content = new StringContent(
            JsonSerializer.Serialize(snapshot, JsonOptions),
            System.Text.Encoding.UTF8,
            "application/json");

        using var resp = await _http.SendAsync(req, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            throw new HttpRequestException($"Inventory failed: {(int)resp.StatusCode} {body}");
        }
    }

    public async Task<UpdateCheckResponse> CheckUpdateAsync(string apiKey, string currentVersion, CancellationToken ct)
    {
        var url = $"{_baseUrl}/v1/agent/update/check?current={Uri.EscapeDataString(currentVersion)}";
        using var req = new HttpRequestMessage(HttpMethod.Get, url);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await _http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Update check failed: {(int)resp.StatusCode} {body}");
        }

        return UpdateCheckResponse.FromJson(body);
    }

    public async Task DownloadUpdateMsiAsync(string apiKey, string relativeOrAbsoluteUrl, string destPath, CancellationToken ct)
    {
        var url = relativeOrAbsoluteUrl.StartsWith("http", StringComparison.OrdinalIgnoreCase)
            ? relativeOrAbsoluteUrl
            : $"{_baseUrl}/{relativeOrAbsoluteUrl.TrimStart('/')}";

        using var req = new HttpRequestMessage(HttpMethod.Get, url);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            throw new HttpRequestException($"Update download failed: {(int)resp.StatusCode} {body}");
        }

        Directory.CreateDirectory(Path.GetDirectoryName(destPath)!);
        await using var fs = File.Create(destPath);
        await resp.Content.CopyToAsync(fs, ct);
    }

    public void Dispose() => _http.Dispose();
}
