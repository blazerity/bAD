using System.Net;

namespace BadAgent;

/// <summary>Ошибка ответа API агента с HTTP status (для offline queue / revoke).</summary>
public sealed class AgentApiException : HttpRequestException
{
    public bool IsAuthFailure =>
        StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden;

    public AgentApiException(HttpStatusCode statusCode, string message)
        : base(message, null, statusCode)
    {
    }
}
