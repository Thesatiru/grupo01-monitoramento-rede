FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py .
ENV PYTHONUNBUFFERED=1 MONITOR_DB=/dados/monitor.db
EXPOSE 5000
CMD ["python", "api.py"]
