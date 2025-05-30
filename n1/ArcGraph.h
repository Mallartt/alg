#pragma once
#include "IGraph.h"
#include <vector>
#include <cassert>

class ArcGraph : public IGraph {
public:
    ArcGraph(int vertexCount);
    ArcGraph(const IGraph& graph);
    ArcGraph(const ArcGraph&) = default;
    ArcGraph& operator=(const ArcGraph&) = default;
    ~ArcGraph() override = default;
    void AddEdge(int from, int to) override;
    int VerticesCount() const override;
    std::vector<int> GetNextVertices(int vertex) const override;
    std::vector<int> GetPrevVertices(int vertex) const override;

private:
    int vertexCount;
    std::vector<std::pair<int, int>> edges;
};
