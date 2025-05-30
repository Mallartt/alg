#pragma once
#include "IGraph.h"
#include <vector>
#include <cassert>

class ListGraph : public IGraph {
public:
    ListGraph(int vertexCount);
    ListGraph(const IGraph& graph);

    void AddEdge(int from, int to) override;
    int VerticesCount() const override;
    std::vector<int> GetNextVertices(int vertex) const override;
    std::vector<int> GetPrevVertices(int vertex) const override;

private:
    std::vector<std::vector<int>> adjLists;
    std::vector<std::vector<int>> prevAdjLists;
};
