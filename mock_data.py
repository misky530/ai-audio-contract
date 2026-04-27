# mock_data.py  —  字段分层管理（IT设备供货商版）

from datetime import date
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

# ── 2. 用户语音输入字段 ───────────────────────────────────────────────
VOICE_FIELDS = [
    {"key": "甲方名称",     "label": "甲方公司名称",   "hint": "请说出对方公司全称，例如：北京星辰科技有限公司",          "vocab": "甲方名称"},
    {"key": "甲方联系人",   "label": "甲方联系人",     "hint": "请说出对方联系人姓名，例如：张伟",                        "vocab": "甲方联系人"},
    {"key": "甲方电话",     "label": "甲方联系电话",   "hint": "请说出对方联系电话，例如：一三八零零一三八零零零",         "vocab": "甲方电话"},
    {"key": "货物品类",     "label": "货物品类",       "hint": "请说出设备类型，例如：笔记本电脑、服务器、交换机",         "vocab": "货物品类"},
    {"key": "货物品牌",     "label": "货物品牌",       "hint": "请说出品牌名称，例如：联想、戴尔、华为",                   "vocab": "货物品牌"},
    {"key": "货物型号",     "label": "货物型号",       "hint": "请说出具体型号，例如：ThinkPad X1 Carbon Gen12",          "vocab": "货物型号"},
    {"key": "货物规格",     "label": "货物规格配置",   "hint": "请说出主要配置，例如：十六G内存 五百一十二G固态",          "vocab": "货物规格"},
    {"key": "数量",         "label": "采购数量",       "hint": "请说出数量和单位，例如：五十台",                           "vocab": "数量"},
    {"key": "合同金额数字", "label": "合同总金额（元）","hint": "请说出合同金额，例如：四十九万，或者四十九万元整",         "vocab": "合同金额数字"},
]

# ── 3. 标准条款默认值 ─────────────────────────────────────────────────
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
    "到货付款天数":     "10",
    "验收期限":         "5",
    "整改期限":         "15",
    "逾期违约金比例":   "3",
    "逾期付款利率":     "2",
    "争议解决地":       "北京",
    "其他约定":         "无",
}


# ── 4. 自动计算字段 ───────────────────────────────────────────────────

def 数字转大写(amount_str: str) -> str:
    digits = re.sub(r"[^\d.]", "", amount_str)
    if not digits:
        return ""
    try:
        amount = float(digits)
    except ValueError:
        return amount_str
    units  = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]
    chars  = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
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
    from datetime import datetime
    return f"HT{datetime.now().strftime('%Y%m%d%H%M%S')}"


def auto_generate(voice_input: dict) -> dict:
    """把用户语音输入 + 乙方固定信息 + 默认值 + 自动计算，合并成完整字段字典"""
    fields = {}
    fields.update(OUR_COMPANY)
    fields.update(DEFAULTS)
    fields.update(voice_input)

    # 货物名称：拼合品牌 + 型号 + 品类 + 规格
    parts = [voice_input.get("货物品牌",""), voice_input.get("货物型号",""), voice_input.get("货物品类","")]
    spec  = voice_input.get("货物规格", "")
    名称  = " ".join(p for p in parts if p)
    if spec:
        名称 += f"（{spec}）"
    fields["货物名称"] = 名称
    fields["品牌产地"] = voice_input.get("货物品牌", "")

    # 从数量原文中提取单位
    数量原文 = voice_input.get("数量", "")
    m = re.search(r"(台|套|个|件|块|片|条|根|批|箱)", 数量原文)
    if m:
        fields["计量单位"] = m.group(1)
        fields["数量"]     = re.sub(r"[台套个件块片条根批箱]", "", 数量原文).strip()

    # 金额自动计算
    金额原文 = voice_input.get("合同金额数字", "0")
    fields["合同金额数字"] = 格式化金额(金额原文)
    fields["合同金额大写"] = 数字转大写(金额原文)
    try:
        金额 = float(re.sub(r"[^\d.]", "", 金额原文))
        税率 = float(fields.get("税率","13")) / 100
        fields["税额"]      = f"{金额 * 税率 / (1 + 税率):,.2f}"
        预付 = 金额 * float(fields.get("预付款比例","30")) / 100
        fields["预付款金额"] = f"{预付:,.2f}"
        fields["余款金额"]   = f"{金额 - 预付:,.2f}"
    except (ValueError, ZeroDivisionError):
        fields["税额"] = fields["预付款金额"] = fields["余款金额"] = ""

    # 交货地点默认同甲方地址
    if not fields.get("交货地点"):
        fields["交货地点"] = fields.get("甲方地址") or "甲方指定地点"

    fields["合同编号"] = 生成合同编号()
    fields["签署日期"] = date.today().strftime("%Y年%m月%d日")
    return fields


# ── 5. Mock 语音输入（测试用）────────────────────────────────────────
MOCK_VOICE_INPUT = {
    "甲方名称":     "北京星辰科技有限公司",
    "甲方联系人":   "张伟",
    "甲方电话":     "13800138000",
    "甲方地址":     "北京市朝阳区望京街道10号",
    "货物品类":     "笔记本电脑",
    "货物品牌":     "联想",
    "货物型号":     "ThinkPad X1 Carbon Gen12",
    "货物规格":     "十六G内存 五百一十二G固态",
    "数量":         "50台",
    "合同金额数字": "490000",
}
