import numpy as np
from picamera2 import Picamera2
from PIL import Image
import tflite_runtime.interpreter as tflite
import time
import os


# ---------- MODEL SETUP ----------
MODEL_PATH = "animal_detector.tflite"

interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_shape = input_details[0]['shape']  # e.g., (1, 96, 96, 3)
IMG_SIZE = (input_shape[2], input_shape[1])  # (width, height)


# ---------- CAPTURE FUNCTION ----------
def capture_photo(filename="capture.jpg"):
    """Captures a photo using Raspberry Pi Camera and saves it."""
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (640, 480)})
    picam2.configure(config)
    picam2.start()
    time.sleep(2)  # warm-up
    picam2.capture_file(filename)
    picam2.close()
    return filename


# ---------- PREPROCESSING ----------
def preprocess_image(image_path):
    """Loads image, resizes and normalizes for TFLite model."""
    image = Image.open(image_path).convert("RGB")
    image = image.resize(IMG_SIZE)
    img_array = np.asarray(image, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)  # shape (1, H, W, 3)
    return img_array


# ---------- PREDICTION ----------
def predict_animal(image_array):
    """Runs inference and returns probability and class."""
    interpreter.set_tensor(input_details[0]['index'], image_array)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0][0]
    return float(output)


# ---------- MAIN FUNCTION ----------
def main():
    print("📸 Capturing photo...")
    img_path = capture_photo()

    print("🔄 Preprocessing image...")
    img_array = preprocess_image(img_path)

    print("🧠 Running model inference...")
    prob = predict_animal(img_array)

    print(f"\nPrediction Probability: {prob:.3f}")
    if prob > 0.5:
        print("✅ Animal detected!")
    else:
        print("❌ No animal detected.")


if __name__ == "__main__":
    main()
