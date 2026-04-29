FROM python:3.12-slim

WORKDIR /app

# 系统依赖（docx 处理需要 libxml2）
RUN apt-get update \
    && apt-get install -y --no-install-recommends libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 层缓存，代码改动时不用重装包）
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# 复制代码
COPY . .

# 生成合同模板（含多条货物循环）
RUN python create_template.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
