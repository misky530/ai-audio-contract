# main.py  —  语音合同生成（阶段二：接入 STT）

import os, urllib.parse, logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from contract import generate_contract, list_templates
from mock_data import HEADER_FIELDS, ITEM_FIELDS, OUR_COMPANY, DEFAULTS, MOCK_VOICE_INPUT, MOCK_ITEMS, auto_generate
from vocab import get_prompt
from stt import transcribe_bytes, STT_BACKEND
import knowledge as kb
from pdf_extractor import pdf_bytes_list_to_contract_fields

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="语音合同生成", version="0.4.0")

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
@app.post("/generate", summary="传入字段数据，生成合同文件")
def generate(req: VoiceInput):
    fields = auto_generate(req.voice_data, req.items or None)
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


@app.post("/generate/from-pdf", summary="上传一个或多个报价单 PDF，自动提取字段并生成合同")
async def generate_from_pdf(
    files: list[UploadFile] = File(..., description="一个或多个报价单 PDF"),
    contract_type: str = Form("采购合同"),
):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个 PDF 文件")

    pdf_bytes_list = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} 不是 PDF 文件")
        pdf_bytes_list.append(await f.read())

    try:
        voice_data, items = pdf_bytes_list_to_contract_fields(pdf_bytes_list)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"PDF 提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {e}")

    fields = auto_generate(voice_data, items or None)

    try:
        buf = generate_contract(contract_type, fields)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{contract_type}_{fields['合同编号']}.docx"
    encoded  = urllib.parse.quote(filename)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@app.post("/generate/from-pdf/preview", summary="预览从 PDF 提取的字段（不生成合同）")
async def preview_from_pdf(
    files: list[UploadFile] = File(..., description="一个或多个报价单 PDF"),
):
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个 PDF 文件")

    pdf_bytes_list = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} 不是 PDF 文件")
        pdf_bytes_list.append(await f.read())

    try:
        voice_data, items = pdf_bytes_list_to_contract_fields(pdf_bytes_list)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"PDF 提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {e}")

    fields = auto_generate(voice_data, items or None)
    return {"extracted": voice_data, "items": items, "full_fields": fields}


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
