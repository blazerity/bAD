namespace BadAgent;

/// <summary>
/// Тема A / SEC cleartext: единые правила <c>server_url</c> для службы и CLI.
/// В бою — только <c>https://</c>; <c>http://</c> лишь при точном <c>BAD_ALLOW_HTTP=1</c> (lab).
/// </summary>
public static class ServerUrlRules
{
    /// <summary>Сообщение при отклонении cleartext (служба / CLI / Event Log).</summary>
    public const string CleartextHttpRejectedMessage =
        "Cleartext http:// запрещён: укажите https:// в server_url. "
        + "BAD_ALLOW_HTTP=1 — только для lab/локальной разработки, не для production.";

    /// <summary>Не абсолютный http(s) URL.</summary>
    public const string AbsoluteUrlRequiredMessage =
        "server_url должен быть абсолютным URL (https://…; http:// — только lab с BAD_ALLOW_HTTP=1)";

    public const string EmptyUrlMessage = "server_url: пустое значение недопустимо";

    public const string InvalidUrlMessage = "server_url: некорректный URL";

    /// <summary>
    /// Lab opt-in: только точное значение env <c>BAD_ALLOW_HTTP=1</c> (не true/yes).
    /// Не ослаблять и не расширять алиасы.
    /// </summary>
    public static bool IsLabHttpAllowed() =>
        string.Equals(
            Environment.GetEnvironmentVariable("BAD_ALLOW_HTTP"),
            "1",
            StringComparison.Ordinal);

    public static bool IsCleartextRejectedException(Exception ex) =>
        ex is InvalidOperationException
        && string.Equals(ex.Message, CleartextHttpRejectedMessage, StringComparison.Ordinal);

    /// <summary>
    /// Нормализует (trim, без trailing <c>/</c>) и проверяет схему.
    /// </summary>
    public static bool TryNormalize(string? raw, out string normalized, out string? error)
    {
        normalized = "";
        error = null;

        if (string.IsNullOrWhiteSpace(raw))
        {
            error = EmptyUrlMessage;
            return false;
        }

        var url = raw.Trim().TrimEnd('/');
        if (url.Length == 0)
        {
            error = EmptyUrlMessage;
            return false;
        }

        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)
            || (uri.Scheme != Uri.UriSchemeHttps && uri.Scheme != Uri.UriSchemeHttp))
        {
            // Префикс http:// без lab — отдельное сообщение (тема A / bootstrap ≠ HTTP агента).
            if (url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) && !IsLabHttpAllowed())
            {
                error = CleartextHttpRejectedMessage;
                return false;
            }

            error = AbsoluteUrlRequiredMessage;
            return false;
        }

        if (uri.Scheme == Uri.UriSchemeHttp)
        {
            if (!IsLabHttpAllowed())
            {
                error = CleartextHttpRejectedMessage;
                return false;
            }
        }
        else if (uri.Scheme != Uri.UriSchemeHttps)
        {
            error = AbsoluteUrlRequiredMessage;
            return false;
        }

        // Без userinfo в боевом URL (не раздувать поверхность; MSI/CLI не должны класть secrets в URL).
        if (!string.IsNullOrEmpty(uri.UserInfo))
        {
            error = InvalidUrlMessage;
            return false;
        }

        normalized = url;
        return true;
    }

    /// <summary>Для службы: бросает <see cref="InvalidOperationException"/> / <see cref="ArgumentException"/>.</summary>
    public static string RequireNormalized(string? serverUrl)
    {
        if (!TryNormalize(serverUrl, out var normalized, out var error))
        {
            if (string.Equals(error, EmptyUrlMessage, StringComparison.Ordinal))
            {
                throw new ArgumentException("server_url is required", nameof(serverUrl));
            }

            throw new InvalidOperationException(error);
        }

        return normalized;
    }
}
