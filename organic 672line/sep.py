from pathlib import Path

import cv2
import numpy as np


INPUT_DIR = Path("res")
OUTPUT_DIR = Path("final")

VISUALIZE = True
SAVE_MASK = False

MAX_VERTICAL_SHIFT = 200
MAX_HORIZONTAL_SHIFT = 200

# Параметры обнаружения. Они влияют только на маску,
# но не меняют яркость исходных снимков.
BACKGROUND_SIGMA = 35
CONTRAST_GAIN = 1.0
DETECTION_THRESHOLD = 3000
MIN_OBJECT_AREA = 16


def split_image(image):
    if image is None or image.ndim != 2 or image.dtype != np.uint16:
        raise ValueError("ожидается одноканальный 16-битный TIFF")

    if image.shape[1] % 4:
        raise ValueError("ширина изображения должна делиться на 4")

    return list(np.hsplit(image, 4))


def detect_mask(part):
    source = part.astype(np.float32)

    background = cv2.GaussianBlur(
        source,
        (0, 0),
        sigmaX=BACKGROUND_SIGMA,
        sigmaY=BACKGROUND_SIGMA,
    )

    # Контраст используется исключительно для обнаружения.
    contrast = np.maximum(background - source, 0.0)
    contrast *= CONTRAST_GAIN

    mask = (
        (contrast >= DETECTION_THRESHOLD).astype(np.uint8) * 255
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3),
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    filtered = np.zeros_like(mask)

    for label in range(1, count):
        _, _, width, height, area = stats[label]

        if (
            area >= MIN_OBJECT_AREA
            and width > 2
            and height > 2
        ):
            filtered[labels == label] = 255

    return filtered


def prepare(image):
    """Вычисляется один раз; при движении ползунков не повторяется."""
    parts = split_image(image)
    masks = [detect_mask(part) for part in parts]

    # Внутри каждой пары снимки уже совмещены.
    # OR учитывает объект, найденный хотя бы на одном контрасте пары.
    pair_13_mask = cv2.bitwise_or(masks[0], masks[2])
    pair_24_mask = cv2.bitwise_or(masks[1], masks[3])

    return parts, pair_13_mask, pair_24_mask


def common_slices(height, width, shift_y, shift_x):
    """
    Сдвигаем пару (1, 3) относительно пары (2, 4).

    shift_y > 0: пара (1, 3) движется вниз.
    shift_x > 0: пара (1, 3) движется вправо.

    Возвращаем срезы одной и той же общей области
    в исходных координатах каждой пары.
    """
    top = max(0, shift_y)
    bottom = min(height, height + shift_y)

    left = max(0, shift_x)
    right = min(width, width + shift_x)

    if bottom <= top or right <= left:
        raise ValueError(
            "после сдвига не осталось общей области"
        )

    pair_13_slice = (
        slice(top - shift_y, bottom - shift_y),
        slice(left - shift_x, right - shift_x),
    )

    pair_24_slice = (
        slice(top, bottom),
        slice(left, right),
    )

    return pair_13_slice, pair_24_slice


def process_prepared(prepared, shift_y, shift_x):
    parts, pair_13_mask, pair_24_mask = prepared
    height, width = parts[0].shape

    slice_13, slice_24 = common_slices(
        height,
        width,
        shift_y,
        shift_x,
    )

    # Порядок снимков сохраняется: 1, 2, 3, 4.
    cropped_parts = [
        parts[0][slice_13],
        parts[1][slice_24],
        parts[2][slice_13],
        parts[3][slice_24],
    ]

    aligned_13_mask = pair_13_mask[slice_13]
    aligned_24_mask = pair_24_mask[slice_24]

    # Объект должен быть найден в обеих парах.
    common_mask = cv2.bitwise_and(
        aligned_13_mask,
        aligned_24_mask,
    )

    selected = common_mask > 0

    if not np.any(selected):
        raise ValueError(
            "общая маска пустая: проверьте совмещение "
            "или параметры обнаружения"
        )

    results = []

    for part in cropped_parts:
        background_pixels = part[~selected]

        if background_pixels.size == 0:
            raise ValueError(
                "маска заняла всю общую область"
            )

        # Медиана фона вычисляется отдельно для каждого
        # исходного снимка после обрезки.
        background_median = np.uint16(
            np.rint(np.median(background_pixels))
        )

        result = np.full(
            part.shape,
            background_median,
            dtype=np.uint16,
        )

        # Объект — пиксели исходного снимка без изменений.
        result[selected] = part[selected]
        results.append(result)

    return (
        results,
        common_mask,
        cropped_parts,
        aligned_13_mask,
        aligned_24_mask,
    )


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


def preview_8bit(image):
    """Преобразование только для просмотра, не для сохранения TIFF."""
    return (image / 257).astype(np.uint8)


