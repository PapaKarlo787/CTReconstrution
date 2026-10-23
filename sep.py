from pathlib import Path

import cv2
import numpy as np


INPUT_DIR = Path("res")
OUTPUT_DIR = Path("final")
PART_COUNT = 4

BLACK_THRESHOLD = 5000
MIN_OBJECT_AREA = 16

# Подбираются под размер засветлений на ваших снимках.
LIGHT_KERNEL = 31
LIGHT_MARGIN = 1
LIGHT_MIN_DIFFERENCE = 9200


def remove_dead_lines(image):
    image = image.astype(np.float32).copy()
    rows, cols = image.shape

    dead_rows = image.mean(axis=1) < BLACK_THRESHOLD
    good_rows = np.flatnonzero(~dead_rows)

    if 0 < len(good_rows) < rows:
        missing = np.flatnonzero(dead_rows)
        for col in range(cols):
            image[missing, col] = np.interp(
                missing, good_rows, image[good_rows, col]
            )

    dead_cols = image.mean(axis=0) < BLACK_THRESHOLD
    good_cols = np.flatnonzero(~dead_cols)

    if 0 < len(good_cols) < cols:
        missing = np.flatnonzero(dead_cols)
        for row in range(rows):
            image[row, missing] = np.interp(
                missing, good_cols, image[row, good_cols]
            )

    return image


def highlight_mask(image):
    source = np.clip(image, 0, 65535).astype(np.uint16)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (LIGHT_KERNEL, LIGHT_KERNEL))
    bright_difference = cv2.morphologyEx(source, cv2.MORPH_TOPHAT, kernel)
    difference_limit = max(LIGHT_MIN_DIFFERENCE, 0.04 * float(np.median(source)))
    bright_level = np.percentile(source, 70)
    spots = ((bright_difference > difference_limit) & (source >= bright_level)).astype(np.uint8) * 255
    margin = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (LIGHT_MARGIN, LIGHT_MARGIN))
    return cv2.dilate(spots, margin) > 0


def clean_part(part):
    image = remove_dead_lines(part)
    # Усредняем до разделения яркостей.
    blurred = cv2.GaussianBlur(image.astype(np.float32), (5, 5), 0)

    dark = float(np.percentile(blurred, 2))
    middle = float(np.median(blurred))

    # Светлый уровень берём из самого верхнего хвоста распределения.
    # Так к нему попадёт минимум пикселей.
    light = float(np.percentile(blurred, 99.7))
    light = max(light, middle + 2000.0)

    if middle <= dark:
        dark = middle - 1.0

    # Тёмные → 0, медианные → 128, очень светлые → 255.
    separated = np.interp(
        blurred.ravel(),
        [dark, middle, light],
        [0, 128, 255],
    ).reshape(blurred.shape).astype(np.uint8)

    # Захватываем тёмную группу, не включая медианный фон.
    mask = np.where(separated < 110, 255, 0).astype(np.uint8)

    # Закрываем мелкие разрывы внутри объектов.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)

    filtered_mask = np.zeros_like(mask)
    for label in range(1, count):
        _, _, width, height, area = stats[label]
        if area >= MIN_OBJECT_AREA and width > 2 and height > 2:
            filtered_mask[labels == label] = 255

    # Изображение для итогового результата, как и раньше.
    image = image + 65535 - np.median(image)
    image = np.clip(image, 0, 65535).astype(np.float32)

    return image, filtered_mask

def process(image):
    if image is None or image.ndim != 2 or image.dtype != np.uint16:
        raise ValueError("ожидается одноканальный 16-битный TIFF")

    height, total_width = image.shape
    if total_width % PART_COUNT:
        raise ValueError("ширина изображения должна делиться на 4")

    part_width = total_width // PART_COUNT
    if part_width < LIGHT_KERNEL:
        raise ValueError("части изображения слишком узкие")

    parts = [
        image[:, i * part_width:(i + 1) * part_width]
        for i in range(PART_COUNT)
    ]
    cleaned, masks = zip(*(clean_part(part) for part in parts))

    # Совмещаем маски соответствующих пар, как в исходном скрипте.
    mask_1_3 = cv2.bitwise_and(masks[0], masks[2])
    mask_2_4 = cv2.bitwise_and(masks[1], masks[3])
    final_masks = [mask_1_3, mask_2_4, mask_1_3, mask_2_4]

    output_parts = []
    for part, mask in zip(cleaned, final_masks):
        result = np.full(part.shape, 65535.0, dtype=np.float32)
        selected = mask > 0
        result[selected] = part[selected] * 0.9
        output_parts.append(
            np.clip(result * 0.85, 0, 65535).astype(np.uint16)
        )

    return np.hstack(output_parts), np.hstack(final_masks)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path for path in INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
    )

    for path in files:
        try:
            image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            result, mask = process(image)

            result_path = OUTPUT_DIR / path.name
            mask_path = OUTPUT_DIR / f"{path.stem}_mask.tif"

            if not cv2.imwrite(str(result_path), result):
                raise OSError(f"не удалось сохранить {result_path}")
            if not cv2.imwrite(str(mask_path), mask):
                raise OSError(f"не удалось сохранить {mask_path}")

            print(f"{path} → {result_path}, {mask_path}")
        except (ValueError, OSError, cv2.error) as error:
            print(f"{path}: пропущен — {error}")

    if not files:
        print("В ./res/ нет TIFF-файлов")


if __name__ == "__main__":
    main()
