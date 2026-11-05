from pathlib import Path

import cv2
import numpy as np


INPUT_DIR = Path("res")
OUTPUT_DIR = Path("final")

VISUALIZE = True
SAVE_MASK = False

MAX_VERTICAL_SHIFT = 200
MAX_HORIZONTAL_SHIFT = 200

DEFAULTS = {
    "background_sigma": 35,
    "pair_gain": 200,        # Усиление изображения пары, %
    "contrast_gain": 100,    # Дополнительное усиление только для маски, %
    "threshold": 3000,
    "min_object_area": 16,
    "shift_y": 0,
    "shift_x": 0,
}

WINDOW = "Parameters"


def split_image(image):
    if image is None or image.ndim != 2 or image.dtype != np.uint16:
        raise ValueError("ожидается одноканальный 16-битный TIFF")

    if image.shape[1] % 4 != 0:
        raise ValueError("ширина изображения должна делиться на 4")

    parts = list(np.hsplit(image, 4))

    if min(parts[0].shape) < 2:
        raise ValueError("снимки слишком маленькие")

    return parts


def dark_signal(part, sigma):
    """
    Насколько каждый пиксель темнее локального фона.

    Используется только для построения изображений пар и масок.
    Исходный снимок не меняется.
    """
    source = part.astype(np.float32)

    background = cv2.GaussianBlur(
        source,
        (0, 0),
        sigmaX=sigma,
        sigmaY=sigma,
    )

    return np.maximum(background - source, 0.0)


def filter_mask(mask, min_object_area):
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (3, 3)
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
    )

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    filtered = np.zeros_like(mask)

    for label in range(1, count):
        _, _, width, height, area = stats[label]

        if (
            area >= min_object_area
            and width > 2
            and height > 2
        ):
            filtered[labels == label] = 255

    return filtered


def make_pair(first, second, params):
    """
    Суммирует тёмные отклонения снимков пары от их медианного фона.
    Pair gain влияет и на просмотр, и на маску.
    """
    first_float = first.astype(np.float32)
    second_float = second.astype(np.float32)

    first_background = float(np.median(first))
    second_background = float(np.median(second))

    first_dark = np.maximum(
        first_background - first_float, 0.0
    )
    second_dark = np.maximum(
        second_background - second_float, 0.0
    )

    # Та же формула затемнения, что была до изменения алгоритма.
    pair_signal = (
        first_dark + second_dark
    ) * (params["pair_gain"] / 100.0)

    pair_image = np.clip(
        65535.0 - pair_signal,
        0,
        65535,
    ).astype(np.uint16)

    # Маска строится по тому же сигналу, который затемняет
    # изображение пары. Дополнительное усиление — только для маски.
    detection = pair_signal * (
        params["contrast_gain"] / 100.0
    )

    initial_mask = np.where(
        detection >= max(1, params["threshold"]),
        255,
        0,
    ).astype(np.uint8)

    mask = filter_mask(
        initial_mask,
        params["min_object_area"],
    )

    return pair_image, mask


def prepare_pairs(parts, params):
    # Снимки внутри каждой пары уже совпадают по координатам.
    pair_13 = make_pair(parts[0], parts[2], params)
    pair_24 = make_pair(parts[1], parts[3], params)

    return pair_13, pair_24


def common_slices(height, width, shift_y, shift_x):
    """
    Двигаем пару (1, 3) относительно неподвижной пары (2, 4).

    Положительный Y — вниз.
    Положительный X — вправо.
    """
    top = max(0, shift_y)
    bottom = min(height, height + shift_y)

    left = max(0, shift_x)
    right = min(width, width + shift_x)

    if top >= bottom or left >= right:
        raise ValueError("после сдвига не осталось общей области")

    slice_13 = (
        slice(top - shift_y, bottom - shift_y),
        slice(left - shift_x, right - shift_x),
    )

    slice_24 = (
        slice(top, bottom),
        slice(left, right),
    )

    return slice_13, slice_24


