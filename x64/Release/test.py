import numpy as np
import tigre
import tigre.algorithms as algs
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import pyvista as pv


folder = Path("projs")
files = sorted(folder.glob("*.tiff"))

if not files:
    raise RuntimeError("В папке projs не найдены TIFF-файлы")

imgs = [
    np.asarray(Image.open(file).convert("F"), dtype=np.float32)
    for file in files
]

projections = 1.0 - np.stack(imgs) / 65535.0
projections = projections.astype(np.float32)

N, H, W = projections.shape


nVoxel = np.array([256, 256, 256], dtype=np.int32)

geo = tigre.geometry(mode="parallel", nVoxel=nVoxel)

geo.nVoxel = nVoxel
geo.sVoxel = np.array([512.0, 512.0, 512.0], dtype=np.float32)
geo.dVoxel = geo.sVoxel / geo.nVoxel

geo.nDetector = np.array([H, W], dtype=np.int32)
geo.dDetector = np.array([0.8, 0.8], dtype=np.float32)
geo.sDetector = geo.nDetector * geo.dDetector

geo.offOrigin = np.zeros(3, dtype=np.float32)
geo.offDetector = np.zeros(2, dtype=np.float32)

angles = -np.linspace(
    0, 2 * np.pi, N, endpoint=False, dtype=np.float32
)

vol = algs.fdk(projections, geo, angles).astype(np.float32)
vol = np.nan_to_num(vol)

nz, ny, nx = vol.shape

dz, dy, dx = (
    float(geo.dVoxel[2]),
    float(geo.dVoxel[1]),
    float(geo.dVoxel[0])
)

grid = pv.ImageData(
    dimensions=(nx, ny, nz),
    spacing=(dx, dy, dz)
)

grid.point_data["values"] = vol.ravel(order="C")


vmin, vmax = np.percentile(vol, [1.0, 99.9])
level = [float(np.percentile(vol, 99.3))]

MIN_CELLS = 500
MOVE_STEP = 2.0

parts = []
actors = []
colors = []
offsets = []
selected = [0]
selection_box = [None]

plotter = pv.Plotter()
plotter.set_background("#202020")

cmap = plt.get_cmap("turbo")


def show_selection():
    if not actors:
        return

    i = selected[0]

    for j, current_actor in enumerate(actors):
        prop = current_actor.GetProperty()
        prop.SetColor(*colors[j])
        prop.EdgeVisibilityOff()

    prop = actors[i].GetProperty()
    prop.SetColor(1.0, 1.0, 0.0)
    prop.EdgeVisibilityOn()
    prop.SetEdgeColor(1.0, 0.0, 0.0)
    prop.SetLineWidth(2.0)

    if selection_box[0] is not None:
        plotter.remove_actor(
            selection_box[0],
            reset_camera=False,
            render=False
        )

    box = pv.Box(bounds=actors[i].GetBounds())

    selection_box[0] = plotter.add_mesh(
        box,
        style="wireframe",
        color="cyan",
        line_width=4,
        pickable=False,
        reset_camera=False,
        render=False
    )

    x, y, z = offsets[i]

    plotter.add_text(
        f"ВЫБРАН ОБЪЕКТ: {i + 1}/{len(actors)}\n"
        f"Смещение: X={x:.1f}, Y={y:.1f}, Z={z:.1f}",
        name="selection",
        position="upper_left",
        color="yellow",
        font_size=13
    )

    plotter.render()


def select_object(index):
    if not actors:
        return

    selected[0] = index % len(actors)
    show_selection()

def move_object(dx=0.0, dy=0.0, dz=0.0):
    if not actors:
        return

    i = selected[0]

    offsets[i] += MOVE_STEP * np.array(
        [dx, dy, dz],
        dtype=float
    )

    actors[i].SetPosition(*offsets[i])

    show_selection()

def update(value):
    if selection_box[0] is not None:
        plotter.remove_actor(
            selection_box[0],
            reset_camera=False,
            render=False
        )
        selection_box[0] = None
    level[0] = float(value)

    # Удаляем предыдущие актёры
    for current_actor in actors:
        plotter.remove_actor(
            current_actor,
            reset_camera=False,
            render=False
        )

    actors.clear()
    parts.clear()
    colors.clear()
    offsets.clear()

    surface = grid.contour(
        [level[0]],
        scalars="values",
        method="flying_edges"
    )

    if surface.n_cells == 0:
        plotter.add_text(
            "Поверхность отсутствует",
            name="selection",
            position="upper_left"
        )
        plotter.render()
        return

    components = list(surface.split_bodies())
    components.sort(key=lambda item: item.n_cells, reverse=True)

    components = [
        item.extract_surface(algorithm="dataset_surface").triangulate()	
        for item in components
        if item.n_cells >= MIN_CELLS
    ]

    for i, part in enumerate(components):
        color = cmap(i / max(1, len(components) - 1))[:3]

        current_actor = plotter.add_mesh(
            part,
            color=color,
            smooth_shading=True,
            show_edges=False,
            specular=0.25,
            reset_camera=False,
            render=False
        )

        parts.append(part)
        actors.append(current_actor)
        colors.append(color)
        offsets.append(np.zeros(3, dtype=float))

    print(f"Найдено компонентов: {len(parts)}")

    if actors:
        select_object(0)
    else:
        plotter.add_text(
            "Нет компонентов нужного размера",
            name="selection",
            position="upper_left"
        )
        plotter.render()


plotter.add_key_event("Tab", lambda: select_object(selected[0] + 1))

plotter.add_key_event("a", lambda: move_object(dx=-1))
plotter.add_key_event("d", lambda: move_object(dx=1))

plotter.add_key_event("s", lambda: move_object(dy=-1))
plotter.add_key_event("w", lambda: move_object(dy=1))

plotter.add_key_event("f", lambda: move_object(dz=-1))
plotter.add_key_event("r", lambda: move_object(dz=1))

plotter.add_text(
    "Tab — change\n"
    "A/D — X\n"
    "S/W — Y\n"
    "Q/E — Z",
    position="lower_left",
    font_size=10
)


update(level[0])
plotter.reset_camera()

plotter.add_slider_widget(
    update,
    rng=(float(vmin), float(vmax)),
    value=level[0],
    title="Порог",
    interaction_event="end"
)

plotter.show()

output_folder = Path("result_parts")
output_folder.mkdir(exist_ok=True)

if parts:
    for i, (part, offset) in enumerate(zip(parts, offsets), start=1):
        moved = part.copy()
        moved.translate(offset, inplace=True)
        moved = moved.triangulate()

        output_path = output_folder / f"volume_{i:03d}.stl"
        moved.save(output_path)

        print(f"Сохранено: {output_path} ({moved.n_cells} полигонов)")
else:
    print("Нет объёмов для сохранения")
