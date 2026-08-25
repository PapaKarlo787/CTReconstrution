import numpy as np
import tigre
import tigre.algorithms as algs
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
from skimage import measure
import trimesh
import pyvista as pv

folder = Path("projs")
files = sorted(folder.glob("*.tiff"))

imgs = []
for f in files:
	img = Image.open(f).convert("F")   # grayscale float
	img = np.array(img, dtype=np.float32)
	imgs.append(img)

projections = 1.0 - np.stack(imgs, axis=0).astype(np.float32) / 65535.0
N, H, W = projections.shape

nVoxel = np.array([256, 256, 256], dtype=np.int32)

geo = tigre.geometry(
	mode="parallel",
	nVoxel=nVoxel
)

geo.nVoxel = nVoxel
geo.sVoxel = np.array([512.0, 512.0, 512.0], dtype=np.float32)
geo.dVoxel = geo.sVoxel / geo.nVoxel

geo.nDetector = np.array([W, H], dtype=np.int32)
geo.dDetector = np.array([0.8, 0.8], dtype=np.float32)
geo.sDetector = geo.nDetector * geo.dDetector

geo.offOrigin = np.array([0.0, 0.0, 0.0], dtype=np.float32)
geo.offDetector = np.array([0.0, 0.0], dtype=np.float32)
angles = -np.linspace(0, 2*np.pi, N, endpoint=False)

rec = algs.fdk(projections, geo, angles, niter=1, tviter=1)


vol = rec.astype(np.float32)

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

vmin, vmax = np.percentile(vol, [1, 99.9])
level = [float(np.percentile(vol, 99.3))]
actor = [None]

plotter = pv.Plotter()
plotter.set_background("#202020")

def update(value):
	level[0] = float(value)

	mesh = grid.contour(
		[level[0]],
		scalars="values",
		method="flying_edges"
	)

	if actor[0] is not None:
		plotter.remove_actor(actor[0], reset_camera=False, render=False)
	plotter.set_background("green")
	actor[0] = plotter.add_mesh(
		mesh,
		color="red",
		smooth_shading=True,
		show_edges=False,
		specular=0.3,
		reset_camera=False,
		render=False
	)

	plotter.render()

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
result = grid.contour(
	[level[0]],
	scalars="values",
	method="flying_edges"
)
result.save("result.stl")

print("Сохранено: result.stl")
