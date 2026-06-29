FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data/tokens /app/data/state /app/logs
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "from pathlib import Path; raise SystemExit(0 if Path('/app/config/settings.yaml').exists() else 1)"
CMD ["python", "main.py"]
