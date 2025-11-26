#!/usr/bin/env python3
"""
Raspberry Pi TFLite Binary Classifier
Captures images and runs inference for animal detection.
"""

import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
import time
import os
import sys
from pathlib import Path


# ==================== CONFIGURATION ====================
MODEL_PATH = "realfinal.tflite"
CAPTURE_FILENAME = "capture.jpg"
CAPTURE_WIDTH = 640
CAPTURE_HEIGHT = 480
CAMERA_TIMEOUT_MS = 1500
CONFIDENCE_THRESHOLD = 0.5

# Camera command priority (newer to older)
CAMERA_COMMANDS = ["rpicam-still", "libcamera-still", "raspistill"]


# ==================== HELPER FUNCTIONS ====================
def find_camera_command():
    """Detects which camera command is available on the system."""
    for cmd in CAMERA_COMMANDS:
        result = os.system(f"which {cmd} > /dev/null 2>&1")
        if result == 0:
            print(f"✓ Found camera command: {cmd}")
            return cmd
    raise RuntimeError(
        "No camera command found. Install libcamera or enable legacy camera.\n"
        "Try: sudo apt install libcamera-apps"
    )


def verify_model_exists():
    """Checks if the TFLite model file exists."""
    if not Path(MODEL_PATH).is_file():
        raise FileNotFoundError(
            f"Model file '{MODEL_PATH}' not found in current directory.\n"
            f"Current directory: {os.getcwd()}"
        )
    print(f"✓ Model found: {MODEL_PATH}")


# ==================== MODEL SETUP ====================
def load_model():
    """Loads TFLite model and returns interpreter with input/output details."""
    try:
        interpreter = tflite.Interpreter(model_path=MODEL_PATH)
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        
        # Extract shape information
        input_shape = input_details['shape']
        input_dtype = input_details['dtype']
        
        print(f"✓ Model loaded successfully")
        print(f"  Input shape: {input_shape}")
        print(f"  Input dtype: {input_dtype}")
        print(f"  Output shape: {output_details['shape']}")
        
        # Determine image size (assuming NHWC format: batch, height, width, channels)
        if len(input_shape) == 4:
            img_height = input_shape[1]
            img_width = input_shape[2]
        else:
            raise ValueError(f"Unexpected input shape: {input_shape}")
        
        return interpreter, input_details, output_details, (img_width, img_height), input_dtype
        
    except Exception as e:
        raise RuntimeError(f"Failed to load model: {e}")


# ==================== CAMERA FUNCTIONS ====================
def capture_photo(camera_cmd, filename=CAPTURE_FILENAME):
    """
    Captures a photo using the detected camera command.
    Returns the path to the captured image.
    """
    # Remove old capture if exists
    if os.path.exists(filename):
        os.remove(filename)
    
    print("📸 Capturing photo...")
    
    # Build command based on camera type
    if camera_cmd in ["rpicam-still", "libcamera-still"]:
        cmd = (
            f"{camera_cmd} -o {filename} "
            f"--width {CAPTURE_WIDTH} --height {CAPTURE_HEIGHT} "
            f"--nopreview -t {CAMERA_TIMEOUT_MS}"
        )
    else:  # raspistill (legacy)
        cmd = (
            f"{camera_cmd} -o {filename} "
            f"-w {CAPTURE_WIDTH} -h {CAPTURE_HEIGHT} "
            f"-n -t {CAMERA_TIMEOUT_MS}"
        )
    
    # Execute capture
    result = os.system(cmd)
    
    # Verify capture success
    if result != 0:
        raise RuntimeError(f"Camera command failed with exit code {result}")
    
    # Wait for file to be written
    time.sleep(0.3)
    
    if not os.path.exists(filename):
        raise RuntimeError("Image file was not created after capture")
    
    print(f"✓ Photo captured: {filename}")
    return filename


