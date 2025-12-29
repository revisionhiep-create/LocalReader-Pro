Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 1. Force the script to look in the folder where THIS file lives
' This fixes the "File not found" error if you use shortcuts
WshShell.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)

' 2. Run the command using your working method
' 0 = Hide the CMD black box
' False = Don't freeze the script waiting for it to close
WshShell.Run "cmd /c python main.py", 0, False