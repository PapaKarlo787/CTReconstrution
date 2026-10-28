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


def correct_smooth_row_drift(image, neighbor_rows=2, smooth_sigma=25, edge_threshold=None):
	source = np.asarray(image, dtype=np.float64)
	if source.ndim != 2:
		raise ValueError("ожидается двумерное изображение")

	height, width = source.shape
	if width < 8:
		return source.copy()
	detection = gaussian_filter1d(source, sigma=1.0, axis=1)
	curvature = np.abs(np.diff(detection, n=2, axis=1))

	if edge_threshold is None:
		median = np.median(curvature)
		noise = 1.4826 * np.median(np.abs(curvature - median))
		threshold = median + 6.0 * noise
	else:
		threshold = edge_threshold

	local_edges = np.zeros_like(source, dtype=bool)
	local_edges[:, 1:-1] = curvature > threshold

	protected = maximum_filter1d(local_edges.astype(np.uint8), size=2 * neighbor_rows + 1, axis=0).astype(bool)
	protected = maximum_filter1d(protected.astype(np.uint8), size=7, axis=1).astype(bool)
	protected = protected[:, 1:] | protected[:, :-1]

	original_derivative = np.diff(source, axis=1)
	usable = (~protected).astype(np.float64)

	numerator = gaussian_filter1d(original_derivative * usable, sigma=smooth_sigma, axis=1)
	denominator = gaussian_filter1d(usable, sigma=smooth_sigma, axis=1)

	smooth_derivative = np.divide(numerator, denominator, out=np.zeros_like(original_derivative), where=denominator > 0.05)
	smooth_derivative[protected] = 0.0

	drift = np.zeros_like(source)
	drift[:, 1:] = np.cumsum(smooth_derivative, axis=1)
	drift -= np.median(drift, axis=1)[:, None]

	return source - drift


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
	black = source <= BLACK_LEVEL
	black_rows = black.mean(axis=1) >= STRIPE_FRACTION

	good_rows = np.flatnonzero(~black_rows)
	if good_rows.size >= 2:
		for y in np.flatnonzero(black_rows):
			above = good_rows[good_rows < y]
			below = good_rows[good_rows > y]
			if above.size and below.size:
				y0, y1 = above[-1], below[0]
				t = (y - y0) / (y1 - y0)
				source[y] = (1 - t) * source[y0] + t * source[y1]

	vertical, reference_horizontal = factorize(
		source[:, -REFERENCE_WIDTH:]
	)

	valid_rows = (
		(vertical > 0)
		& (vertical >= 0.15 * vertical.max())
	)
	if not np.any(valid_rows):
		raise ValueError(f"фрагмент {k + 1}: нет пригодных строк")

	ratios = source[valid_rows, :] / vertical[valid_rows, None]

	horizontal = np.quantile(ratios, 0.90, axis=0)
	horizontal[-REFERENCE_WIDTH:] = reference_horizontal
	horizontal = np.maximum(np.rint(horizontal), 0)

	brightness = np.median(
		source[valid_rows, -REFERENCE_WIDTH:]
	)

	product = vertical[:, None] * horizontal[None, :]
	corrected = source.copy()
	np.divide(
		source * brightness,
		product,
		out=corrected,
		where=product > 0,
	)


	for _ in range(0):
		corrected = correct_smooth_row_drift(
			corrected,
			neighbor_rows=2,
			smooth_sigma=25,
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
