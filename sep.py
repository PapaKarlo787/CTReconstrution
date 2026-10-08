import cv2
import numpy as np
from scipy.ndimage import percentile_filter
from scipy.optimize import minimize_scalar

def advanced_xray_contrast(coefficients, stiffness=15.0, plateau_width=0.15, max_ratio=2.0):
	left_sigmoid = 1.0 / (1.0 + np.exp(-stiffness * (coefficients - (1.0 - plateau_width))))
	right_sigmoid = 1.0 / (1.0 + np.exp(-stiffness * (coefficients - (1.0 + plateau_width))))
	output = left_sigmoid + right_sigmoid * (max_ratio - 1.0)
	return output

def remove_horizontal_stripes_pure(img_float, black_threshold=5000.0):
	"""
	Чистая математическая функция для устранения горизонтальных полос на интроскопе.
	Принимает и возвращает двумерный массив numpy (float32).
	"""
	rows, cols = img_float.shape
	img_clean = img_float.copy()

	# 1. Интерполяция черных строк по вертикали
	row_means = np.mean(img_float, axis=1)
	dead_rows_mask = row_means < black_threshold
	all_rows = np.arange(rows)
	good_rows = all_rows[~dead_rows_mask]
	
	if len(good_rows) > 0 and len(good_rows) < rows:
		for c in range(cols):
			col_data = img_float[:, c]
			good_values = col_data[good_rows]
			img_clean[dead_rows_mask, c] = np.interp(all_rows[dead_rows_mask], good_rows, good_values)
	
	# 2. Интерполяция чёрных столбцов по горизонтали
	col_means = np.mean(img_clean, axis=0)
	dead_cols_mask = col_means < black_threshold

	all_cols = np.arange(cols)
	good_cols = all_cols[~dead_cols_mask]

	if 0 < len(good_cols) < cols:
		for r in range(rows):
			row_data = img_clean[r, :]
			good_values = row_data[good_cols]
			img_clean[r, dead_cols_mask] = np.interp(
				all_cols[dead_cols_mask],
				good_cols,
				good_values,
			)
	ref_column = np.median(img_clean, axis=1)[:, np.newaxis]
	ref_column[ref_column == 0] = 1.0

	return img_clean / ref_column * np.median(img_clean)

def isolate_objects_and_darken_all(img_clean_float, mask_contours, global_best_k=1.0, darken_factor=0.85):
	final_image = np.full_like(img_clean_float, 65535.0)
	object_pixels_mask = mask_contours > 0
	corrected_all_objects = img_clean_float * global_best_k
	final_image[object_pixels_mask] = corrected_all_objects[object_pixels_mask]    
	return np.clip(final_image * darken_factor, 0.0, 65535.0)

def evaluate_contour_variance(img_orig_float, mask_contours):
	num_labels, labels_mask, stats, _ = cv2.connectedComponentsWithStats(mask_contours)
	variance_report = {}

	for label in range(1, num_labels):
		single_obj_mask = (labels_mask == label)
		obj_pixels = img_orig_float[single_obj_mask]
		
		if len(obj_pixels) == 0:
			continue
			
		mean_val = np.mean(obj_pixels)                          # Средняя яркость
		std_val = np.std(obj_pixels)                            # Стандартное отклонение (сила шума)
		min_val = np.min(obj_pixels)                            # Самый темный пиксель
		max_val = np.max(obj_pixels)                            # Самый светлый пиксель
		range_val = max_val - min_val                           # Полный размах (дельта)
		
		cv_val = (std_val / mean_val * 100.0) if mean_val > 0 else 0.0
		
		variance_report[label] = {
			"Contour_ID": label,
			"Pixel_Count": len(obj_pixels),
			"Mean_Brightness": float(mean_val),
			"Std_Deviation_Sigma": float(std_val),
			"Min_Value": float(min_val),
			"Max_Value": float(max_val),
			"Range_Delta": float(range_val),
			"Coefficient_of_Variation_Pct": float(cv_val)
		}
		
		print(f"Контур #{label:02d} | Пикселей: {len(obj_pixels):5d} | "
			  f"Шум (Sigma): {std_val:7.2f} | Перепад (Delta): {range_val:7.2f} | "
			  f"Вариация: {cv_val:5.2f}%")

	return variance_report

def clean_16bit_image(img):
	rows, cols = img.shape
	img_float = remove_horizontal_stripes_pure(np.float32(img))

	# ШАГ 1: ПЕРВЫЙ ПРОХОД (ОЧИСТКА ФОНА)
	top_bottom_only = np.vstack((img_float[:rows//4, :], img_float[3*rows//4:, :]))
	vert_profile = np.median(top_bottom_only, axis=0)
	vert_noise = vert_profile - np.median(vert_profile)
	img_first_pass = img_float

	img_first_pass = img_first_pass / vert_profile * np.median(vert_profile)

	img_first_pass_contours = advanced_xray_contrast(img_first_pass / np.median(vert_profile), 30, 0.05, np.max(img_float) / np.median(vert_profile)) * np.median(vert_profile)
	img_first_pass_contours = img_first_pass_contours + 65535 - np.median(img_first_pass_contours)
	img_first_pass = img_first_pass + 65535 - np.median(img_first_pass)
	
	img_first_pass = np.clip(img_first_pass, 0, 65535).astype(np.float32)
	img_first_pass_contours = np.clip(img_first_pass_contours, 0, 65535).astype(np.uint16)


	# ШАГ 2: ПОИСК И ФИЛЬТРАЦИЯ КОНТУРОВ
	img_8bit_for_mask = np.uint8(img_first_pass_contours / 256)
	dst = cv2.GaussianBlur(img_8bit_for_mask, (5, 5), 0)
	_, thresh = cv2.threshold(dst, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
	contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

	rects = []
	cnt_list = []
	white_color = 255

	for i in range(len(contours)):
		x, y, w, h = cv2.boundingRect(contours[i])
		cv2.rectangle(dst, (x, y), (x + w, y + h), white_color, 1)
		if w > 2 and h > 2:
			rects.append((x, y, w, h))
			cnt_list.append(contours[i])

	mask = np.zeros_like(img_8bit_for_mask)
	cv2.drawContours(mask, cnt_list, -1, 255, thickness=-1)

	return img_first_pass, mask


def process_snapshot(path):
	image = cv2.imread(path, cv2.IMREAD_UNCHANGED)

	w = 704
	parts = [image[:, i * w:(i + 1) * w].copy() for i in range(4)]

	results = [clean_16bit_image(part) for part in parts]
	masks = [result[1] for result in results]

	mask_1_3 = (np.logical_and(masks[0] != 0, masks[2] != 0) * 255).astype(np.uint8)
	mask_2_4 = (np.logical_and(masks[1] != 0, masks[3] != 0) * 255).astype(np.uint8)

	results = [[results[i][0], mask_2_4 if i&1 else mask_1_3] for i in range(len(results))]
	
	for i, res in enumerate(results):
		res[0] = isolate_objects_and_darken_all(res[0], res[1], 0.9, 0.85)
		evaluate_contour_variance(res[0], res[1])
		cv2.imshow('Original', np.uint8(parts[i] / 256))
		cv2.imshow('Mask', res[1])
		cv2.imshow('Result', np.uint8(res[0] / 256))
		cv2.waitKey(0)
		cv2.destroyAllWindows()
		

process_snapshot("2.tif")



