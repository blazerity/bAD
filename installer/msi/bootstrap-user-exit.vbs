Function BootstrapUserExitAction
  On Error Resume Next
  Dim fso, sh, marker
  Set fso = CreateObject("Scripting.FileSystemObject")
  Set sh = CreateObject("WScript.Shell")
  marker = sh.ExpandEnvironmentStrings("%ProgramData") & "\blazerity\bAD\updates\.bootstrap-scheduled"
  If fso.FileExists(marker) Then
    fso.DeleteFile marker, True
    BootstrapUserExitAction = 2
  Else
    BootstrapUserExitAction = 0
  End If
End Function
BootstrapUserExitAction
