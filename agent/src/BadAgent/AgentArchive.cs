using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;

namespace BadAgent;

/// <summary>BADARC1: соль, nonce, AES-256-GCM. Внутри zip без путей «..».</summary>
public static class AgentArchive
{
    private static readonly byte[] Magic = "BADARC1\n"u8.ToArray();

    public static void DecryptToDirectory(string arcPath, string password, string destDir)
    {
        var raw = File.ReadAllBytes(arcPath);
        if (raw.Length < 8 + 16 + 12 + 16 || !raw.AsSpan(0, 8).SequenceEqual(Magic))
        {
            throw new InvalidDataException("archive header");
        }

        var salt = raw.AsSpan(8, 16);
        var nonce = raw.AsSpan(24, 12);
        var sealedSpan = raw.AsSpan(36);
        var tag = sealedSpan[^16..];
        var cipher = sealedSpan[..^16];
        var key = new Rfc2898DeriveBytes(password, salt.ToArray(), 100000, HashAlgorithmName.SHA256).GetBytes(32);
        var plain = new byte[cipher.Length];
        using (var aes = new AesGcm(key, 16))
        {
            aes.Decrypt(nonce, cipher, tag, plain);
        }

        Directory.CreateDirectory(destDir);
        using var ms = new MemoryStream(plain, writable: false);
        using var zip = new ZipArchive(ms, ZipArchiveMode.Read);
        var root = Path.GetFullPath(destDir);
        if (!root.EndsWith(Path.DirectorySeparatorChar))
        {
            root += Path.DirectorySeparatorChar;
        }

        foreach (var entry in zip.Entries)
        {
            var name = entry.FullName.Replace('\\', '/');
            if (name.Length == 0 || name.EndsWith('/'))
            {
                continue;
            }

            if (name.StartsWith('/') || name.Contains("..", StringComparison.Ordinal) || name.Contains(':'))
            {
                throw new InvalidDataException("archive path");
            }

            var dest = Path.GetFullPath(Path.Combine(destDir, name.Replace('/', Path.DirectorySeparatorChar)));
            if (!dest.StartsWith(root, OperatingSystem.IsWindows()
                    ? StringComparison.OrdinalIgnoreCase
                    : StringComparison.Ordinal))
            {
                throw new InvalidDataException("archive path");
            }

            var parent = Path.GetDirectoryName(dest);
            if (!string.IsNullOrEmpty(parent))
            {
                Directory.CreateDirectory(parent);
            }

            entry.ExtractToFile(dest, overwrite: true);
        }
    }
}
