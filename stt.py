# stt.py  —  语音转文字模块
#
# 支持两种后端，通过环境变量 STT_BACKEND 切换：
#   local  → faster-whisper（本地，无数据外传，推荐生产使用）
#   openai → OpenAI Whisper API（云端，无需 GPU，适合快速验证）
#
# 用法：
#   STT_BACKEND=local  uvicorn main:app   # 本地模型
#   STT_BACKEND=openai uvicorn main:app   # OpenAI API

import os
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────────────────────────
STT_BACKEND    = os.getenv("STT_BACKEND", "local")      # local | openai
WHISPER_MODEL  = os.getenv("WHISPER_MODEL", "medium")   # tiny/base/small/medium/large
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")     # cpu | cuda
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ── 本地 faster-whisper 后端 ──────────────────────────────────────────
_local_model = None  # 单例，避免重复加载

def _get_local_model():
    global _local_model
    if _local_model is None:
        from faster_whisper import WhisperModel
        logger.info(f"加载 Whisper 模型: {WHISPER_MODEL} / {WHISPER_DEVICE}")
        _local_model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type="int8",   # CPU 推荐 int8，速度快内存省
        )
        logger.info("模型加载完成")
    return _local_model


def _transcribe_local(audio_path: str, language: str, prompt: str) -> str:
    """使用本地 faster-whisper 转录"""
    model = _get_local_model()
    segments, info = model.transcribe(
        audio_path,
        language=language,
        initial_prompt=prompt or None,
        beam_size=5,
        vad_filter=True,            # 过滤静音段，减少幻觉
        vad_parameters={
            "min_silence_duration_ms": 500,
        },
    )
    text = " ".join(seg.text.strip() for seg in segments)
    logger.info(f"[local] 识别结果: {text!r}  (检测语言: {info.language})")
    return text.strip()


# ── OpenAI Whisper API 后端 ───────────────────────────────────────────
def _transcribe_openai(audio_path: str, language: str, prompt: str) -> str:
    """使用 OpenAI Whisper API 转录"""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(audio_path, "rb") as f:
        kwargs = {
            "model":    "whisper-1",
            "file":     f,
            "language": language,
        }
        if prompt:
            kwargs["prompt"] = prompt

        result = client.audio.transcriptions.create(**kwargs)

    text = result.text.strip()
    logger.info(f"[openai] 识别结果: {text!r}")
    return text


# ── 公共接口 ──────────────────────────────────────────────────────────
def transcribe(
    audio_path: str,
    language:   str = "zh",
    prompt:     str = "",
) -> str:
    """
    语音转文字主入口。

    Args:
        audio_path: 音频文件路径（支持 wav / mp3 / m4a / webm 等）
        language:   语言代码，中文用 "zh"
        prompt:     Whisper initial_prompt，传入字段词库提升准确率

    Returns:
        识别出的文字字符串
    """
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    logger.info(f"STT 后端: {STT_BACKEND}  文件: {audio_path}")

    if STT_BACKEND == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("使用 OpenAI 后端需要设置环境变量 OPENAI_API_KEY")
        return _transcribe_openai(audio_path, language, prompt)
    else:
        return _transcribe_local(audio_path, language, prompt)


def transcribe_bytes(
    audio_bytes: bytes,
    suffix:      str = ".wav",
    language:    str = "zh",
    prompt:      str = "",
) -> str:
    """
    接收音频字节流，写入临时文件后转录。
    适合 FastAPI UploadFile 场景。
    """
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        return transcribe(tmp_path, language=language, prompt=prompt)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
