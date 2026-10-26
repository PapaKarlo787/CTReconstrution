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
from scipy.ndimage import gaussian_filter1d, median_filter, maximum_filter1d


def correct_smooth_row_drift(
    image,
    neighbor_rows=2,
    edge_threshold=None,
    window=25,
    step=8,
    max_white_width=20,
):
    source = np.asarray(image, dtype=np.float64)
    if source.ndim != 2:
        raise ValueError("ожидается двумерное изображение")

    height, width = source.shape
    if width < 12:
        return source.copy()

    # Фильтрация нужна только для поиска границ.
    # Значения пикселей объекта из source не сглаживаются.
    detection = median_filter(source, size=(1, 3))
    derivative = np.diff(detection, axis=1)
    sharpness = derivative - gaussian_filter1d(
        derivative, sigma=8, axis=1
    )

    if edge_threshold is None:
        center = np.median(sharpness)
        noise = 1.4826 * np.median(np.abs(sharpness - center))
        edge_threshold = max(5.0, 6.0 * noise)

    magnitude = np.abs(sharpness)
    peaks = (
        (magnitude >= edge_threshold)
        & (magnitude >= maximum_filter1d(magnitude, size=3, axis=1))
    )

    # Для сравнения уровней нужны пиксели с обеих сторон границы.
    peaks[:, :4] = False
    peaks[:, -4:] = False

    def jump_at(row, x):
        """Перепад через границу между x и x+1."""
        left = np.median(detection[row, x-3:x+1])
        right = np.median(detection[row, x+1:x+5])
        return float(right - left)

    # Области, которые нельзя использовать для оценки фона.
    dark_mask = np.zeros((height, width), dtype=bool)
    white_mask = np.zeros((height, width), dtype=bool)

    for y in range(height):
        y0 = max(0, y - neighbor_rows)
        y1 = min(height, y + neighbor_rows + 1)

        # Кандидаты из текущей и соседних строк.
        candidates = []
        for yy in range(y0, y1):
            for x in np.flatnonzero(peaks[yy]):
                candidates.append((int(x), yy))
        candidates.sort()

        # Одну границу, найденную рядом в нескольких строках,
        # считаем одним событием.
        groups = []
        for item in candidates:
            if not groups or item[0] - groups[-1][-1][0] > 1:
                groups.append([item])
            else:
                groups[-1].append(item)

        edges = []
        for group in groups:
            own = [x for x, yy in group if yy == y]
            x = (
                max(own, key=lambda xx: magnitude[y, xx])
                if own else
                int(round(np.mean([xx for xx, _ in group])))
            )

            neighbor_jumps = np.array(
                [jump_at(yy, xx) for xx, yy in group],
                dtype=np.float64,
            )

            # Знак определяем по обнаруженным соседним границам.
            sign = np.sign(np.median(neighbor_jumps))
            supported = neighbor_jumps[
                np.sign(neighbor_jumps) == sign
            ]
            if sign == 0 or supported.size == 0:
                continue

            mean_jump = float(np.mean(supported))
            own_jump = jump_at(y, x)

            # Сильная граница в текущей строке — её собственная.
            # Если здесь она слаба, используем среднюю по соседям
            # для определения типа границы, НЕ для замены пикселей.
            if own and abs(own_jump) >= edge_threshold:
                jump = own_jump
            else:
                jump = mean_jump

            if np.sign(jump) == sign:
                edges.append((x + 1, jump))

        edges.sort()

        # Сопоставляем пары границ.
        pending = None
        for position, jump in edges:
            if pending is None:
                pending = (position, jump)
                continue

            start, first_jump = pending

            if np.sign(first_jump) == np.sign(jump):
                # Несколько границ одного направления:
                # ждём противоположную; берём последнюю.
                pending = (position, jump)
                continue

            if first_jump < 0 and jump > 0:
                # Вниз -> вверх: тёмный объект.
                dark_mask[y, start:position] = True

            elif first_jump > 0 and jump < 0:
                # Вверх -> вниз: короткий белый всплеск.
                # Длинную светлую область автоматически не стираем.
                if position - start <= max_white_width:
                    white_mask[y, start:position] = True

            pending = None

        # Если объект начался, но до края строки не закончился,
        # не используем этот хвост для оценки фона.
        if pending is not None and pending[1] < 0:
            dark_mask[y, pending[0]:] = True

    excluded = dark_mask | white_mask
    # Не берём в опорные точки сами края объектов и всплесков.
    excluded = maximum_filter1d(
        excluded.astype(np.uint8), size=7, axis=1
    ).astype(bool)

    # Общая медиана видимого фона — целевая ровная яркость.
    visible = source[~excluded]
    if visible.size == 0:
        return source.copy()
    target = float(np.median(visible))

    result = source.copy()
    half = window // 2

    for y in range(height):
        valid = ~excluded[y]
        if np.count_nonzero(valid) < max(8, window // 2):
            # Недостаточно открытого фона: не угадываем его под объектом.
            continue

        # Опорные точки плавного фона по всей строке.
        anchor_x = []
        anchor_value = []

        centers = list(range(0, width, step))
        if centers[-1] != width - 1:
            centers.append(width - 1)

        for center in centers:
            left = max(0, center - half)
            right = min(width, center + half + 1)
            xs = np.flatnonzero(valid[left:right]) + left

            if xs.size < max(4, (right - left) // 4):
                continue

            anchor_x.append(float(np.median(xs)))
            anchor_value.append(float(np.median(source[y, xs])))

        if not anchor_x:
            continue

        # Линейная интерполяция не даёт колебаний у резких границ.
        # Под объектом фон продолжается между соседними опорами.
        background = np.interp(
            np.arange(width), anchor_x, anchor_value
        )

        # Сохраняем исходные детали объекта:
        # убираем только оценённый плавный дрейф фона.
        result[y] = source[y] - (background - target)

        # Только распознанный короткий белый всплеск убираем целиком.
        # Выход из тёмного объекта (вниз -> вверх) сюда не попадает.
        result[y, white_mask[y]] = target

    return result
    
    
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

	result = np.empty_like(original, dtype=np.uint16)

	for k in range(FRAGMENT_COUNT):
		x0 = k * fragment_width
		source = original[:, x0:x0 + fragment_width].astype(np.float64)

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

		# Оцениваем фон каждого столбца без заданных «чистых» строк.
		horizontal = np.quantile(ratios, 0.90, axis=0)

		# В заведомо пустой области используем непосредственно результат factorize.
		horizontal[-REFERENCE_WIDTH:] = reference_horizontal
		horizontal = np.clip(np.rint(horizontal), 0, 255)

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
		
		corrected = correct_smooth_row_drift(
			corrected,
			neighbor_rows=2
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
