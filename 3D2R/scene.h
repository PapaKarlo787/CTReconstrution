#pragma once
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>
#include "stl.h"

STL arrangeModels(std::vector<STL> models, float gap = 0.1f) {
    struct Item {
        size_t index;
        Vertex min;
        float width, height;
    };

    std::vector<Item> items;
    float area = 0.0f;
    float maxWidth = 0.0f;

    for (size_t i = 0; i < models.size(); ++i) {
        const auto& edges = models[i].getEdges();
        if (edges.empty()) continue;

        Vertex min = edges[0].vertex(1);
        Vertex max = min;

        for (const Edge& edge : edges) edge.minmax(min, max);

        float width = max.x - min.x;
        float height = max.z - min.z;

        items.push_back({ i, min, width, height });
        area += width * height;
        maxWidth = std::max(maxWidth, width);
    }

    std::sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
        return a.height > b.height;
        });

    float targetWidth = std::max(maxWidth, std::sqrt(area));
    float x = 0.0f;
    float z = 0.0f;
    float rowHeight = 0.0f;

    STL scene;
    auto& sceneEdges = const_cast<std::vector<Edge>&>(scene.getEdges());

    for (const Item& item : items) {
        if (x > 0.0f && x + item.width > targetWidth) {
            x = 0.0f;
            z += rowHeight + gap;
            rowHeight = 0.0f;
        }

        STL& model = models[item.index];
        auto& edges = const_cast<std::vector<Edge>&>(model.getEdges());
        Vertex offset(item.min.x - x, item.min.y, item.min.z - z);

        for (Edge& edge : edges) edge.moveBy(offset);

        sceneEdges.insert(sceneEdges.end(), edges.begin(), edges.end());

        x += item.width + gap;
        rowHeight = std::max(rowHeight, item.height);
    }

    return scene;
}