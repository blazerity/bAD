using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace BadAgent;

public sealed class BadApiClient : IDisposable
{
    /// <summary>Совместимость с CLI/Worker: то же, что <see cref="ServerUrlRules.CleartextHttpRejectedMessage"/>.</summary>
    public const string CleartextHttpRejectedMessage = ServerUrlRules.CleartextHttpRejectedMessage;

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
        // Тема A: https в бою; http:// только BAD_ALLOW_HTTP=1 (lab). Не ослаблять.
        _baseUrl = ServerUrlRules.RequireNormalized(serverUrl);
        _agentVersion = agentVersion;
        var handler = new HttpClientHandler
        {
            // Нормальная проверка TLS-сертификата (не обходить)
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
            throw new AgentApiException(resp.StatusCode, $"Enroll failed: {(int)resp.StatusCode} {body}");
        }

        using var doc = JsonDocument.Parse(body);
        var apiKey = doc.RootElement.GetProperty("api_key").GetString()
                     ?? throw new InvalidOperationException("enroll response missing api_key");
        var returnedId = doc.RootElement.GetProperty("device_id").GetString() ?? deviceId;
        return (apiKey, returnedId);
    }

    public async Task<HeartbeatServerResponse?> SendHeartbeatAsync(
        string apiKey,
        HeartbeatQueuePayload payload,
        CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/heartbeat");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        // config_local — контракт API Lead (keys = agent_local; optional settings / server_url).
        req.Content = JsonContent.Create(new
        {
            device_id = payload.DeviceId,
            agent_version = _agentVersion,
            last_inventory_at = payload.LastInventoryAt,
            config_version = payload.ConfigVersion,
            last_inventory_ok = payload.LastInventoryOk,
            last_inventory_error = payload.LastInventoryError,
            agent_uptime_seconds = payload.AgentUptimeSeconds,
            system_drive_free_bytes = payload.SystemDriveFreeBytes,
            config_local = payload.ConfigLocal
        }, options: JsonOptions);

        using var resp = await _http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new AgentApiException(resp.StatusCode, $"Heartbeat failed: {(int)resp.StatusCode} {body}");
        }

        return ParseHeartbeatResponse(body);
    }

    internal static HeartbeatServerResponse? ParseHeartbeatResponse(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            RemoteAgentConfigResponse? config = null;
            if (root.TryGetProperty("config", out var configEl)
                && configEl.ValueKind == JsonValueKind.Object)
            {
                config = JsonSerializer.Deserialize<RemoteAgentConfigResponse>(configEl.GetRawText());
            }

            HeartbeatActions? actions = null;
            if (root.TryGetProperty("actions", out var actionsEl)
                && actionsEl.ValueKind == JsonValueKind.Object)
            {
                actions = JsonSerializer.Deserialize<HeartbeatActions>(actionsEl.GetRawText());
            }

            if (config is null && actions is null)
            {
                return null;
            }

            return new HeartbeatServerResponse { Config = config, Actions = actions };
        }
        catch (JsonException)
        {
            // Heartbeat успешен; разбор тела — best-effort.
            return null;
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
            throw new AgentApiException(resp.StatusCode, $"Inventory failed: {(int)resp.StatusCode} {body}");
        }
    }

    public async Task<UpdateCheckResponse> CheckUpdateAsync(
        string apiKey,
        string currentVersion,
        CancellationToken ct)
    {
        // Сервер 0.10 сам берёт target из effective device config (не из query).
        var url =
            $"{_baseUrl}/v1/agent/update/check?current={Uri.EscapeDataString(currentVersion)}";
        using var req = new HttpRequestMessage(HttpMethod.Get, url);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await _http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new AgentApiException(resp.StatusCode, $"Update check failed: {(int)resp.StatusCode} {body}");
        }

        return UpdateCheckResponse.FromJson(body);
    }

    /// <summary>
    /// Скачать MSI обновления. URL — только relative или same-origin к <see cref="_baseUrl"/> (SEC-009).
    /// </summary>
    public async Task DownloadUpdateMsiAsync(string apiKey, string relativeOrAbsoluteUrl, string destPath, CancellationToken ct)
    {
        var url = UpdatePathUtil.ResolveSameOriginUpdateUrl(_baseUrl, relativeOrAbsoluteUrl);

        using var req = new HttpRequestMessage(HttpMethod.Get, url);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

        using var resp = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            throw new AgentApiException(resp.StatusCode, $"Update download failed: {(int)resp.StatusCode} {body}");
        }

        Directory.CreateDirectory(Path.GetDirectoryName(destPath)!);
        await using var fs = File.Create(destPath);
        await resp.Content.CopyToAsync(fs, ct);
    }

    public void Dispose() => _http.Dispose();
}
