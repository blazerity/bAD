using System.Text.Json;
using System.Text.Json.Serialization;

namespace BadAgent;

/// <summary>
/// Локальная очередь неотправленных inventory/heartbeat в ProgramData.
/// Retry с backoff; не молча терять навсегда (cap по числу файлов + возраст).
/// </summary>
public static class OfflineQueue
{
    public const int MaxItems = 64;
    public const int MaxAgeDays = 14;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = false
    };

    public static string QueueDir => Path.Combine(ConfigStore.ProgramDataDir, "queue");

    public static string MetaPath => Path.Combine(QueueDir, "meta.json");

    public static void EnqueueInventory(InventorySnapshot snapshot)
    {
        var json = JsonSerializer.Serialize(snapshot, JsonOptions);
        Enqueue("inventory", json);
    }

    public static void EnqueueHeartbeat(HeartbeatQueuePayload payload)
    {
        var json = JsonSerializer.Serialize(payload, JsonOptions);
        Enqueue("heartbeat", json);
    }

    public static void Enqueue(string kind, string jsonBody)
    {
        Directory.CreateDirectory(QueueDir);

        var id = $"{DateTime.UtcNow:yyyyMMddHHmmssfff}-{Guid.NewGuid():N}"[..40];
        var item = new QueueItem
        {
            Id = id,
            Kind = kind,
            CreatedAtUtc = DateTime.UtcNow.ToString("O"),
            Body = jsonBody,
            Attempts = 0
        };

        var path = ItemPath(id);
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(item, JsonOptions));
        File.Move(tmp, path, overwrite: true);
        // Один prune после записи: возраст + cap MaxItems.
        PruneUnlocked();
    }

    /// <summary>
    /// Пытается отправить накопившееся. При auth failure — стоп (caller чистит ключ).
    /// При сетевых ошибках — backoff в meta.
    /// </summary>
    public static async Task<OfflineFlushResult> FlushAsync(
        BadApiClient client,
        string apiKey,
        CancellationToken ct)
    {
        Directory.CreateDirectory(QueueDir);
        var meta = LoadMeta();
        if (meta.NextRetryUtc is { } next && DateTime.UtcNow < next)
        {
            return OfflineFlushResult.CreateDeferred(next);
        }

        var files = Directory.GetFiles(QueueDir, "*.json")
            .Where(f => !string.Equals(Path.GetFileName(f), "meta.json", StringComparison.OrdinalIgnoreCase))
            .OrderBy(f => f, StringComparer.Ordinal)
            .ToList();

        var sent = 0;
        foreach (var file in files)
        {
            ct.ThrowIfCancellationRequested();
            QueueItem? item;
            try
            {
                item = JsonSerializer.Deserialize<QueueItem>(File.ReadAllText(file));
            }
            catch
            {
                TryDelete(file);
                continue;
            }

            if (item is null || string.IsNullOrWhiteSpace(item.Body))
            {
                TryDelete(file);
                continue;
            }

            if (IsTooOld(item))
            {
                TryDelete(file);
                continue;
            }

            try
            {
                if (string.Equals(item.Kind, "inventory", StringComparison.OrdinalIgnoreCase))
                {
                    var snap = JsonSerializer.Deserialize<InventorySnapshot>(item.Body)
                               ?? throw new InvalidOperationException("bad inventory payload");
                    await client.SendInventoryAsync(apiKey, snap, ct);
                }
                else if (string.Equals(item.Kind, "heartbeat", StringComparison.OrdinalIgnoreCase))
                {
                    var hb = JsonSerializer.Deserialize<HeartbeatQueuePayload>(item.Body)
                             ?? throw new InvalidOperationException("bad heartbeat payload");
                    await client.SendHeartbeatAsync(apiKey, hb, ct);
                }
                else
                {
                    TryDelete(file);
                    continue;
                }

                TryDelete(file);
                sent++;
                meta.ConsecutiveFailures = 0;
                meta.NextRetryUtc = null;
                SaveMeta(meta);
            }
            catch (AgentApiException ex) when (ex.IsAuthFailure)
            {
                item.Attempts++;
                SaveItem(file, item);
                return OfflineFlushResult.CreateAuthFailed(ex);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                item.Attempts++;
                SaveItem(file, item);
                meta.ConsecutiveFailures = Math.Min(meta.ConsecutiveFailures + 1, 20);
                var delay = BackoffDelay(meta.ConsecutiveFailures);
                meta.NextRetryUtc = DateTime.UtcNow.Add(delay);
                SaveMeta(meta);
                return OfflineFlushResult.CreateFailed(delay, meta.ConsecutiveFailures, ex);
            }
        }

        meta.ConsecutiveFailures = 0;
        meta.NextRetryUtc = null;
        SaveMeta(meta);
        return OfflineFlushResult.CreateOk(sent);
    }

    public static int CountPending()
    {
        if (!Directory.Exists(QueueDir))
        {
            return 0;
        }

        return Directory.GetFiles(QueueDir, "*.json")
            .Count(f => !string.Equals(Path.GetFileName(f), "meta.json", StringComparison.OrdinalIgnoreCase));
    }

    private static TimeSpan BackoffDelay(int failures)
    {
        // 1m, 2m, 4m … cap 6h
        var minutes = Math.Min(360.0, Math.Pow(2, Math.Min(failures, 10)));
        return TimeSpan.FromMinutes(Math.Max(1.0, minutes));
    }

    private static bool IsTooOld(QueueItem item)
    {
        if (!DateTime.TryParse(item.CreatedAtUtc, null,
                System.Globalization.DateTimeStyles.RoundtripKind, out var created))
        {
            // Битая метка времени — выбросить (иначе живёт до MaxItems prune).
            return true;
        }

        return DateTime.UtcNow - created.ToUniversalTime() > TimeSpan.FromDays(MaxAgeDays);
    }

    private static void PruneUnlocked()
    {
        if (!Directory.Exists(QueueDir))
        {
            return;
        }

        var files = Directory.GetFiles(QueueDir, "*.json")
            .Where(f => !string.Equals(Path.GetFileName(f), "meta.json", StringComparison.OrdinalIgnoreCase))
            .OrderBy(f => f, StringComparer.Ordinal)
            .ToList();

        foreach (var file in files.ToList())
        {
            try
            {
                var item = JsonSerializer.Deserialize<QueueItem>(File.ReadAllText(file));
                if (item is not null && IsTooOld(item))
                {
                    TryDelete(file);
                    files.Remove(file);
                }
            }
            catch
            {
                TryDelete(file);
                files.Remove(file);
            }
        }

        while (files.Count > MaxItems)
        {
            TryDelete(files[0]);
            files.RemoveAt(0);
        }
    }

    private static string ItemPath(string id) => Path.Combine(QueueDir, id + ".json");

    private static void SaveItem(string path, QueueItem item)
    {
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(item, JsonOptions));
        File.Move(tmp, path, overwrite: true);
    }

    private static QueueMeta LoadMeta()
    {
        try
        {
            if (File.Exists(MetaPath))
            {
                return JsonSerializer.Deserialize<QueueMeta>(File.ReadAllText(MetaPath)) ?? new QueueMeta();
            }
        }
        catch
        {
            // ignore
        }

        return new QueueMeta();
    }

    private static void SaveMeta(QueueMeta meta)
    {
        Directory.CreateDirectory(QueueDir);
        var tmp = MetaPath + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(meta, JsonOptions));
        File.Move(tmp, MetaPath, overwrite: true);
    }

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch
        {
            // ignore
        }
    }

    private sealed class QueueItem
    {
        [JsonPropertyName("id")]
        public string Id { get; set; } = "";

        [JsonPropertyName("kind")]
        public string Kind { get; set; } = "";

        [JsonPropertyName("created_at_utc")]
        public string CreatedAtUtc { get; set; } = "";

        [JsonPropertyName("body")]
        public string Body { get; set; } = "";

        [JsonPropertyName("attempts")]
        public int Attempts { get; set; }
    }

    private sealed class QueueMeta
    {
        [JsonPropertyName("consecutive_failures")]
        public int ConsecutiveFailures { get; set; }

        [JsonPropertyName("next_retry_utc")]
        public DateTime? NextRetryUtc { get; set; }
    }
}

