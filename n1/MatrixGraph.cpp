#include "MatrixGraph.h"

MatrixGraph::MatrixGraph(int vertexCount) {
    matrix.resize(vertexCount, std::vector<bool>(vertexCount, false));
}

MatrixGraph::MatrixGraph(const IGraph& graph) {
    int size = graph.VerticesCount();
    matrix.resize(size, std::vector<bool>(size, false));
    for (int from = 0; from < size; ++from) {
        for (int to : graph.GetNextVertices(from)) {
            matrix[from][to] = true;
        }
    }
}

void MatrixGraph::AddEdge(int from, int to) {
    assert(from >= 0 && from < matrix.size());
    assert(to >= 0 && to < matrix.size());
    matrix[from][to] = true;
}

int MatrixGraph::VerticesCount() const {
    return matrix.size();
}

std::vector<int> MatrixGraph::GetNextVertices(int vertex) const {
    std::vector<int> result;
    for (int i = 0; i < matrix.size(); ++i) {
        if (matrix[vertex][i]) {
            result.push_back(i);
        }
    }
    return result;
}

std::vector<int> MatrixGraph::GetPrevVertices(int vertex) const {
    std::vector<int> result;
    for (int i = 0; i < matrix.size(); ++i) {
        if (matrix[i][vertex]) {
            result.push_back(i);
        }
    }
    return result;
}
