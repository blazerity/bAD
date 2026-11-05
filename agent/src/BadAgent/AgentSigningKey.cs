using System.Security.Cryptography;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace BadAgent;

/// <summary>
/// Ed25519 ключ подписи inventory (secure-channel 3). Секрет — файл рядом с config.json, не в логах.
/// </summary>
public static class AgentSigningKey
{
    /// <summary>%ProgramData%\blazerity\bAD\signing_key — одна строка base64 (32 байта raw private).</summary>
    public static string KeyPath => Path.Combine(ConfigStore.ProgramDataDir, "signing_key");

    /// <summary>Маркер: POST /v1/agent/signing-key недоступен или секрет уже выдан на сервере.</summary>
    public static string SkipFetchPath => Path.Combine(ConfigStore.ProgramDataDir, "signing_key.skip");

    public static bool TryLoadPrivateKeyBase64(out string privateKeyBase64)
    {
        privateKeyBase64 = "";
        try
        {
            if (!File.Exists(KeyPath))
            {
                return false;
            }

            var text = File.ReadAllText(KeyPath).Trim();
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            privateKeyBase64 = text;
            return true;
        }
        catch
        {
            return false;
        }
    }

    public static string ComputeFingerprintFromPrivateKeyBase64(string privateKeyBase64)
    {
        var privateKey = Convert.FromBase64String(privateKeyBase64.Trim());
        if (privateKey.Length != 32)
        {
            throw new InvalidOperationException("signing_key must be 32-byte Ed25519 private key (base64)");
        }

        if (!Ed25519.TryGetPublicKey(privateKey, out var publicKey) || publicKey.Length != 32)
        {
            throw new InvalidOperationException("invalid Ed25519 private key");
        }

        return Convert.ToHexString(SHA256.HashData(publicKey)).ToLowerInvariant();
    }

    public static void SavePrivateKeyBase64(string privateKeyBase64)
    {
        Directory.CreateDirectory(ConfigStore.ProgramDataDir);
        var tmp = KeyPath + ".tmp";
        File.WriteAllText(tmp, privateKeyBase64.Trim());
        File.Move(tmp, KeyPath, overwrite: true);
        TryDelete(SkipFetchPath);
    }

    public static void MarkFetchUnavailable()
    {
        Directory.CreateDirectory(ConfigStore.ProgramDataDir);
        File.WriteAllText(SkipFetchPath, DateTime.UtcNow.ToString("O"));
    }

    public static void ClearLocal()
    {
        TryDelete(KeyPath);
        TryDelete(SkipFetchPath);
        TryDelete(KeyPath + ".tmp");
    }

    /// <summary>
    /// Один раз с сервера, если локального файла нет. 404 / нет маршрута — без ошибки, без подписи.
    /// </summary>
    public static async Task EnsureFromServerAsync(
        BadApiClient client,
        string apiKey,
        ILogger logger,
        CancellationToken ct)
    {
        if (TryLoadPrivateKeyBase64(out _))
        {
            return;
        }

        if (File.Exists(SkipFetchPath))
        {
            return;
        }

        var result = await client.RequestSigningKeyAsync(apiKey, ct);
        if (result.RouteMissing)
        {
            logger?.LogInformation(
                "Server has no signing-key endpoint; inventory will be sent unsigned (legacy server)");
            MarkFetchUnavailable();
            return;
        }

        if (!string.IsNullOrWhiteSpace(result.SigningKeyBase64))
        {
            SavePrivateKeyBase64(result.SigningKeyBase64);
            var fp = ComputeFingerprintFromPrivateKeyBase64(result.SigningKeyBase64);
            logger?.LogInformation("Inventory signing key stored (fingerprint sha256={Fingerprint})", fp);
            return;
        }

        logger?.LogInformation(
            "Signing key not returned (already issued on server or empty response); sending inventory unsigned");
        MarkFetchUnavailable();
    }

    public static bool TrySignInventory(InventorySnapshot snapshot, out string signatureBase64)
    {
        signatureBase64 = "";
        if (!TryLoadPrivateKeyBase64(out var keyB64))
        {
            return false;
        }

        snapshot.Signature = null;
        var payloadJson = JsonSerializer.Serialize(snapshot, InventoryJsonOptions);
        using var doc = JsonDocument.Parse(payloadJson);
        var bytes = CanonicalSigningBytes(doc.RootElement);
        var privateKey = Convert.FromBase64String(keyB64.Trim());
        if (privateKey.Length != 32)
        {
            return false;
        }

        var sig = Ed25519.Sign(bytes, privateKey);
        signatureBase64 = Convert.ToBase64String(sig);
        snapshot.Signature = signatureBase64;
        return true;
    }

    internal static readonly JsonSerializerOptions InventoryJsonOptions = new()
    {
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = null,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    /// <summary>Канон как server security.inventory_signing_bytes (sort_keys, compact, UTF-8).</summary>
    internal static byte[] CanonicalSigningBytes(JsonElement element)
    {
        using var ms = new MemoryStream();
        using (var writer = new Utf8JsonWriter(ms, new JsonWriterOptions
               {
                   Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
               }))
        {
            WriteCanonicalJson(writer, element);
        }

        return ms.ToArray();
    }

    private static void WriteCanonicalJson(Utf8JsonWriter writer, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var prop in element.EnumerateObject().OrderBy(p => p.Name, StringComparer.Ordinal))
                {
                    if (string.Equals(prop.Name, "signature", StringComparison.Ordinal))
                    {
                        continue;
                    }

                    writer.WritePropertyName(prop.Name);
                    WriteCanonicalJson(writer, prop.Value);
                }

                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in element.EnumerateArray())
                {
                    WriteCanonicalJson(writer, item);
                }

                writer.WriteEndArray();
                break;
            case JsonValueKind.String:
                writer.WriteStringValue(element.GetString());
                break;
            case JsonValueKind.Number:
                writer.WriteRawValue(element.GetRawText());
                break;
            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;
            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;
            case JsonValueKind.Null:
                writer.WriteNullValue();
                break;
            default:
                writer.WriteRawValue(element.GetRawText());
                break;
        }
    }

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch
        {
            // ignore
        }
    }
}

public readonly record struct SigningKeyFetchResult(
    string? SigningKeyBase64,
    bool RouteMissing);
