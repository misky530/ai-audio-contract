import asyncio, os, edge_tts

VOICE = "zh-CN-YunxiNeural"

SAMPLES = [
    ("甲方名称",     "北京星辰科技有限公司"),
    ("甲方联系人",   "张伟"),
    ("甲方电话",     "一三八，零零一，三八，零零零"),
    ("货物品类",     "笔记本电脑"),
    ("货物品牌",     "联想"),
    ("货物型号",     "ThinkPad X1 Carbon Gen12"),
    ("货物规格",     "十六个G内存，五百一十二个G固态硬盘"),  # 避免裸G
    ("数量",         "五十台"),
    ("合同金额数字", "四十九万元整"),
]

async def gen(text, path):
    await edge_tts.Communicate(text, VOICE).save(path)

async def main():
    os.makedirs("test_audio", exist_ok=True)
    print(f"声音：{VOICE}\n")
    for field_key, text in SAMPLES:
        path = f"test_audio/{field_key}.mp3"
        if os.path.exists(path):
            print(f"  - 跳过（已存在）: {field_key}.mp3")
            continue
        try:
            await gen(text, path)
            size = os.path.getsize(path)
            print(f"  ✓ {field_key}.mp3  {size:,} bytes  [{text}]")
        except Exception as e:
            print(f"  ✗ {field_key} 失败: {e}")

    print("""
完成！test_audio/ 目录下的 mp3 文件可直接用于测试。

测试命令（CMD，服务启动后）：
  curl -X POST "http://localhost:8000/transcribe/货物型号" ^
       -F "audio=@test_audio/货物型号.mp3" ^
       -F "language=zh"

或访问 http://localhost:8000/docs 在线上传测试
""")

asyncio.run(main())
