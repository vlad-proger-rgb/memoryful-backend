FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt mcp_server/requirements.mcp.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements.mcp.txt

RUN adduser --disabled-password --gecos '' appuser

USER appuser

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
