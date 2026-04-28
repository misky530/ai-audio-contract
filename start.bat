@echo off
REM Start FastAPI + ngrok for demo
REM Usage: start.bat [model_size]   e.g.  start.bat tiny

SET MODEL=%1
IF "%MODEL%"=="" SET MODEL=tiny

echo === Voice Contract Demo ===
echo Whisper model: %MODEL%
echo.

WHERE ngrok >nul 2>nul
IF ERRORLEVEL 1 (
  echo ngrok not found. Download: https://ngrok.com/download
  pause & exit /b 1
)

SET STT_BACKEND=local
SET WHISPER_MODEL=%MODEL%
SET WHISPER_DEVICE=cpu

START "FastAPI" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
echo FastAPI starting on port 8000 ...
timeout /t 3 /nobreak >nul

START "ngrok" cmd /k "ngrok http 8000"
echo.
echo ============================================
echo  Check the ngrok window for the HTTPS URL.
echo  Open on your phone:
echo    https://xxxx.ngrok-free.app/static/
echo ============================================
echo.
pause
