"""Tests for serve.py MCP tool handlers (build_tool_handlers).

These exercise the per-tool dispatch logic that backs the MCP ``call_tool``
endpoint without needing the optional ``mcp`` package or a running stdio
server.
"""
from __future__ import annotations

import json

import networkx as nx
import pytest

from graphify.serve import build_tool_handlers, _communities_from_graph


def _make_digraph() -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_node("n1", label="extract", source_file="extract.py", source_location="L10",
               file_type="code", community=0)
    G.add_node("n2", label="cluster", source_file="cluster.py", source_location="L5",
               file_type="code", community=0)
    G.add_node("n3", label="build", source_file="build.py", source_location="L1",
               file_type="code", community=1)
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED")
    G.add_edge("n2", "n3", relation="imports", confidence="EXTRACTED")
    return G


@pytest.fixture
def handlers(tmp_path):
    G = _make_digraph()
    comms = _communities_from_graph(G)
    return build_tool_handlers(G, comms, str(tmp_path / "graph.json"))


# ---------------------------------------------------------------------------
# factory wiring
# ---------------------------------------------------------------------------

def test_build_tool_handlers_registers_all_tools(handlers):
    expected = {
        "query_graph", "get_node", "get_neighbors", "get_community",
        "god_nodes", "graph_stats", "shortest_path",
        "list_prs", "get_pr_impact", "triage_prs",
    }
    assert expected <= set(handlers)
    assert all(callable(h) for h in handlers.values())


# ---------------------------------------------------------------------------
# graph_stats
# ---------------------------------------------------------------------------

def test_graph_stats_reports_counts(handlers):
    out = handlers["graph_stats"]({})
    assert "Nodes: 3" in out
    assert "Edges: 2" in out
    assert "Communities:" in out
    # 1 EXTRACTED + 1 INFERRED of 2 edges = 50% each
    assert "EXTRACTED: 50%" in out
    assert "INFERRED: 50%" in out


# ---------------------------------------------------------------------------
# get_node
# ---------------------------------------------------------------------------

def test_get_node_found(handlers):
    out = handlers["get_node"]({"label": "extract"})
    assert "Node: extract" in out
    assert "ID: n1" in out
    assert "extract.py" in out
    assert "Degree: 1" in out

def test_get_node_not_found(handlers):
    assert "No node matching" in handlers["get_node"]({"label": "nonexistent"})

def test_get_node_match_by_id(handlers):
    out = handlers["get_node"]({"label": "n2"})
    assert "cluster" in out


# ---------------------------------------------------------------------------
# get_neighbors
# ---------------------------------------------------------------------------

def test_get_neighbors_lists_successors_and_predecessors(handlers):
    out = handlers["get_neighbors"]({"label": "cluster"})
    assert "Neighbors of cluster" in out
    assert "-->" in out  # cluster -> build
    assert "<--" in out  # extract -> cluster
    assert "build" in out
    assert "extract" in out

def test_get_neighbors_relation_filter(handlers):
    out = handlers["get_neighbors"]({"label": "cluster", "relation_filter": "imports"})
    assert "build" in out
    assert "extract" not in out  # the 'calls' edge is filtered out

def test_get_neighbors_not_found(handlers):
    assert "No node matching" in handlers["get_neighbors"]({"label": "zzz"})


# ---------------------------------------------------------------------------
# get_community
# ---------------------------------------------------------------------------

def test_get_community_found(handlers):
    out = handlers["get_community"]({"community_id": 0})
    assert "Community 0" in out
    assert "extract" in out
    assert "cluster" in out

def test_get_community_not_found(handlers):
    assert "not found" in handlers["get_community"]({"community_id": 999})


# ---------------------------------------------------------------------------
# god_nodes
# ---------------------------------------------------------------------------

def test_god_nodes_lists_connected(handlers):
    out = handlers["god_nodes"]({"top_n": 3})
    assert "God nodes" in out
    assert "edges" in out
    # cluster has degree 2 (in + out), should rank first
    assert "cluster" in out


# ---------------------------------------------------------------------------
# shortest_path
# ---------------------------------------------------------------------------

def test_shortest_path_found(handlers):
    out = handlers["shortest_path"]({"source": "extract", "target": "build"})
    assert "Shortest path" in out
    assert "extract" in out
    assert "build" in out

def test_shortest_path_same_node_guard(handlers):
    out = handlers["shortest_path"]({"source": "extract", "target": "extract"})
    assert "same node" in out

def test_shortest_path_unknown_source(handlers):
    out = handlers["shortest_path"]({"source": "zzz", "target": "build"})
    assert "No node matching source" in out

def test_shortest_path_unknown_target(handlers):
    out = handlers["shortest_path"]({"source": "extract", "target": "zzz"})
    assert "No node matching target" in out


# ---------------------------------------------------------------------------
# query_graph (also writes a query log)
# ---------------------------------------------------------------------------

def test_query_graph_returns_context(handlers, monkeypatch, tmp_path):
    # querylog writes under CWD; isolate it.
    monkeypatch.chdir(tmp_path)
    out = handlers["query_graph"]({"question": "extract", "depth": 2})
    assert isinstance(out, str)
    assert len(out) > 0


# ---------------------------------------------------------------------------
# unknown / error handling is delegated to call_tool, but handlers raise on
# bad input — confirm a missing required arg surfaces as an exception the
# server wraps. Here we assert the raw handler raises KeyError.
# ---------------------------------------------------------------------------

def test_get_node_missing_required_arg_raises(handlers):
    with pytest.raises(KeyError):
        handlers["get_node"]({})
