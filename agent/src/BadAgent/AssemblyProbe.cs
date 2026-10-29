using System.Reflection;
using System.Runtime.Loader;

namespace BadAgent;

/// <summary>
/// Подгрузка DLL из <c>bin\ms\</c> (Microsoft/System) и <c>bin\lib\</c> (остальные пакеты).
/// Вызывать до любых обращений к типам из этих сборок.
/// </summary>
public static class AssemblyProbe
{
    private static int _registered;

    public static void Register()
    {
        if (Interlocked.Exchange(ref _registered, 1) != 0)
        {
            return;
        }

        var baseDir = AppContext.BaseDirectory;
        var probeDirs = new[]
        {
            Path.Combine(baseDir, "ms"),
            Path.Combine(baseDir, "lib"),
        };

        AssemblyLoadContext.Default.Resolving += (_, name) =>
        {
            if (string.IsNullOrEmpty(name.Name))
            {
                return null;
            }

            var fileName = name.Name + ".dll";
            foreach (var dir in probeDirs)
            {
                var path = Path.Combine(dir, fileName);
                if (File.Exists(path))
                {
                    return AssemblyLoadContext.Default.LoadFromAssemblyPath(path);
                }
            }

            return null;
        };
    }
}
