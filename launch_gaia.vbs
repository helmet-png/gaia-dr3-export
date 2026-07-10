' Gaia DR3 export tool launcher
' Starts server.py hidden (no console window), then opens the browser.
' Safe to double-click repeatedly: a second server instance exits silently.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir_ = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "pyw """ & dir_ & "\server.py""", 0, False
WScript.Sleep 1500
sh.Run "http://localhost:8777", 1, False
