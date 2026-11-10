using System.Security.Cryptography;

namespace BadAgent;

/// <summary>
/// Локальный секрет заявки. В запрос и в консоль уходит только SHA256.
/// </summary>
public static class EnrollmentProof
{
    public static string ProofPath => Path.Combine(ConfigStore.ProgramDataDir, "enrollment_proof");

    /// <summary>64 hex. null — файл есть, но прочитать его нельзя. Новый секрет тогда не пишется.</summary>
    public static string? TryFingerprintHex()
    {
        Directory.CreateDirectory(ConfigStore.ProgramDataDir);
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

        try
        {
            var data = File.ReadAllBytes(ProofPath);
            if (data.Length == 0)
            {
                return null;
            }

            return Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
        }
        catch
        {
            return null;
        }
    }
}
