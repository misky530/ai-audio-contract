# pdf_extractor.py
# 从报价单 PDF 提取合同字段（pdfplumber + 正则，无需 AI API）

import re
import logging
from io import BytesIO

import pdfplumber

logger = logging.getLogger(__name__)


# ── 工具函数 ──────────────────────────────────────────────────────────

def _clean_price(s: str) -> str:
    """'1,100,000' → '1100000'"""
    return re.sub(r"[^\d.]", "", s or "")


def _months_to_days(text: str) -> str:
    """'4个月' → '120'，'30天' → '30'，纯数字直接返回"""
    m = re.search(r"(\d+)\s*个?月", text)
    if m:
        return str(int(m.group(1)) * 30)
    m = re.search(r"(\d+)\s*天", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d+)", text)
    return m.group(1) if m else ""


def _years_to_months(text: str) -> str:
    """'1 year' / '2年' → '12' / '24'"""
    m = re.search(r"(\d+)\s*(?:year|年)", text, re.IGNORECASE)
    if m:
        return str(int(m.group(1)) * 12)
    m = re.search(r"(\d+)\s*(?:month|个?月)", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


# ── 单 PDF 解析 ───────────────────────────────────────────────────────

def _parse_one(pdf_bytes: bytes) -> dict:
    """
    解析单份报价单 PDF，返回字段字典：
      header  : 甲乙方信息及条款
      items   : 货物列表（排除 Break Down 明细表）
    """
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        all_tables = [t for p in pdf.pages for t in p.extract_tables()]

    result = {}

    # ── 甲方 / 乙方 ───────────────────────────────────────────────────
    # 文本里两栏并排：左侧买方（甲方），右侧卖方（乙方）
    # 示例行: "Company:无锡中汇汽车电子科技有限公司 Company: 珠海凌智自动化科技有限公司"
    companies = re.findall(r"Company\s*[:：]\s*(\S[^\n]*?)(?=\s+Company\s*[:：]|\n|$)", full_text)
    if len(companies) >= 1:
        result["甲方名称"] = companies[0].strip()
    if len(companies) >= 2:
        result["乙方名称"] = companies[1].strip()

    # 甲方地址（第一个 Address）
    addresses = re.findall(r"Address\s*[:：]\s*(.+?)(?=\s+Address\s*[:：]|\n|Tel\s*[:：]|$)", full_text)
    if len(addresses) >= 1:
        result["甲方地址"] = addresses[0].strip()
    if len(addresses) >= 2:
        result["乙方地址"] = addresses[1].strip()

    # 乙方电话（Tel 行）
    m = re.search(r"Tel\s*[:：]\s*([+\d\-\s]+)", full_text)
    if m:
        result["乙方电话"] = m.group(1).strip()

    # 乙方联系人 + 手机
    m = re.search(r"Contact\s*[:：]\s*(.+?)(?:\(([+\d\s\-]+)\))?[\n$]", full_text)
    if m:
        result["乙方联系人"] = m.group(1).strip()

    # ── 条款 ─────────────────────────────────────────────────────────
    # 质保期  "Warranty : 1 year"
    m = re.search(r"Warranty\s*[:：]\s*(.+)", full_text, re.IGNORECASE)
    if m:
        result["质保期"] = _years_to_months(m.group(1))

    # 交货期  "Lead time:货期4个月" / "货期4个月"
    m = re.search(r"[Ll]ead\s*[Tt]ime\s*[:：]?\s*货?期?(.+)", full_text)
    if m:
        result["交货期限"] = _months_to_days(m.group(1))

    # 付款条款  "预付款 50%,出厂前验收40%，到厂验收后10%"
    m = re.search(r"预付款\s*(\d+)\s*%", full_text)
    if m:
        result["预付款比例"] = m.group(1)
    m = re.search(r"出厂[前]?验收\s*(\d+)\s*%", full_text)
    if m:
        result["出厂验收比例"] = m.group(1)
    m = re.search(r"到厂验收后?\s*(\d+)\s*%", full_text)
    if m:
        result["到厂验收比例"] = m.group(1)

    # 税率  "13%增值税"
    m = re.search(r"(\d+)\s*%\s*增值税", full_text)
    if m:
        result["税率"] = m.group(1)

    # 运费 / 交货地点  "送货至客户现场"
    m = re.search(r"[Dd]elivery\s*[Tt]erms\s*[:：]\s*(.+)", full_text)
    if m:
        val = m.group(1).strip()
        if "客户" in val or "现场" in val:
            result["运费承担方"] = "乙方"
            result["交货地点"]   = "甲方指定地点"

    # ── 货物列表（主报价表，跳过 Break Down 明细表）────────────────────
    items = []
    for table in all_tables:
        if not table:
            continue
        # Break Down 明细表：首行含 'Break Down'
        header = table[0]
        if any("Break Down" in str(c) for c in header):
            continue
        # 主货物表：行格式 [seq, model, description, qty, unit_price, total]
        for row in table:
            if not row or len(row) < 4:
                continue
            seq, *rest = row
            # seq 必须是纯数字
            if not str(seq or "").strip().isdigit():
                continue
            # 根据列数解析
            if len(rest) >= 4:
                # [model_or_desc, desc, qty, price, ...]  (6 列含型号)
                model = str(rest[0] or "").strip()
                desc  = str(rest[1] or "").strip()
                qty   = str(rest[2] or "1").strip()
                price = _clean_price(rest[3])
                name  = f"{model} {desc}".strip() if model else desc
            else:
                # [desc, qty, price, ...]  (4-5 列无型号)
                desc  = str(rest[0] or "").strip()
                qty   = str(rest[1] or "1").strip()
                price = _clean_price(rest[2]) if len(rest) > 2 else ""
                name  = desc

            if name:
                items.append({
                    "货物品类": name,
                    "货物品牌": "",
                    "货物型号": "",
                    "货物规格": "",
                    "数量":     f"{qty}台",
                    "单价":     price,
                })

    result["_items"] = items
    return result


# ── 多 PDF 合并 ───────────────────────────────────────────────────────

def pdf_bytes_list_to_contract_fields(pdf_bytes_list: list[bytes]) -> tuple[dict, list]:
    """
    主入口：解析一个或多个报价单 PDF，返回 (voice_data, items)。
    多个 PDF 的 items 会合并；甲乙方信息取第一个有值的文档。
    """
    all_items: list[dict] = []
    merged: dict = {}

    for pdf_bytes in pdf_bytes_list:
        parsed = _parse_one(pdf_bytes)
        items  = parsed.pop("_items", [])
        all_items.extend(items)
        # header 字段：不覆盖已有值（优先第一份 PDF）
        for k, v in parsed.items():
            if v and k not in merged:
                merged[k] = v

    # 乙方信息不传给 auto_generate（系统 OUR_COMPANY 是固定乙方）
    voice_data = {k: v for k, v in merged.items()
                  if not k.startswith("乙方") and v}

    # 条款字段透传
    for key in ("质保期", "交货期限", "预付款比例", "出厂验收比例", "到厂验收比例",
                "税率", "运费承担方", "交货地点"):
        if key in merged and merged[key]:
            voice_data[key] = merged[key]

    logger.info(f"PDF 提取完成：{len(all_items)} 个货物，字段={list(voice_data.keys())}")
    return voice_data, all_items
