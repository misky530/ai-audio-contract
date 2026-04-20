# main.py  —  语音合同生成（阶段二：接入 STT）

import os, urllib.parse, logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from contract import generate_contract, list_templates
from mock_data import VOICE_FIELDS, OUR_COMPANY, DEFAULTS, MOCK_VOICE_INPUT, auto_generate
from vocab import get_prompt
from stt import transcribe_bytes, STT_BACKEND

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="语音合同生成", version="0.3.0")


# ── Schema ────────────────────────────────────────────────────────────
class VoiceInput(BaseModel):
    contract_type: str = "采购合同"
    voice_data: dict
    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_type": "采购合同",
                "voice_data": MOCK_VOICE_INPUT,
            }
        }
    }


# ── 基础接口 ──────────────────────────────────────────────────────────
@app.get("/", summary="服务状态")
def root():
    return {"status": "ok", "version": "0.3.0", "stt_backend": STT_BACKEND}

@app.get("/templates")
def get_templates():
    return {"templates": list_templates()}

@app.get("/fields", summary="语音输入字段清单")
def get_fields():
    return {
        "voice_fields": VOICE_FIELDS,
        "our_company":  OUR_COMPANY,
        "defaults":     DEFAULTS,
        "total_voice":  len(VOICE_FIELDS),
    }

@app.get("/vocab/{field_key}", summary="获取字段的 Whisper 词库")
def get_vocab(field_key: str):
    prompt = get_prompt(field_key)
    return {"field_key": field_key, "prompt": prompt, "length": len(prompt)}


# ── 核心：单字段语音转文字 ────────────────────────────────────────────
@app.post("/transcribe/{field_key}", summary="上传单字段音频，返回识别文字")
async def transcribe_field(
    field_key:  str,
    audio:      UploadFile = File(..., description="音频文件 wav/mp3/m4a/webm"),
    language:   str = Form("zh"),
):
    """
    前端逐字段录音后调用此接口。
    - field_key: 当前录的是哪个字段（用于自动匹配词库）
    - 返回识别出的文字，前端展示给用户确认后再调 /generate
    """
    # 获取该字段的专用词库
    prompt = get_prompt(field_key)

    # 读取音频并转录
    audio_bytes = await audio.read()
    suffix = "." + (audio.filename or "audio.wav").rsplit(".", 1)[-1]

    try:
        text = transcribe_bytes(audio_bytes, suffix=suffix, language=language, prompt=prompt)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"STT 失败: {e}")
        raise HTTPException(status_code=500, detail=f"STT 识别失败: {e}")

    return {
        "field_key": field_key,
        "text":      text,
        "prompt_used": bool(prompt),
        "backend":   STT_BACKEND,
    }


# ── 生成合同 ──────────────────────────────────────────────────────────
@app.post("/generate", summary="传入字段数据，生成合同文件")
def generate(req: VoiceInput):
    fields = auto_generate(req.voice_data)
    try:
        buf = generate_contract(req.contract_type, fields)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{req.contract_type}_{fields['合同编号']}.docx"
    encoded  = urllib.parse.quote(filename)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@app.post("/generate/mock", summary="mock 数据一键生成（测试）")
def generate_mock(contract_type: str = "采购合同"):
    fields = auto_generate(MOCK_VOICE_INPUT)
    try:
        buf = generate_contract(contract_type, fields)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{contract_type}_{fields['合同编号']}_mock.docx"
    encoded  = urllib.parse.quote(filename)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@app.get("/preview/mock", summary="预览 mock 生成的完整字段")
def preview_mock():
    return auto_generate(MOCK_VOICE_INPUT)
