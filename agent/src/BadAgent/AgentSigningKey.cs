using System.Security.Cryptography;
using System.Text.Encodings.Web;
using System.Text.Json;
using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.Crypto.Signers;

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

    public readonly record struct InventorySignTrace(
        bool Signed,
        string KeyFp,
        string CanonLen,
        string CanonSha256,
        string SigLen);

    /// <summary>Отпечаток файла, которым только что подписали. Файла нет или он не читается — пусто.</summary>
    public static string CurrentFileFingerprint()
    {
        if (!File.Exists(KeyPath) || !TryLoadPrivateKeyBase64(out var keyB64))
        {
            return "";
        }

        try
        {
            return ComputeFingerprintFromPrivateKeyBase64(keyB64);
        }
        catch (InvalidOperationException)
        {
            return "";
        }
        catch (FormatException)
        {
            return "";
        }
    }

    /// <summary>След только что поставленной подписи. Канон — те же байты, что ушли в Ed25519.</summary>
    public static InventorySignTrace TraceSignature(InventorySnapshot snapshot)
    {
        var signature = snapshot.Signature;
        if (string.IsNullOrWhiteSpace(signature))
        {
            return new InventorySignTrace(false, "", "", "", "0");
        }

        var keyFp = CurrentFileFingerprint();
        var signed = keyFp.Length > 0;
        string canonLen = "";
        string canonSha = "";
        snapshot.Signature = null;
        try
        {
            var payloadJson = JsonSerializer.Serialize(snapshot, InventoryJsonOptions);
            using var doc = JsonDocument.Parse(payloadJson);
            var bytes = CanonicalSigningBytes(doc.RootElement);
            canonLen = bytes.Length.ToString(System.Globalization.CultureInfo.InvariantCulture);
            canonSha = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        }
        catch (JsonException)
        {
            canonLen = "";
            canonSha = "";
        }
        finally
        {
            snapshot.Signature = signature;
        }

        var sigLen = "";
        try
        {
            sigLen = Convert.FromBase64String(signature).Length.ToString(
                System.Globalization.CultureInfo.InvariantCulture);
        }
        catch (FormatException)
        {
            sigLen = "0";
        }

        return new InventorySignTrace(signed, keyFp, canonLen, canonSha, sigLen);
    }

    public static string ComputeFingerprintFromPrivateKeyBase64(string privateKeyBase64)
    {
        var privateKey = Convert.FromBase64String(privateKeyBase64.Trim());
        if (privateKey.Length != 32)
        {
            throw new InvalidOperationException("signing_key must be 32-byte Ed25519 private key (base64)");
        }

        var publicKey = Ed25519PublicKeyBytes(privateKey);
        return Convert.ToHexString(SHA256.HashData(publicKey)).ToLowerInvariant();
    }

    public static void SavePrivateKeyBase64(string privateKeyBase64)
    {
        Directory.CreateDirectory(ConfigStore.ProgramDataDir);
        var tmp = KeyPath + ".tmp";
        File.WriteAllText(tmp, privateKeyBase64.Trim());
        File.Move(tmp, KeyPath, overwrite: true);
        QuietFiles.TryDelete(SkipFetchPath);
    }

    public static void ClearLocal()
    {
        QuietFiles.TryDelete(KeyPath);
        QuietFiles.TryDelete(SkipFetchPath);
        QuietFiles.TryDelete(KeyPath + ".tmp");
    }

    /// <summary>
    /// Один раз с сервера, если локального файла нет. 404 / нет маршрута — без ошибки, без подписи.
    /// </summary>
    public static async Task EnsureFromServerAsync(
        BadApiClient client,
        string apiKey,
        ILogger? logger,
        CancellationToken ct,
        string deviceId = "",
        string oldFingerprint = "")
    {
        if (File.Exists(KeyPath))
        {
            return;
        }

        QuietFiles.TryDelete(SkipFetchPath);

        var result = await client.RequestSigningKeyAsync(apiKey, ct);
        if (result.RouteMissing)
        {
            logger?.LogInformation(
                "Server has no signing-key endpoint; inventory will be sent unsigned (legacy server)");
            LogKeyReplace(logger, deviceId, oldFingerprint, issued: false, newFp: "");
            return;
        }

        if (!string.IsNullOrWhiteSpace(result.SigningKeyBase64))
        {
            SavePrivateKeyBase64(result.SigningKeyBase64);
            var fp = "";
            try
            {
                fp = ComputeFingerprintFromPrivateKeyBase64(result.SigningKeyBase64);
            }
            catch (InvalidOperationException)
            {
                fp = "";
            }
            catch (FormatException)
            {
                fp = "";
            }

            if (fp.Length > 0)
            {
                logger?.LogInformation("Inventory signing key stored (fingerprint sha256={Fingerprint})", fp);
            }

            LogKeyReplace(logger, deviceId, oldFingerprint, issued: true, newFp: fp);
            return;
        }

        logger?.LogInformation(
            "Signing key not returned; inventory stays unsigned until the next request");
        LogKeyReplace(logger, deviceId, oldFingerprint, issued: false, newFp: "");
    }

    private static void LogKeyReplace(
        ILogger? logger, string deviceId, string oldFp, bool issued, string newFp)
    {
        var issuedText = issued ? "true" : "false";
        if (logger is null)
        {
            Console.Error.WriteLine(
                "inventory signing key replace device_id={0} old_fp={1} issued={2} new_fp={3}",
                deviceId,
                oldFp,
                issuedText,
                newFp);
            return;
        }

        logger.LogInformation(
            "inventory signing key replace device_id={DeviceId} old_fp={OldFp} issued={Issued} new_fp={NewFp}",
            deviceId,
            oldFp,
            issuedText,
            newFp);
    }

    public static bool TrySignInventory(InventorySnapshot snapshot, out string signatureBase64)
    {
        signatureBase64 = "";
        if (!TryLoadPrivateKeyBase64(out var keyB64))
        {
            snapshot.Signature = null;
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

        var sig = Ed25519Sign(bytes, privateKey);
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

    private static byte[] Ed25519PublicKeyBytes(byte[] seed32)
    {
        var privateParams = new Ed25519PrivateKeyParameters(seed32, 0);
        var publicParams = (Ed25519PublicKeyParameters)privateParams.GeneratePublicKey();
        return publicParams.GetEncoded();
    }

    private static byte[] Ed25519Sign(byte[] message, byte[] seed32)
    {
        var privateParams = new Ed25519PrivateKeyParameters(seed32, 0);
        var signer = new Ed25519Signer();
        signer.Init(true, privateParams);
        signer.BlockUpdate(message, 0, message.Length);
        return signer.GenerateSignature();
    }
}

public readonly record struct SigningKeyFetchResult(
    string? SigningKeyBase64,
    bool RouteMissing);
