"""Tests for graphify/tree_html.py - D3 collapsible-tree HTML view of a graph."""
from __future__ import annotations

import json
from pathlib import Path

from graphify.tree_html import (
    DEFAULT_MAX_CHILDREN,
    _common_root,
    _make_truncation_leaf,
    build_tree,
    emit_html,
    write_tree_html,
)


# ---------------------------------------------------------------------------
# _common_root
# ---------------------------------------------------------------------------

def test_common_root_empty():
    assert _common_root([]) == ""

def test_common_root_blank_entries_only():
    assert _common_root(["", ""]) == ""

def test_common_root_single_path():
    # The common root of a single file is its parent directory chain.
    assert _common_root(["src/pkg/mod.py"]) == str(Path("src/pkg/mod.py"))

def test_common_root_shared_prefix():
    root = _common_root(["src/pkg/a.py", "src/pkg/b.py", "src/pkg/sub/c.py"])
    assert root == str(Path("src/pkg"))

def test_common_root_no_shared_prefix():
    assert _common_root(["a/x.py", "b/y.py"]) == ""


# ---------------------------------------------------------------------------
# _make_truncation_leaf
# ---------------------------------------------------------------------------

def test_make_truncation_leaf():
    leaf = _make_truncation_leaf(7)
    assert leaf == {"name": "(+7 more)", "total_count": 7, "children": []}


# ---------------------------------------------------------------------------
# build_tree
# ---------------------------------------------------------------------------

def test_build_tree_empty_graph():
    tree = build_tree({"nodes": []})
    assert tree == {"name": "(empty graph)", "total_count": 0, "children": []}

def test_build_tree_ignores_nodes_without_source_file():
    tree = build_tree({"nodes": [{"id": "x", "label": "x"}]})
    assert tree["name"] == "(empty graph)"

def test_build_tree_basic_hierarchy():
    graph = {
        "nodes": [
            {"id": "a", "label": "Alpha", "source_file": "src/pkg/a.py"},
            {"id": "b", "label": "Beta", "source_file": "src/pkg/b.py"},
            {"id": "c", "label": "Gamma", "source_file": "src/pkg/sub/c.py"},
        ]
    }
    tree = build_tree(graph)
    # total_count propagates to the leaf count (3 symbols across the tree).
    assert tree["total_count"] == 3
    # Every node has the required keys.
    def _check(node):
        assert {"name", "total_count", "children"} <= set(node)
        for child in node["children"]:
            _check(child)
    _check(tree)

def test_build_tree_uses_project_label():
    graph = {"nodes": [{"id": "a", "label": "Alpha", "source_file": "src/a.py"}]}
    tree = build_tree(graph, project_label="MyProject")
    assert tree["name"] == "MyProject"

def test_build_tree_skips_redundant_filename_node():
    # A node whose label equals the file name and is file_type=code is dropped.
    graph = {
        "nodes": [
            {"id": "f", "label": "a.py", "source_file": "src/a.py", "file_type": "code"},
            {"id": "g", "label": "real_symbol", "source_file": "src/a.py", "file_type": "code"},
        ]
    }
    tree = build_tree(graph)
    names = json.dumps(tree)
    assert "real_symbol" in names
    # the redundant "a.py" *symbol* leaf should not appear as a child symbol
    # (the file node itself is still named a.py).
    def _symbol_leaves(node, acc):
        for c in node["children"]:
            if not c["children"]:
                acc.append(c["name"])
            _symbol_leaves(c, acc)
        return acc
    leaves = _symbol_leaves(tree, [])
    assert "real_symbol" in leaves
    assert leaves.count("a.py") == 0

def test_build_tree_truncates_wide_directories():
    syms = [
        {"id": f"s{i}", "label": f"sym{i:03d}", "source_file": "src/wide.py"}
        for i in range(10)
    ]
    tree = build_tree({"nodes": syms}, max_children=3)
    # Find the file node and assert truncation leaf present.
    blob = json.dumps(tree)
    assert "(+7 more)" in blob

def test_build_tree_explicit_root():
    graph = {"nodes": [{"id": "a", "label": "Alpha", "source_file": "src/pkg/a.py"}]}
    tree = build_tree(graph, root="src")
    assert tree["name"] == "src"


# ---------------------------------------------------------------------------
# emit_html
# ---------------------------------------------------------------------------

def test_emit_html_contains_data_and_d3():
    tree = {"name": "root", "total_count": 1, "children": []}
    html = emit_html(tree, title="T", header="H")
    assert "<!DOCTYPE html>" in html
    assert "d3js.org/d3.v7" in html
    assert "const initialJsonData =" in html
    assert "<title>T</title>" in html
    assert "<h1>H</h1>" in html

def test_emit_html_escapes_title_and_header():
    tree = {"name": "root", "total_count": 0, "children": []}
    html = emit_html(tree, title="<script>x</script>", header="<b>h</b>")
    assert "<title><script>x</script></title>" not in html
    assert "&lt;script&gt;" in html

def test_emit_html_escapes_script_close_in_data():
    # A label containing </script> must not break out of the <script> blob.
    tree = {"name": "</script><img>", "total_count": 0, "children": []}
    html = emit_html(tree, title="t", header="h")
    assert "</script><img>" not in html.split("const initialJsonData")[1].split("\n")[0]
    assert "<\\/script>" in html


# ---------------------------------------------------------------------------
# write_tree_html (end-to-end)
# ---------------------------------------------------------------------------

def test_write_tree_html_roundtrip(tmp_path):
    graph = {
        "nodes": [
            {"id": "a", "label": "Alpha", "source_file": "src/a.py"},
            {"id": "b", "label": "Beta", "source_file": "src/b.py"},
        ]
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    out = tmp_path / "out" / "tree.html"
    result = write_tree_html(graph_path, out)
    assert result == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Alpha" in content
    assert "Beta" in content

def test_write_tree_html_default_max_children_is_200():
    assert DEFAULT_MAX_CHILDREN == 200

def test_write_tree_html_respects_project_label(tmp_path):
    graph = {"nodes": [{"id": "a", "label": "Alpha", "source_file": "src/a.py"}]}
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    out = tmp_path / "tree.html"
    write_tree_html(graph_path, out, project_label="CoolProj")
    assert "CoolProj" in out.read_text(encoding="utf-8")
