import argparse
from pathlib import Path

import numpy as np
import tifffile

N_SHOTS = 4
STRIP_WIDTH = 64


def main():
    parser = argparse.ArgumentParser(
        description="Карта горизонтального рельефа и графики профилей."
    )
    parser.add_argument("input", type=Path, help="Входной 16-битный TIFF")
    parser.add_argument(
        "--window", type=int, default=31,
        help="Число значений в центральном окне (по умолчанию 31)",
    )
    parser.add_argument("-o", "--output", type=Path, help="Выходной CSV")
    parser.add_argument(
        "--no-show", action="store_true",
        help="Сохранить только CSV, не открывая окна",
    )
    args = parser.parse_args()

    image = tifffile.imread(args.input)
    if image.ndim != 2 or image.dtype.kind != "u" or image.dtype.itemsize != 2:
        parser.error("Ожидается одно двумерное изображение uint16.")

    height, width = image.shape
    if width == 0 or width % (N_SHOTS * STRIP_WIDTH) != 0:
        parser.error("Ширина должна быть кратна 4 × 64.")
    if not 1 <= args.window <= height:
        parser.error(f"--window должен быть от 1 до {height}.")

    shot_width = width // N_SHOTS
    x = np.arange(shot_width)
    start = (height - args.window) // 2
    stop = start + args.window
    output = args.output or args.input.with_name(f"{args.input.stem}_relief.csv")

    if not args.no_show:
        import matplotlib.pyplot as plt

        vmin = int(image.min())
        vmax = max(int(image.max()), vmin + 1)

        fig_sorted, sorted_axes = plt.subplots(
            2, 2, figsize=(13, 8), layout="constrained"
        )
        fig_sorted.suptitle("Отсортированные снимки · медианное окно между линиями")

        fig_profiles, profile_axes = plt.subplots(
            2, 2, figsize=(13, 8), layout="constrained"
        )
        fig_profiles.suptitle("Горизонтальный профиль до и после коррекции")

        plt.show(block=False)
        plt.pause(0.05)

    rows = []
    for i, shot in enumerate(np.split(image, N_SHOTS, axis=1)):
        sorted_pixels = np.sort(shot, axis=0)
        profile = sorted_pixels[start:stop].mean(axis=0)
        median = np.median(profile)
        if median == 0:
            parser.error(f"Снимок {i + 1}: медиана профиля равна нулю.")

        coefficients = profile / median
        rows.append(np.column_stack((
            np.full(shot_width, i + 1),
            x,
            i * shot_width + x,
            coefficients,
        )))

        if not args.no_show:
            if plt.fignum_exists(fig_sorted.number):
                ax = sorted_axes.flat[i]
                ax.imshow(
                    sorted_pixels, cmap="gray", vmin=vmin, vmax=vmax,
                    aspect="auto", interpolation="nearest", origin="upper",
                )
                ax.axhline(start - 0.5, color="orange")
                ax.axhline(stop - 0.5, color="orange")
                ax.set(
                    title=f"Снимок {i + 1}",
                    xlabel="Столбец",
                    ylabel="Позиция после сортировки",
                )
                fig_sorted.canvas.draw_idle()

            if plt.fignum_exists(fig_profiles.number):
                # Нулевой коэффициент: деление не определено, оставляем разрыв.
                corrected = np.full_like(profile, np.nan)
                np.divide(profile, coefficients, out=corrected, where=coefficients > 0)

                ax = profile_axes.flat[i]
                ax.axvspan(
                    shot_width - STRIP_WIDTH - 0.5, shot_width - 0.5,
                    color="gray", alpha=0.15,
                )
                ax.plot(x, profile, color="tab:blue")
                ax.plot(
                    x, corrected, "--", color="tab:orange", linewidth=2,
                )
                ax.set(
                    title=f"Снимок {i + 1}",
                    xlim=(-0.5, shot_width - 0.5),
                )
                ax.grid(alpha=0.2)
                ax.legend()
                fig_profiles.canvas.draw_idle()

            if plt.get_fignums():
                plt.pause(0.05)

    np.savetxt(
        output,
        np.concatenate(rows, axis=0),
        delimiter=",",
        header="shot,x_in_shot,x_in_image,coefficient",
        comments="",
        fmt=["%d", "%d", "%d", "%.12g"],
    )
    print(f"Коэффициенты сохранены: {output}")

    if not args.no_show and plt.get_fignums():
        plt.show(block=True)


if __name__ == "__main__":
    main()
