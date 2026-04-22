"""
GraphRAG runtime utilities for syllabus Knowledge Graph retrieval.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger("GraphRAG")


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFD", (value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class GraphNodeRecord:
    node_id: str
    label: str
    properties: Dict[str, Any]


@dataclass(frozen=True)
class GraphEdgeRecord:
    source: str
    target: str
    edge_type: str
    properties: Dict[str, Any]


class GraphRAG:
    CORE_COURSE_RELATIONS: Set[str] = {
        "OFFERS",
        "BELONGS_TO_PROGRAM",
        "REQUIRES",
        "PRECEDED_BY",
        "COREQUISITE_WITH",
    }
    COURSE_RELATION_GROUPS: Dict[str, Set[str]] = {
        "lecturer": {"TAUGHT_BY", "AFFILIATED_WITH", "OFFERS"},
        "grading": {"HAS_ASSESSMENT", "ASSESSES_TOPIC"},
        "materials": {"USES_MATERIAL"},
        "objectives": {"HAS_OBJECTIVE", "HAS_CLO", "ALIGNS_WITH_OBJECTIVE", "ALIGNS_WITH_PLO", "HAS_PLO"},
        "schedule": {"HAS_TOPIC", "SUPPORTS_CLO", "ASSESSES_TOPIC"},
        "dependency": {"REQUIRES", "PRECEDED_BY", "COREQUISITE_WITH"},
    }
    DEFAULT_COURSE_RELATIONS: Set[str] = {
        "TAUGHT_BY",
        "OFFERS",
        "BELONGS_TO_PROGRAM",
        "REQUIRES",
        "PRECEDED_BY",
        "COREQUISITE_WITH",
        "HAS_CLO",
        "HAS_ASSESSMENT",
        "HAS_TOPIC",
        "USES_MATERIAL",
    }
    DEFAULT_MAJOR_RELATIONS: Set[str] = {"HAS_PLO", "BELONGS_TO_PROGRAM", "OFFERS"}

    def __init__(self, knowledge_graph_dir: str):
        self.knowledge_graph_dir = knowledge_graph_dir
        self.nodes: Dict[str, GraphNodeRecord] = {}
        self.out_edges: Dict[str, List[GraphEdgeRecord]] = defaultdict(list)
        self.in_edges: Dict[str, List[GraphEdgeRecord]] = defaultdict(list)
        self.course_ids: Set[str] = set()
        self.program_ids: Set[str] = set()
        self.available = False

        self._load()

    def _load(self) -> None:
        nodes_path = os.path.join(self.knowledge_graph_dir, "nodes.jsonl")
        edges_path = os.path.join(self.knowledge_graph_dir, "edges.jsonl")

        if not os.path.exists(nodes_path) or not os.path.exists(edges_path):
            logger.warning("Knowledge graph files are missing in %s", self.knowledge_graph_dir)
            return

        try:
            with open(nodes_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    node = GraphNodeRecord(
                        node_id=record["id"],
                        label=record["label"],
                        properties=record.get("properties", {}),
                    )
                    self.nodes[node.node_id] = node
                    if node.label == "Course":
                        self.course_ids.add(node.node_id)
                    elif node.label == "Program":
                        self.program_ids.add(node.node_id)

            with open(edges_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    edge = GraphEdgeRecord(
                        source=record["source"],
                        target=record["target"],
                        edge_type=record["type"],
                        properties=record.get("properties", {}),
                    )
                    self.out_edges[edge.source].append(edge)
                    self.in_edges[edge.target].append(edge)

            self.available = True
            logger.info(
                "GraphRAG loaded successfully (%s nodes, %s adjacency lists)",
                len(self.nodes),
                len(self.out_edges),
            )
        except Exception as exc:
            logger.exception("Failed to load knowledge graph: %s", exc)
            self.available = False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "node_count": len(self.nodes),
            "course_count": len(self.course_ids),
            "program_count": len(self.program_ids),
        }

    def find_course_node(self, course_code: str, course_name_hint: Optional[str] = None) -> Optional[GraphNodeRecord]:
        if not self.available:
            return None

        code_norm = _normalize_text(course_code)
        name_norm = _normalize_text(course_name_hint or "")
        best: Optional[Tuple[int, GraphNodeRecord]] = None

        for node_id in self.course_ids:
            node = self.nodes[node_id]
            props = node.properties
            if props.get("is_reference"):
                continue

            score = 0
            node_code = _normalize_text(str(props.get("course_code", "")))
            node_name = _normalize_text(str(props.get("name_vi", "")))

            if code_norm and node_code and node_code == code_norm:
                score += 100
            if name_norm and node_name == name_norm:
                score += 80
            elif name_norm and name_norm and name_norm in node_name:
                score += 60
            if course_name_hint and props.get("source_file") and _normalize_text(os.path.basename(props["source_file"])) in name_norm:
                score += 10

            if score <= 0:
                continue
            if best is None or score > best[0]:
                best = (score, node)

        return best[1] if best else None

    def find_program_node(self, program_code: str = "", program_name_hint: Optional[str] = None) -> Optional[GraphNodeRecord]:
        if not self.available:
            return None

        code_norm = _normalize_text(program_code)
        name_norm = _normalize_text(program_name_hint or "")
        best: Optional[Tuple[int, GraphNodeRecord]] = None

        for node_id in self.program_ids:
            node = self.nodes[node_id]
            props = node.properties
            score = 0
            node_code = _normalize_text(str(props.get("program_code", "")))
            node_name = _normalize_text(str(props.get("name_vi", "")))

            if code_norm and node_code and node_code == code_norm:
                score += 100
            if name_norm and node_name == name_norm:
                score += 90
            elif name_norm and name_norm in node_name:
                score += 70

            if score <= 0:
                continue
            if best is None or score > best[0]:
                best = (score, node)

        if best:
            return best[1]
        if len(self.program_ids) == 1:
            only_program_id = next(iter(self.program_ids))
            return self.nodes.get(only_program_id)
        return None

    def build_course_context(
        self,
        course_code: str,
        course_name_hint: Optional[str] = None,
        section_intent: Optional[str] = None,
    ) -> str:
        logger.info(
            "GraphRAG course lookup started: course_code=%s, course_name_hint=%s, section_intent=%s",
            course_code,
            course_name_hint,
            section_intent,
        )
        course_node = self.find_course_node(course_code, course_name_hint)
        if not course_node:
            logger.warning(
                "GraphRAG course lookup found no node: course_code=%s, course_name_hint=%s",
                course_code,
                course_name_hint,
            )
            return ""

        if section_intent and section_intent in self.COURSE_RELATION_GROUPS:
            relations = set(self.CORE_COURSE_RELATIONS)
            relations.update(self.COURSE_RELATION_GROUPS[section_intent])
        else:
            relations = set(self.DEFAULT_COURSE_RELATIONS)

        lines = self._describe_course_node(course_node)
        lines.extend(self._summarize_edges(course_node.node_id, relations, max_items=18))
        context = "\n".join(line for line in lines if line).strip()
        logger.info(
            "GraphRAG course context built: node_id=%s, relations=%s, lines=%s, chars=%s",
            course_node.node_id,
            sorted(relations),
            len([line for line in lines if line]),
            len(context),
        )
        return context

    def build_program_context(self, program_code: str = "", program_name_hint: Optional[str] = None) -> str:
        logger.info(
            "GraphRAG program lookup started: program_code=%s, program_name_hint=%s",
            program_code,
            program_name_hint,
        )
        program_node = self.find_program_node(program_code, program_name_hint)
        if not program_node:
            logger.warning(
                "GraphRAG program lookup found no node: program_code=%s, program_name_hint=%s",
                program_code,
                program_name_hint,
            )
            return ""

        lines = self._describe_program_node(program_node)
        lines.extend(self._summarize_edges(program_node.node_id, self.DEFAULT_MAJOR_RELATIONS, max_items=20))
        context = "\n".join(line for line in lines if line).strip()
        logger.info(
            "GraphRAG program context built: node_id=%s, lines=%s, chars=%s",
            program_node.node_id,
            len([line for line in lines if line]),
            len(context),
        )
        return context

    def _describe_course_node(self, node: GraphNodeRecord) -> List[str]:
        props = node.properties
        lines = [
            "# GRAPH FACTS: COURSE",
            f"- Môn học: {props.get('name_vi', 'N/A')}",
        ]
        if props.get("course_code"):
            lines.append(f"- Mã môn: {props['course_code']}")
        if props.get("name_en"):
            lines.append(f"- Tên tiếng Anh: {props['name_en']}")
        if props.get("credits") is not None:
            lines.append(f"- Số tín chỉ: {props['credits']}")
        hours = []
        if props.get("theory_hours") is not None:
            hours.append(f"lý thuyết {props['theory_hours']}")
        if props.get("practice_hours") is not None:
            hours.append(f"thực hành {props['practice_hours']}")
        if props.get("exercise_hours") is not None:
            hours.append(f"bài tập {props['exercise_hours']}")
        if hours:
            lines.append(f"- Phân bổ giờ: {', '.join(hours)}")
        if props.get("knowledge_type"):
            lines.append(f"- Nhóm kiến thức: {props['knowledge_type']}")
        return lines

    def _describe_program_node(self, node: GraphNodeRecord) -> List[str]:
        props = node.properties
        lines = [
            "# GRAPH FACTS: PROGRAM",
            f"- Chương trình/ngành: {props.get('name_vi', 'N/A')}",
        ]
        if props.get("program_code"):
            lines.append(f"- Mã ngành/chương trình: {props['program_code']}")
        if props.get("name_en"):
            lines.append(f"- Tên tiếng Anh: {props['name_en']}")
        if props.get("cohort"):
            lines.append(f"- Khóa tuyển: {props['cohort']}")
        if props.get("degree_level"):
            lines.append(f"- Trình độ đào tạo: {props['degree_level']}")
        if props.get("total_credits") is not None:
            lines.append(f"- Tổng số tín chỉ: {props['total_credits']}")
        return lines

    def _summarize_edges(self, node_id: str, relations: Set[str], max_items: int = 18) -> List[str]:
        lines: List[str] = []
        items_added = 0

        outgoing = [edge for edge in self.out_edges.get(node_id, []) if edge.edge_type in relations]
        incoming = [edge for edge in self.in_edges.get(node_id, []) if edge.edge_type in relations]

        for edge in outgoing:
            if items_added >= max_items:
                break
            target = self.nodes.get(edge.target)
            rendered = self._render_edge(edge, target, outgoing=True)
            if rendered:
                lines.append(rendered)
                items_added += 1

            if items_added >= max_items:
                break
            lines.extend(self._expand_second_hop(edge, target, max_items - items_added))
            items_added = len(lines)

        for edge in incoming:
            if items_added >= max_items:
                break
            source = self.nodes.get(edge.source)
            rendered = self._render_edge(edge, source, outgoing=False)
            if rendered:
                lines.append(rendered)
                items_added += 1

        return lines[:max_items]

    def _expand_second_hop(self, edge: GraphEdgeRecord, target: Optional[GraphNodeRecord], remaining: int) -> List[str]:
        if not target or remaining <= 0:
            return []
        if target.label not in {"CLO", "Assessment", "Topic"}:
            return []

        lines: List[str] = []
        for sub_edge in self.out_edges.get(target.node_id, []):
            if sub_edge.edge_type not in {"ALIGNS_WITH_OBJECTIVE", "ALIGNS_WITH_PLO", "SUPPORTS_CLO", "ASSESSES_TOPIC"}:
                continue
            sub_target = self.nodes.get(sub_edge.target)
            rendered = self._render_compound_edge(target, sub_edge, sub_target)
            if rendered:
                lines.append(rendered)
            if len(lines) >= remaining:
                break
        return lines

    def _render_edge(self, edge: GraphEdgeRecord, other_node: Optional[GraphNodeRecord], outgoing: bool) -> str:
        if not other_node:
            return ""

        label = other_node.label
        props = other_node.properties
        direction_text = {
            "TAUGHT_BY": lambda: f"- Giảng viên: {props.get('full_name', other_node.node_id)}",
            "OFFERS": lambda: f"- Bộ môn phụ trách: {props.get('name_vi', other_node.node_id)}",
            "BELONGS_TO_PROGRAM": lambda: f"- Thuộc chương trình/ngành: {props.get('name_vi', other_node.node_id)}",
            "REQUIRES": lambda: f"- Học phần tiên quyết: {props.get('name_vi', other_node.node_id)}",
            "PRECEDED_BY": lambda: f"- Học trước học phần này: {props.get('name_vi', other_node.node_id)}",
            "COREQUISITE_WITH": lambda: f"- Học phần song hành: {props.get('name_vi', other_node.node_id)}",
            "HAS_CLO": lambda: f"- CLO {props.get('code', '')}: {props.get('description', '')}",
            "HAS_OBJECTIVE": lambda: f"- Mục tiêu {props.get('code', '')}: {props.get('description', '')}",
            "HAS_ASSESSMENT": lambda: self._format_assessment(props),
            "HAS_TOPIC": lambda: self._format_topic(props),
            "USES_MATERIAL": lambda: self._format_material(props),
            "HAS_PLO": lambda: f"- PLO {props.get('code', '')}: {props.get('description', '')}",
        }

        if edge.edge_type == "BELONGS_TO_PROGRAM" and not outgoing and label == "Course":
            return f"- Môn thuộc chương trình: {props.get('course_code', '')} - {props.get('name_vi', other_node.node_id)}"

        if edge.edge_type in direction_text:
            rendered = direction_text[edge.edge_type]()
            return "" if self._is_placeholder_line(rendered) else rendered

        if not outgoing and edge.edge_type == "OFFERS" and label == "Course":
            rendered = f"- Học phần thuộc bộ môn: {props.get('course_code', '')} - {props.get('name_vi', other_node.node_id)}"
            return "" if self._is_placeholder_line(rendered) else rendered
        return ""

    def _render_compound_edge(
        self,
        anchor_node: GraphNodeRecord,
        edge: GraphEdgeRecord,
        target_node: Optional[GraphNodeRecord],
    ) -> str:
        if not target_node:
            return ""

        anchor_name = anchor_node.properties.get("code") or anchor_node.properties.get("name") or anchor_node.node_id
        target_props = target_node.properties

        if edge.edge_type == "ALIGNS_WITH_OBJECTIVE":
            return f"- {anchor_name} liên kết mục tiêu {target_props.get('code', '')}: {target_props.get('description', '')}"
        if edge.edge_type == "ALIGNS_WITH_PLO":
            return f"- {anchor_name} liên kết PLO {target_props.get('code', '')}: {target_props.get('description', '')}"
        if edge.edge_type == "SUPPORTS_CLO":
            return f"- {anchor_name} hỗ trợ CLO {target_props.get('code', '')}: {target_props.get('description', '')}"
        if edge.edge_type == "ASSESSES_TOPIC":
            return f"- {anchor_name} đánh giá nội dung: {target_props.get('title', target_node.node_id)}"
        return ""

    def _format_assessment(self, props: Dict[str, Any]) -> str:
        parts = [f"- Đánh giá {props.get('code', '')}: {props.get('name', '')}"]
        if props.get("weight") is not None:
            parts.append(f"({props['weight']}%)")
        return " ".join(part for part in parts if part).strip()

    def _format_topic(self, props: Dict[str, Any]) -> str:
        details = [f"- Chủ đề {props.get('code', '')}: {props.get('title', '')}"]
        if props.get("week_range"):
            details.append(f"(tuần {props['week_range']})")
        return " ".join(part for part in details if part).strip()

    def _format_material(self, props: Dict[str, Any]) -> str:
        details = [f"- Tài liệu: {props.get('title', '')}"]
        if props.get("authors_raw"):
            details.append(f"- Tác giả: {props['authors_raw']}")
        if props.get("year"):
            details.append(f"- Năm: {props['year']}")
        if props.get("material_type"):
            details.append(f"- Loại: {props['material_type']}")
        return " ".join(part for part in details if part).strip()

    def _is_placeholder_line(self, value: str) -> bool:
        raw = (value or "").strip()
        normalized = _normalize_text(raw)
        if normalized in {"", "hoc phan song hanh", "giang vien", "hoc phan tien quyet"}:
            return True
        if "…" in raw or raw.endswith("..."):
            return True
        if raw.endswith(":") or raw.endswith("-"):
            return True
        return False
