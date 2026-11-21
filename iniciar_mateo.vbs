Option Explicit

Dim shell, files, projectFolder, scriptPath, pythonPath, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")

projectFolder = files.GetParentFolderName(WScript.ScriptFullName)
scriptPath = files.BuildPath(projectFolder, "asistente.py")
pythonPath = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & _
    "\Programs\Python\Python313\python.exe"

If Not files.FileExists(pythonPath) Then
    MsgBox "No encuentro Python 3.13 en:" & vbCrLf & pythonPath, _
        vbExclamation, "Mateo"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectFolder
command = """" & pythonPath & """ """ & scriptPath & """"
shell.Run command, 0, False
