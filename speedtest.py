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
    """Return distance in meters. Returns None on timeout."""
    # Send trigger pulse
    GPIO.output(trig, False)
    time.sleep(0.000002)  # 2µs to settle
    GPIO.output(trig, True)
    time.sleep(0.00001)   # 10µs pulse
    GPIO.output(trig, False)

    start_time = time.time()
    timeout_start = start_time

    # Wait for echo to go high
    while GPIO.input(echo) == 0:
        start_time = time.time()
        if start_time - timeout_start > ECHO_TIMEOUT:
            return None

    # Wait for echo to go low
    stop_time = time.time()
    while GPIO.input(echo) == 1:
        stop_time = time.time()
        if stop_time - start_time > ECHO_TIMEOUT:
            return None

    duration = stop_time - start_time
    distance = (duration * 343.0) / 2.0  # speed of sound 343 m/s
    return distance


# ============================================================
# SPEED MEASUREMENT
# ============================================================

def measure_speed(trigcar, echocar, trigani, echoani,delay): # delay is 900 ms

    caroridis=measure_distance(trigcar, echocar)
    anioridis=measure_distance(trigani, echoani)

    time.sleep(delay)

    car_distance=measure_distance(trigcar, echocar)
    animal_distance=measure_distance(trigani, echoani)

    car_speed=(caroridis-car_distance)/delay
    animal_speed=(anioridis-animal_distance)/delay

    return car_speed, animal_speed, car_distance, animal_distance


animal_speed, animal_distance, car_speed, car_distance = measure_speed(USS1_TRIG, USS1_ECHO, USS2_TRIG, USS2_ECHO, 0.9)
print(animal_distance, animal_speed)
print(car_distance, car_speed)