#pragma once
#include "IGraph.h"
#include <vector>
#include <cassert>

class MatrixGraph : public IGraph {
public:
    MatrixGraph(int vertexCount);
    MatrixGraph(const IGraph& graph);
    MatrixGraph(const MatrixGraph&) = default;
    MatrixGraph& operator=(const MatrixGraph&) = default;
    ~MatrixGraph() override = default;
    void AddEdge(int from, int to) override;
    int VerticesCount() const override;
    std::vector<int> GetNextVertices(int vertex) const override;
    std::vector<int> GetPrevVertices(int vertex) const override;

private:
    std::vector<std::vector<bool>> matrix;
};
