FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AEGIS_ENV=production \
    AEGIS_DATA_DIR=/var/data \
    AEGIS_MAX_UPLOAD_MB=25 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    PORT=8501

WORKDIR /app

RUN useradd --system --uid 10001 --create-home aegis \
    && mkdir -p /var/data \
    && chown -R aegis:aegis /app /var/data

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY config ./config
COPY data/samples ./data/samples

RUN python -m pip install --no-cache-dir .[parquet] \
    && python -m pip check \
    && chown -R aegis:aegis /app

USER 10001:10001
VOLUME ["/var/data"]
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT', '8501') + '/_stcore/health', timeout=3)"

CMD ["python", "scripts/container_entrypoint.py"]
