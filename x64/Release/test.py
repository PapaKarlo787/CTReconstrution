import numpy as np
import tigre
import tigre.algorithms as algs
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
from skimage import measure
import trimesh
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

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

rec = algs.fdk(projections, geo, angles, niter=1000, tviter=100,
	maxl2err = 1e-3 * np.linalg.norm(projections))

vol = rec.astype(np.float32)
vmin, vmax = np.percentile(vol, [1, 99.9])
threshold = np.percentile(vol, 99.3)

spacing = (
	float(geo.dVoxel[2]),
	float(geo.dVoxel[1]),
	float(geo.dVoxel[0])
)

fig = plt.figure(figsize=(9, 8))
ax = fig.add_subplot(111, projection="3d")
plt.subplots_adjust(bottom=0.15)

slider_ax = plt.axes([0.2, 0.05, 0.65, 0.03])
slider = Slider(
	slider_ax, "Порог", vmin, vmax,
	valinit=threshold
)

def update(value):
	xlim = ax.get_xlim3d()
	ylim = ax.get_ylim3d()
	zlim = ax.get_zlim3d()
	elev, azim = ax.elev, ax.azim
	ax.clear()

	try:
		verts, faces, _, _ = measure.marching_cubes(
			vol, level=value, spacing=spacing,
			step_size=1
		)
		verts = verts[:, [2, 1, 0]]
		triangles = verts[faces]

		normals = np.cross(
			triangles[:, 1] - triangles[:, 0],
			triangles[:, 2] - triangles[:, 0]
		)
		normals /= np.maximum(
			np.linalg.norm(normals, axis=1, keepdims=True), 1e-10
		)

		light = np.array([0.5, -0.5, 1.0])
		light /= np.linalg.norm(light)

		brightness = 0.25 + 0.75 * np.clip(normals @ light, 0, 1)
		base_color = np.array([1.0, 0.45, 0.05])

		colors = np.clip(brightness[:, None] * base_color, 0, 1)

		surface = Poly3DCollection(
			triangles,
			facecolors=colors,
			edgecolors="none",
			linewidths=0,
			alpha=1.0
		)
		
		ax.add_collection3d(surface)
		ax.set_facecolor("#202020")
		ax.add_collection3d(surface)

		ax.set_xlim3d(xlim)
		ax.set_ylim3d(ylim)
		ax.set_zlim3d(zlim)
		ax.view_init(elev=elev, azim=azim)
		ax.set_box_aspect((
			vol.shape[2] * spacing[2],
			vol.shape[1] * spacing[1],
			vol.shape[0] * spacing[0]
		))

	except ValueError:
		ax.set_title("Поверхности нет")

	fig.canvas.draw_idle()

slider.on_changed(update)
ax.view_init(elev=25, azim=45)
ax.set_xlim(0, vol.shape[2] * spacing[2])
ax.set_ylim(0, vol.shape[1] * spacing[1])
ax.set_zlim(0, vol.shape[0] * spacing[0])
update(threshold)
plt.show()

verts, faces, normals, _ = measure.marching_cubes(
	vol, level=slider.val, spacing=spacing
)

verts = verts[:, [2, 1, 0]]
normals = normals[:, [2, 1, 0]]

mesh = trimesh.Trimesh(
	vertices=verts,
	faces=faces,
	vertex_normals=normals,
	process=False
)
mesh.export("result.stl")
