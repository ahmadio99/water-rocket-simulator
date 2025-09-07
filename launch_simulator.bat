@echo off
cd /d "%~dp0"

:: Start FastAPI server in apart venster
start "" cmd /k uvicorn server:app --host 0.0.0.0 --port 8000 --reload

:: Even wachten tot de server draait
timeout /t 3 >nul

:: Start Ngrok in apart venster
start "" cmd /k ngrok.exe http 8000

:: Wachten tot Ngrok API beschikbaar is
:waitloop
timeout /t 2 >nul
curl -s http://127.0.0.1:4040/api/tunnels | findstr "public_url" >nul
if errorlevel 1 goto waitloop

:: URL ophalen en naar klembord kopiëren
powershell -command "$url = (Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels[0].public_url; Set-Clipboard -Value $url; Write-Host 'Gekopieerd naar klembord:' $url"

:: Simulator openen in browser
start "" "http://localhost:8000/static/index.html"

