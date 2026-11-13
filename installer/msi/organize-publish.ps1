# Self-contained publish: плоский bin, без каталогов культур и без библиотек,
# на которые агент и его зависимости не ссылаются. Сборки из графа ссылок не режутся.

param(
    [Parameter(Mandatory = $true)]
    [string]$BinDir
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $BinDir)) {
    throw "organize-publish: bin dir not found: $BinDir"
}

Write-Host "organize-publish: flat bin -> $BinDir"

Get-ChildItem -LiteralPath $BinDir -Directory | ForEach-Object {
    $files = @(Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue)
    if ($files.Count -eq 0) {
        return
    }
    $resources = @($files | Where-Object { $_.Name -like "*.resources.dll" })
    if ($resources.Count -eq $files.Count) {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
        Write-Host "organize-publish: removed culture dir $($_.Name)"
    }
}

# Имена сняты с self-contained win-x64: нет ссылки из BadAgent и библиотек, которые он тянет.
# System.Text.Json, CoreLib, WMI, каталог, реестр, служба, Serilog и BouncyCastle остаются целиком.
$unused = @(
    "Microsoft.CSharp.dll",
    "Microsoft.VisualBasic.dll",
    "Microsoft.VisualBasic.Core.dll",
    "mscorlib.dll",
    "netstandard.dll",
    "System.dll",
    "System.AppContext.dll",
    "System.Buffers.dll",
    "System.ComponentModel.DataAnnotations.dll",
    "System.ComponentModel.EventBasedAsync.dll",
    "System.Configuration.dll",
    "System.Core.dll",
    "System.Data.dll",
    "System.Data.Common.dll",
    "System.Data.DataSetExtensions.dll",
    "System.Diagnostics.Contracts.dll",
    "System.Diagnostics.Debug.dll",
    "System.Diagnostics.EventLog.Messages.dll",
    "System.Diagnostics.StackTrace.dll",
    "System.Diagnostics.TextWriterTraceListener.dll",
    "System.Diagnostics.Tools.dll",
    "System.Drawing.dll",
    "System.Dynamic.Runtime.dll",
    "System.Formats.Tar.dll",
    "System.Globalization.dll",
    "System.Globalization.Calendars.dll",
    "System.Globalization.Extensions.dll",
    "System.IO.dll",
    "System.IO.Compression.FileSystem.dll",
    "System.IO.Compression.ZipFile.dll",
    "System.IO.FileSystem.dll",
    "System.IO.FileSystem.Primitives.dll",
    "System.IO.IsolatedStorage.dll",
    "System.IO.UnmanagedMemoryStream.dll",
    "System.Linq.Parallel.dll",
    "System.Linq.Queryable.dll",
    "System.Net.dll",
    "System.Net.HttpListener.dll",
    "System.Net.Mail.dll",
    "System.Net.Ping.dll",
    "System.Net.Requests.dll",
    "System.Net.ServicePoint.dll",
    "System.Net.WebClient.dll",
    "System.Net.WebHeaderCollection.dll",
    "System.Net.WebProxy.dll",
    "System.Net.WebSockets.dll",
    "System.Net.WebSockets.Client.dll",
    "System.Numerics.dll",
    "System.Private.DataContractSerialization.dll",
    "System.Reflection.dll",
    "System.Reflection.DispatchProxy.dll",
    "System.Reflection.Extensions.dll",
    "System.Reflection.TypeExtensions.dll",
    "System.Resources.Reader.dll",
    "System.Resources.ResourceManager.dll",
    "System.Runtime.CompilerServices.VisualC.dll",
    "System.Runtime.Extensions.dll",
    "System.Runtime.Handles.dll",
    "System.Runtime.InteropServices.JavaScript.dll",
    "System.Runtime.InteropServices.RuntimeInformation.dll",
    "System.Runtime.Serialization.dll",
    "System.Runtime.Serialization.Json.dll",
    "System.Runtime.Serialization.Primitives.dll",
    "System.Runtime.Serialization.Xml.dll",
    "System.Security.dll",
    "System.Security.Cryptography.Cng.dll",
    "System.Security.Cryptography.OpenSsl.dll",
    "System.Security.Principal.dll",
    "System.Security.SecureString.dll",
    "System.ServiceModel.Web.dll",
    "System.ServiceProcess.dll",
    "System.Text.Encoding.dll",
    "System.Text.Encoding.CodePages.dll",
    "System.Threading.Tasks.dll",
    "System.Threading.Tasks.Dataflow.dll",
    "System.Threading.Tasks.Extensions.dll",
    "System.Threading.Tasks.Parallel.dll",
    "System.Threading.Timer.dll",
    "System.Transactions.dll",
    "System.Transactions.Local.dll",
    "System.ValueTuple.dll",
    "System.Web.dll",
    "System.Web.HttpUtility.dll",
    "System.Windows.dll",
    "System.Xml.dll",
    "System.Xml.Linq.dll",
    "System.Xml.ReaderWriter.dll",
    "System.Xml.Serialization.dll",
    "System.Xml.XmlDocument.dll",
    "System.Xml.XmlSerializer.dll",
    "System.Xml.XPath.dll",
    "System.Xml.XPath.XDocument.dll",
    "WindowsBase.dll"
)

foreach ($name in $unused) {
    $path = Join-Path $BinDir $name
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
        Write-Host "organize-publish: removed $name"
    }
}
