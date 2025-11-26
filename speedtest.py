#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import subprocess

# ============================================================
# CONFIGURATION
# ============================================================

# USS1 (Animal)
USS1_TRIG = 23
USS1_ECHO = 24

# USS2 (Car)
USS2_TRIG = 17
USS2_ECHO = 27

# LED + BUZZER
LED_PIN = 5
BUZZER_PIN = 6

# Constants
CRITICAL_TIME_DIFF = 1.0
ECHO_TIMEOUT = 0.03  # 30ms max echo wait

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(USS1_TRIG, GPIO.OUT)
GPIO.setup(USS1_ECHO, GPIO.IN)
GPIO.setup(USS2_TRIG, GPIO.OUT)
GPIO.setup(USS2_ECHO, GPIO.IN)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Ensure triggers are low
GPIO.output(USS1_TRIG, False)
GPIO.output(USS2_TRIG, False)
time.sleep(0.5) # Sensor settling time

# ============================================================
# CORE FUNCTIONS
# ============================================================

def measure_distance(trig, echo):
    """
    Return distance in meters. 
    Returns None if sensor times out or fails.
    """
    # Trigger pulse
    GPIO.output(trig, True)
    time.sleep(0.00001) # 10us pulse
    GPIO.output(trig, False)

    start_timeout = time.monotonic()
    
    # Wait for Echo Rise
    while GPIO.input(echo) == 0:
        if time.monotonic() - start_timeout > ECHO_TIMEOUT:
            return None

    t0 = time.monotonic()
    
    # Wait for Echo Fall
    while GPIO.input(echo) == 1:
        if time.monotonic() - t0 > ECHO_TIMEOUT:
            return None

    t1 = time.monotonic()

    # Calculate distance
    duration = t1 - t0
    distance = (duration * 343.0) / 2.0
    return distance

def measure_speed_dual(trig_car, echo_car, trig_ani, echo_ani, delay=0.9):
    """
    Measures speed for both Car and Animal simultaneously.
    Returns: (car_speed, animal_speed, car_dist, animal_dist)
    """
    # 1. Take Initial Measurements
    dist_car_1 = measure_distance(trig_car, echo_car)
    dist_ani_1 = measure_distance(trig_ani, echo_ani)
    time_1 = time.monotonic()

    # Wait for the interval
    time.sleep(delay)

    # 2. Take Final Measurements
    dist_car_2 = measure_distance(trig_car, echo_car)
    dist_ani_2 = measure_distance(trig_ani, echo_ani)
    time_2 = time.monotonic()

    # Calculate actual time delta (more accurate than relying on sleep)
    actual_dt = time_2 - time_1

    # --- CALCULATE CAR SPEED ---
    if dist_car_1 is not None and dist_car_2 is not None:
        # Positive speed = approaching, Negative = moving away
        car_speed = (dist_car_1 - dist_car_2) / actual_dt
        final_car_dist = dist_car_2
    else:
        car_speed = 0.0
        final_car_dist = dist_car_2 if dist_car_2 is not None else -1

    # --- CALCULATE ANIMAL SPEED ---
    if dist_ani_1 is not None and dist_ani_2 is not None:
        ani_speed = (dist_ani_1 - dist_ani_2) / actual_dt
        final_ani_dist = dist_ani_2
    else:
        ani_speed = 0.0
        final_ani_dist = dist_ani_2 if dist_ani_2 is not None else -1

    return car_speed, ani_speed, final_car_dist, final_ani_dist

# ============================================================
# MAIN EXECUTION
# ============================================================

try:
    print("Measuring...")
    
    # CORRECT MAPPING:
    # arg1=Car_Trig, arg2=Car_Echo, arg3=Ani_Trig, arg4=Ani_Echo
    c_speed, a_speed, c_dist, a_dist = measure_speed_dual(
        USS2_TRIG, USS2_ECHO,  # Car Pins
        USS1_TRIG, USS1_ECHO,  # Animal Pins
        delay=0.9
    )

    print(f"ANIMAL: Dist={a_dist:.5f}m, Speed={a_speed:.5f} m/s")
    print(f"CAR   : Dist={c_dist:.5f}m, Speed={c_speed:.5f} m/s")

except KeyboardInterrupt:
    print("Stopped by user")
finally:
    GPIO.cleanup()