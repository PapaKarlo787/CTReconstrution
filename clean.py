import argparse
import csv
from pathlib import Path

import numpy as np
import tifffile

N_SHOTS = 4
BACKGROUND_WIDTH = 64
MAX16 = 65535


def load_map(path):
    values = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not {"x_in_image", "coefficient"}.issubset(reader.fieldnames or []):
            raise ValueError("в CSV нужны колонки x_in_image и coefficient")

        for row in reader:
            x = int(row["x_in_image"])
            gain = float(row["coefficient"])
            if x < 0 or x in values or not np.isfinite(gain) or gain < 0:
                raise ValueError(f"неверный индекс или коэффициент: столбец {x}")
            values[x] = gain

    if not values or max(values) != len(values) - 1:
        raise ValueError("индексы столбцов должны идти от 0 без пропусков")

    gains = np.array([values[x] for x in range(len(values))], dtype=np.float64)
    if gains.size % (N_SHOTS * BACKGROUND_WIDTH):
        raise ValueError("ширина карты должна быть кратна 4 × 64")
    return gains


def prepare_map(gains, threshold):
    parts = []
    for i, shot_gains in enumerate(np.split(gains, N_SHOTS), start=1):
        columns = np.flatnonzero(shot_gains > threshold)
        # Определяем фон по исходным координатам, до удаления.
        background = columns >= shot_gains.size - BACKGROUND_WIDTH
        if not background.any():
            raise ValueError(f"снимок {i}: не осталось пикселей фоновой полосы")
        parts.append((columns, shot_gains[columns], background))
    return parts


def normalize(image, parts, black_threshold):
    result = []
    restored_count = 0

    for i, (shot, part) in enumerate(
        zip(np.split(image, N_SHOTS, axis=1), parts), start=1
    ):
        columns, gains, background = part
        pixels = shot[:, columns].astype(np.float64)

        # Определяем плохие строки до деления на коэффициенты.
        raw_means = pixels[:, background].mean(axis=1)
        good = np.flatnonzero(raw_means > black_threshold)
        if good.size == 0:
            raise ValueError(f"снимок {i}: нет нормальных строк для восстановления")

        restored_count += pixels.shape[0] - good.size

        # Края не замыкаются: используем ближайшую нормальную строку.
        pixels[:good[0]] = pixels[good[0]]
        pixels[good[-1] + 1:] = pixels[good[-1]]

        # Внутренние полосы: среднее двух исходных соседних строк.
        for j in np.flatnonzero(np.diff(good) > 1):
            above, below = good[j], good[j + 1]
            pixels[above + 1:below] = (pixels[above] + pixels[below]) / 2.0

        # Сначала коррекция столбцов, затем выравнивание по первой строке.
        pixels /= gains[None, :]
        row_means = pixels[:, background].mean(axis=1)
        pixels *= (row_means[0] / row_means)[:, None]

        np.rint(pixels, out=pixels)
        np.clip(pixels, 0, MAX16, out=pixels)
        result.append(pixels.astype(np.uint16))

    return np.concatenate(result, axis=1), restored_count

def main():
    parser = argparse.ArgumentParser(
        description="Коррекция исходных TIFF по картам и фону первой строки."
    )
    parser.add_argument("maps", nargs="*", type=Path)
    parser.add_argument("--min-coefficient", type=float, default=0.2)
    parser.add_argument("--output-dir", type=Path, default=Path("res_first_row"))
    parser.add_argument(
        "--black-threshold", type=int, default=100,
        help="Восстанавливать строки со средним фоном не выше порога",
    )
    args = parser.parse_args()
    if not 0 <= args.black_threshold <= MAX16:
        parser.error("--black-threshold должен быть от 0 до 65535")
    if not np.isfinite(args.min_coefficient) or args.min_coefficient < 0:
        parser.error("--min-coefficient должен быть конечным числом не меньше 0")

    root = Path.cwd()
    maps = {}
    for path in args.maps or [Path("view0.csv"), Path("view1.csv")]:
        key = path.stem.casefold()
        if key in maps:
            parser.error(f"повторяющийся суффикс карты: {path.stem}")
        try:
            gains = load_map(path)
            parts = prepare_map(gains, args.min_coefficient)
        except (OSError, ValueError, TypeError, csv.Error) as exc:
            parser.error(f"{path}: {exc}")
        maps[key] = (path.stem, gains.size, parts)
        print(f"{path.name}: фоновых столбцов по снимкам: "
              f"{[int(part[2].sum()) for part in parts]}")

    suffixes = sorted(maps, key=len, reverse=True)
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".tif", ".tiff"}:
            continue

        key = next((s for s in suffixes if path.stem.casefold().endswith(s)), None)
        if key is None:
            print(f"{path.name}: пропущен — нет карты для суффикса")
            continue

        view, width, parts = maps[key]
        output = args.output_dir / view / path.name
        try:
            if output.parent.resolve() == root or output.is_symlink():
                raise ValueError("небезопасный путь вывода: исходная папка или ссылка")

            image = tifffile.imread(path)
            if (
                image.ndim != 2 or image.size == 0
                or image.dtype.kind != "u" or image.dtype.itemsize != 2
            ):
                raise ValueError("ожидается непустой двумерный TIFF uint16")
            if image.shape[1] != width:
                raise ValueError(f"ширина TIFF {image.shape[1]}, ширина карты {width}")

            result, restored_count = normalize(image, parts, args.black_threshold)
            result = np.repeat(result, 1, axis=0)

            output.parent.mkdir(parents=True, exist_ok=True)
            tifffile.imwrite(output, result, photometric="minisblack")
            print(f"{path.name} → {output}; восстановлено строк: {restored_count}")
        except Exception as exc:
            print(f"{path.name}: пропущен — {exc}")


if __name__ == "__main__":
    main()
