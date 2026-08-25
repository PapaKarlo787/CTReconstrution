#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <sstream>
#include <omp.h>
#include <functional>

#include "stl.h"
#include "bmp.h"
#include "scene.h"

struct Snapshot {
	std::string filename;
	std::vector<float> image;
};

std::vector<float> scanSquareImageFast(STL& model, int steps, const Vertex& frameMin, const Vertex& frameMax) {
	const float sx = frameMax.x - frameMin.x;
	const float sy = frameMax.y - frameMin.y;
	const float size = std::max(sx, sy);
	const float cx = (frameMin.x + frameMax.x) * 0.5f;
	const float cy = (frameMin.y + frameMax.y) * 0.5f;
	const float startX = cx - size * 0.5f;
	const float startY = cy - size * 0.5f;
	const float step = size / static_cast<float>(steps);

	std::vector<std::vector<float>> zbuffer(steps * steps);

	auto clampInt = [](int v, int a, int b) { return std::max(a, std::min(v, b)); };

	const auto& edges = model.getEdges();

	for (int e = 0; e < static_cast<int>(edges.size()); ++e) {
		const Edge& edge = edges[e];
		const Vertex& a = edge.vertex(1);
		const Vertex& b = edge.vertex(2);
		const Vertex& c = edge.vertex(3);
		constexpr float eps = 1e-6f;
	
		const float den = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);
		if (std::fabs(den) < eps) continue;

		const float minx = std::min({ a.x, b.x, c.x });
		const float maxx = std::max({ a.x, b.x, c.x });
		const float miny = std::min({ a.y, b.y, c.y });
		const float maxy = std::max({ a.y, b.y, c.y });
		int ix0 = static_cast<int>((minx - startX) / step) - 1;
		int ix1 = static_cast<int>((maxx - startX) / step) + 1;
		int iy0 = static_cast<int>((miny - startY) / step) - 1;
		int iy1 = static_cast<int>((maxy - startY) / step) + 1;

		ix0 = clampInt(ix0, 0, steps - 1);
		ix1 = clampInt(ix1, 0, steps - 1);
		iy0 = clampInt(iy0, 0, steps - 1);
		iy1 = clampInt(iy1, 0, steps - 1);

		for (int j = iy0; j <= iy1; ++j) {
			const float y = startY + (j + 0.5f) * step;

			for (int i = ix0; i <= ix1; ++i) {
				const float x = startX + (i + 0.5f) * step;
				const float u = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / den;
				const float v = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / den;
				const float w = 1.0f - u - v;

				if (u < -eps || v < -eps || w < -eps) {
					continue;
				}
				zbuffer[j * steps + i].push_back(u * a.z + v * b.z + w * c.z);
			}
		}
	}

	std::vector<float> image;
	image.reserve(steps * steps);

	for (auto& zs : zbuffer) {
		std::sort(zs.begin(), zs.end());

		float thickness = 0.0f;
		for (size_t i = 0; i + 1 < zs.size(); i += 2) {
			thickness += zs[i + 1] - zs[i];
		}
		image.push_back(thickness);
	}

	return image;
}

void saveImageSharedScale(const Snapshot& snapshot, int width, int height, float globalMaxThickness) {
	const size_t pos = snapshot.filename.find_last_of('.');
	const std::string extension = snapshot.filename.substr(pos + 1);

	if (extension == "bmp") {
		std::vector<uint8_t> raw(snapshot.image.size());

		for (size_t i = 0; i < snapshot.image.size(); ++i) {
			float normalized = snapshot.image[i] / globalMaxThickness;
			raw[i] = static_cast<uint8_t>(std::lround((1.0f - normalized) * 255.0f));
		}

		saveBMP(snapshot.filename.c_str(), raw, width, height);
	}
	else if (extension == "tif" || extension == "tiff") {
		std::vector<uint16_t> raw(snapshot.image.size());
		for (size_t i = 0; i < snapshot.image.size(); ++i) {
			float normalized = snapshot.image[i] / globalMaxThickness;
			raw[i] = static_cast<uint16_t>(std::lround((1.0f - normalized) * 65535.0f));
		}
		saveTIFF16(snapshot.filename.c_str(), raw, width, height);
	}
	else {
		std::cerr << "Unsupported output format: " << snapshot.filename << std::endl;
	}
}

