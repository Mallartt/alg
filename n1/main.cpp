#include <iostream>
#include <vector>
#include <queue>
#include <cassert>

#include "IGraph.h"
#include "ListGraph.h"
#include "MatrixGraph.h"
#include "SetGraph.h"
#include "ArcGraph.h"

void BFS(const IGraph& graph, int start, void (*visit)(int)) {
    std::vector<bool> visited(graph.VerticesCount(), false);
    std::queue<int> q;
    q.push(start);
    visited[start] = true;
    while (!q.empty()) {
        int v = q.front(); q.pop();
        visit(v);
        for (int to : graph.GetNextVertices(v)) {
            if (!visited[to]) {
                visited[to] = true;
                q.push(to);
            }
        }
    }
}

int main() {
    struct NamedGraph {
        const char* name;
        IGraph* graph;
    };

    std::vector<NamedGraph> graphs = {
        { "ListGraph",   new ListGraph(6) },
        { "MatrixGraph", new MatrixGraph(6) },
        { "SetGraph",    new SetGraph(6) },
        { "ArcGraph",    new ArcGraph(6) }
    };

    std::vector<std::pair<int,int>> edges = {
        {0,1}, {0,5}, {1,3}, {2,1},
        {3,2}, {3,4}, {4,5}, {5,3}
    };

    for (auto& ng : graphs) {
        for (auto& e : edges) {
            ng.graph->AddEdge(e.first, e.second);
        }

        std::cout << ng.name << ": BFS: ";
        BFS(*ng.graph, 0, [](int v) {
            std::cout << v << " ";
        });
        std::cout << std::endl;

        delete ng.graph;
    }

    return 0;
}
