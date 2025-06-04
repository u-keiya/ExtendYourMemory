FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x server_fastapi.py

EXPOSE 8501

CMD ["python", "server_fastapi.py"]