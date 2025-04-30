from PIL import Image

def crop_and_resize(img: Image.Image, target_size: tuple) -> tuple[Image.Image, int]:
    """
    Schneidet das Bild proportional so zu, dass es das gewünschte Seitenverhältnis erhält,
    ohne verzerrt zu werden – und behält dabei so viel wie möglich vom Originalinhalt.
    """
    orig_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]

    if abs(orig_ratio - target_ratio) < 0.01:
        # Verhältnis stimmt schon – nur skalieren
        cropped = img
        crop_mode = 0
    elif orig_ratio > target_ratio:
        # Bild ist zu breit → Seitlich beschneiden
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        cropped = img.crop((left, 0, left + new_width, img.height))
        crop_mode = 1
    else:
        # Bild ist zu hoch → Oben und unten beschneiden
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        cropped = img.crop((0, top, img.width, top + new_height))
        crop_mode = 2

    final_img = cropped.resize(target_size)
    return final_img, crop_mode  # crop_mode = Info für UI
