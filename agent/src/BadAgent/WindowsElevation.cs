using System.Runtime.Versioning;
using System.Security.Principal;

namespace BadAgent;

/// <summary>Проверка elevated (Administrator) для CLI, меняющего config или службу.</summary>
public static class WindowsElevation
{
    [SupportedOSPlatform("windows")]
    public static bool IsElevated()
    {
        if (!OperatingSystem.IsWindows())
        {
            return false;
        }

        using var identity = WindowsIdentity.GetCurrent();
        var principal = new WindowsPrincipal(identity);
        return principal.IsInRole(WindowsBuiltInRole.Administrator);
    }

    /// <summary>Сообщение на stderr и код 1, если не elevated. Иначе 0.</summary>
    public static int RequireElevatedOrExit(string actionDescriptionRu)
    {
        if (OperatingSystem.IsWindows() && IsElevated())
        {
            return 0;
        }

        if (!OperatingSystem.IsWindows())
        {
            Console.Error.WriteLine(
                "error: изменение конфигурации поддерживается только на Windows с правами администратора.");
            return 1;
        }

        Console.Error.WriteLine(
            $"error: для {actionDescriptionRu} нужны права администратора " +
            "(запустите командную строку или PowerShell «От имени администратора»).");
        return 1;
    }
}