public sealed class HeartbeatQueuePayload
{
    [JsonPropertyName("device_id")]
    public string DeviceId { get; set; } = "";

    [JsonPropertyName("last_inventory_at")]
    public string? LastInventoryAt { get; set; }

    [JsonPropertyName("config_version")]
    public string? ConfigVersion { get; set; }

    [JsonPropertyName("last_inventory_ok")]
    public bool? LastInventoryOk { get; set; }

    [JsonPropertyName("last_inventory_error")]
    public string? LastInventoryError { get; set; }

    [JsonPropertyName("agent_uptime_seconds")]
    public long? AgentUptimeSeconds { get; set; }

    [JsonPropertyName("system_drive_free_bytes")]
    public long? SystemDriveFreeBytes { get; set; }

    /// <summary>Provenance: manual / agent_local keys (+ optional settings / server_url).</summary>
    [JsonPropertyName("config_local")]
    public ConfigLocalPayload? ConfigLocal { get; set; }
}

public sealed class OfflineFlushResult
{
    public bool Success { get; private init; }
    public bool AuthFailed { get; private init; }
    public bool Deferred { get; private init; }
    public int Sent { get; private init; }
    public TimeSpan? RetryAfter { get; private init; }
    public DateTime? NextRetryUtc { get; private init; }
    public int Failures { get; private init; }
    public AgentApiException? AuthException { get; private init; }
    public Exception? Error { get; private init; }

    public static OfflineFlushResult CreateOk(int sent) => new() { Success = true, Sent = sent };

    public static OfflineFlushResult CreateDeferred(DateTime next) =>
        new() { Deferred = true, NextRetryUtc = next };

    public static OfflineFlushResult CreateFailed(TimeSpan retryAfter, int failures, Exception? error = null) =>
        new() { RetryAfter = retryAfter, Failures = failures, Error = error };

    public static OfflineFlushResult CreateAuthFailed(AgentApiException ex) =>
        new() { AuthFailed = true, AuthException = ex };
}
