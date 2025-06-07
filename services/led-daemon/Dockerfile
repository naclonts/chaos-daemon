# Drive PCA9685 LEDs/servos inside a container
FROM python:3.12

# Optional: helpful CLI tools for I²C debugging
RUN apt-get update && \
    apt-get install -y --no-install-recommends i2c-tools libatlas-base-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY led_driver.py .

# Run the FastAPI application
CMD ["python", "-m", "app.main"]

