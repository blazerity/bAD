namespace BadAgent;

/// <summary>
/// Колонки CLI: поле на 16 символов, значение, статус последним словом.
/// </summary>
static class CliColumns
{
    public const int FieldWidth = 16;
    public const int ValueWidth = 30;

    public static string Shown(string? value) =>
        string.IsNullOrWhiteSpace(value) ? "не задан" : value;

    public static string Format(string field, string? value, string? status = null)
    {
        var shown = Shown(value);
        var head = field.Length >= FieldWidth ? field + "  " : field.PadRight(FieldWidth);
        if (status is null)
        {
            return head + shown;
        }

        var body = shown.Length >= ValueWidth ? shown + "  " : shown.PadRight(ValueWidth);
        return head + body + status;
    }

    public static void Write(string field, string? value, string? status = null) =>
        Console.WriteLine(Format(field, value, status));
}
