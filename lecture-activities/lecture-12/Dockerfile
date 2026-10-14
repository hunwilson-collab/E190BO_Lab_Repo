FROM python:3.13-slim
WORKDIR /app
COPY src/ .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["--host", "0.0.0.0", "uvicorn", "main:app"]