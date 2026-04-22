"""
Lightweight graph models and ID utilities for the syllabus Knowledge Graph POC.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def slugify(value: str) -> str:
    text = strip_accents((value or "").strip().lower())
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def stable_hash(*parts: str, size: int = 12) -> str:
    joined = "|".join(part.strip() for part in parts if part)
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()
    return digest[:size]


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def build_node_id(label: str, *parts: str) -> str:
    clean_parts = [slugify(part) for part in parts if part]
    suffix = ":".join(clean_parts) if clean_parts else "unknown"
    return f"{slugify(label)}:{suffix}"


@dataclass
class GraphNode:
    id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def merge(self, new_properties: Dict[str, Any]) -> None:
        for key, value in new_properties.items():
            if value in (None, "", [], {}):
                continue
            current = self.properties.get(key)
            if current in (None, "", [], {}):
                self.properties[key] = value

    def to_record(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label, "properties": self.properties}


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def key(self) -> Tuple[str, str, str, str]:
        provenance = self.properties.get("source_section", "")
        return self.source, self.target, self.type, str(provenance)

    def to_record(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "properties": self.properties,
        }


@dataclass
class GraphDocument:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)
    _edge_keys: set = field(default_factory=set, init=False, repr=False)

    def add_node(self, node_id: str, label: str, **properties: Any) -> GraphNode:
        if node_id in self.nodes:
            self.nodes[node_id].merge(properties)
            return self.nodes[node_id]

        node = GraphNode(id=node_id, label=label, properties=properties)
        self.nodes[node_id] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        **properties: Any,
    ) -> Optional[GraphEdge]:
        edge = GraphEdge(source=source, target=target, type=edge_type, properties=properties)
        key = edge.key()
        if key in self._edge_keys:
            return None
        self._edge_keys.add(key)
        self.edges.append(edge)
        return edge

    def add_evidence(
        self,
        entity_id: str,
        section_id: str,
        source_file: str,
        source_section: str,
        parser_version: str,
    ) -> None:
        self.add_edge(
            entity_id,
            section_id,
            "EVIDENCED_BY",
            source_file=source_file,
            source_section=source_section,
            parser_version=parser_version,
        )

    def merge(self, other: "GraphDocument") -> None:
        for node in other.nodes.values():
            self.add_node(node.id, node.label, **node.properties)
        for edge in other.edges:
            self.add_edge(edge.source, edge.target, edge.type, **edge.properties)

    def to_jsonl_records(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes = [node.to_record() for node in self.nodes.values()]
        edges = [edge.to_record() for edge in self.edges]
        return nodes, edges


def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
