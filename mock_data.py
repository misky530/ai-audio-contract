# mock_data.py  —  字段分层管理（IT设备供货商版）

from datetime import date, datetime
import re

# ── 1. 乙方（我方）固定信息 ──────────────────────────────────────────
OUR_COMPANY = {
    "乙方名称":   "北京云帆科技有限公司",
    "乙方联系人": "王芳",
    "乙方电话":   "010-88888888",
    "乙方地址":   "北京市海淀区中关村南大街5号",
    "收款户名":   "北京云帆科技有限公司",
    "开户银行":   "中国工商银行北京中关村支行",
    "银行账号":   "0200004609200114114",
}

# ── 2. 甲方语音录入字段（仅甲方信息）────────────────────────────────
HEADER_FIELDS = [
    {"key": "甲方名称",   "label": "甲方公司名称", "hint": "请说出对方公司全称，例如：北京星辰科技有限公司",   "vocab": "甲方名称"},
    {"key": "甲方联系人", "label": "甲方联系人",   "hint": "请说出对方联系人姓名，例如：张伟",                 "vocab": "甲方联系人"},
    {"key": "甲方电话",   "label": "甲方联系电话", "hint": "请逐字说出电话号码，例如：一三八零零一三八零零零", "vocab": "甲方电话"},
]

# ── 3. 每条货物的录入字段 ─────────────────────────────────────────────
ITEM_FIELDS = [
    {"key": "货物品类", "label": "货物品类",       "hint": "请说出设备类型，例如：笔记本电脑、服务器",            "vocab": "货物品类"},
    {"key": "货物品牌", "label": "货物品牌",       "hint": "请说出品牌名称，例如：联想、戴尔、华为",              "vocab": "货物品牌"},
    {"key": "货物型号", "label": "货物型号",       "hint": "请说出具体型号，例如：ThinkPad X1 Carbon Gen12",     "vocab": "货物型号"},
    {"key": "货物规格", "label": "货物规格配置",   "hint": "请说出主要配置，例如：十六G内存 五百一十二G固态",     "vocab": "货物规格"},
    {"key": "数量",     "label": "采购数量",       "hint": "请说出数量和单位，例如：五十台",                      "vocab": "数量"},
    {"key": "单价",     "label": "单价（元/台）",  "hint": "请说出单件价格，例如：九千八百元，或不知道直接跳过",  "vocab": "合同金额数字"},
]

# 向后兼容
VOICE_FIELDS = HEADER_FIELDS + ITEM_FIELDS

# ── 4. 标准条款默认值 ─────────────────────────────────────────────────
DEFAULTS = {
    "甲方地址":         "",
    "计量单位":         "台",
    "品牌产地":         "",
    "备注":             "无",
    "税率":             "13",
    "交货地点":         "",
    "交货期限":         "30",
    "运费承担方":       "乙方",
    "质量标准":         "国家相关质量标准",
    "质保期":           "12",
    "预付款比例":       "30",
    "预付款天数":       "5",
    "出厂验收比例":     "60",
    "到厂验收比例":     "10",
    "到货付款天数":     "10",
    "验收期限":         "5",
    "整改期限":         "15",
    "逾期违约金比例":   "3",
    "逾期付款利率":     "2",
    "争议解决地":       "北京",
    "其他约定":         "无",
}

# ── 5. 工具函数 ───────────────────────────────────────────────────────
def 数字转大写(amount_str: str) -> str:
    digits = re.sub(r"[^\d.]", "", amount_str)
    if not digits:
        return ""
    try:
        amount = float(digits)
    except ValueError:
        return amount_str
    units = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]
    chars = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
    int_part = int(amount)
    result, s, n = "", str(int_part), len(str(int_part))
    for i, c in enumerate(s):
        d, pos = int(c), n - i - 1
        if d != 0:
            result += chars[d] + units[pos]
        elif result and result[-1] != "零":
            result += "零"
    result = result.rstrip("零") or "零"
    return result + "元整"


def 格式化金额(amount_str: str) -> str:
    digits = re.sub(r"[^\d.]", "", amount_str)
    try:
        return f"{float(digits):,.2f}"
    except (ValueError, TypeError):
        return amount_str


def 生成合同编号() -> str:
    return f"HT{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _parse_quantity(数量原文: str) -> tuple:
    """返回 (数量字符串, 单位字符串)"""
    m = re.search(r"(台|套|个|件|块|片|条|根|批|箱)", 数量原文)
    单位 = m.group(1) if m else "台"
    数量 = re.sub(r"[台套个件块片条根批箱]", "", 数量原文).strip() or 数量原文
    return 数量, 单位


