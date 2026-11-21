Option Explicit

Dim files, projectFolder, scriptPath, oldGuiPath, assistantPath, service, processes, process, stopped
Set files = CreateObject("Scripting.FileSystemObject")
projectFolder = files.GetParentFolderName(WScript.ScriptFullName)
scriptPath = LCase(files.BuildPath(projectFolder, "widget_mateo.py"))
oldGuiPath = LCase(files.BuildPath(projectFolder, "interfaz_mateo.py"))
assistantPath = LCase(files.BuildPath(projectFolder, "asistente_local.py"))
Set service = GetObject("winmgmts:\\.\root\cimv2")
Set processes = service.ExecQuery( _
    "SELECT * FROM Win32_Process WHERE Name='python.exe' OR Name='pythonw.exe'")

stopped = False
For Each process In processes
    If InStr(1, LCase(process.CommandLine), scriptPath, vbTextCompare) > 0 Or _
       InStr(1, LCase(process.CommandLine), oldGuiPath, vbTextCompare) > 0 Or _
       InStr(1, LCase(process.CommandLine), assistantPath, vbTextCompare) > 0 Then
        process.Terminate
        stopped = True
    End If
Next

If stopped Then
    MsgBox "Mateo se ha cerrado.", vbInformation, "Mateo"
Else
    MsgBox "Mateo no estaba ejecutandose.", vbInformation, "Mateo"
End If
