FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src
COPY data ./data

# usuário sem privilégios: o processo não precisa de root nem de escrita no disco
RUN useradd --system --no-create-home --uid 10001 agente
USER agente

EXPOSE 8000
CMD ["uvicorn", "agente.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
