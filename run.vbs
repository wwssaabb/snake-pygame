Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
If Right(base, 1) <> "\" Then base = base & "\"
pythonw = base & ".venv\Scripts\pythonw.exe"
target = base & "main.py"
If fso.FileExists(pythonw) Then
    shell.CurrentDirectory = base
    shell.Run """" & pythonw & """ """ & target & """", 0, False
Else
    shell.CurrentDirectory = base
    shell.Run "pythonw """ & target & """", 0, False
End If
