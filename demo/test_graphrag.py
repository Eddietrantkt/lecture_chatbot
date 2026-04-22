"""
Quick GraphRAG inspection script.

Examples:
    python demo/test_graphrag.py --course-code MTH00014 --course-name "Giải tích 3A"
    python demo/test_graphrag.py --program-name "Toán học"
"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.graph_rag import GraphRAG


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect GraphRAG context for a course or program.")
    parser.add_argument("--course-code", default="")
    parser.add_argument("--course-name", default="")
    parser.add_argument("--section-intent", default="")
    parser.add_argument("--program-code", default="")
    parser.add_argument("--program-name", default="")
    args = parser.parse_args()

    graph = GraphRAG(Config.KNOWLEDGE_GRAPH_DIR)
    print("Graph stats:", graph.get_stats())

    if args.course_code or args.course_name:
        context = graph.build_course_context(
            args.course_code,
            course_name_hint=args.course_name or None,
            section_intent=args.section_intent or None,
        )
        print("\n=== Course Graph Context ===")
        print(context or "No course graph context found.")

    if args.program_code or args.program_name:
        context = graph.build_program_context(
            args.program_code,
            program_name_hint=args.program_name or None,
        )
        print("\n=== Program Graph Context ===")
        print(context or "No program graph context found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
