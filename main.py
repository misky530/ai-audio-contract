# main.py  —  语音合同生成（阶段二：接入 STT）

import os, uuid, urllib.parse, logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO

from contract import generate_contract, list_templates
from mock_data import HEADER_FIELDS, ITEM_FIELDS, OUR_COMPANY, DEFAULTS, MOCK_VOICE_INPUT, MOCK_ITEMS, auto_generate
from vocab import get_prompt
from stt import transcribe_bytes, STT_BACKEND
import knowledge as kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="语音合同生成", version="0.4.0")

# 临时文件存储：token -> (bytes, filename)，用于移动端可靠下载
_download_store: dict = {}

# ── CORS（允许手机/前端跨域访问）────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 静态文件（H5 前端）────────────────────────────────────────────────
import pathlib
STATIC_DIR = pathlib.Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

@app.get("/app", include_in_schema=False)
async def serve_app():
    """返回前端页面，强制 no-cache，避免手机浏览器缓存旧版本"""
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


# ── Schema ────────────────────────────────────────────────────────────
class VoiceInput(BaseModel):
    contract_type: str = "采购合同"
    voice_data: dict
    items: list[dict] = []
    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_type": "采购合同",
                "voice_data": MOCK_VOICE_INPUT,
                "items": MOCK_ITEMS,
            }
        }
    }


# ── 基础接口 ──────────────────────────────────────────────────────────
@app.get("/", summary="服务状态")
def root():
    return {"status": "ok", "version": "0.4.0", "stt_backend": STT_BACKEND}

@app.get("/templates")
def get_templates():
    return {"templates": list_templates()}

@app.get("/fields", summary="语音输入字段清单")
def get_fields():
    return {
        "header_fields": HEADER_FIELDS,
        "item_fields":   ITEM_FIELDS,
        "our_company":   OUR_COMPANY,
        "defaults":      DEFAULTS,
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
    prompt      = get_prompt(field_key)
    audio_bytes = await audio.read()
    suffix      = "." + (audio.filename or "audio.wav").rsplit(".", 1)[-1]

    try:
        text = transcribe_bytes(audio_bytes, suffix=suffix, language=language, prompt=prompt)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"STT 失败: {e}")
        raise HTTPException(status_code=500, detail=f"STT 识别失败: {e}")

    suggestions = kb.suggest(field_key, text)
    return {
        "field_key":   field_key,
        "text":        text,
        "suggestions": suggestions,
        "prompt_used": bool(prompt),
        "backend":     STT_BACKEND,
    }


# ── 生成合同 ──────────────────────────────────────────────────────────
@app.post("/generate", summary="传入字段数据，生成合同文件（返回下载 token）")
def generate(req: VoiceInput):
    fields = auto_generate(req.voice_data, req.items or None)
    try:
        buf = generate_contract(req.contract_type, fields)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{req.contract_type}_{fields['合同编号']}.docx"
    token    = str(uuid.uuid4())
    _download_store[token] = (buf.read(), filename)
    return JSONResponse({"token": token, "filename": filename})


@app.get("/download/{token}", summary="凭 token 下载合同文件")
def download(token: str):
    if token not in _download_store:
        raise HTTPException(status_code=404, detail="下载链接已失效，请重新生成")
    data, filename = _download_store.pop(token)
    encoded = urllib.parse.quote(filename)
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@app.post("/generate/mock", summary="mock 数据一键生成（测试）")
def generate_mock(contract_type: str = "采购合同"):
    fields = auto_generate(MOCK_VOICE_INPUT, MOCK_ITEMS)
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


# ── 知识库管理 ────────────────────────────────────────────────────────
@app.get("/knowledge", summary="查看知识库")
def get_knowledge():
    return kb.load()

@app.post("/knowledge/reload", summary="重新加载知识库（编辑 knowledge.json 后调用）")
def reload_knowledge():
    data = kb.reload()
    return {"status": "ok", "counts": {k: len(v) for k, v in data.items()}}
