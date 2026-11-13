using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
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

    public async Task<EnrollResult> EnrollAsync(
        string enrollmentBearer,
        string deviceId,
        string hostname,
        CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/enroll");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", enrollmentBearer);
        req.Content = JsonContent.Create(new
        {
            bad_id = deviceId,
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
        var returnedId = doc.RootElement.GetProperty("bad_id").GetString() ?? deviceId;
        string? signingKey = null;
        if (doc.RootElement.TryGetProperty("signing_key", out var skEl)
            && skEl.ValueKind == JsonValueKind.String)
        {
            signingKey = skEl.GetString();
        }

        return new EnrollResult(apiKey, returnedId, signingKey);
    }

    /// <summary>POST /v1/enrollment-requests — без Bearer; секреты только после approve.</summary>
    public async Task<EnrollmentRequestResult> SubmitEnrollmentRequestAsync(
        string hostname,
        string ip,
        string serial,
        byte[] proof,
        string? badId,
        string? machineGuid,
        string? smbiosUuid,
        CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/enrollment-requests");
        var payload = new Dictionary<string, string>
        {
            ["hostname"] = hostname,
            ["ip"] = ip ?? "",
            ["serial"] = serial ?? "",
            ["proof"] = Convert.ToBase64String(proof),
        };
        if (!string.IsNullOrWhiteSpace(badId))
        {
            payload["bad_id"] = badId.Trim();
        }

        if (!string.IsNullOrWhiteSpace(smbiosUuid))
        {
            payload["machine_guid"] = machineGuid ?? "";
            payload["smbios_uuid"] = smbiosUuid;
        }

        req.Content = JsonContent.Create(payload, options: JsonOptions);

        using var resp = await _http.SendAsync(req, ct);
        if (resp.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            return new EnrollmentRequestResult("missing", null, null, null, RouteMissing: true);
        }

        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new AgentApiException(resp.StatusCode, $"Enrollment request failed: {(int)resp.StatusCode} {body}");
        }

        using var doc = JsonDocument.Parse(body);
        var status = doc.RootElement.TryGetProperty("status", out var stEl)
                       && stEl.ValueKind == JsonValueKind.String
            ? stEl.GetString() ?? "pending"
            : "pending";

        string? returnedBadId = null;
        string? apiKey = null;
        string? signingKey = null;
        if (doc.RootElement.TryGetProperty("bad_id", out var idEl)
            && idEl.ValueKind == JsonValueKind.String)
        {
            returnedBadId = idEl.GetString();
        }

        if (doc.RootElement.TryGetProperty("api_key", out var keyEl)
            && keyEl.ValueKind == JsonValueKind.String)
        {
            apiKey = keyEl.GetString();
        }

        if (doc.RootElement.TryGetProperty("signing_key", out var skEl)
            && skEl.ValueKind == JsonValueKind.String)
        {
            signingKey = skEl.GetString();
        }

        return new EnrollmentRequestResult(status, returnedBadId, apiKey, signingKey, RouteMissing: false);
    }

    /// <summary>Один раз выдать ключ подписи для уже enrolled устройства (secure-channel 3).</summary>
    public async Task<SigningKeyFetchResult> RequestSigningKeyAsync(string apiKey, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/agent/signing-key");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        req.Content = new StringContent("{}", System.Text.Encoding.UTF8, "application/json");

        using var resp = await _http.SendAsync(req, ct);
        if (resp.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            return new SigningKeyFetchResult(null, RouteMissing: true);
        }

        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            throw new AgentApiException(resp.StatusCode, $"Signing key request failed: {(int)resp.StatusCode} {body}");
        }

        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("signing_key", out var el)
                && el.ValueKind == JsonValueKind.String)
            {
                var key = el.GetString();
                if (!string.IsNullOrWhiteSpace(key))
                {
                    return new SigningKeyFetchResult(key.Trim(), RouteMissing: false);
                }
            }
        }
        catch (JsonException)
        {
            // Пустое/не JSON тело — как «секрет не выдан».
        }

        return new SigningKeyFetchResult(null, RouteMissing: false);
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
            bad_id = payload.BadId,
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
                actions = ParseHeartbeatActions(actionsEl);
            }

            if (config is not null)
            {
                return new HeartbeatServerResponse { Config = config, Actions = actions };
            }

            if (actions is not null
                && (actions.Inventory
                    || actions.UpdateCheck
                    || actions.Uninstall))
            {
                return new HeartbeatServerResponse { Config = null, Actions = actions };
            }

            return null;
        }
        catch (JsonException)
        {
            // Heartbeat успешен; разбор тела — best-effort.
            return null;
        }
    }

    private static HeartbeatActions ParseHeartbeatActions(JsonElement actionsEl)
    {
        var a = new HeartbeatActions();
        if (actionsEl.TryGetProperty("inventory", out var inv) && inv.ValueKind == JsonValueKind.True)
        {
            a.Inventory = true;
        }

        if (actionsEl.TryGetProperty("update_check", out var uc) && uc.ValueKind == JsonValueKind.True)
        {
            a.UpdateCheck = true;
        }

        if (actionsEl.TryGetProperty("uninstall", out var un) && un.ValueKind == JsonValueKind.True)
        {
            a.Uninstall = true;
        }

        return a;
    }

    public async Task SendInventoryAsync(
        string apiKey,
        InventorySnapshot snapshot,
        CancellationToken ct,
        ILogger? logger = null)
    {
        AgentSigningKey.TrySignInventory(snapshot, out _);
        var failure = await PostInventoryAsync(apiKey, snapshot, ct);
        LogInventoryAttempt(logger, 1, snapshot, failure);
        if (failure is null)
        {
            return;
        }

        if (!IsSignatureRejection(failure.Value.Body))
        {
            throw new AgentApiException(
                failure.Value.Status,
                $"Inventory failed: {(int)failure.Value.Status} {failure.Value.Body}");
        }

        var oldFingerprint = AgentSigningKey.CurrentFileFingerprint();
        AgentSigningKey.ClearLocal();
        await AgentSigningKey.EnsureFromServerAsync(
            this, apiKey, logger, ct, snapshot.BadId, oldFingerprint);
        AgentSigningKey.TrySignInventory(snapshot, out _);
        var again = await PostInventoryAsync(apiKey, snapshot, ct);
        LogInventoryAttempt(logger, 2, snapshot, again);
        if (again is null)
        {
            return;
        }

        throw new AgentApiException(
            again.Value.Status,
            $"Inventory failed: {(int)again.Value.Status} {again.Value.Body}");
    }

    private static void LogInventoryAttempt(
        ILogger? logger,
        int attempt,
        InventorySnapshot snapshot,
        InventoryPostFailure? failure)
    {
        var trace = AgentSigningKey.TraceSignature(snapshot);
        var statusCode = failure is null ? 200 : (int)failure.Value.Status;
        var detail = failure is null || statusCode != 401
            ? ""
            : DetailText(failure.Value.Body);
        var signed = trace.Signed ? "true" : "false";
        var keyFp = ShortTrace(trace.KeyFp);
        var canonSha = ShortTrace(trace.CanonSha256);
        if (logger is null)
        {
            Console.Error.WriteLine(
                "inventory signature attempt={0} bad_id={1} key_fp={2} signed={3} canon_len={4} canon_sha256={5} sig_len={6} status={7} detail={8}",
                attempt,
                snapshot.BadId,
                keyFp,
                signed,
                trace.CanonLen,
                canonSha,
                trace.SigLen,
                statusCode,
                detail);
            return;
        }

        logger.LogInformation(
            "inventory signature attempt={Attempt} bad_id={DeviceId} key_fp={KeyFp} signed={Signed} canon_len={CanonLen} canon_sha256={CanonSha256} sig_len={SigLen} status={Status} detail={Detail}",
            attempt,
            snapshot.BadId,
            keyFp,
            signed,
            trace.CanonLen,
            canonSha,
            trace.SigLen,
            statusCode,
            detail);
    }

    private static string ShortTrace(string value) =>
        string.IsNullOrEmpty(value) ? "" : value.Length <= 8 ? value : value[..8];

    private static string DetailText(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("detail", out var detail)
                && detail.ValueKind == JsonValueKind.String)
            {
                return detail.GetString() ?? "";
            }
        }
        catch (JsonException)
        {
            return "";
        }

        return "";
    }

    private static bool IsSignatureRejection(string body) =>
        body.Contains("Invalid inventory signature", StringComparison.Ordinal)
        || body.Contains("Inventory signature required", StringComparison.Ordinal);

    /// <summary>Один POST снимка. null — сервер принял.</summary>
    private async Task<InventoryPostFailure?> PostInventoryAsync(
        string apiKey, InventorySnapshot snapshot, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/inventory");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        req.Content = new StringContent(
            JsonSerializer.Serialize(snapshot, AgentSigningKey.InventoryJsonOptions),
            System.Text.Encoding.UTF8,
            "application/json");

        using var resp = await _http.SendAsync(req, ct);
        if (resp.IsSuccessStatusCode)
        {
            _ = await resp.Content.ReadAsStringAsync(ct);
            return null;
        }

        var body = await resp.Content.ReadAsStringAsync(ct);
        return new InventoryPostFailure(resp.StatusCode, body);
    }

    private readonly record struct InventoryPostFailure(System.Net.HttpStatusCode Status, string Body);

    /// <summary>HTML отчёт с сервера (панель): тот же snapshot, что inventory.</summary>
    public async Task<string?> TryPostReportHtmlAsync(string apiKey, InventorySnapshot snapshot, CancellationToken ct)
    {
        AgentSigningKey.TrySignInventory(snapshot, out _);
        var json = JsonSerializer.Serialize(snapshot, AgentSigningKey.InventoryJsonOptions);
        using var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/agent/report.html");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        req.Headers.Accept.ParseAdd("text/html");
        req.Content = new StringContent(json, Encoding.UTF8, "application/json");

        using var resp = await _http.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            return null;
        }

        var media = resp.Content.Headers.ContentType?.MediaType;
        if (!string.IsNullOrEmpty(media)
            && media.Contains("html", StringComparison.OrdinalIgnoreCase))
        {
            return body;
        }

        var trimmed = body.TrimStart();
        if (trimmed.StartsWith("<!DOCTYPE", StringComparison.OrdinalIgnoreCase)
            || trimmed.StartsWith("<html", StringComparison.OrdinalIgnoreCase))
        {
            return body;
        }

        return null;
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
    /// Скачать архив обновления. URL — только relative или same-origin к <see cref="_baseUrl"/> (SEC-009).
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

public readonly record struct EnrollResult(string ApiKey, string BadId, string? SigningKeyBase64);
