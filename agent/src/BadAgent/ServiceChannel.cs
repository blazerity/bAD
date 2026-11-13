using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Text.Json;

namespace BadAgent;

/// <summary>Локальный канал одной машины: CLI просит, служба bADagent отвечает. Ключ в ответ не входит.</summary>
internal static class ServiceChannel
{
    public const string PipeName = "bad-agent-cli";

    private static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    private static readonly HashSet<string> SecretNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "api_key",
        "apikey",
        "signing_key",
        "signingkey",
        "enrollment_token",
        "enrollment_code",
        "enrollmentcode"
    };

    public static void Listen(IHostApplicationLifetime lifetime, CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            NamedPipeServerStream? server = null;
            try
            {
                server = CreateServer();
                server.WaitForConnectionAsync(stoppingToken).GetAwaiter().GetResult();
                var request = ReadFrame(server);
                var reply = ServiceCommands.Dispatch(request);
                WriteFrame(server, reply);
                if (ReplyStops(reply))
                {
                    lifetime.StopApplication();
                    return;
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                return;
            }
            catch (Exception)
            {
                // Один кривой клиент не останавливает службу.
            }
            finally
            {
                server?.Dispose();
            }
        }
    }

    public static JsonDocument? Call(object request, int connectMilliseconds = 2000)
    {
        try
        {
            using var pipe = new NamedPipeClientStream(
                ".", PipeName, PipeDirection.InOut, PipeOptions.None);
            pipe.Connect(connectMilliseconds);
            pipe.ReadTimeout = 15 * 60 * 1000;
            WriteFrame(pipe, JsonSerializer.Serialize(request, Json));
            var json = StripSecrets(ReadFrame(pipe));
            return JsonDocument.Parse(json);
        }
        catch (Exception)
        {
            return null;
        }
    }

    public static int Print(JsonDocument reply)
    {
        if (reply.RootElement.TryGetProperty("lines", out var lines) && lines.ValueKind == JsonValueKind.Array)
        {
            foreach (var line in lines.EnumerateArray())
            {
                var field = line.TryGetProperty("field", out var fieldEl) ? fieldEl.GetString() ?? "" : "";
                var value = line.TryGetProperty("value", out var valueEl) ? valueEl.GetString() : "";
                string? status = null;
                if (line.TryGetProperty("status", out var statusEl) && statusEl.ValueKind == JsonValueKind.String)
                {
                    status = statusEl.GetString();
                }

                CliColumns.Write(field, value, status);
            }
        }

        if (reply.RootElement.TryGetProperty("tail", out var tail) && tail.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in tail.EnumerateArray())
            {
                if (item.ValueKind == JsonValueKind.String)
                {
                    Console.WriteLine(item.GetString());
                }
            }
        }

        if (reply.RootElement.TryGetProperty("exit", out var exitEl) && exitEl.TryGetInt32(out var exit))
        {
            return exit;
        }

        return 1;
    }

    public static void ServiceDown() =>
        CliColumns.Write("Служба", "не запущена", "ошибка");

    private static bool ReplyStops(string reply)
    {
        try
        {
            using var doc = JsonDocument.Parse(reply);
            return doc.RootElement.TryGetProperty("stop", out var stop) && stop.ValueKind == JsonValueKind.True;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static NamedPipeServerStream CreateServer()
    {
        if (!OperatingSystem.IsWindows())
        {
            return new NamedPipeServerStream(
                PipeName,
                PipeDirection.InOut,
                1,
                PipeTransmissionMode.Byte,
                PipeOptions.Asynchronous);
        }

        var security = new PipeSecurity();
        security.AddAccessRule(new PipeAccessRule(
            new SecurityIdentifier(WellKnownSidType.AuthenticatedUserSid, null),
            PipeAccessRights.ReadWrite,
            AccessControlType.Allow));
        var current = WindowsIdentity.GetCurrent().User;
        if (current is not null)
        {
            security.AddAccessRule(new PipeAccessRule(
                current, PipeAccessRights.FullControl, AccessControlType.Allow));
        }

        return NamedPipeServerStreamAcl.Create(
            PipeName,
            PipeDirection.InOut,
            1,
            PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous,
            0,
            0,
            security);
    }

    private static void WriteFrame(Stream stream, string json)
    {
        var bytes = Encoding.UTF8.GetBytes(json);
        var len = BitConverter.GetBytes(bytes.Length);
        stream.Write(len, 0, len.Length);
        stream.Write(bytes, 0, bytes.Length);
        stream.Flush();
    }

    private static string ReadFrame(Stream stream)
    {
        var lenBuf = new byte[4];
        ReadExact(stream, lenBuf);
        var len = BitConverter.ToInt32(lenBuf, 0);
        if (len < 2 || len > 32 * 1024 * 1024)
        {
            throw new IOException("bad frame");
        }

        var body = new byte[len];
        ReadExact(stream, body);
        return Encoding.UTF8.GetString(body);
    }

    private static void ReadExact(Stream stream, byte[] buffer)
    {
        var offset = 0;
        while (offset < buffer.Length)
        {
            var read = stream.Read(buffer, offset, buffer.Length - offset);
            if (read == 0)
            {
                throw new EndOfStreamException();
            }

            offset += read;
        }
    }

    private static string StripSecrets(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            return JsonSerializer.Serialize(Strip(doc.RootElement));
        }
        catch (JsonException)
        {
            return "{\"exit\":1,\"lines\":[{\"field\":\"Служба\",\"value\":\"ответ без разбора\",\"status\":\"ошибка\"}]}";
        }
    }

    private static object? Strip(JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                var map = new Dictionary<string, object?>();
                foreach (var prop in element.EnumerateObject())
                {
                    if (SecretNames.Contains(prop.Name))
                    {
                        continue;
                    }

                    map[prop.Name] = Strip(prop.Value);
                }

                return map;
            case JsonValueKind.Array:
                return element.EnumerateArray().Select(Strip).ToList();
            case JsonValueKind.String:
                return element.GetString();
            case JsonValueKind.Number:
                return element.TryGetInt64(out var n) ? n : element.GetDouble();
            case JsonValueKind.True:
                return true;
            case JsonValueKind.False:
                return false;
            default:
                return null;
        }
    }
}
