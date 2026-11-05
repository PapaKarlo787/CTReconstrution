from pathlib import Path

import numpy as np
from PIL import Image


FRAGMENT_WIDTH = 704
REFERENCE_WIDTH = 64
FRAGMENT_COUNT = 4

TOP_ROWS = 0
BOTTOM_ROWS = 70
BLACK_LEVEL = 5000
STRIPE_FRACTION = 0.90


def factorize(fragment):
    matrix = fragment.astype(np.float64)
    height, width = matrix.shape

    if not np.any(matrix):
        return np.zeros(height), np.zeros(width)

    u, singular_values, vt = np.linalg.svd(matrix, full_matrices=False)
    vertical = np.abs(u[:, 0]) * np.sqrt(singular_values[0])
    horizontal = np.abs(vt[0, :]) * np.sqrt(singular_values[0])

    for _ in range(20):
        residual = matrix - vertical[:, None] * horizontal[None, :]
        threshold = max(1.0, 3.0 * np.median(np.abs(residual)))

        weights = np.ones_like(matrix)
        outliers = np.abs(residual) > threshold
        weights[outliers] = threshold / np.abs(residual[outliers])

        vertical = np.maximum(
            0,
            np.sum(weights * matrix * horizontal[None, :], axis=1)
            / (np.sum(weights * horizontal[None, :] ** 2, axis=1) + 1e-12),
        )
        horizontal = np.maximum(
            0,
            np.sum(weights * matrix * vertical[:, None], axis=0)
            / (np.sum(weights * vertical[:, None] ** 2, axis=0) + 1e-12),
        )

    min_scale = vertical.max() / 255
    max_scale = 255 / horizontal.max()

    scales = (
        np.linspace(min_scale, max_scale, 121)
        if min_scale <= max_scale
        else [np.sqrt(min_scale * max_scale)]
    )

    rows = np.linspace(0, height - 1, min(height, 300), dtype=int)
    sample = matrix[rows]
    best_score = float("inf")
    best_factors = None

    for scale in scales:
        v = np.clip(np.rint(vertical / scale), 0, 255)
        h = np.clip(np.rint(horizontal * scale), 0, 255)
        error = np.abs(sample - v[rows, None] * h[None, :])
        score = np.mean(np.minimum(error, 10) ** 2)

        if score < best_score:
            best_score = score
            best_factors = v, h

    return best_factors


def process(path):
    with Image.open(path) as image:
        original = np.asarray(image).copy()

    if original.ndim != 2:
        raise ValueError("ожидается одноканальный TIFF")

    height, total_width = original.shape

    if total_width % FRAGMENT_COUNT != 0:
        raise ValueError("ширина TIFF должна делиться на 4")

    fragment_width = total_width // FRAGMENT_COUNT
    if fragment_width < REFERENCE_WIDTH:
        raise ValueError(
            f"ширина каждой картинки должна быть не меньше {REFERENCE_WIDTH} пикселей"
        )

    if TOP_ROWS < 0 or BOTTOM_ROWS < 0 or not 0 < TOP_ROWS + BOTTOM_ROWS <= height:
        raise ValueError("проверьте TOP_ROWS и BOTTOM_ROWS")

    clean_rows = np.zeros(height, dtype=bool)
    if TOP_ROWS:
        clean_rows[:TOP_ROWS] = True
    if BOTTOM_ROWS:
        clean_rows[-BOTTOM_ROWS:] = True

    result = np.empty_like(original, dtype=np.uint16)

    for k in range(FRAGMENT_COUNT):
        x0 = k * fragment_width
        source = original[:, x0:x0 + fragment_width].astype(np.float64)

        vertical, reference_horizontal = factorize(
            source[:, -REFERENCE_WIDTH:]
        )

        usable_rows = (
            clean_rows
            & (vertical > 0)
            & (vertical >= 0.15 * vertical.max())
        )
        if not np.any(usable_rows):
            raise ValueError(f"фрагмент {k + 1}: нет пригодных чистых строк")

        horizontal = np.median(
            source[usable_rows] / vertical[usable_rows, None],
            axis=0,
        )
        horizontal[-REFERENCE_WIDTH:] = reference_horizontal
        horizontal = np.clip(np.rint(horizontal), 0, 255)

        brightness = np.median(source[clean_rows, -REFERENCE_WIDTH:])
        product = vertical[:, None] * horizontal[None, :]

        corrected = source.copy()
        np.divide(
            source * brightness,
            product,
            out=corrected,
            where=product > 0,
        )

        black = source <= BLACK_LEVEL
        black_rows = black.mean(axis=1) >= STRIPE_FRACTION
        black_cols = black.mean(axis=0) >= STRIPE_FRACTION
        corrected[black & (black_rows[:, None] | black_cols[None, :])] = brightness

        result[:, x0:x0 + fragment_width] = np.clip(
            np.rint(corrected), 0, 65535
        ).astype(np.uint16)

    return result

def main():
    output_dir = Path("res")
    output_dir.mkdir(exist_ok=True)

    files = sorted(
        path for path in Path(".").iterdir()
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
    )

    for path in files:
        try:
            result = process(path)
            destination = output_dir / path.name
            Image.fromarray(result).save(destination)
            print(f"{path} → {destination}")
        except (OSError, ValueError, np.linalg.LinAlgError) as error:
            print(f"{path}: пропущен — {error}")

    if not files:
        print("В текущей директории нет TIFF-файлов")


if __name__ == "__main__":
    main()
