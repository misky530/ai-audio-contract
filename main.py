# main.py  —  语音合同生成 Demo（IT设备供货商版）

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import urllib.parse

from contract import generate_contract, list_templates
from mock_data import VOICE_FIELDS, OUR_COMPANY, DEFAULTS, MOCK_VOICE_INPUT, auto_generate
from vocab import get_prompt, FIELD_PROMPTS

app = FastAPI(title="语音合同生成 Demo", version="0.2.0")


class VoiceInput(BaseModel):
    contract_type: str = "采购合同"
    voice_data: dict   # 只传用户说的那几个字段

    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_type": "采购合同",
                "voice_data": MOCK_VOICE_INPUT,
            }
        }
    }


@app.get("/", summary="服务状态")
def root():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/templates", summary="可用合同类型")
def get_templates():
    return {"templates": list_templates()}


@app.get("/fields", summary="语音输入字段清单")
def get_fields():
    """返回用户需要语音说的字段（9个），以及对应的引导提示和词库 key"""
    return {
        "voice_fields": VOICE_FIELDS,
        "our_company":  OUR_COMPANY,   # 乙方预填，前端可展示给用户确认
        "defaults":     DEFAULTS,       # 标准条款，前端可以折叠展示
        "total_voice":  len(VOICE_FIELDS),
    }


@app.get("/vocab/{field_key}", summary="获取某字段的 Whisper 词库")
def get_vocab(field_key: str):
    """前端在录制某字段音频前，调用此接口获取 initial_prompt，传给 STT 服务"""
    prompt = get_prompt(field_key)
    return {
        "field_key": field_key,
        "prompt": prompt,
        "prompt_length": len(prompt),
    }


@app.post("/generate", summary="传入语音字段，生成合同并下载")
def generate(req: VoiceInput):
    """
    只需传用户说的字段（voice_data），其余自动补全：
    - 乙方信息：系统预填
    - 合同金额大写、税额、预付款等：自动计算
    - 货物名称：由品类+品牌+型号+规格自动拼合
    - 合同编号、签署日期：自动生成
    """
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


@app.post("/generate/mock", summary="用 mock 数据一键生成（测试）")
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


@app.get("/preview/mock", summary="预览 mock 数据生成的完整字段（不下载文件）")
def preview_mock():
    """查看 auto_generate 生成的完整字段，验证自动计算是否正确"""
    return auto_generate(MOCK_VOICE_INPUT)