def process_prepared(parts, pairs, params):
    (image_13, mask_13), (image_24, mask_24) = pairs

    height, width = parts[0].shape

    slice_13, slice_24 = common_slices(
        height,
        width,
        params["shift_y"],
        params["shift_x"],
    )

    # Снимки 1 и 3 обрезаем одинаково.
    # Снимки 2 и 4 обрезаем одинаково.
    cropped_parts = [
        parts[0][slice_13],
        parts[1][slice_24],
        parts[2][slice_13],
        parts[3][slice_24],
    ]

    aligned_image_13 = image_13[slice_13]
    aligned_image_24 = image_24[slice_24]

    aligned_mask_13 = mask_13[slice_13]
    aligned_mask_24 = mask_24[slice_24]

    # Одна маска для всех четырёх снимков.
    common_mask = cv2.bitwise_and(
        aligned_mask_13,
        aligned_mask_24,
    )

    selected = common_mask > 0

    if not np.any(selected):
        raise ValueError(
            "общая маска пуста: измените сдвиг или параметры маски"
        )

    results = []

    for part in cropped_parts:
        background_pixels = part[~selected]

        if background_pixels.size == 0:
            raise ValueError("маска заняла весь снимок")

        background_median = np.uint16(
            np.rint(np.median(background_pixels))
        )

        result = np.full(
            part.shape,
            background_median,
            dtype=np.uint16,
        )

        # Объект копируется из исходного снимка без изменений.
        result[selected] = part[selected]
        results.append(result)

    return {
        "results": results,
        "common_mask": common_mask,
        "cropped_parts": cropped_parts,
        "image_13": aligned_image_13,
        "image_24": aligned_image_24,
        "mask_13": aligned_mask_13,
        "mask_24": aligned_mask_24,
    }


def process(image, params):
    """Обработка без графического интерфейса."""
    parts = split_image(image)
    pairs = prepare_pairs(parts, params)
    return process_prepared(parts, pairs, params)


def preview_8bit(image):
    """Преобразование только для окон, не для сохраняемых TIFF."""
    return (image >> 8).astype(np.uint8)


def fit_preview(image, max_width=1200, max_height=700):
    height, width = image.shape[:2]

    scale = min(
        max_width / width,
        max_height / height,
        1.0,
    )

    if scale < 1.0:
        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA,
        )

    return image


def create_controls():
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    controls = [
        ("Background sigma", DEFAULTS["background_sigma"], 150),
        ("Pair gain %", DEFAULTS["pair_gain"], 1000),
        ("Contrast gain %", DEFAULTS["contrast_gain"], 500),
        ("Detection threshold", DEFAULTS["threshold"], 30000),
        ("Min object area", DEFAULTS["min_object_area"], 500),
        (
            "Vertical shift",
            DEFAULTS["shift_y"] + MAX_VERTICAL_SHIFT,
            2 * MAX_VERTICAL_SHIFT,
        ),
        (
            "Horizontal shift",
            DEFAULTS["shift_x"] + MAX_HORIZONTAL_SHIFT,
            2 * MAX_HORIZONTAL_SHIFT,
        ),
    ]

    for name, initial, maximum in controls:
        cv2.createTrackbar(
            name,
            WINDOW,
            initial,
            maximum,
            lambda _: None,
        )


def read_controls():
    return {
        "background_sigma": max(
            1,
            cv2.getTrackbarPos("Background sigma", WINDOW),
        ),
        "pair_gain": cv2.getTrackbarPos(
            "Pair gain %", WINDOW
        ),
        "contrast_gain": max(
            1,
            cv2.getTrackbarPos("Contrast gain %", WINDOW),
        ),
        "threshold": cv2.getTrackbarPos(
            "Detection threshold", WINDOW
        ),
        "min_object_area": cv2.getTrackbarPos(
            "Min object area", WINDOW
        ),
        "shift_y": (
            cv2.getTrackbarPos("Vertical shift", WINDOW)
            - MAX_VERTICAL_SHIFT
        ),
        "shift_x": (
            cv2.getTrackbarPos("Horizontal shift", WINDOW)
            - MAX_HORIZONTAL_SHIFT
        ),
    }


