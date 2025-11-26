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


# ============================================================
# ULTRASONIC MEASUREMENT
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

def measure_speed_dual(trig_car, echo_car, trig_ani, echo_ani, delay):
    """
    Measures speed for both Car and Animal simultaneously.
    Returns: (car_speed, animal_speed, car_dist, animal_dist)
    """
    # 1. Take Initial Measurements
    dist_car_1 = measure_distance(trig_car, echo_car)
    dist_ani_1 = measure_distance(trig_ani, echo_ani)
    time_1 = time.monotonic()
    GPIO.output(LED_PIN, True)
    GPIO.output(BUZZER_PIN, True)
    time.sleep(delay)
    GPIO.output(LED_PIN, False)
    GPIO.output(BUZZER_PIN, False)

    # Wait for the interval
    # time.sleep(delay)

    # 2. Take Final Measurements
    dist_car_2 = measure_distance(trig_car, echo_car)
    dist_ani_2 = measure_distance(trig_ani, echo_ani)
    time_2 = time.monotonic()

    # Calculate actual time delta (more accurate than relying on sleep)
    actual_dt = (time_2 - time_1) 

    # --- CALCULATE CAR SPEED ---
    if dist_car_1 is not None and dist_car_2 is not None:
        # Positive speed = approaching, Negative = moving away
        car_speed = (dist_car_1 - dist_car_2) / actual_dt
        final_car_dist = dist_car_2
    else:
        car_speed = 0.00001
        final_car_dist = dist_car_2 if dist_car_2 is not None else -1

    # --- CALCULATE ANIMAL SPEED ---
    if dist_ani_1 is not None and dist_ani_2 is not None:
        ani_speed = (dist_ani_1 - dist_ani_2) / actual_dt
        final_ani_dist = dist_ani_2
    else:
        ani_speed = 0.00001
        final_ani_dist = dist_ani_2 if dist_ani_2 is not None else -1
    # if ani_speed==0:
        # ani_speed=0.00001
    # if car_distance==0:
        # car_distance=0.00001
    print(dist_ani_1,'animal distance 1')
    print(dist_ani_2,'animal distance 2')
    print(dist_car_1,'car distance 1')
    print(dist_car_2,'car distance 2')
    print(time_1,'time1')
    print(time_2,'time2')
    print(actual_dt,'actual dt')
    print(car_speed,'car speed')
    print(ani_speed,'animal speed')
    # print(dist_ani_1, dist_ani_2, actual_dt,time_1,time_2)
    return car_speed, ani_speed, final_car_dist, final_ani_dist

    """
    Returns speed in m/s based on multiple distance samples.
    Returns (speed, last_distance).
    speed = 0.0 if cannot be measured.
    """
    # ds = []
    # ts = []

    # for _ in range(samples):
    #     d = measure_distance(trig, echo)
    #     t = time.time()

    #     if d is None:
    #         # If any measurement fails, skip speed calc
    #         return 0.0, None

    #     ds.append(d)
    #     ts.append(t)
    #     time.sleep(delay)

    # total_dist = ds[0] - ds[-1]  # how much closer it came (or went away)
    # total_time = ts[-1] - ts[0]

    # if total_time <= 0:
        # return 0.0, ds[-1]

    # speed = total_dist / total_time  # postive = approaching, negative = receding
    # return speed, ds[-1]  # return latest distance too


# ============================================================
# ALERT SYSTEM
# ============================================================

def alert():
    print("RED ALERT: Possible crash!")
    # GPIO.output(LED_PIN, True)
    GPIO.output(BUZZER_PIN, True)
    time.sleep(1.0)
    # GPIO.output(LED_PIN, False)
    GPIO.output(BUZZER_PIN, False)
# def oranalert():
#     print("ORANGE")
#     GPIO.output(LED_PIN, True)
#     # GPIO.output(BUZZER_PIN, True)
#     time.sleep(1.0)
#     GPIO.output(LED_PIN, False)
#     # GPIO.output(BUZZER_PIN, False)


# ============================================================
# MAIN LOOP
# ============================================================
# ===================== MAIN LOOP =====================

prev_d1 = None
MOTION_THRESHOLD = 0.005   # 0.5 cm movement triggers detection

try:
    while True:
        # Step 1: detect motion via USS1
        d1 = measure_distance(USS1_TRIG, USS1_ECHO)

        motion_detected = False
        if prev_d1 is not None and d1 is not None and d1 < 0.50:
            if abs(d1 - prev_d1) > MOTION_THRESHOLD:
                motion_detected = True
                print(f"Motion detected near USS1 (Δ={abs(d1 - prev_d1):.2f} m). Checking for animal...")

        prev_d1 = d1

        if not motion_detected:
            time.sleep(0.5) # 500 ms
            continue

        # Step 2: run animal detector
        try:
            result = subprocess.check_output(
                ["python3", "ani_det.py"]
            ).decode().strip().lower()
        except Exception as e:
            print(f"Error running animal_detector.py: {e}")
            time.sleep(0.5) # 500 ms
            continue

        if "no_animal" in result:
            print("No animal detected — likely leaf, wind, etc.")
            time.sleep(0.5) # 500 ms
            continue

        print("Animal confirmed by ML detector.")

        # ===================== ANIMAL (USS1) =====================
        # animal_speed, animal_distance = measure_speed(USS1_TRIG, USS1_ECHO)

        # if animal_speed < 0:
            # print("There is animal close by but its going farther away.")
            # time.sleep(0.5)
            # continue


        # if animal_distance is None:
            # print("Animal distance could not be measured.")
            # time.sleep(0.5)
            # continue

        car_speed, animal_speed, car_distance, animal_distance = measure_speed_dual(USS2_TRIG, USS2_ECHO,USS1_TRIG,USS1_ECHO,0.9)
        
        time_animal = (animal_distance - 0.06) / animal_speed
        print(
            f"Animal: distance={animal_distance:.2f} m, "
            f"speed={animal_speed:.2f} m/s, "
            f"time_to_reach MIDDLE OF THE ROAD={time_animal:.2f} s"
        )

        # ===================== CAR (USS2) =====================
        # car_speed, car_distance = measure_speed(USS2_TRIG, USS2_ECHO)
        if car_speed==0:
            car_speed=0.00001
        time_car = car_distance / car_speed
        print(
            f"Car: distance={car_distance:.2f} m, "
            f"speed={car_speed:.2f} m/s, "
            f"time_to_reach={time_car:.2f} s"
        )

        # ===================== CRASH PREDICTION =====================
        delta_t = abs(time_animal - time_car)
        print(f"del t = |t_animal - t_car| = {delta_t:.2f} s")

        if delta_t < CRITICAL_TIME_DIFF:
            alert()
        else:
            print("Safe — no immediate danger.")

        time.sleep(0.02)

except KeyboardInterrupt:
    print("Exiting...")

finally:
    GPIO.cleanup()