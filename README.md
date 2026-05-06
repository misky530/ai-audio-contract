# 语音合同生成 Demo — 阶段一：链路跑通（Mock）

## 项目结构

```
contract_demo/
├── main.py              # FastAPI 主入口，所有接口定义
├── contract.py          # 合同模板填充逻辑
├── mock_data.py         # Mock 字段数据和字段清单
├── requirements.txt     # 依赖列表
└── templates/
    └── 采购合同模板.docx  # 带 {{占位符}} 的合同模板
```

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 把模板放到 templates/ 目录下
#    （已提供：采购合同模板.docx）

# 3. 启动服务
uvicorn main:app --reload --port 8000

# 4. 访问交互文档
open http://localhost:8000/docs
```

---

## 接口说明

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/`               | 服务状态检查 |
| GET  | `/templates`      | 查看可用合同类型 |
| GET  | `/fields`         | 字段清单（必填 / 选填），供前端引导语音输入 |
| GET  | `/mock-fields`    | 返回完整 mock 字段，可直接复制用于测试 |
| POST | `/generate/mock`  | 用内置 mock 数据一键生成合同，无需传参 |
| POST | `/generate`       | 传入字段字典，生成并下载合同 |

---

## 测试方法

### 方法一：浏览器打开 Swagger UI

访问 `http://localhost:8000/docs`，找到 `POST /generate/mock`，点击 **Try it out → Execute**，浏览器自动下载合同文件。

### 方法二：curl 命令

```bash
# 用 mock 数据生成（最简单）
curl -X POST "http://localhost:8000/generate/mock?contract_type=采购合同" \
     -o 采购合同_测试.docx

# 传入自定义字段
curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "contract_type": "采购合同",
       "fields": {
         "合同编号": "HT2025-000001",
         "甲方名称": "北京某某科技有限公司",
         "乙方名称": "上海某某设备有限公司",
         "货物名称": "服务器（Dell PowerEdge R750）",
         "数量": "10",
         "计量单位": "台",
         "合同金额大写": "捌拾万元整",
         "合同金额数字": "800,000.00",
         "交货期限": "45",
         "签署日期": "2025年5月1日"
       }
     }' \
     -o 采购合同_自定义.docx
```

---

## 合同模板字段列表

### 必填字段（15 个）

| 字段名 | 说明 |
|--------|------|
| `合同编号` | 合同唯一编号 |
| `甲方名称` | 买方公司全称 |
| `甲方联系人` | 买方联系人姓名 |
| `甲方电话` | 买方联系电话 |
| `甲方地址` | 买方详细地址 |
| `乙方名称` | 卖方公司全称 |
| `乙方联系人` | 卖方联系人姓名 |
| `乙方电话` | 卖方联系电话 |
| `货物名称` | 货物名称及规格型号 |
| `数量` | 采购数量 |
| `计量单位` | 台、件、套等 |
| `合同金额大写` | 例：肆拾玖万元整 |
| `合同金额数字` | 例：490,000.00 |
| `交货期限` | 合同签订后 N 天内交货 |
| `签署日期` | 例：2025年4月20日 |

### 选填字段（13 个）

`品牌产地` / `税率` / `税额` / `交货地点` / `运费承担方` / `质量标准` / `质保期` / `预付款比例` / `收款户名` / `开户银行` / `银行账号` / `争议解决地` / `其他约定`

---

## 下一步计划

| 阶段 | 内容 | 说明 |
|------|------|------|
| 阶段二 | 接入 STT | 替换 `mock_stt()`，接入 `faster-whisper` 本地语音识别 |
| 阶段三 | 接入 LLM | 替换 `mock_llm_extract()`，接入 Claude API 提取字段 |
| 阶段四 | 前端录音页面 | 浏览器 MediaRecorder 录音 → 上传 → 显示字段确认 → 下载合同 |
| 阶段五 | 历史分析 | 合同入库 + 金额异常提示 + 到期提醒 |


# 运行
```
STT_BACKEND=local WHISPER_MODEL=tiny uvicorn main:app --reload --port 8000


set STT_BACKEND=local
set WHISPER_MODEL=tiny
set WHISPER_DEVICE=cpu
uvicorn main:app --reload --port 8000
```
# compose run
```
docker compose build && docker compose up -d

docker compose up -d --build

```
