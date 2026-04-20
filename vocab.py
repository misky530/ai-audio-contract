# vocab.py  —  IT设备语音识别词库
#
# 按字段类型分组，录音时根据当前字段切换对应的 initial_prompt
# Whisper 会把 prompt 当作"上文"，优先识别其中出现过的词汇

# ── 品类词库 ──────────────────────────────────────────────────────────
# 用于：录入"货物品类"子字段时
PROMPT_CATEGORY = """
笔记本电脑，台式机，工作站，服务器，
显示器，打印机，复印机，扫描仪，投影仪，
交换机，路由器，防火墙，无线AP，网络设备，
UPS电源，机柜，KVM切换器，
固态硬盘，机械硬盘，内存条，显卡，CPU处理器，
键盘，鼠标，摄像头，耳机，麦克风，
移动硬盘，U盘，读卡器，网卡，声卡，
光纤模块，网线，光纤，跳线，理线架
"""

# ── 品牌词库 ──────────────────────────────────────────────────────────
# 用于：录入"品牌"子字段时
PROMPT_BRAND = """
联想，ThinkPad，ThinkCentre，ThinkStation，Legion，
戴尔，Dell，OptiPlex，Latitude，Precision，PowerEdge，
惠普，HP，EliteBook，ProBook，ZBook，ProLiant，
华为，HUAWEI，MateBook，FusionServer，
苹果，Apple，MacBook，Mac Pro，Mac mini，iMac，
华硕，ASUS，宏碁，Acer，微星，MSI，
微软，Microsoft，Surface，
思科，Cisco，华三，H3C，锐捷，
博科，Brocade，Juniper，瞻博，
西部数据，WD，希捷，Seagate，三星，Samsung，
金士顿，Kingston，英睿达，Crucial，芝奇，G.Skill，
英伟达，NVIDIA，AMD，英特尔，Intel
"""

# ── 型号词库 ──────────────────────────────────────────────────────────
# 用于：录入"型号"子字段时（常见型号缩写 STT 最容易出错）
PROMPT_MODEL = """
X1 Carbon，X1 Extreme，T14，T16，P16，P1，
L14，L15，E14，E15，V14，V15，
Latitude 5540，Latitude 7440，Precision 5570，
OptiPlex 7090，OptiPlex 3090，
EliteBook 840，EliteBook 1040，ZBook Studio，
ProBook 450，ProBook 640，
PowerEdge R750，PowerEdge R650，PowerEdge T550，
ProLiant DL380，ProLiant ML350，
FusionServer 2288H，FusionServer 5288，
MateBook 14，MateBook X Pro，MateBook D16，
Surface Pro，Surface Laptop，Surface Book，
MacBook Pro，MacBook Air，Mac mini，Mac Pro，
Gen9，Gen10，Gen11，Gen12，Gen13，Gen14，
i5，i7，i9，志强，Xeon，至强，
E5，E7，Silver，Gold，Platinum，
EPYC，Ryzen，Threadripper，
RTX 4090，RTX 4080，RTX 4070，RTX 3090，
A100，A40，A30，H100，L40
"""

# ── 规格词库 ──────────────────────────────────────────────────────────
# 用于：录入"规格配置"子字段时
PROMPT_SPEC = """
八核，十二核，十六核，三十二核，六十四核，
十六G，三十二G，六十四G，一二八G，二五六G，
内存，DDR4，DDR5，ECC，
五百一十二G，一T，二T，四T，八T，
固态，SSD，NVMe，SATA，SAS，
千兆，万兆，二十五G，四十G，一百G，
单电源，双电源，冗余电源，
十四寸，十五寸，十六寸，十七寸，
1080P，2K，4K，IPS，OLED，
标准版，专业版，企业版，旗舰版，
含税，不含税，原装，行货，国行
"""

# ── 单位词库 ──────────────────────────────────────────────────────────
PROMPT_UNIT = """
台，套，个，件，块，片，条，根，
批，箱，包，卷，米，根
"""

# ── 公司名词库 ────────────────────────────────────────────────────────
# 用于：录入"甲方公司名称"时
# 实际使用时可以把你们的常见客户名称加进来
PROMPT_COMPANY = """
北京，上海，广州，深圳，杭州，成都，武汉，南京，
有限公司，股份有限公司，集团有限公司，
科技，信息技术，数据，网络，系统，软件，
中国，国家，中心，研究院，研究所，大学，
总公司，分公司，子公司，事业部
"""

# ── 按字段名映射到对应词库 ────────────────────────────────────────────
FIELD_PROMPTS = {
    "甲方名称":   PROMPT_COMPANY,
    "甲方联系人": "",               # 人名不需要词库
    "甲方电话":   "",               # 数字 Whisper 本身准确
    "货物品类":   PROMPT_CATEGORY,
    "货物品牌":   PROMPT_BRAND,
    "货物型号":   PROMPT_MODEL,
    "货物规格":   PROMPT_SPEC,
    "数量":       PROMPT_UNIT,
    "合同金额数字": "",             # 纯数字，Whisper 准确
}


def get_prompt(field_key: str) -> str:
    """根据字段名返回对应的 Whisper initial_prompt"""
    return FIELD_PROMPTS.get(field_key, "")
