from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d, maximum_filter1d, uniform_filter1d


FRAGMENT_WIDTH = 704
REFERENCE_WIDTH = 64
FRAGMENT_COUNT = 4

TOP_ROWS = 0
BOTTOM_ROWS = 70
BLACK_LEVEL = 5000
STRIPE_FRACTION = 0.90


import numpy as np
from scipy.ndimage import gaussian_filter1d, maximum_filter1d, median_filter

def remove_vertical_stripes(image, sigma=25):
    image = np.asarray(image, dtype=np.float64)

    # Не используем почти полностью пустые строки для оценки полос.
    valid_rows = np.mean(image > 0, axis=1) > 0.8
    if not np.any(valid_rows):
        return image

    log_image = np.log(np.maximum(image[valid_rows], 1))
    smooth = gaussian_filter1d(log_image, sigma=sigma, axis=1)

    # Полоса повторяется в одних и тех же столбцах разных строк.
    stripe = np.median(log_image - smooth, axis=0)
    stripe -= np.median(stripe)

    return image * np.exp(-stripe)[None, :]

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

	scale = np.median(horizontal[horizontal > 0])
	if scale > 0:
		vertical *= scale
		horizontal /= scale

	return vertical, horizontal


def clear(source):
    source = np.asarray(source, dtype=np.float64).copy()

    if source.ndim != 2:
        raise ValueError("ожидается двумерный фрагмент")
    if source.shape[1] < REFERENCE_WIDTH:
        raise ValueError("фрагмент уже опорной области")

    # Восстанавливаем полностью или почти полностью чёрные строки
    # по ближайшим пригодным строкам сверху и снизу.
    black_rows = np.mean(source <= BLACK_LEVEL, axis=1) >= STRIPE_FRACTION
    good_rows = np.flatnonzero(~black_rows)

    if good_rows.size < 2:
        raise ValueError("нет достаточного числа пригодных строк")

    for y in np.flatnonzero(black_rows):
        above = good_rows[good_rows < y]
        below = good_rows[good_rows > y]

        if above.size and below.size:
            y0, y1 = above[-1], below[0]
            t = (y - y0) / (y1 - y0)
            source[y] = (1 - t) * source[y0] + t * source[y1]

    # Разложение опорной области:
    # reference ≈ vertical[:, None] * reference_horizontal[None, :]
    vertical, reference_horizontal = factorize(
        source[:, -REFERENCE_WIDTH:]
    )

    valid_rows = (
        ~black_rows
        & (vertical > 0)
        & (vertical >= 0.15 * np.max(vertical))
    )

    if not np.any(valid_rows):
        raise ValueError("нет пригодных строк для оценки карты шума")

    # Оценка горизонтального множителя как медианы по строкам.
    ratios = source[valid_rows] / vertical[valid_rows, None]
    horizontal = np.median(ratios, axis=0)

    # Для опорной области используем вектор, полученный факторизацией.
    horizontal[-REFERENCE_WIDTH:] = reference_horizontal

    # Не округляем коэффициенты карты шума до деления.
    noise_map = vertical[:, None] * horizontal[None, :]

    # После деления возвращаем изображение к исходному масштабу яркости.
    brightness = np.median(
        source[valid_rows, -REFERENCE_WIDTH:]
    )

    corrected = source.copy()
    np.divide(
        source * brightness,
        noise_map,
        out=corrected,
        where=noise_map > 0,
    )

    return corrected
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

	result = np.empty_like(original, dtype=np.uint16)

	for k in range(FRAGMENT_COUNT):
		x0 = k * fragment_width
		corrected = original[:, x0:x0 + fragment_width].astype(np.float64)
		for _ in range(1):
			corrected = clear(corrected)
		
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
