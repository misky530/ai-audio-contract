# stt.py  —  语音转文字模块
#
# 支持三种后端，通过环境变量 STT_BACKEND 切换：
#   local  → faster-whisper（本地）
#   openai → OpenAI Whisper API
#   xfyun  → 讯飞语音听写 IAT WebSocket（推荐演示用）
#
# 讯飞后端所需环境变量：
#   XFYUN_APP_ID / XFYUN_API_KEY / XFYUN_API_SECRET

import os
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────────────────────────
STT_BACKEND    = os.getenv("STT_BACKEND", "local")
WHISPER_MODEL  = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
XFYUN_APP_ID     = os.getenv("XFYUN_APP_ID", "")
XFYUN_API_KEY    = os.getenv("XFYUN_API_KEY", "")
XFYUN_API_SECRET = os.getenv("XFYUN_API_SECRET", "")


# ── 本地 faster-whisper 后端 ──────────────────────────────────────────
_local_model = None

def _get_local_model():
    global _local_model
    if _local_model is None:
        from faster_whisper import WhisperModel
        logger.info(f"加载 Whisper 模型: {WHISPER_MODEL} / {WHISPER_DEVICE}")
        _local_model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")
        logger.info("模型加载完成")
    return _local_model


def _transcribe_local(audio_path: str, language: str, prompt: str) -> str:
    model = _get_local_model()
    segments, info = model.transcribe(
        audio_path,
        language=language,
        initial_prompt=prompt or None,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    text = " ".join(seg.text.strip() for seg in segments)
    logger.info(f"[local] 识别结果: {text!r}  (语言: {info.language})")
    return text.strip()


# ── OpenAI Whisper API 后端 ───────────────────────────────────────────
def _transcribe_openai(audio_path: str, language: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        kwargs = {"model": "whisper-1", "file": f, "language": language}
        if prompt:
            kwargs["prompt"] = prompt
        result = client.audio.transcriptions.create(**kwargs)
    text = result.text.strip()
    logger.info(f"[openai] 识别结果: {text!r}")
    return text


# ── 讯飞 IAT WebSocket 后端 ───────────────────────────────────────────
def _to_pcm16k(src: str) -> tuple:
    """用 ffmpeg 把任意音频转为 16kHz 16bit 单声道 PCM raw，返回 (路径, 是否临时文件)"""
    out = src + "_16k.pcm"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src,
             "-ar", "16000", "-ac", "1", "-f", "s16le", out],
            check=True, capture_output=True,
        )
        return out, True
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"音频转换失败（ffmpeg）: {e.stderr.decode(errors='ignore')}")


def _transcribe_xfyun(audio_path: str) -> str:
    """讯飞语音听写 IAT WebSocket"""
    import hmac, hashlib, base64, threading, json
    from datetime import datetime, timezone
    from urllib.parse import quote

    try:
        import websocket as _ws
    except ImportError:
        raise RuntimeError("请先安装: pip install websocket-client")

    if not all([XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET]):
        raise RuntimeError("请设置环境变量 XFYUN_APP_ID / XFYUN_API_KEY / XFYUN_API_SECRET")

    # 转换音频格式
    pcm_path, is_temp = _to_pcm16k(audio_path)
    try:
        with open(pcm_path, "rb") as f:
            audio_data = f.read()
    finally:
        if is_temp:
            Path(pcm_path).unlink(missing_ok=True)

    # 构建鉴权 URL
    host = "iat-api.xfyun.cn"
    path = "/v2/iat"
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    sig_str = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    sig = base64.b64encode(
        hmac.new(XFYUN_API_SECRET.encode(), sig_str.encode(), hashlib.sha256).digest()
    ).decode()
    auth_origin = (
        f'api_key="{XFYUN_API_KEY}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{sig}"'
    )
    auth = base64.b64encode(auth_origin.encode()).decode()
    url  = f"wss://{host}{path}?authorization={auth}&date={quote(date)}&host={host}"

    # WebSocket 收发
    result_parts = []
    done_event   = threading.Event()
    errors       = []
    CHUNK        = 1280  # 40ms @ 16kHz 16bit

    def on_open(ws):
        offset = 0
        while offset < len(audio_data):
            chunk  = audio_data[offset: offset + CHUNK]
            status = 0 if offset == 0 else 1
            msg = {
                "data": {
                    "status":   status,
                    "format":   "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio":    base64.b64encode(chunk).decode(),
                }
            }
            if status == 0:
                msg["common"]   = {"app_id": XFYUN_APP_ID}
                msg["business"] = {
                    "language": "zh_cn", "domain": "iat",
                    "accent": "mandarin", "vad_eos": 3000,
                }
            ws.send(json.dumps(msg))
            offset += CHUNK
        ws.send(json.dumps({
            "data": {"status": 2, "format": "audio/L16;rate=16000",
                     "encoding": "raw", "audio": ""}
        }))

    def on_message(ws, msg):
        d = json.loads(msg)
        if d.get("code", 0) != 0:
            errors.append(f"讯飞错误 {d['code']}: {d.get('message')}")
            ws.close()
            return
        for w in d.get("data", {}).get("result", {}).get("ws", []):
            for cw in w.get("cw", []):
                result_parts.append(cw.get("w", ""))
        if d.get("data", {}).get("status") == 2:
            ws.close()

    def on_error(ws, e):
        errors.append(str(e))

    def on_close(ws, *_):
        done_event.set()

    ws_app = _ws.WebSocketApp(
        url, on_open=on_open, on_message=on_message,
        on_error=on_error, on_close=on_close,
    )
    threading.Thread(target=ws_app.run_forever, daemon=True).start()
    done_event.wait(timeout=30)

    if errors:
        raise RuntimeError(errors[0])

    text = "".join(result_parts).strip()
    logger.info(f"[xfyun] 识别结果: {text!r}")
    return text


# ── 公共接口 ──────────────────────────────────────────────────────────
def transcribe(audio_path: str, language: str = "zh", prompt: str = "") -> str:
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    logger.info(f"STT 后端: {STT_BACKEND}  文件: {audio_path}")

    if STT_BACKEND == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("使用 OpenAI 后端需要设置 OPENAI_API_KEY")
        return _transcribe_openai(audio_path, language, prompt)
    elif STT_BACKEND == "xfyun":
        return _transcribe_xfyun(audio_path)
    else:
        return _transcribe_local(audio_path, language, prompt)


def transcribe_bytes(
    audio_bytes: bytes,
    suffix:      str = ".wav",
    language:    str = "zh",
    prompt:      str = "",
) -> str:
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        return transcribe(tmp_path, language=language, prompt=prompt)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
