Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d P:\fitxestecniques\backend && venv\Scripts\activate && python run.py", 0, False
