# create_template.py — 生成支持多条货物的合同模板
# 运行一次即可：python create_template.py

from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUTPUT = Path("templates") / "采购合同模板.docx"
Path("templates").mkdir(exist_ok=True)

doc = Document()
for sec in doc.sections:
    sec.top_margin = sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(3); sec.right_margin = Cm(2.5)

def bold_para(doc, text, size=12, center=False):
    p = doc.add_paragraph()
    if center: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.bold = True; r.font.size = Pt(size)
    return p

def clause(doc, text):
    p = doc.add_paragraph(text)
    p.paragraph_format.left_indent = Pt(24)
    return p

def set_col_width(table, col, width_cm):
    for cell in table.columns[col].cells:
        cell.width = Cm(width_cm)

# ── 标题 ──────────────────────────────────────────────────────────────
bold_para(doc, "采  购  合  同", size=22, center=True)
doc.add_paragraph()

# ── 编号 & 日期 ───────────────────────────────────────────────────────
p = doc.add_paragraph()
p.add_run("合同编号：").bold = True
p.add_run("{{合同编号}}")
p.add_run("          签署日期：").bold = True
p.add_run("{{签署日期}}")

doc.add_paragraph()

# ── 甲乙方信息 ────────────────────────────────────────────────────────
pt = doc.add_table(rows=4, cols=2); pt.style = "Table Grid"
rows_data = [
    ("甲方（买方）：{{甲方名称}}", "地址：{{甲方地址}}"),
    ("联系人：{{甲方联系人}}",     "电话：{{甲方电话}}"),
    ("乙方（卖方）：{{乙方名称}}", "地址：{{乙方地址}}"),
    ("联系人：{{乙方联系人}}",     "电话：{{乙方电话}}"),
]
for r, (a, b) in enumerate(rows_data):
    pt.rows[r].cells[0].text = a
    pt.rows[r].cells[1].text = b

doc.add_paragraph()

# ── 一、货物清单（多条，Jinja2 loop）────────────────────────────────
bold_para(doc, "一、货物清单")

COLS = ["序号", "货物名称及规格", "品牌", "数量", "单位", "单价（元）", "小计（元）"]
COL_W = [1.2, 5.5, 2.5, 1.5, 1.2, 2.5, 2.5]

gt = doc.add_table(rows=3, cols=len(COLS)); gt.style = "Table Grid"

# 表头行
for i, (h, w) in enumerate(zip(COLS, COL_W)):
    c = gt.rows[0].cells[i]; c.text = h
    c.paragraphs[0].runs[0].bold = True
    c.width = Cm(w)

# 循环模板行（docxtpl: {%tr for %} 放在第一列）
loop_row = [
    "{%tr for item in items %}",
    "{{item.货物名称}}",
    "{{item.品牌}}",
    "{{item.数量}}",
    "{{item.单位}}",
    "{{item.单价}}",
    "{{item.小计}}",
]
for i, v in enumerate(loop_row):
    gt.rows[1].cells[i].text = v

# 合计行（{%tr endfor %} 放在第一列）
total_row = ["{%tr endfor %}", "合    计", "", "", "", "", "{{合同金额数字}} 元"]
for i, v in enumerate(total_row):
    c = gt.rows[2].cells[i]; c.text = v
    if i in (1, 6): c.paragraphs[0].runs[0].bold = True

doc.add_paragraph()

# ── 二、合同金额 ──────────────────────────────────────────────────────
bold_para(doc, "二、合同金额")
clause(doc, "合同总价款人民币（大写）{{合同金额大写}}，小写 ¥{{合同金额数字}} 元，"
            "含税率 {{税率}}%，税额 {{税额}} 元。")

# ── 三、交货条款 ──────────────────────────────────────────────────────
bold_para(doc, "三、交货条款")
clause(doc, "1. 交货地点：{{交货地点}}。")
clause(doc, "2. 交货期限：合同签订后 {{交货期限}} 天内完成交付；运费由{{运费承担方}}承担。")
clause(doc, "3. 质量标准：{{质量标准}}；质保期 {{质保期}} 个月。")

# ── 四、付款方式 ──────────────────────────────────────────────────────
bold_para(doc, "四、付款方式")
clause(doc, "1. 合同签订后 {{预付款天数}} 个工作日内，甲方支付预付款（{{预付款比例}}%）"
            "共 ¥{{预付款金额}} 元。")
clause(doc, "2. 验收合格后 {{到货付款天数}} 个工作日内，甲方支付余款 ¥{{余款金额}} 元。")
clause(doc, "3. 收款户名：{{收款户名}}；开户行：{{开户银行}}；账号：{{银行账号}}。")

# ── 五、违约 ──────────────────────────────────────────────────────────
bold_para(doc, "五、验收与违约")
clause(doc, "1. 甲方收货后 {{验收期限}} 天内完成验收；质量问题乙方 {{整改期限}} 天内整改。")
clause(doc, "2. 逾期交货：每日按合同金额 {{逾期违约金比例}}‰ 支付违约金。")
clause(doc, "3. 逾期付款：每日按逾期金额 {{逾期付款利率}}‰ 支付利息。")

# ── 六、其他 ──────────────────────────────────────────────────────────
bold_para(doc, "六、其他约定")
clause(doc, "{{其他约定}}")
clause(doc, "争议提交{{争议解决地}}仲裁委员会仲裁。本合同一式两份，签字盖章后生效。")

doc.add_paragraph(); doc.add_paragraph()

# ── 签字页 ────────────────────────────────────────────────────────────
st = doc.add_table(rows=3, cols=2); st.style = "Table Grid"
sig_rows = [
    ("甲方（盖章）：", "乙方（盖章）："),
    ("授权代表（签字）：", "授权代表（签字）："),
    ("日期：", "日期："),
]
for r, (a, b) in enumerate(sig_rows):
    st.rows[r].cells[0].text = a
    st.rows[r].cells[1].text = b

doc.save(OUTPUT)
print(f"✓ 新模板已生成：{OUTPUT}")
print("  货物清单支持多条（items 循环），其余条款完整。")