def show_preview(processed):
    image_13 = processed["image_13"]
    image_24 = processed["image_24"]

    cv2.imshow(
        "Pair 1+3",
        fit_preview(preview_8bit(image_13)),
    )
    cv2.imshow(
        "Pair 2+4",
        fit_preview(preview_8bit(image_24)),
    )

    # Тёмные детали пары 1+3 -> красный канал.
    # Тёмные детали пары 2+4 -> зелёный канал.
    red = 255 - preview_8bit(image_13)
    green = 255 - preview_8bit(image_24)

    overlay = cv2.merge([
        np.zeros_like(red),
        green,
        red,
    ])

    cv2.imshow(
        "Alignment: red=1+3 green=2+4",
        fit_preview(overlay),
    )

    cv2.imshow(
        "Common mask",
        fit_preview(processed["common_mask"]),
    )

    result_preview = np.hstack([
        preview_8bit(part)
        for part in processed["results"]
    ])

    cv2.imshow(
        "Result: 1 | 2 | 3 | 4",
        fit_preview(result_preview),
    )


def adjust(image, filename):
    """
    Вся визуализация находится здесь.
    Чтобы её убрать, установите VISUALIZE = False.
    """
    parts = split_image(image)
    create_controls()

    print(f"\n{filename}")
    print("Сдвиги перемещают пару (1, 3) относительно пары (2, 4).")
    print("S или Enter — сохранить; Q или Esc — выйти.")

    previous_pair_settings = None
    previous_shifts = None

    pairs = None
    current_result = None

    try:
        while True:
            params = read_controls()

            pair_settings = (
                params["background_sigma"],
                params["pair_gain"],
                params["contrast_gain"],
                params["threshold"],
                params["min_object_area"],
            )

            shifts = (
                params["shift_y"],
                params["shift_x"],
            )

            pairs_changed = pair_settings != previous_pair_settings
            shifts_changed = shifts != previous_shifts

            # Изображения и маски пар пересчитываются при изменении
            # любого параметра обнаружения, включая Pair gain %.
            if pairs_changed:
                pairs = prepare_pairs(parts, params)
                previous_pair_settings = pair_settings

            if pairs_changed or shifts_changed:
                previous_shifts = shifts

                try:
                    current_result = process_prepared(
                        parts,
                        pairs,
                        params,
                    )

                    show_preview(current_result)

                    height, width = current_result[
                        "common_mask"
                    ].shape

                    print(
                        f"\rY={params['shift_y']:+d}, "
                        f"X={params['shift_x']:+d}; "
                        f"область {width}×{height}; "
                        f"маска: "
                        f"{np.count_nonzero(current_result['common_mask'])}"
                        " пикселей       ",
                        end="",
                        flush=True,
                    )

                except ValueError as error:
                    current_result = None
                    print(f"\nТекущие настройки: {error}")

            key = cv2.waitKey(40) & 0xFF

            if key in (ord("s"), ord("S"), 13):
                if current_result is not None:
                    print()
                    return current_result, False

                print("\nСохранение невозможно при текущих настройках.")

            if key in (ord("q"), ord("Q"), 27):
                print()
                return None, True

    finally:
        cv2.destroyAllWindows()


def save_results(path, processed):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for number, result in enumerate(
        processed["results"],
        start=1,
    ):
        destination = OUTPUT_DIR / f"{path.stem}_{number}.tif"

        if not cv2.imwrite(str(destination), result):
            raise OSError(f"не удалось сохранить {destination}")

    if SAVE_MASK:
        destination = OUTPUT_DIR / f"{path.stem}_mask.tif"

        if not cv2.imwrite(
            str(destination),
            processed["common_mask"],
        ):
            raise OSError(f"не удалось сохранить {destination}")

    print(f"{path.name}: сохранены 4 снимка в {OUTPUT_DIR}/")


def main():
    if not INPUT_DIR.exists():
        print(f"Каталог {INPUT_DIR} не найден")
        return

    files = sorted(
        path for path in INPUT_DIR.iterdir()
        if (
            path.is_file()
            and path.suffix.lower() in {".tif", ".tiff"}
            and not path.stem.endswith("_mask")
        )
    )

    if not files:
        print(f"В {INPUT_DIR} нет TIFF-файлов")
        return

    for path in files:
        try:
            image = cv2.imread(
                str(path),
                cv2.IMREAD_UNCHANGED,
            )

            if VISUALIZE:
                processed, stop = adjust(image, path.name)

                if stop:
                    break
            else:
                processed = process(image, DEFAULTS)

            save_results(path, processed)

        except (ValueError, OSError, cv2.error) as error:
            print(f"{path}: пропущен — {error}")


if __name__ == "__main__":
    main()
