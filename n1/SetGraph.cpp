#include "SetGraph.h"

SetGraph::SetGraph(int vertexCount) {
    outEdges.resize(vertexCount);
    inEdges.resize(vertexCount);
}

SetGraph::SetGraph(const IGraph& graph) {
    int size = graph.VerticesCount();
    outEdges.resize(size);
    inEdges.resize(size);
    for (int i = 0; i < size; ++i) {
        for (int to : graph.GetNextVertices(i)) {
            outEdges[i].insert(to);
            inEdges[to].insert(i);
        }
    }
}

void SetGraph::AddEdge(int from, int to) {
    assert(from >= 0 && from < outEdges.size());
    assert(to >= 0 && to < outEdges.size());
    outEdges[from].insert(to);
    inEdges[to].insert(from);
}

int SetGraph::VerticesCount() const {
    return outEdges.size();
}

std::vector<int> SetGraph::GetNextVertices(int vertex) const {
    return std::vector<int>(outEdges[vertex].begin(), outEdges[vertex].end());
}

std::vector<int> SetGraph::GetPrevVertices(int vertex) const {
    return std::vector<int>(inEdges[vertex].begin(), inEdges[vertex].end());
}
