# contract.py
# 合同模板填充 + 文件生成

from pathlib import Path
from io import BytesIO
from docxtpl import DocxTemplate

TEMPLATE_DIR = Path(__file__).parent / "templates"

TEMPLATES = {
    "采购合同": "采购合同模板.docx",
    # 以后加更多类型：
    # "服务合同": "服务合同模板.docx",
    # "劳动合同": "劳动合同模板.docx",
}


def list_templates() -> list[str]:
    return list(TEMPLATES.keys())


def generate_contract(contract_type: str, fields: dict) -> BytesIO:
    """
    用 fields 字典填充指定类型的合同模板，返回 docx 内容的 BytesIO。
    """
    if contract_type not in TEMPLATES:
        raise ValueError(f"未知合同类型：{contract_type}，可用类型：{list(TEMPLATES.keys())}")

    tpl_path = TEMPLATE_DIR / TEMPLATES[contract_type]
    if not tpl_path.exists():
        raise FileNotFoundError(f"模板文件不存在：{tpl_path}")

    tpl = DocxTemplate(str(tpl_path))
    tpl.render(fields)

    buf = BytesIO()
    tpl.save(buf)
    buf.seek(0)
    return buf