std::string makeSnapshotFilename(int index, char axis, const std::string& outputName) {
	std::ostringstream stream;
	stream << "r_" << std::setw(3) << std::setfill('0') << index << axis << "_" << outputName;
	return stream.str();
}

int main(int argc, char** argv)
{
#include <iostream>
#include <string>
#include <vector>

	int outputPos = -1;

	for (int i = 1; i < argc; ++i) {
		if (std::string(argv[i]) == "-o") {
			outputPos = i;
			break;
		}
	}

	const int oargc = outputPos >= 0 ? argc - outputPos - 1 : 0;

	if (outputPos < 2 || (oargc != 1 && oargc != 3)) {
		std::cerr << "usage:\n" << "  " << argv[0] << " in1.stl [in2.stl ...] -o out.tiff [snapshots axis]\n";
		return -1;
	}

	std::vector<STL> models;
	models.reserve(outputPos - 1);
	argv++;
	for (int i = 1; i < outputPos; ++i) {
		models.emplace_back(STL(argv[0]));
		models.back().scaleToSize(5);
		argv++;
	}
	argv++;

	const int imageSize = 512;
	STL scene = arrangeModels(models);
	Vertex mn;
	Vertex mx;
	scene.minmax(mn, mx);

	const float ax = std::max(std::fabs(mn.x), std::fabs(mx.x));
	const float ay = std::max(std::fabs(mn.y), std::fabs(mx.y));
	const float az = std::max(std::fabs(mn.z), std::fabs(mx.z));
	const float r = std::sqrt(ax * ax + ay * ay + az * az);

	const Vertex cubeMin(-r, -r, -r);
	const Vertex cubeMax(r, r, r);
	std::vector<Snapshot> snapshots;

	if (oargc == 3) {
		const int snapshotCount = std::atoi(argv[1]);
		const char axis = argv[2][0];
		const float angle = 2.0f * 3.14159265358979323846f / snapshotCount;

		omp_set_dynamic(0);
		const int threadCount = omp_get_max_threads();
		std::cout << "OpenMP threads: " << threadCount << std::endl;
		std::vector<STL> scenes(threadCount, scene);
		snapshots.resize(snapshotCount);

		std::function<void(STL&, float)> rotateModel;

		if (axis == 'x') {
			rotateModel = [](STL& model, float value) { model.rotate(value, 0.0f, 0.0f); };
		}
		else if (axis == 'y') {
			rotateModel = [](STL& model, float value) { model.rotate(0.0f, value, 0.0f); };
		}
		else if (axis == 'z') {
			rotateModel = [](STL& model, float value) { model.rotate(0.0f, 0.0f, value); };
		}
		else {
			std::cerr << "Ungle must be in [x y z]" << std::endl;
			return -1;
		}

#pragma omp parallel num_threads(threadCount)
		{
			const int threadId = omp_get_thread_num();
			const int actualThreadCount = omp_get_num_threads();
			const int begin = snapshotCount * threadId / actualThreadCount;
			const int end = snapshotCount * (threadId + 1) / actualThreadCount;

			STL& localModel = scenes[threadId];
			rotateModel(localModel, angle * begin);

			for (int i = begin; i < end; ++i) {
				snapshots[i] = { makeSnapshotFilename(i, axis, argv[0]),  scanSquareImageFast(localModel, imageSize, cubeMin, cubeMax) };
				rotateModel(localModel, angle);
			}
		}
	}
	else {
		Snapshot snapshot;

		snapshot.filename = "r_" + std::string(argv[2]);
		snapshot.image = scanSquareImageFast(scene, imageSize, cubeMin, cubeMax);
		snapshots.push_back(std::move(snapshot));
	}

	float globalMaxThickness = 0.0f;

	for (const Snapshot& snapshot : snapshots) {
		const float imageMax = *std::max_element(snapshot.image.begin(), snapshot.image.end());
		globalMaxThickness = std::max(globalMaxThickness, imageMax);
	}

#pragma omp parallel for
	for (int i = 0; i < snapshots.size(); ++i) {
		saveImageSharedScale(snapshots[i], imageSize, imageSize, globalMaxThickness);
	}

	return 0;
}