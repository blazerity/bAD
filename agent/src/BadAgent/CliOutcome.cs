namespace BadAgent;

/// <summary>Ответ службы для колонок CLI. Секретов здесь нет.</summary>
internal sealed class CliOutcome
{
    public int ExitCode { get; set; }
    public List<CliLine> Lines { get; } = new();
    public List<string> Tail { get; } = new();
    public bool StopAfterReply { get; set; }
    public string? Html { get; set; }
    public bool KeyRejected { get; set; }
    public Dictionary<string, string>? Values { get; set; }

    public void Line(string field, string? value, string? status = null) =>
        Lines.Add(new CliLine(field, value ?? "", status));
}

internal sealed record CliLine(string Field, string Value, string? Status);
