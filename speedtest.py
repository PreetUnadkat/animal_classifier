#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import subprocess

# ============================================================
# CONFIGURATION
# ============================================================

# USS1 (animal)
USS1_TRIG = 23
USS1_ECHO = 24

# USS2 (car)
USS2_TRIG = 17
USS2_ECHO = 27

# LED + BUZZER
LED_PIN = 5
BUZZER_PIN = 6

# If times differ by < 1 sec → danger
CRITICAL_TIME_DIFF = 1.0

# Max time to wait for echo (seconds) to avoid infinite loops
ECHO_TIMEOUT = 0.03  # ~30ms → ~5m range

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(USS1_TRIG, GPIO.OUT)
GPIO.setup(USS1_ECHO, GPIO.IN)

GPIO.setup(USS2_TRIG, GPIO.OUT)
GPIO.setup(USS2_ECHO, GPIO.IN)

GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)


def measure_distance(trig, echo):
    """Best-possible HC-SR04 distance measurement (meters)."""
    GPIO.output(trig, False)
    time.sleep(0.000002)
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    start = time.monotonic()
    timeout = start + ECHO_TIMEOUT

    # Wait for echo HIGH
    while GPIO.input(echo) == 0:
        if time.monotonic() > timeout:
            return None

    t0 = time.monotonic()

    # Wait for echo LOW
    while GPIO.input(echo) == 1:
        if time.monotonic() > timeout:
            return None

    t1 = time.monotonic()

    dt = t1 - t0
    if dt <= 0 or dt > 0.030:   # >30ms = >5m = junk
        return None

    return (dt * 343.0) / 2.0

# ============================================================
# SPEED MEASUREMENT
# ============================================================

import statistics

def measure_speed(trig, echo, samples=6, delay=0.035):
    """
    Returns (speed_mps, last_distance_m).
    Speed is positive when approaching.
    Uses median filtering + linear regression for best accuracy.
    """

    ds = []
    ts = []

    for _ in range(samples):
        d = measure_distance(trig, echo)
        if d is None:
            return 0.0, None

        ds.append(d)
        ts.append(time.monotonic())
        time.sleep(delay)

    # -------- median smoothing --------
    smoothed = []
    k = 2  # median window radius

    for i in range(len(ds)):
        L = max(0, i - k)
        R = min(len(ds), i + k + 1)
        smoothed.append(statistics.median(ds[L:R]))

    xs = [t - ts[0] for t in ts]
    ys = smoothed

    n = len(xs)
    sumx = sum(xs)
    sumy = sum(ys)
    sumxy = sum(x*y for x, y in zip(xs, ys))
    sumx2 = sum(x*x for x in xs)

    denom = n * sumx2 - sumx * sumx
    if denom == 0:
        return 0.0, ys[-1]

    slope = (n * sumxy - sumx * sumy) / denom

    # slope is Δdistance / Δtime  → m/s
    return slope, ys[-1]



animal_speed, animal_distance = measure_speed(USS1_TRIG, USS1_ECHO)
print(animal_distance, animal_speed)
car_speed, car_distance = measure_speed(USS2_TRIG, USS2_ECHO)
print(car_distance, car_speed)