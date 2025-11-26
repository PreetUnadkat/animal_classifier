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

prev_d1 = None
MOTION_THRESHOLD = 0.005   # 0.5 cm movement triggers detection

try:
    while True:
        GPIO.output(LED_PIN, False)
        GPIO.output(BUZZER_PIN, False)
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