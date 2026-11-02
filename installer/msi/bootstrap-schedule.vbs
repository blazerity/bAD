' First-pass MajorUpgrade from 2.0.x: copy MSI, schtasks (+90s), return 1602 = UserExit.
' Script CA return codes are Win32/MSI codes (0 success, 1602 user exit, 1603 failure) - NOT 1/2/3.
' ASCII-only: Package Codepage 1251 (WIX0311).
Option Explicit

Function BootstrapScheduleAction
  On Error Resume Next
  Dim fso, sh, orig, pd, updates, logs, dest, blog, xmlPath, exe, ver
  Dim startAt, startIso, xml, rc

  BootstrapScheduleAction = 1603
  Set fso = CreateObject("Scripting.FileSystemObject")
  Set sh = CreateObject("WScript.Shell")

  orig = Session.Property("OriginalDatabase")
  If Len(Trim(orig)) = 0 Or Not fso.FileExists(orig) Then
    Call WriteLog(fso, sh, "ERROR BAD_MSI_121 OriginalDatabase missing: '" & orig & "'")
    Exit Function
  End If

  pd = sh.ExpandEnvironmentStrings("%ProgramData%")
  updates = pd & "\blazerity\bAD\updates"
  logs = pd & "\blazerity\bAD\logs"
  dest = updates & "\bad-agent-bootstrap.msi"
  blog = logs & "\msiexec-bootstrap.log"
  xmlPath = updates & "\bAD-bootstrap-task.xml"

  If Not fso.FolderExists(pd & "\blazerity") Then fso.CreateFolder pd & "\blazerity"
  If Not fso.FolderExists(pd & "\blazerity\bAD") Then fso.CreateFolder pd & "\blazerity\bAD"
  If Not fso.FolderExists(updates) Then fso.CreateFolder updates
  If Not fso.FolderExists(logs) Then fso.CreateFolder logs

  exe = GetAgentExe(fso, sh)
  If Len(exe) > 0 And fso.FileExists(exe) Then
    ver = fso.GetFileVersion(exe)
    If VersionGreaterThanLegacy(ver) Then
      Call WriteLog(fso, sh, "INFO bootstrap skipped (installed agent " & ver & ")")
      BootstrapScheduleAction = 0
      Exit Function
    End If
  End If

  Call WriteLog(fso, sh, "INFO bootstrap begin orig=" & orig & " exe=" & exe & " ver=" & ver)

  Err.Clear
  fso.CopyFile orig, dest, True
  If Err.Number <> 0 Or Not fso.FileExists(dest) Then
    Call WriteLog(fso, sh, "ERROR BAD_MSI_121 copy failed: " & Err.Description)
    Exit Function
  End If

  startAt = DateAdd("s", 90, Now)
  startIso = IsoLocal(startAt)
  xml = ""
  xml = xml & "<?xml version=""1.0"" encoding=""UTF-16""?>" & vbCrLf
  xml = xml & "<Task version=""1.2"" xmlns=""http://schemas.microsoft.com/windows/2004/02/mit/task"">" & vbCrLf
  xml = xml & "  <Triggers><TimeTrigger><StartBoundary>" & startIso & "</StartBoundary>"
  xml = xml & "<Enabled>true</Enabled></TimeTrigger></Triggers>" & vbCrLf
  xml = xml & "  <Principals><Principal id=""Author""><UserId>S-1-5-18</UserId>"
  xml = xml & "<RunLevel>HighestAvailable</RunLevel></Principal></Principals>" & vbCrLf
  xml = xml & "  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>"
  xml = xml & "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>"
  xml = xml & "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>"
  xml = xml & "<StartWhenAvailable>true</StartWhenAvailable><Enabled>true</Enabled></Settings>" & vbCrLf
  xml = xml & "  <Actions Context=""Author""><Exec>"
  xml = xml & "<Command>" & sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\msiexec.exe</Command>"
  xml = xml & "<Arguments>/i """ & dest & """ /qn /norestart BADBOOTSTRAP=1 REBOOT=ReallySuppress /l*v """ & blog & """</Arguments>"
  xml = xml & "</Exec></Actions>" & vbCrLf
  xml = xml & "</Task>" & vbCrLf

  Err.Clear
  Call WriteUtf16File(fso, xmlPath, xml)
  If Err.Number <> 0 Then
    Call WriteLog(fso, sh, "ERROR BAD_MSI_122 write task xml: " & Err.Description)
    Exit Function
  End If

  rc = sh.Run("schtasks.exe /Create /TN ""bAD-bootstrap"" /XML """ & xmlPath & """ /F", 0, True)
  If rc <> 0 Then
    Call WriteLog(fso, sh, "ERROR BAD_MSI_122 schtasks /Create exit " & rc)
    Exit Function
  End If

  Call WriteLog(fso, sh, "INFO bootstrap scheduled copy=" & dest & " at=" & startIso & " -> UserExit 1602")
  BootstrapScheduleAction = 1602
End Function

Function GetAgentExe(fso, sh)
  Dim reg, pf
  On Error Resume Next
  reg = sh.RegRead("HKLM\SOFTWARE\blazerity\bAD\InstallDir")
  If Len(reg) > 0 Then
    If Right(reg, 1) = "\" Then reg = Left(reg, Len(reg) - 1)
    GetAgentExe = reg & "\bin\BadAgent.exe"
    Exit Function
  End If
  pf = sh.ExpandEnvironmentStrings("%ProgramFiles%")
  GetAgentExe = pf & "\blazerity\bad agent\bin\BadAgent.exe"
End Function

Function VersionGreaterThanLegacy(ver)
  Dim parts, major, minor, build
  VersionGreaterThanLegacy = False
  parts = Split(ver, ".")
  If UBound(parts) < 2 Then Exit Function
  major = CInt(parts(0))
  minor = CInt(parts(1))
  build = 0
  If UBound(parts) >= 2 Then build = CInt(parts(2))
  If major > 2 Then VersionGreaterThanLegacy = True : Exit Function
  If major = 2 And minor > 1 Then VersionGreaterThanLegacy = True : Exit Function
  If major = 2 And minor = 1 And build > 4 Then VersionGreaterThanLegacy = True
End Function

Function IsoLocal(dt)
  IsoLocal = Year(dt) & "-" & Right("0" & Month(dt), 2) & "-" & Right("0" & Day(dt), 2) & _
    "T" & Right("0" & Hour(dt), 2) & ":" & Right("0" & Minute(dt), 2) & ":" & Right("0" & Second(dt), 2)
End Function

Sub WriteUtf16File(fso, path, text)
  Dim stream
  Set stream = CreateObject("ADODB.Stream")
  stream.Type = 2
  stream.Charset = "utf-16"
  stream.Open
  stream.WriteText text
  stream.SaveToFile path, 2
  stream.Close
End Sub

Sub WriteLog(fso, sh, msg)
  On Error Resume Next
  Dim logs, path, ts, line, ts2, root
  root = sh.ExpandEnvironmentStrings("%ProgramData%")
  logs = root & "\blazerity\bAD\logs"
  If Not fso.FolderExists(root & "\blazerity") Then fso.CreateFolder root & "\blazerity"
  If Not fso.FolderExists(root & "\blazerity\bAD") Then fso.CreateFolder root & "\blazerity\bAD"
  If Not fso.FolderExists(logs) Then fso.CreateFolder logs
  path = logs & "\msi-install.log"
  ts = Year(Now) & "-" & Right("0" & Month(Now), 2) & "-" & Right("0" & Day(Now), 2) & _
       "T" & Right("0" & Hour(Now), 2) & ":" & Right("0" & Minute(Now), 2) & ":" & Right("0" & Second(Now), 2)
  line = ts & " " & msg
  Set ts2 = fso.OpenTextFile(path, 8, True)
  ts2.WriteLine line
  ts2.Close
End Sub
