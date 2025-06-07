FROM python:3.12-alpine

WORKDIR /app
COPY requirements.txt .

# Install build dependencies and Python packages
RUN apk add --no-cache gcc musl-dev python3-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del gcc musl-dev python3-dev

COPY app ./app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
