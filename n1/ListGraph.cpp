#include "ListGraph.h"

ListGraph::ListGraph(int vertexCount) {
    assert(vertexCount > 0);
    adjLists.resize(vertexCount);
    prevAdjLists.resize(vertexCount);
}

ListGraph::ListGraph(const IGraph& graph) {
    int size = graph.VerticesCount();
    adjLists.resize(size);
    prevAdjLists.resize(size);
    for (int i = 0; i < size; ++i) {
        adjLists[i] = graph.GetNextVertices(i);
        prevAdjLists[i] = graph.GetPrevVertices(i);
    }
}

void ListGraph::AddEdge(int from, int to) {
    assert(from >= 0 && from < adjLists.size());
    assert(to >= 0 && to < adjLists.size());
    adjLists[from].push_back(to);
    prevAdjLists[to].push_back(from);
}

int ListGraph::VerticesCount() const {
    return adjLists.size();
}

std::vector<int> ListGraph::GetNextVertices(int vertex) const {
    assert(vertex >= 0 && vertex < adjLists.size());
    return adjLists[vertex];
}

std::vector<int> ListGraph::GetPrevVertices(int vertex) const {
    assert(vertex >= 0 && vertex < prevAdjLists.size());
    return prevAdjLists[vertex];
}
