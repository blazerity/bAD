using System.ServiceProcess;

namespace BadAgent;

/// <summary>Локальный ремонт агента и проверка связи через службу.</summary>
public static class DoctorCli
{
    public static int Run(string[] args)
    {
        if (args.Length == 1 && BadCli.IsHelpToken(args[0]))
        {
            Console.WriteLine("bad doctor               Найти поломку агента и починить локальное");
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
            ServiceStateLine();
            return 1;
        }

        return ServiceChannel.Print(reply);
    }

    internal static void ServiceStateLine()
    {
        if (!OperatingSystem.IsWindows())
        {
            ServiceChannel.ServiceDown();
            return;
        }

        try
        {
            using var sc = new ServiceController(ServiceCli.ServiceName);
            sc.Refresh();
            var status = sc.Status;
            if (status is ServiceControllerStatus.Stopped or ServiceControllerStatus.StopPending)
            {
                CliColumns.Write("Служба", "остановлена, bad service start", "ошибка");
                return;
            }

            CliColumns.Write("Служба", "не отвечает", "ошибка");
        }
        catch (InvalidOperationException)
        {
            CliColumns.Write("Служба", "не установлена", "ошибка");
        }
    }

    internal static CliOutcome Execute()
    {
        var outcome = new CliOutcome();
        AgentConfig config;
        try
        {
            config = ConfigStore.LoadOrCreate();
        }
        catch (Exception ex)
        {
            outcome.Line("Каталог", ex.Message, "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }

        if (string.IsNullOrWhiteSpace(config.ServerUrl))
        {
            outcome.Line("Сервер", "bad config set server_url", "ошибка");
            outcome.ExitCode = 1;
            return outcome;
        }

        var removed = OfflineQueue.DeleteBrokenItems();
        outcome.Line("Очередь", removed == 0 ? "цела" : $"удалено {removed}", removed == 0 ? "без изменений" : "ok");

        RepairPendingUpdate(ref config, outcome);
        AgentSigningKey.QuarantineGarbage(outcome);

        var link = LinkProbe.Status(config);
        var kind = link.Kind;
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

        outcome.StopAfterReply = update.StopAfterReply;
        outcome.ExitCode = update.ExitCode;
        return outcome;
    }

    private static void RepairPendingUpdate(ref AgentConfig config, CliOutcome outcome)
    {
        if (string.IsNullOrWhiteSpace(config.PendingUpdateVersion))
        {
            outcome.Line("Обновление", "не ждёт", "без изменений");
            return;
        }

        var agentVersion = VersionUtil.GetAgentVersion();
        if (string.Equals(config.PendingUpdateVersion.Trim(), agentVersion, StringComparison.OrdinalIgnoreCase))
        {
            ClearPendingUpdate(ref config);
            outcome.Line("Обновление", "ожидание снято", "ok");
            return;
        }

        var startedAt = config.PendingUpdateStartedAt;
        if (string.IsNullOrWhiteSpace(startedAt)
            || !DateTime.TryParse(startedAt, null, System.Globalization.DateTimeStyles.RoundtripKind, out var started)
            || DateTime.UtcNow - started.ToUniversalTime() >= AgentUpdater.PendingCooldown)
        {
            ClearPendingUpdate(ref config);
            outcome.Line("Обновление", "ожидание снято", "ok");
            return;
        }

        outcome.Line("Обновление", "установка уже идёт", "без изменений");
    }

    private static void ClearPendingUpdate(ref AgentConfig config)
    {
        config.PendingUpdateVersion = null;
        config.PendingUpdateStartedAt = null;
        ConfigStore.Save(config);
        config = ConfigStore.LoadOrCreate();
    }
}