def _process_item(item: dict, index: int) -> tuple:
    """处理单条货物，返回 (item_dict, 小计数字)"""
    品牌 = item.get("货物品牌", "")
    型号 = item.get("货物型号", "")
    品类 = item.get("货物品类", "")
    规格 = item.get("货物规格", "")

    名称 = " ".join(p for p in [品牌, 型号, 品类] if p)
    if 规格:
        名称 += f"（{规格}）"

    数量, 单位 = _parse_quantity(item.get("数量", ""))

    单价原文  = item.get("单价", "0")
    单价数字  = float(re.sub(r"[^\d.]", "", 单价原文) or "0")
    try:
        数量数字 = float(re.sub(r"[^\d.]", "", 数量) or "0")
    except ValueError:
        数量数字 = 0
    小计数字 = 单价数字 * 数量数字

    return {
        "序号":   str(index + 1),
        "货物名称": 名称,
        "品牌":   品牌,
        "数量":   数量,
        "单位":   单位,
        "单价":   f"{单价数字:,.2f}" if 单价数字 else "",
        "小计":   f"{小计数字:,.2f}" if 小计数字 else "",
        "备注":   item.get("备注", ""),
    }, 小计数字


# ── 6. 核心：合并所有字段 ─────────────────────────────────────────────
def auto_generate(voice_input: dict, items: list = None, breakdown: list = None) -> dict:
    """
    voice_input : 甲方信息等 header 字段
    items       : 货物列表，每项含 货物品牌/型号/品类/规格/数量/单价
    """
    fields = {}
    fields.update(OUR_COMPANY)
    fields.update(DEFAULTS)
    fields.update(voice_input)

    processed_items = []
    total_amount    = 0.0

    if items:
        for i, item in enumerate(items):
            p, subtotal = _process_item(item, i)
            processed_items.append(p)
            total_amount += subtotal
    else:
        # 兼容旧单品模式
        parts = [voice_input.get("货物品牌",""), voice_input.get("货物型号",""), voice_input.get("货物品类","")]
        spec  = voice_input.get("货物规格", "")
        名称  = " ".join(p for p in parts if p)
        if spec:
            名称 += f"（{spec}）"
        数量, 单位 = _parse_quantity(voice_input.get("数量", ""))
        processed_items = [{
            "序号": "1", "货物名称": 名称, "品牌": voice_input.get("货物品牌",""),
            "数量": 数量, "单位": 单位, "单价": "", "小计": "", "备注": "",
        }]
        金额原文     = voice_input.get("合同金额数字", "0")
        total_amount = float(re.sub(r"[^\d.]", "", 金额原文) or "0")
        fields["计量单位"] = 单位
        fields["数量"]     = 数量

    fields["items"] = processed_items

    # 金额计算
    if total_amount > 0:
        fields["合同金额数字"] = f"{total_amount:,.2f}"
        fields["合同金额大写"] = 数字转大写(str(total_amount))
        税率  = float(fields.get("税率", "13")) / 100
        fields["税额"] = f"{total_amount * 税率 / (1 + 税率):,.2f}"
        预付比  = float(fields.get("预付款比例",   "30")) / 100
        出厂比  = float(fields.get("出厂验收比例", "60")) / 100
        到厂比  = float(fields.get("到厂验收比例", "10")) / 100
        fields["预付款金额"]   = f"{total_amount * 预付比:,.2f}"
        fields["出厂验收金额"] = f"{total_amount * 出厂比:,.2f}"
        fields["到厂验收金额"] = f"{total_amount * 到厂比:,.2f}"
        # 兼容旧字段
        fields["余款金额"] = f"{total_amount * (1 - 预付比):,.2f}"
    else:
        fields["合同金额数字"] = fields["合同金额大写"] = ""
        fields["税额"] = fields["预付款金额"] = fields["余款金额"] = ""
        fields["出厂验收金额"] = fields["到厂验收金额"] = ""

    if not fields.get("交货地点"):
        fields["交货地点"] = fields.get("甲方地址") or "甲方指定地点"

    fields["breakdown_items"] = breakdown or []
    fields["合同编号"] = 生成合同编号()
    fields["签署日期"] = date.today().strftime("%Y年%m月%d日")
    return fields


# ── 7. Mock 数据 ──────────────────────────────────────────────────────
MOCK_VOICE_INPUT = {
    "甲方名称":   "北京星辰科技有限公司",
    "甲方联系人": "张伟",
    "甲方电话":   "13800138000",
    "甲方地址":   "北京市朝阳区望京街道10号",
}

MOCK_ITEMS = [
    {
        "货物品类": "笔记本电脑",
        "货物品牌": "联想",
        "货物型号": "ThinkPad X1 Carbon Gen12",
        "货物规格": "16G内存 512G固态",
        "数量":     "50台",
        "单价":     "9800",
    },
    {
        "货物品类": "服务器",
        "货物品牌": "戴尔",
        "货物型号": "PowerEdge R750",
        "货物规格": "双路Xeon 256G内存",
        "数量":     "2台",
        "单价":     "85000",
    },
]
