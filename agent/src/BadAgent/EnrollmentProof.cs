using System.Runtime.InteropServices;
using System.Security.Cryptography;

namespace BadAgent;

/// <summary>
/// Локальный секрет заявки: 32 байта файла. В запрос уходит base64 этих байт, не SHA256.
/// </summary>
public static class EnrollmentProof
{
    private const string DataDirSddl = "D:PAI(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)";

    public static string ProofPath => Path.Combine(ConfigStore.ProgramDataDir, "enrollment_proof");

    /// <summary>Уже лежащий секрет. Файла нет или длина не 32 — null, новый не создаём.</summary>
    public static byte[]? ReadExistingProof()
    {
        if (!File.Exists(ProofPath))
        {
            return null;
        }

        return ReadProofBytes();
    }

    /// <summary>32 байта. null — файл есть, но прочитать ровно 32 байта нельзя. Новый секрет тогда не пишется.</summary>
    public static byte[]? TryProof()
    {
        EnsureProgramDataDir();
        if (!File.Exists(ProofPath))
        {
            var bytes = RandomNumberGenerator.GetBytes(32);
            var tmp = ProofPath + ".tmp";
            File.WriteAllBytes(tmp, bytes);
            try
            {
                File.Move(tmp, ProofPath, overwrite: false);
            }
            catch (IOException)
            {
                try
                {
                    File.Delete(tmp);
                }
                catch
                {
                    // Файл уже есть. Чужой секрет не затираем.
                }
            }
        }

        return ReadProofBytes();
    }

    private static void EnsureProgramDataDir()
    {
        var path = ConfigStore.ProgramDataDir;
        if (Directory.Exists(path))
        {
            return;
        }

        var parent = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(parent) && !Directory.Exists(parent))
        {
            Directory.CreateDirectory(parent);
        }

        var sd = IntPtr.Zero;
        try
        {
            if (!ConvertStringSecurityDescriptorToSecurityDescriptor(
                    DataDirSddl,
                    1,
                    out sd,
                    IntPtr.Zero))
            {
                return;
            }

            var sa = new SecurityAttributes
            {
                nLength = Marshal.SizeOf<SecurityAttributes>(),
                lpSecurityDescriptor = sd,
                bInheritHandle = 0,
            };
            CreateDirectoryW(path, ref sa);
        }
        finally
        {
            if (sd != IntPtr.Zero)
            {
                LocalFree(sd);
            }
        }
    }

    private static byte[]? ReadProofBytes()
    {
        try
        {
            var data = File.ReadAllBytes(ProofPath);
            if (data.Length != 32)
            {
                return null;
            }

            return data;
        }
        catch
        {
            return null;
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct SecurityAttributes
    {
        public int nLength;
        public IntPtr lpSecurityDescriptor;
        public int bInheritHandle;
    }

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertStringSecurityDescriptorToSecurityDescriptor(
        string stringSecurityDescriptor,
        int stringSdRevision,
        out IntPtr securityDescriptor,
        IntPtr securityDescriptorSize);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, EntryPoint = "CreateDirectoryW")]
    private static extern bool CreateDirectoryW(string lpPathName, ref SecurityAttributes lpSecurityAttributes);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr hMem);
}