def adjust_alignment(prepared, filename):
    """
    Вся визуализация находится здесь.
    Для обработки без окон установите VISUALIZE = False.
    """
    window = "Alignment controls"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    cv2.createTrackbar(
        "Vertical shift",
        window,
        MAX_VERTICAL_SHIFT,
        2 * MAX_VERTICAL_SHIFT,
        lambda _: None,
    )

    cv2.createTrackbar(
        "Horizontal shift",
        window,
        MAX_HORIZONTAL_SHIFT,
        2 * MAX_HORIZONTAL_SHIFT,
        lambda _: None,
    )

    print(f"\n{filename}")
    print(
        "Оба ползунка двигают пару (1, 3). "
        "Пара (2, 4) неподвижна."
    )
    print("S или Enter — сохранить; Q или Esc — выход.")

    previous_shifts = None
    current_result = None

    try:
        while True:
            shift_y = (
                cv2.getTrackbarPos("Vertical shift", window)
                - MAX_VERTICAL_SHIFT
            )
            shift_x = (
                cv2.getTrackbarPos("Horizontal shift", window)
                - MAX_HORIZONTAL_SHIFT
            )

            shifts = (shift_y, shift_x)

            if shifts != previous_shifts:
                previous_shifts = shifts

                try:
                    current_result = process_prepared(
                        prepared,
                        shift_y,
                        shift_x,
                    )

                    (
                        results,
                        common_mask,
                        cropped_parts,
                        aligned_13_mask,
                        aligned_24_mask,
                    ) = current_result

                    # Маска пары (1, 3) красная,
                    # маска пары (2, 4) зелёная.
                    # Совпадающие области видны жёлтыми.
                    zero = np.zeros_like(aligned_13_mask)

                    mask_overlay = cv2.merge([
                        zero,
                        aligned_24_mask,
                        aligned_13_mask,
                    ])

                    cv2.imshow(
                        "Alignment masks: red=1,3 green=2,4",
                        fit_preview(mask_overlay),
                    )

                    # Дополнительный просмотр самих снимков:
                    # снимок 1 красный, снимок 2 зелёный.
                    first = preview_8bit(cropped_parts[0])
                    second = preview_8bit(cropped_parts[1])

                    image_overlay = cv2.merge([
                        np.zeros_like(first),
                        second,
                        first,
                    ])

                    cv2.imshow(
                        "Alignment images: red=1 green=2",
                        fit_preview(image_overlay),
                    )

                    cv2.imshow(
                        "Common mask",
                        fit_preview(common_mask),
                    )

                    result_preview = np.hstack([
                        preview_8bit(part)
                        for part in results
                    ])

                    cv2.imshow(
                        "Result: 1 | 2 | 3 | 4",
                        fit_preview(result_preview),
                    )

                    print(
                        f"\rСдвиг: Y={shift_y:+d}, X={shift_x:+d}; "
                        f"общий размер: "
                        f"{common_mask.shape[1]}×"
                        f"{common_mask.shape[0]} px       ",
                        end="",
                        flush=True,
                    )

                except ValueError as error:
                    current_result = None
                    print(
                        f"\nСдвиг Y={shift_y:+d}, "
                        f"X={shift_x:+d}: {error}"
                    )

            key = cv2.waitKey(40) & 0xFF

            if key in (ord("s"), ord("S"), 13):
                if current_result is not None:
                    print()
                    return current_result

                print("\nПри текущем сдвиге сохранять нечего.")

            if key in (ord("q"), ord("Q"), 27):
                print()
                return None

    finally:
        cv2.destroyAllWindows()


def save_results(path, processed):
    results, common_mask, _, _, _ = processed
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for number, result in enumerate(results, start=1):
        destination = OUTPUT_DIR / f"{path.stem}_{number}.tif"

        if not cv2.imwrite(str(destination), result):
            raise OSError(
                f"не удалось сохранить {destination}"
            )

    if SAVE_MASK:
        destination = OUTPUT_DIR / f"{path.stem}_mask.tif"

        if not cv2.imwrite(str(destination), common_mask):
            raise OSError(
                f"не удалось сохранить {destination}"
            )

    print(
        f"{path.name}: сохранены 4 обрезанных снимка "
        f"в {OUTPUT_DIR}/"
    )


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

            prepared = prepare(image)

            if VISUALIZE:
                processed = adjust_alignment(
                    prepared,
                    path.name,
                )

                if processed is None:
                    break
            else:
                processed = process_prepared(
                    prepared,
                    shift_y=0,
                    shift_x=0,
                )

            save_results(path, processed)

        except (ValueError, OSError, cv2.error) as error:
            print(f"{path}: пропущен — {error}")


if __name__ == "__main__":
    main()
