"""
Build a schema-first Knowledge Graph from syllabus JSON files.

Outputs:
- index/knowledge_graph/nodes.jsonl
- index/knowledge_graph/edges.jsonl
- index/knowledge_graph/stats.json
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.kg_models import GraphDocument, write_jsonl
from script.knowledge_graph_parser import ProgramContext, is_program_file, load_json, parse_course_document, parse_program_document


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


logger = logging.getLogger("build_knowledge_graph")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def discover_json_files(root_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in root_dir.rglob("*.json"):
        if "frontend" in path.parts or "node_modules" in path.parts or "index" in path.parts:
            continue
        if not any(part.startswith("BM_") for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def ensure_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def build_graph(project_root: Path) -> GraphDocument:
    graph = GraphDocument()
    program_context = ProgramContext()
    json_files = discover_json_files(project_root)

    program_files = [path for path in json_files if is_program_file(str(path))]
    course_files = [path for path in json_files if not is_program_file(str(path))]

    logger.info("Discovered %s JSON files (%s program, %s course)", len(json_files), len(program_files), len(course_files))

    for path in program_files:
        logger.info("Parsing program document: %s", path.name)
        data = load_json(str(path))
        program_graph, detected_context = parse_program_document(str(path), data)
        graph.merge(program_graph)
        if not program_context.program_id:
            program_context = detected_context

    for path in course_files:
        logger.info("Parsing course document: %s", path.name)
        try:
            data = load_json(str(path))
            course_graph = parse_course_document(str(path), data, program_context=program_context)
            graph.merge(course_graph)
        except Exception as exc:
            logger.exception("Failed to parse course file %s: %s", path, exc)

    return graph


def write_stats(path: Path, graph: GraphDocument) -> None:
    label_counts = {}
    for node in graph.nodes.values():
        label_counts[node.label] = label_counts.get(node.label, 0) + 1

    edge_counts = {}
    for edge in graph.edges:
        edge_counts[edge.type] = edge_counts.get(edge.type, 0) + 1

    stats = {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "labels": label_counts,
        "edge_types": edge_counts,
    }

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)


def main() -> None:
    configure_logging()
    output_dir = PROJECT_ROOT / "index" / "knowledge_graph"
    ensure_output_dir(output_dir)

    logger.info("Building knowledge graph from project root: %s", PROJECT_ROOT)
    graph = build_graph(PROJECT_ROOT)
    nodes, edges = graph.to_jsonl_records()

    write_jsonl(str(output_dir / "nodes.jsonl"), nodes)
    write_jsonl(str(output_dir / "edges.jsonl"), edges)
    write_stats(output_dir / "stats.json", graph)

    logger.info("Knowledge graph build complete")
    logger.info("Nodes: %s", len(nodes))
    logger.info("Edges: %s", len(edges))
    logger.info("Output directory: %s", output_dir)


if __name__ == "__main__":
    main()
