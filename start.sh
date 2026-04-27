#!/bin/bash
# 启动后端 + ngrok，自动打印手机访问地址
# 用法：bash start.sh [whisper模型大小]
# 示例：bash start.sh tiny

MODEL=${1:-tiny}

echo "=== 语音合同生成 Demo ==="
echo "STT 模型: $MODEL"
echo ""

# 检查 ngrok
if ! command -v ngrok &> /dev/null; then
  echo "未找到 ngrok，请先安装：https://ngrok.com/download"
  echo "安装后运行：ngrok config add-authtoken <your-token>"
  exit 1
fi

# 后台启动 FastAPI
STT_BACKEND=local WHISPER_MODEL=$MODEL WHISPER_DEVICE=cpu \
  uvicorn main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!
echo "FastAPI 已启动 (PID $UVICORN_PID)，端口 8000"
sleep 2

# 后台启动 ngrok
ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!
echo "ngrok 已启动 (PID $NGROK_PID)，等待隧道…"
sleep 3

# 从 ngrok API 获取公网地址
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels \
  | python3 -c "import sys,json; t=json.load(sys.stdin)['tunnels']; \
    print(next((x['public_url'] for x in t if x['proto']=='https'), t[0]['public_url'] if t else ''))" \
  2>/dev/null)

echo ""
echo "============================================"
echo "  手机访问地址（HTTPS，可录音）："
echo "  $NGROK_URL/static/"
echo "============================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待退出信号
trap "kill $UVICORN_PID $NGROK_PID 2>/dev/null; echo '已停止'" INT TERM
wait $UVICORN_PID
