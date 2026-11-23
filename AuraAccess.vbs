' AuraAccess 1-Click Silent Background Launcher
' Runs completely silently with ZERO black command prompt window
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

' Launch pythonw without opening any console window (0 = hidden)
WshShell.Run "pythonw run_app.py", 0, False
