#pragma once
#include <cmath>
#include <algorithm>
#include <vector>
#include <fstream>
#include <cstdint>
#include <stdexcept>

#pragma pack(push, 1)
class Vertex {
public:
    Vertex(float _x = 0.0f, float _y = 0.0f, float _z = 0.0f) : x(_x), y(_y), z(_z) { }

    void rotate(float ux, float uy, float uz) {
        {
            float cy = std::cos(ux);
            float sy = std::sin(ux);

            float ny = y * cy - z * sy;
            float nz = y * sy + z * cy;

            y = ny;
            z = nz;
        }
        {
            float cy = std::cos(uy);
            float sy = std::sin(uy);

            float nx = x * cy + z * sy;
            float nz = -x * sy + z * cy;

            x = nx;
            z = nz;
        }
        {
            float cy = std::cos(uz);
            float sy = std::sin(uz);

            float nx = x * cy - y * sy;
            float ny = x * sy + y * cy;

            x = nx;
            y = ny;
        }
    }

    void minmax(Vertex& min, Vertex& max) const {
        min.x = std::min(min.x, x);
        min.y = std::min(min.y, y);
        min.z = std::min(min.z, z);

        max.x = std::max(max.x, x);
        max.y = std::max(max.y, y);
        max.z = std::max(max.z, z);
    }

    Vertex& operator-=(const Vertex& other) {
        x -= other.x;
        y -= other.y;
        z -= other.z;
        return *this;
    }
    
    Vertex operator-() const {
        return Vertex(-x, -y, -z);
    }

    Vertex& operator+=(const Vertex& other) {
        x += other.x;
        y += other.y;
        z += other.z;
        return *this;
    }

    Vertex& operator*=(float k) {
        x *= k;
        y *= k;
        z *= k;
        return *this;
    }    

    friend Vertex operator-(Vertex first, const Vertex& other) {
        first -= other;
        return first;
    }

    friend Vertex operator+(Vertex first, const Vertex& other) {
        first += other;
        return first;
    }

    float x, y, z;
};

class Edge {
public:
	void rotate(float ux, float uy, float uz) {
		verteces[0].rotate(ux, uy, uz);
		verteces[1].rotate(ux, uy, uz);
		verteces[2].rotate(ux, uy, uz);
		verteces[3].rotate(ux, uy, uz);
	}

	void scale(float k) {
		verteces[1] *= k;
		verteces[2] *= k;
		verteces[3] *= k;
	}

    void addToMass(Vertex& mass) const {
        mass += verteces[1];
        mass += verteces[2];
        mass += verteces[3];
    }

    void moveBy(const Vertex& offset) {
        verteces[1] -= offset;
        verteces[2] -= offset;
        verteces[3] -= offset;
    }

    void minmax(Vertex& min, Vertex& max) const {
        verteces[1].minmax(min, max);
        verteces[2].minmax(min, max);
        verteces[3].minmax(min, max);
    }

    void translate(const Vertex& offset) {
        verteces[1] += offset;
        verteces[2] += offset;
        verteces[3] += offset;
    }

    const Vertex& vertex(int i) const {
        return verteces[i];
    }

    bool intersectZ(float x, float y, float& z) const {
        const Vertex& a = verteces[1];
        const Vertex& b = verteces[2];
        const Vertex& c = verteces[3];

        const float eps = 1e-6f;

        float minx = std::min(a.x, std::min(b.x, c.x));
        float maxx = std::max(a.x, std::max(b.x, c.x));
        float miny = std::min(a.y, std::min(b.y, c.y));
        float maxy = std::max(a.y, std::max(b.y, c.y));

        if (x < minx - eps || x > maxx + eps || y < miny - eps || y > maxy + eps) {
            return false;
        }

        float den =
            (b.y - c.y) * (a.x - c.x) +
            (c.x - b.x) * (a.y - c.y);

        if (std::fabs(den) < eps) {
            return false;
        }

        float u =
            ((b.y - c.y) * (x - c.x) +
                (c.x - b.x) * (y - c.y)) / den;

        float v =
            ((c.y - a.y) * (x - c.x) +
                (a.x - c.x) * (y - c.y)) / den;

        float w = 1.0f - u - v;

        if (u < -eps || v < -eps || w < -eps) {
            return false;
        }

        z = u * a.z + v * b.z + w * c.z;
        return true;
    }



private:
	Vertex verteces[4];
	uint16_t attr;
};
#pragma pack(pop)


class STL {
public:
    STL() = default;

	STL(std::string fn) {
        std::ifstream file(fn, std::ios::binary);

        file.seekg(80, std::ios_base::_Seekbeg);

        uint32_t count = 0;
        file.read(reinterpret_cast<char*>(&count), sizeof(count));
        edges.resize(count);
        file.read(reinterpret_cast<char*>(edges.data()), static_cast<std::streamsize>(count * sizeof(Edge)));
	}

	void rotate(float ux, float uy, float uz) {
		for (auto& e : edges) {
			e.rotate(ux, uy, uz);
		}
	}

	void scale(float k) {
		for (auto& e : edges) {
			e.scale(k);
		}
	}

    void center() {
        if (edges.empty()) return;

        Vertex min = edges[0].vertex(1);
        Vertex max = min;

        for (const Edge& edge : edges) edge.minmax(min, max);

        Vertex center((min.x + max.x) * 0.5f, (min.y + max.y) * 0.5f, (min.z + max.z) * 0.5f);

        for (Edge& edge : edges) edge.moveBy(-center);
    }

    void minmax(Vertex& min, Vertex& max) {
        if (edges.empty()) {
            return;
        }

        edges[0].minmax(min, max);

        for (size_t i = 1; i < edges.size(); ++i) {
            edges[i].minmax(min, max);
        }
    }

    void translate(const Vertex& offset) {
        for (Edge& edge : edges) {
            edge.translate(offset);
        }
    }

    void append(const STL& model) {
        edges.insert(edges.end(), model.edges.begin(), model.edges.end());
    }

    bool empty() const {
        return edges.empty();
    }

    float scaleToSize(float targetSize) {
        Vertex min = edges[0].vertex(1);
        Vertex max = min;

        for (const Edge& edge : edges) {
            edge.minmax(min, max);
        }

        const float currentSize = std::max({ max.x - min.x, max.y - min.y, max.z - min.z });
        const float factor = targetSize / currentSize;
        const Vertex center((min.x + max.x) * 0.5f, (min.y + max.y) * 0.5f, (min.z + max.z) * 0.5f);

        for (Edge& edge : edges) {
            edge.moveBy(center);
            edge.scale(factor);
            edge.moveBy(-center);
        }

        return factor;
    }

    const std::vector<Edge>& getEdges() const {
        return edges;
    }

private:
	std::vector<Edge> edges;
};