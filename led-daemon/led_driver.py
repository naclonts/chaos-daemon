#!/usr/bin/env python
"""
Long-running LED fade loop for PCA9685.
Handles SIGTERM so Kubernetes can restart gracefully.
"""
import signal, sys, time, board, busio
import random
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# ── Hardware init ──────────────────────────────────────────────────────────────
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50

servo0 = servo.Servo(pca.channels[0])
servo1 = servo.Servo(pca.channels[1])

LED1 = pca.channels[2]   # Green
LED2 = pca.channels[3]   # Red

def set_led(chan, bright: float):
    bright = max(0.0, min(bright, 1.0))
    chan.duty_cycle = int(bright * 65_535)

# ── Graceful shutdown ─────────────────────────────────────────────────────────
def _shutdown(_sig, _frame):
    pca.deinit()
    sys.exit(0)

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT,  _shutdown)

# ── Main loop ─────────────────────────────────────────────────────────────────
while True:
    for led in (LED1, LED2):
        increment = random.randint(1, 5)
        for up in range(0, 101, increment):
            set_led(led, up / 100.0); time.sleep(0.05)
        decrement = -random.randint(1, 5)
        for down in range(100, -1, decrement):
            set_led(led, down / 100.0); time.sleep(0.05)

