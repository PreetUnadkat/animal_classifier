import os
from PIL import Image, ImageEnhance
import random

def augment_image(img):
    # slight rotation
    angle = random.uniform(-15, 15)
    img = img.rotate(angle, expand=True)
    
    # brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(random.uniform(0.8, 1.2))

    # contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(random.uniform(0.8, 1.2))

    # color
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(random.uniform(0.8, 1.2))

    # optional horizontal flip
    if random.random() < 0.5:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    return img


def multiply_dataset(in_dir, out_dir, multiplier=10):
    os.makedirs(out_dir, exist_ok=True)
    files = [f for f in os.listdir(in_dir) if f.lower().endswith((".jpg", ".png"))]

    for f in files:
        img_path = os.path.join(in_dir, f)
        img = Image.open(img_path).convert("RGB")

        for i in range(multiplier):
            aug = augment_image(img)
            out_name = f"{os.path.splitext(f)[0]}_aug_{i}.jpg"
            aug.save(os.path.join(out_dir, out_name), quality=90)


# Example usage:
multiply_dataset("animals", "animals_aug", multiplier=12)
multiply_dataset("nonanimals", "nonanimals_aug", multiplier=12)