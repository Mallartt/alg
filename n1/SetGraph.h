#pragma once
#include "IGraph.h"
#include <vector>
#include <set>
#include <cassert>

class SetGraph : public IGraph {
public:
    SetGraph(int vertexCount);
    SetGraph(const IGraph& graph);

    void AddEdge(int from, int to) override;
    int VerticesCount() const override;
    std::vector<int> GetNextVertices(int vertex) const override;
    std::vector<int> GetPrevVertices(int vertex) const override;

private:
    std::vector<std::set<int>> outEdges;
    std::vector<std::set<int>> inEdges;
};
