#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# --- CONFIGURATION ---
USS1_TRIG = 23  # Animal
USS1_ECHO = 24
USS2_TRIG = 17  # Car
USS2_ECHO = 27
LED_PIN = 5
BUZZER_PIN = 6
ECHO_TIMEOUT = 0.03 # 30ms

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(USS1_TRIG, GPIO.OUT)
GPIO.setup(USS1_ECHO, GPIO.IN)
GPIO.setup(USS2_TRIG, GPIO.OUT)
GPIO.setup(USS2_ECHO, GPIO.IN)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Ensure triggers are off
GPIO.output(USS1_TRIG, False)
GPIO.output(USS2_TRIG, False)
time.sleep(0.5)

def measure_distance(trig, echo):
    # settle line
    GPIO.output(trig, False)
    time.sleep(0.000002)

    # trigger pulse
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    start = time.monotonic()
    timeout = start + ECHO_TIMEOUT

    # wait for echo HIGH
    while GPIO.input(echo) == 0:
        if time.monotonic() > timeout:
            return None

    t0 = time.monotonic()
    timeout2 = t0 + ECHO_TIMEOUT

    # wait for echo LOW
    while GPIO.input(echo) == 1:
        if time.monotonic() > timeout2:
            return None

    t1 = time.monotonic()

    dt = t1 - t0
    if dt <= 0 or dt > 0.03:   # >5 m → invalid
        return None

    return (dt * 343.0) / 2.0

def measure_speed(trig_car, echo_car, trig_ani, echo_ani, delay=1.0):
    # 1. First measurement
    d_car_1 = measure_distance(trig_car, echo_car)
    d_ani_1 = measure_distance(trig_ani, echo_ani)

    t_start = time.monotonic()
    time.sleep(delay)
    t_end = time.monotonic()
    
    # 2. Second measurement
    d_car_2 = measure_distance(trig_car, echo_car)
    d_ani_2 = measure_distance(trig_ani, echo_ani)

    # Calculate exact time passed for better precision
    actual_dt = t_end - t_start

    # 3. Calculate Speeds (Speed = Distance / Time)
    # CAR
    if d_car_1 is not None and d_car_2 is not None:
        speed_car = (d_car_1 - d_car_2) / actual_dt
        final_dist_car = d_car_2
    else:
        speed_car = 0.0
        final_dist_car = d_car_2 if d_car_2 is not None else 0.0

    # ANIMAL
    if d_ani_1 is not None and d_ani_2 is not None:
        speed_ani = (d_ani_1 - d_ani_2) / actual_dt
        final_dist_ani = d_ani_2
    else:
        speed_ani = 0.0
        final_dist_ani = d_ani_2 if d_ani_2 is not None else 0.0

    return speed_car, speed_ani, final_dist_car, final_dist_ani

try:
    print("Monitoring...")
    
    # Measure speed with a 0.9 second delay between samples
    c_speed, a_speed, c_dist, a_dist = measure_speed(
        USS2_TRIG, USS2_ECHO,  # Car Pins
        USS1_TRIG, USS1_ECHO,  # Animal Pins
        delay=0.9
    )

    print(f"ANIMAL: Dist={a_dist:.2f} m | Speed={a_speed:.2f} m/s")
    print(f"CAR   : Dist={c_dist:.2f} m | Speed={c_speed:.2f} m/s")

except KeyboardInterrupt:
    print("\nExiting")
finally:
    GPIO.cleanup()