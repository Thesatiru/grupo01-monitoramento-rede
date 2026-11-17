FROM python:3.12-slim
# iputils-ping fornece o comando ping usado nas sondas ICMP
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY coletor.py medir_api.py ./
ENV PYTHONUNBUFFERED=1 FILA=/dados/fila.jsonl
CMD ["python", "coletor.py"]
