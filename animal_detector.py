import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
import time
import os

# ---------- MODEL SETUP ----------
MODEL_PATH = "animal_classifier.tflite"

interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_shape = input_details[0]['shape']  # e.g. (1, 96, 96, 3)
IMG_SIZE = (input_shape[2], input_shape[1])  # (width, height)


# ---------- CAPTURE FUNCTION ----------
def capture_photo(filename="capture.jpg"):
    """
    Captures a photo using the Raspberry Pi camera via libcamera-still.
    No Python camera libs required.
    """
    # remove old photo if any
    if os.path.exists(filename):
        os.remove(filename)

    print("📸 Capturing photo using libcamera-still...")
    # take photo (adjust resolution if needed)
    os.system(f"rpicam-still -o {filename} --width 640 --height 480 --nopreview -t 1500")

    # wait briefly to ensure file is written
    if not os.path.exists(filename):
        raise RuntimeError("Camera capture failed or image not saved.")
    return filename


# ---------- PREPROCESSING ----------
def preprocess_image(image_path):
    """Loads image, resizes, and normalizes for TFLite model."""
    image = Image.open(image_path).convert("RGB")
    image = image.resize(IMG_SIZE)
    img_array = np.asarray(image, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)  # (1, H, W, 3)
    return img_array


# ---------- PREDICTION ----------
def predict_animal(image_array):
    """Runs inference and returns probability."""
    interpreter.set_tensor(input_details[0]['index'], image_array)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0][0]
    return float(output)


# ---------- MAIN FUNCTION ----------
def main():
    img_path = capture_photo()

    print("🔄 Preprocessing image...")
    img_array = preprocess_image(img_path)

    print("🧠 Running model inference...")
    prob = predict_animal(img_array)

    print(f"\nPrediction Probability: {prob:.3f}")
    print(interpreter.get_output_details())
    if prob > 0.5:
        print("✅ Animal detected!")
    else:
        print("❌ No animal detected.")


if __name__ == "__main__":
    main()