# ==================== PREPROCESSING ====================
def preprocess_image(image_path, img_size, input_dtype):
    """
    Loads, resizes, and preprocesses image for model inference.
    Handles both float32 (normalized) and uint8 (raw) inputs.
    """
    try:
        # Load and convert to RGB
        image = Image.open(image_path).convert("RGB")
        
        # Resize to model's expected size
        image = image.resize(img_size, Image.BILINEAR)
        
        # Convert to numpy array with appropriate dtype
        if input_dtype == np.float32:
            img_array = np.asarray(image, dtype=np.float32) / 255.0
        elif input_dtype == np.uint8:
            img_array = np.asarray(image, dtype=np.uint8)
        else:
            raise ValueError(f"Unsupported input dtype: {input_dtype}")
        
        # Add batch dimension: (H, W, C) -> (1, H, W, C)
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
        
    except Exception as e:
        raise RuntimeError(f"Failed to preprocess image: {e}")


# ==================== INFERENCE ====================
def run_inference(interpreter, input_details, output_details, image_array):
    """Runs model inference and returns output probabilities."""
    try:
        # Set input tensor
        interpreter.set_tensor(input_details['index'], image_array)
        
        # Run inference
        start_time = time.time()
        interpreter.invoke()
        inference_time = (time.time() - start_time) * 1000  # milliseconds
        
        # Get output tensor
        output = interpreter.get_tensor(output_details['index'])[0]
        
        print(f"✓ Inference completed in {inference_time:.1f}ms")
        
        return output, inference_time
        
    except Exception as e:
        raise RuntimeError(f"Inference failed: {e}")


# ==================== PREDICTION ====================
def interpret_results(output_probs, threshold=CONFIDENCE_THRESHOLD):
    """
    Interprets model output and returns prediction.
    Your TM labels:
    index 0 = animal
    index 1 = non-animal
    """

    if len(output_probs) == 2:
        animal_prob    = float(output_probs[0])
        no_animal_prob = float(output_probs[1])

    elif len(output_probs) == 1:
        # Single sigmoid output (rare for TM)
        animal_prob = float(output_probs[0])
        no_animal_prob = 1.0 - animal_prob

    else:
        raise ValueError(f"Unexpected output shape: {output_probs.shape}")

    is_animal = animal_prob > threshold
    confidence = max(animal_prob, no_animal_prob)

    return {
        'is_animal': is_animal,
        'animal_probability': animal_prob,
        'no_animal_probability': no_animal_prob,
        'confidence': confidence
    }


# ==================== MAIN FUNCTION ====================
def main():
    # print('Real final')
    """Main execution pipeline."""

    # print("=" * 50)
    # print("Raspberry Pi Animal Classifier")
    # print("=" * 50)

    try:
        # 1. Setup and verification
        # print("\n[1/5] Verifying setup...")
        verify_model_exists()
        camera_cmd = find_camera_command()

        # 2. Load model
        # print("\n[2/5] Loading model...")
        interpreter, input_details, output_details, img_size, input_dtype = load_model()

        # 3. Capture photo
        # print("\n[3/5] Capturing image...")
        img_path = capture_photo(camera_cmd)

        # 4. Preprocess
        # print("\n[4/5] Preprocessing image...")
        img_array = preprocess_image(img_path, img_size, input_dtype)
        # print(f"✓ Preprocessed shape: {img_array.shape}")

        # 5. Run inference
        # print("\n[5/5] Running inference...")
        output_probs, inference_time = run_inference(
            interpreter, input_details, output_details, img_array
        )

        # Interpret results
        # print(f"\nRaw output: {output_probs}")
        results = interpret_results(output_probs)

        # Display results
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"Animal probability: {results['animal_probability']:.4f}")
        print(f"No-animal probability: {results['no_animal_probability']:.4f}")
        print(f"Confidence: {results['confidence']:.4f}")
        print(f"Inference time: {inference_time:.1f}ms")
        print()

        # Final animal/no-animal message (corrected)
        if results["is_animal"]:
            print("ANIMAL DETECTED")
            print("animal")      # machine-readable token
        else:
            print("NO ANIMAL DETECTED")
            print("no_animal")   # machine-readable token

        print("=" * 50)
        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130

    except Exception as e:
        print(f"\n\nERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())