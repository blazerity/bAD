using System.Net;

namespace BadAgent;

/// <summary>
/// Только текст <c>Invalid API key</c>. Подпись и 403 ключ не стирают.
/// </summary>
internal static class InvalidKeyReset
{
    public static bool IsInvalidApiKey(Exception? ex)
    {
        if (ex is not AgentApiException api || api.StatusCode != HttpStatusCode.Unauthorized)
        {
            return false;
        }

        var text = api.Message ?? "";
        if (text.Contains("Invalid inventory signature", StringComparison.Ordinal)
            || text.Contains("Inventory signature required", StringComparison.Ordinal))
        {
            return false;
        }

        return text.Contains("Invalid API key", StringComparison.Ordinal);
    }

    public static void Forget(AgentConfig config, BadApiClient client, CancellationToken ct)
    {
        if (!string.IsNullOrWhiteSpace(config.BadId))
        {
            RetiredDevice.Remember(config.BadId);
        }

        config.ApiKey = null;
        config.BadId = null;
        ConfigStore.Save(config);

        var fingerprint = EnrollmentProof.ReadExistingFingerprintHex();
        if (string.IsNullOrWhiteSpace(fingerprint) || string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            return;
        }

        var (hostname, ip, serial) = EnrollmentHints.ForRequest();
        try
        {
            client.SubmitEnrollmentRequestAsync(
                hostname,
                ip,
                serial,
                fingerprint,
                null,
                DeviceIdentity.ReadMachineGuid(),
                EnrollmentHints.ReadSmbiosUuid(),
                ct).GetAwaiter().GetResult();
        }
        catch (Exception)
        {
            // Повторный опрос обновит ту же заявку, вторую строку не создаёт.
        }
    }
}
