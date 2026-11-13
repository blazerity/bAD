namespace BadAgent;

/// <summary>
/// Связь, затем обновление, затем сброс лишнего. Ключ стирается только если сервер его принял.
/// </summary>
public static class DoctorCli
{
    public static int Run(string[] args)
    {
        if (args.Length == 1 && BadCli.IsHelpToken(args[0]))
        {
            Console.WriteLine("bad doctor               Починить настройки агента и проверить связь.");
            return 0;
        }

        if (args.Length > 0)
        {
            CliColumns.Write("Связь", "нет", "ошибка");
            return 1;
        }

        var reply = ServiceChannel.Call(new { op = "doctor" });
        if (reply is null)
        {
            ServiceChannel.ServiceDown();
            return 1;
        }

        return ServiceChannel.Print(reply);
    }

    internal static CliOutcome Execute()
    {
        var outcome = new CliOutcome();
        var config = ConfigStore.LoadOrCreate();
        if (string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            outcome.Line("Сервер", "bad config set server_url", "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }

        var kind = LinkProbe.Check(config);
        if (kind == "no_url")
        {
            outcome.Line("Сервер", "bad config set server_url", "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }

        if (kind == "auth")
        {
            outcome.Line("Связь", "есть", "ok");
            outcome.Line("Ключ", "отклонён", "ошибка");
            outcome.Line("Заявка", "ожидает «Разрешить»", "без изменений");
            outcome.ExitCode = 1;
            return outcome;
        }

        if (kind != "up")
        {
            outcome.Line("Связь", "нет", "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }

        outcome.Line("Связь", "есть", "ok");
        var update = UpdateCli.Execute();
        foreach (var line in update.Lines)
        {
            if (line.Field == "Обновление")
            {
                outcome.Lines.Add(line);
            }
        }

        if (update.KeyRejected)
        {
            outcome.ExitCode = 1;
            return outcome;
        }

        config = ConfigStore.LoadOrCreate();
        var fresh = new AgentConfig
        {
            ServerUrl = config.ServerUrl ?? "",
            BadId = string.IsNullOrWhiteSpace(config.BadId) ? null : config.BadId,
            ApiKey = string.IsNullOrWhiteSpace(config.ApiKey) ? null : config.ApiKey,
            PendingUpdateVersion = config.PendingUpdateVersion,
            PendingUpdateStartedAt = config.PendingUpdateStartedAt,
        };
        ConfigStore.Save(fresh);
        AgentSigningKey.ClearLocal();
        outcome.Line("Настройки", "сброшены", "ok");
        outcome.Line("Ключ", "стёрт", "ok");
        outcome.StopAfterReply = update.StopAfterReply;
        outcome.ExitCode = update.ExitCode;
        return outcome;
    }
}
