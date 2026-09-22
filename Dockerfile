FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 inboxpilot \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin inboxpilot
COPY --chown=10001:10001 . .
RUN mkdir -p /app/data/tokens /app/data/state /app/logs \
    && chown -R 10001:10001 /app/data /app/logs
USER 10001:10001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "from pathlib import Path; raise SystemExit(0 if Path('/app/config/settings.yaml').exists() else 1)"
CMD ["python", "main.py"]
