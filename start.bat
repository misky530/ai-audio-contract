@echo off
REM 启动后端 + ngrok（Windows）
REM 用法：start.bat [whisper模型大小]
REM 示例：start.bat tiny

SET MODEL=%1
IF "%MODEL%"=="" SET MODEL=tiny

echo === 语音合同生成 Demo ===
echo STT 模型: %MODEL%
echo.

REM 检查 ngrok
WHERE ngrok >nul 2>nul
IF ERRORLEVEL 1 (
  echo 未找到 ngrok，请先安装：https://ngrok.com/download
  echo 安装后运行：ngrok config add-authtoken ^<your-token^>
  pause & exit /b 1
)

REM 启动 FastAPI（新窗口）
SET STT_BACKEND=local
SET WHISPER_MODEL=%MODEL%
SET WHISPER_DEVICE=cpu
START "FastAPI" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
echo FastAPI 已启动，端口 8000
timeout /t 3 /nobreak >nul

REM 启动 ngrok（新窗口）
START "ngrok" cmd /k "ngrok http 8000"
echo ngrok 已启动，请在 ngrok 窗口查看公网地址
echo.
echo ============================================
echo  在 ngrok 窗口找到 https:// 地址，手机访问：
echo  https://xxxxxx.ngrok-free.app/static/
echo ============================================
echo.
echo 关闭本窗口不会停止服务，请手动关闭 FastAPI 和 ngrok 窗口
pause
