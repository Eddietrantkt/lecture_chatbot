"""
Parse syllabus JSON files into a schema-first Knowledge Graph document.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from backend.kg_models import GraphDocument, build_node_id, compact_whitespace, slugify, stable_hash, strip_accents

logger = logging.getLogger("knowledge_graph_parser")

PARSER_VERSION = "kg_parser_v1"


SECTION_ALIASES = {
    "general_info": ["thông tin chung về học phần", "thông tin chung về chương trình đào tạo"],
    "lecturers": ["thông tin về giảng viên"],
    "objectives": ["mục tiêu của học phần", "mục tiêu đào tạo"],
    "clos": ["chuẩn đầu ra"],
    "assessments": ["hình thức, phương pháp và trọng số đánh giá kết quả học phần"],
    "teaching_plan": ["kế hoạch giảng dạy chi tiết của học phần", "kế hoạch giảng dạy chi tiết của  học phần"],
    "materials": ["tài liệu học tập"],
}


@dataclass
class ProgramContext:
    program_id: Optional[str] = None
    program_name: Optional[str] = None
    cohort: Optional[str] = None


def normalize_text(value: str) -> str:
    text = strip_accents((value or "").strip().lower())
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return compact_whitespace(text)


def normalize_heading(value: str) -> str:
    return normalize_text(repair_text(value)).rstrip(":")


def repair_text(value: str) -> str:
    text = str(value or "")
    if not text:
        return text
    if not any(marker in text for marker in ("Ã", "Ä", "á»", "Â", "Æ")):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
        return repaired or text
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_sections(data: Dict[str, Any]) -> Dict[str, List[str]]:
    sections = data.get("sections", {})
    if isinstance(sections, dict):
        return sections
    return {}


def find_section(sections: Dict[str, List[str]], alias_key: str) -> Tuple[str, List[str]]:
    normalized_aliases = [normalize_heading(alias) for alias in SECTION_ALIASES.get(alias_key, [])]
    for heading, content in sections.items():
        heading_norm = normalize_heading(heading)
        if any(alias in heading_norm for alias in normalized_aliases):
            return heading, content if isinstance(content, list) else [str(content)]
    return "", []


def parse_key_value_line(value: str) -> Optional[Tuple[str, str]]:
    if ":" not in value:
        return None
    key, raw_value = value.split(":", 1)
    return compact_whitespace(key), compact_whitespace(raw_value)


def parse_int(value: str) -> Optional[int]:
    if not value:
        return None
    match = re.search(r"\d+", value)
    if not match:
        return None
    return int(match.group(0))


def parse_percent(value: str) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
    if match:
        return float(match.group(1))
    return None


def split_table_row(line: str) -> List[str]:
    if "|" not in line:
        return []
    parts = [compact_whitespace(part) for part in line.strip().strip("|").split("|")]
    return parts


def is_separator_row(parts: Sequence[str]) -> bool:
    if not parts:
        return True
    return all(re.fullmatch(r"[-: ]*", part or "") for part in parts)


def iter_markdown_rows(lines: Iterable[str]) -> Iterable[List[str]]:
    for line in lines:
        parts = split_table_row(line)
        if not parts or is_separator_row(parts):
            continue
        yield parts


def explode_lines(lines: Sequence[str]) -> List[str]:
    expanded: List[str] = []
    for item in lines:
        repaired_item = repair_text(item)
        for subline in str(repaired_item).splitlines():
            clean = compact_whitespace(subline)
            if clean:
                expanded.append(clean)
    return expanded


def create_document_nodes(graph: GraphDocument, file_path: str, doc_type: str, sections: Dict[str, List[str]]) -> Tuple[str, Dict[str, str]]:
    file_name = os.path.basename(file_path)
    document_id = build_node_id("document", Path(file_name).stem)
    graph.add_node(
        document_id,
        "Document",
        document_id=document_id,
        doc_type=doc_type,
        file_name=file_name,
        file_path=file_path,
    )

    section_ids: Dict[str, str] = {}
    for heading, content in sections.items():
        section_id = build_node_id("section", Path(file_name).stem, heading)
        section_ids[heading] = section_id
        repaired_heading = repair_text(heading)
        repaired_content = [repair_text(item) for item in (content if isinstance(content, list) else [str(content)])]
        graph.add_node(
            section_id,
            "Section",
            section_id=section_id,
            heading_raw=repaired_heading,
            heading_norm=normalize_heading(repaired_heading),
            content_raw="\n".join(repaired_content),
            file_path=file_path,
        )
        graph.add_edge(
            document_id,
            section_id,
            "HAS_SECTION",
            source_file=file_path,
            source_section=repaired_heading,
            parser_version=PARSER_VERSION,
        )

    return document_id, section_ids


def extract_general_course_info(lines: Sequence[str]) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "course_code": "",
        "name_vi": "",
        "name_en": "",
        "credits": None,
        "theory_hours": None,
        "practice_hours": None,
        "exercise_hours": None,
        "knowledge_type": "",
        "is_project": False,
        "is_thesis": False,
        "department_name": "",
        "prerequisite": "",
        "prestudy": "",
        "corequisite": "",
    }

    current_knowledge_type = ""
    for raw_line in lines:
        line = compact_whitespace(repair_text(raw_line))
        if not line:
            continue
        parsed = parse_key_value_line(line)
        if not parsed:
            continue
        key, value = parsed
        key_norm = normalize_text(key)

        if "ma hoc phan" in key_norm:
            info["course_code"] = value.rstrip(".")
        elif key_norm == "ten hoc phan":
            info["name_vi"] = value
        elif "ten hoc phan bang tieng anh" in key_norm:
            info["name_en"] = value
        elif "so tin chi" in key_norm:
            info["credits"] = parse_int(value)
        elif "so tiet ly thuyet" in key_norm:
            info["theory_hours"] = parse_int(value)
        elif "so tiet thuc hanh" in key_norm:
            info["practice_hours"] = parse_int(value)
        elif "so tiet bai tap" in key_norm:
            info["exercise_hours"] = parse_int(value)
        elif "kien thuc" in key_norm and "[x]" in value.lower():
            current_knowledge_type = key
        elif "do an" in key_norm and "[x]" in value.lower():
            info["is_project"] = True
        elif "khoa luan" in key_norm and "[x]" in value.lower():
            info["is_thesis"] = True
        elif "bo mon phu trach hoc phan" in key_norm:
            info["department_name"] = value
        elif "hoc phan tien quyet" in key_norm:
            info["prerequisite"] = value
        elif "hoc truoc hoc phan nay" in key_norm:
            info["prestudy"] = value
        elif "hoc phan song hanh" in key_norm:
            info["corequisite"] = value

    info["knowledge_type"] = current_knowledge_type
    return info


def extract_lecturer_entries(lines: Sequence[str]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    current: Dict[str, str] = {}

    for raw_line in lines:
        line = compact_whitespace(repair_text(raw_line))
        if not line:
            continue
        parsed = parse_key_value_line(line)
        if not parsed:
            continue
        key, value = parsed
        key_norm = normalize_text(key)

        if "ho va ten" in key_norm:
            if current:
                entries.append(current)
                current = {}
            current["full_name"] = value
        elif "chuc danh" in key_norm or "hoc ham" in key_norm or "hoc vi" in key_norm:
            current["title_degree"] = value
        elif "don vi cong tac" in key_norm:
            current["affiliation"] = value
        elif "email" in key_norm:
            email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", value)
            current["email"] = email_match.group(0) if email_match else value

    if current:
        entries.append(current)
    return entries


def parse_objectives(course_id: str, lines: Sequence[str]) -> List[Dict[str, Any]]:
    objectives: List[Dict[str, Any]] = []
    current_category = ""

    for raw_line in explode_lines(lines):
        line = compact_whitespace(raw_line)
        if not line:
            continue

        upper_line = strip_accents(line).upper()
        if "KIEN THUC" in upper_line:
            current_category = "knowledge"
            continue
        if "KY NANG" in upper_line:
            current_category = "skill"
            continue
        if "THAI DO" in upper_line:
            current_category = "attitude"
            continue

        parts = split_table_row(line)
        if len(parts) >= 3 and re.fullmatch(r"MH\d+(?:\.\d+)?", parts[0], re.IGNORECASE):
            code = parts[0].upper()
            objectives.append(
                {
                    "objective_id": build_node_id("objective", course_id, code),
                    "course_id": course_id,
                    "code": code,
                    "category": current_category,
                    "description": parts[1],
                    "bloom_level": parts[2],
                }
            )

    return objectives


def parse_clos(course_id: str, lines: Sequence[str], program_id: Optional[str]) -> List[Dict[str, Any]]:
    clos: List[Dict[str, Any]] = []
    current_category = ""

    for raw_line in explode_lines(lines):
        line = compact_whitespace(raw_line)
        if not line:
            continue

        upper_line = strip_accents(line).upper()
        if "KIEN THUC" in upper_line:
            current_category = "knowledge"
            continue
        if "KY NANG" in upper_line:
            current_category = "skill"
            continue
        if "THAI DO" in upper_line:
            current_category = "attitude"
            continue

        parts = split_table_row(line)
        if len(parts) >= 6 and re.fullmatch(r"CHP\d+(?:\.\d+)?", parts[1], re.IGNORECASE):
            code = parts[1].upper()
            objective_refs = re.findall(r"MH\d+(?:\.\d+)?", parts[4], re.IGNORECASE)
            plo_refs = re.findall(r"CCT\d+(?:\.\d+)?", parts[5], re.IGNORECASE)
            clos.append(
                {
                    "clo_id": build_node_id("clo", course_id, code),
                    "course_id": course_id,
                    "code": code,
                    "category": current_category,
                    "description": parts[2],
                    "teaching_level": parts[3],
                    "objective_refs": [ref.upper() for ref in objective_refs],
                    "plo_refs": [ref.upper() for ref in plo_refs],
                    "program_id": program_id,
                }
            )

    return clos


def parse_assessments(course_id: str, lines: Sequence[str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for parts in iter_markdown_rows(explode_lines(lines)):
        if len(parts) < 8:
            continue
        if not re.fullmatch(r"[ĐD]G\d+(?:\.\d+)?", parts[6], re.IGNORECASE):
            continue
        code = parts[6].upper()
        results.append(
            {
                "assessment_id": build_node_id("assessment", course_id, code),
                "course_id": course_id,
                "code": code,
                "assessment_group": parts[0],
                "name": parts[1],
                "method_written": parts[2].upper() == "X",
                "method_mcq": parts[3].upper() == "X",
                "method_oral": parts[4].upper() == "X",
                "method_other": parts[5].upper() == "X",
                "weight": parse_percent(parts[7]),
                "note": parts[8] if len(parts) > 8 else "",
            }
        )
    return results


def parse_topics(course_id: str, lines: Sequence[str]) -> List[Dict[str, Any]]:
    topics: List[Dict[str, Any]] = []
    order_index = 0

    for parts in iter_markdown_rows(explode_lines(lines)):
        if len(parts) < 9:
            continue
        title = parts[0]
        if title.lower().startswith("tên bài giảng") or title.lower().startswith("tong cong"):
            continue

        if not re.search(r"[A-Za-zÀ-ỹ0-9]", title):
            continue

        level = "topic"
        if normalize_text(title).startswith("chuong"):
            level = "chapter"
        elif re.match(r"\d+(\.\d+)+", title):
            level = "subtopic"

        order_index += 1
        code_seed = f"{order_index}_{title}"
        clo_refs = re.findall(r"CHP\d+(?:\.\d+)?", parts[2], re.IGNORECASE)
        assessment_refs = re.findall(r"[ĐD]G\d+(?:\.\d+)?", parts[8], re.IGNORECASE)

        topics.append(
            {
                "topic_id": build_node_id("topic", course_id, code_seed),
                "course_id": course_id,
                "code": f"T{order_index}",
                "title": title,
                "level": level,
                "week_range": parts[1],
                "theory_hours": parse_int(parts[3]) if len(parts) > 3 else None,
                "practice_hours": parse_int(parts[4]) if len(parts) > 4 else None,
                "exercise_hours": parse_int(parts[5]) if len(parts) > 5 else None,
                "self_study_hours": parse_int(parts[6]) if len(parts) > 6 else None,
                "teaching_method_raw": parts[7] if len(parts) > 7 else "",
                "clo_refs": [ref.upper() for ref in clo_refs],
                "assessment_refs": [ref.upper() for ref in assessment_refs],
            }
        )

    return topics


def parse_materials(lines: Sequence[str]) -> List[Dict[str, Any]]:
    materials: List[Dict[str, Any]] = []
    for parts in iter_markdown_rows(explode_lines(lines)):
        if len(parts) < 7:
            continue
        if not re.fullmatch(r"\d+", parts[0]):
            continue

        title = parts[3]
        authors = parts[1]
        year = parts[2]
        material_id = build_node_id("material", stable_hash(authors, title, year))
        materials.append(
            {
                "material_id": material_id,
                "title": title,
                "authors_raw": authors,
                "year": year,
                "publisher": parts[4],
                "material_type": parts[5],
                "location": parts[6],
            }
        )
    return materials


def parse_program_info(file_path: str, sections: Dict[str, List[str]]) -> Dict[str, Any]:
    file_stem = Path(file_path).stem
    cohort_match = re.search(r"k(\d{4})", file_stem, re.IGNORECASE)
    cohort = cohort_match.group(1) if cohort_match else ""

    name_vi = ""
    name_en = ""
    program_code = ""
    degree_level = ""
    duration_years = None
    total_credits = None

    general_heading, general_lines = find_section(sections, "general_info")
    current_context = ""
    for line in explode_lines(general_lines):
        clean = compact_whitespace(line)
        clean_norm = normalize_text(clean)

        if "ten nganh dao tao" in clean_norm:
            current_context = "program_name"
            continue
        if "ten van bang sau khi tot nghiep" in clean_norm:
            current_context = "degree_name"
            continue
        if clean.startswith("-") and ":" in clean and current_context == "program_name":
            label, value = clean.lstrip("-").split(":", 1)
            label_norm = normalize_text(label)
            value = value.strip().rstrip(".")
            if "tieng viet" in label_norm and not name_vi:
                name_vi = value
            elif "tieng anh" in label_norm and not name_en:
                name_en = value
            continue
        if "ma nganh dao tao" in clean_norm and ":" in clean:
            program_code = clean.split(":", 1)[-1].strip().rstrip(".")
        elif "trinh do dao tao" in clean_norm and ":" in clean:
            degree_level = clean.split(":", 1)[-1].strip().rstrip(".")
        elif "thoi gian dao tao" in clean_norm and ":" in clean:
            duration_years = parse_int(clean.split(":", 1)[-1])

    for line in sections.get("3. Khối lượng kiến thức", []):
        if "tín chỉ" in line:
            total_credits = parse_int(line)
            break

    if not name_vi:
        stem_name = file_stem.replace("CTDT_", "").replace("_", " ")
        name_vi = stem_name

    program_id = build_node_id("program", name_vi, cohort)
    return {
        "program_id": program_id,
        "program_code": program_code,
        "name_vi": name_vi,
        "name_en": name_en,
        "cohort": cohort,
        "degree_level": degree_level,
        "duration_years": duration_years,
        "total_credits": total_credits,
        "general_heading": general_heading,
    }


def parse_plos(program_id: str, lines: Sequence[str]) -> List[Dict[str, Any]]:
    plos: List[Dict[str, Any]] = []
    current_category = ""
    for raw_line in lines:
        line = compact_whitespace(raw_line)
        upper_line = strip_accents(line).upper()
        if "KIEN THUC" in upper_line:
            current_category = "knowledge"
            continue
        if "KY NANG" in upper_line:
            current_category = "skill"
            continue
        if "THAI DO" in upper_line:
            current_category = "attitude"
            continue
        if "TRACH NHIEM NGHE NGHIEP" in upper_line:
            current_category = "professional_responsibility"
            continue

        match = re.match(r"\d+\s*,\s*(CCT\d+(?:\.\d+)?)\s*,\s*(.+?)\s*,\s*([0-9]+/[0-9]+)\s*,?", line, re.IGNORECASE)
        if not match:
            continue

        code = match.group(1).upper()
        description = compact_whitespace(match.group(2))
        bloom_level = match.group(3)
        plos.append(
            {
                "plo_id": build_node_id("plo", program_id, code),
                "program_id": program_id,
                "code": code,
                "category": current_category,
                "description": description,
                "bloom_level": bloom_level,
            }
        )
    return plos


def parse_program_course_refs(program_id: str, sections: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    course_refs: List[Dict[str, Any]] = []
    for heading, lines in sections.items():
        heading_norm = normalize_heading(heading)
        if not heading_norm.startswith("7"):
            continue
        for line in lines:
            clean = compact_whitespace(line)
            match = re.match(r"\d+\s*,\s*([A-Z]{3}\d{5}|MTH[0-9Xx]{5})\s*,\s*(.+?)\s*,\s*(\d+)\s*,", clean)
            if not match:
                continue
            course_code = match.group(1).upper()
            course_name = compact_whitespace(match.group(2))
            credits = parse_int(match.group(3))
            reference_id = build_node_id("course", f"program_ref_{course_code}_{course_name}")
            course_refs.append(
                {
                    "course_id": reference_id,
                    "course_code": course_code,
                    "name_vi": course_name,
                    "credits": credits,
                    "program_id": program_id,
                    "is_reference": True,
                    "source_section": heading,
                }
            )
    return course_refs


def link_course_relation(
    graph: GraphDocument,
    course_id: str,
    raw_value: str,
    relation_type: str,
    file_path: str,
    section_heading: str,
) -> None:
    if not raw_value or normalize_text(raw_value) in {"khong co", "khong", "chua co"}:
        return

    reference_course_id = build_node_id("course", f"ref_{raw_value}")
    graph.add_node(
        reference_course_id,
        "Course",
        course_id=reference_course_id,
        course_code="",
        name_vi=raw_value,
        is_reference=True,
        source_file=file_path,
    )
    graph.add_edge(
        course_id,
        reference_course_id,
        relation_type,
        source_file=file_path,
        source_section=section_heading,
        parser_version=PARSER_VERSION,
    )


def parse_course_document(
    file_path: str,
    data: Dict[str, Any],
    program_context: Optional[ProgramContext] = None,
) -> GraphDocument:
    sections = get_sections(data)
    graph = GraphDocument()
    _, section_ids = create_document_nodes(graph, file_path, "course", sections)

    general_heading, general_lines = find_section(sections, "general_info")
    general_info = extract_general_course_info(general_lines)
    course_stem = Path(file_path).stem
    course_id = build_node_id("course", course_stem)

    graph.add_node(
        course_id,
        "Course",
        course_id=course_id,
        course_code=general_info["course_code"],
        name_vi=general_info["name_vi"] or course_stem,
        name_en=general_info["name_en"],
        credits=general_info["credits"],
        theory_hours=general_info["theory_hours"],
        practice_hours=general_info["practice_hours"],
        exercise_hours=general_info["exercise_hours"],
        knowledge_type=general_info["knowledge_type"],
        is_project=general_info["is_project"],
        is_thesis=general_info["is_thesis"],
        is_reference=False,
        source_file=file_path,
        parser_version=PARSER_VERSION,
    )

    if general_heading:
        graph.add_evidence(course_id, section_ids[general_heading], file_path, general_heading, PARSER_VERSION)

    department_name = general_info["department_name"]
    if department_name:
        department_id = build_node_id("department", department_name)
        graph.add_node(
            department_id,
            "Department",
            department_id=department_id,
            name_vi=department_name,
            name_raw=department_name,
            source_file=file_path,
        )
        graph.add_edge(
            department_id,
            course_id,
            "OFFERS",
            source_file=file_path,
            source_section=general_heading,
            parser_version=PARSER_VERSION,
        )

    if program_context and program_context.program_id:
        graph.add_edge(
            course_id,
            program_context.program_id,
            "BELONGS_TO_PROGRAM",
            source_file=file_path,
            source_section=general_heading,
            parser_version=PARSER_VERSION,
        )

    if general_heading:
        link_course_relation(graph, course_id, general_info["prerequisite"], "REQUIRES", file_path, general_heading)
        link_course_relation(graph, course_id, general_info["prestudy"], "PRECEDED_BY", file_path, general_heading)
        link_course_relation(graph, course_id, general_info["corequisite"], "COREQUISITE_WITH", file_path, general_heading)

    lecturer_heading, lecturer_lines = find_section(sections, "lecturers")
    for lecturer in extract_lecturer_entries(lecturer_lines):
        full_name = lecturer.get("full_name")
        if not full_name:
            continue
        lecturer_id = build_node_id("lecturer", full_name)
        graph.add_node(
            lecturer_id,
            "Lecturer",
            lecturer_id=lecturer_id,
            full_name=full_name,
            title_degree=lecturer.get("title_degree", ""),
            email=lecturer.get("email", ""),
            affiliation=lecturer.get("affiliation", ""),
            source_file=file_path,
        )
        graph.add_edge(
            course_id,
            lecturer_id,
            "TAUGHT_BY",
            source_file=file_path,
            source_section=lecturer_heading,
            parser_version=PARSER_VERSION,
        )
        if department_name:
            department_id = build_node_id("department", department_name)
            graph.add_edge(
                lecturer_id,
                department_id,
                "AFFILIATED_WITH",
                source_file=file_path,
                source_section=lecturer_heading,
                parser_version=PARSER_VERSION,
            )
        if lecturer_heading:
            graph.add_evidence(lecturer_id, section_ids[lecturer_heading], file_path, lecturer_heading, PARSER_VERSION)

    objective_heading, objective_lines = find_section(sections, "objectives")
    objective_index: Dict[str, str] = {}
    for objective in parse_objectives(course_id, objective_lines):
        objective_id = objective["objective_id"]
        objective_index[objective["code"]] = objective_id
        graph.add_node(objective_id, "Objective", source_file=file_path, parser_version=PARSER_VERSION, **objective)
        graph.add_edge(
            course_id,
            objective_id,
            "HAS_OBJECTIVE",
            source_file=file_path,
            source_section=objective_heading,
            parser_version=PARSER_VERSION,
        )
        if objective_heading:
            graph.add_evidence(objective_id, section_ids[objective_heading], file_path, objective_heading, PARSER_VERSION)

    clo_heading, clo_lines = find_section(sections, "clos")
    clo_index: Dict[str, str] = {}
    for clo in parse_clos(course_id, clo_lines, program_context.program_id if program_context else None):
        clo_id = clo["clo_id"]
        clo_index[clo["code"]] = clo_id
        graph.add_node(
            clo_id,
            "CLO",
            source_file=file_path,
            parser_version=PARSER_VERSION,
            code=clo["code"],
            category=clo["category"],
            description=clo["description"],
            teaching_level=clo["teaching_level"],
            course_id=course_id,
        )
        graph.add_edge(
            course_id,
            clo_id,
            "HAS_CLO",
            source_file=file_path,
            source_section=clo_heading,
            parser_version=PARSER_VERSION,
        )
        for objective_code in clo["objective_refs"]:
            objective_id = objective_index.get(objective_code)
            if objective_id:
                graph.add_edge(
                    clo_id,
                    objective_id,
                    "ALIGNS_WITH_OBJECTIVE",
                    mapping_raw=objective_code,
                    source_file=file_path,
                    source_section=clo_heading,
                    parser_version=PARSER_VERSION,
                )

        if program_context and program_context.program_id:
            for plo_code in clo["plo_refs"]:
                plo_id = build_node_id("plo", program_context.program_id, plo_code)
                graph.add_node(
                    plo_id,
                    "PLO",
                    plo_id=plo_id,
                    code=plo_code,
                    program_id=program_context.program_id,
                    source_file=file_path,
                )
                graph.add_edge(
                    clo_id,
                    plo_id,
                    "ALIGNS_WITH_PLO",
                    mapping_raw=plo_code,
                    source_file=file_path,
                    source_section=clo_heading,
                    parser_version=PARSER_VERSION,
                )
        if clo_heading:
            graph.add_evidence(clo_id, section_ids[clo_heading], file_path, clo_heading, PARSER_VERSION)

    assessment_heading, assessment_lines = find_section(sections, "assessments")
    assessment_index: Dict[str, str] = {}
    for assessment in parse_assessments(course_id, assessment_lines):
        assessment_id = assessment["assessment_id"]
        assessment_index[assessment["code"]] = assessment_id
        graph.add_node(assessment_id, "Assessment", source_file=file_path, parser_version=PARSER_VERSION, **assessment)
        graph.add_edge(
            course_id,
            assessment_id,
            "HAS_ASSESSMENT",
            source_file=file_path,
            source_section=assessment_heading,
            parser_version=PARSER_VERSION,
        )
        if assessment_heading:
            graph.add_evidence(assessment_id, section_ids[assessment_heading], file_path, assessment_heading, PARSER_VERSION)

    topic_heading, topic_lines = find_section(sections, "teaching_plan")
    for topic in parse_topics(course_id, topic_lines):
        topic_id = topic["topic_id"]
        graph.add_node(
            topic_id,
            "Topic",
            source_file=file_path,
            parser_version=PARSER_VERSION,
            code=topic["code"],
            title=topic["title"],
            level=topic["level"],
            week_range=topic["week_range"],
            theory_hours=topic["theory_hours"],
            practice_hours=topic["practice_hours"],
            exercise_hours=topic["exercise_hours"],
            self_study_hours=topic["self_study_hours"],
            teaching_method_raw=topic["teaching_method_raw"],
            course_id=course_id,
        )
        graph.add_edge(
            course_id,
            topic_id,
            "HAS_TOPIC",
            source_file=file_path,
            source_section=topic_heading,
            parser_version=PARSER_VERSION,
        )
        for clo_code in topic["clo_refs"]:
            clo_id = clo_index.get(clo_code)
            if clo_id:
                graph.add_edge(
                    topic_id,
                    clo_id,
                    "SUPPORTS_CLO",
                    mapping_raw=clo_code,
                    source_file=file_path,
                    source_section=topic_heading,
                    parser_version=PARSER_VERSION,
                )
        for assessment_code in topic["assessment_refs"]:
            assessment_id = assessment_index.get(assessment_code)
            if assessment_id:
                graph.add_edge(
                    assessment_id,
                    topic_id,
                    "ASSESSES_TOPIC",
                    mapping_raw=assessment_code,
                    source_file=file_path,
                    source_section=topic_heading,
                    parser_version=PARSER_VERSION,
                )
        if topic_heading:
            graph.add_evidence(topic_id, section_ids[topic_heading], file_path, topic_heading, PARSER_VERSION)

    material_heading, material_lines = find_section(sections, "materials")
    for material in parse_materials(material_lines):
        material_id = material["material_id"]
        graph.add_node(material_id, "Material", source_file=file_path, parser_version=PARSER_VERSION, **material)
        graph.add_edge(
            course_id,
            material_id,
            "USES_MATERIAL",
            source_file=file_path,
            source_section=material_heading,
            parser_version=PARSER_VERSION,
        )
        if material_heading:
            graph.add_evidence(material_id, section_ids[material_heading], file_path, material_heading, PARSER_VERSION)

    return graph


def parse_program_document(file_path: str, data: Dict[str, Any]) -> Tuple[GraphDocument, ProgramContext]:
    sections = get_sections(data)
    graph = GraphDocument()
    _, section_ids = create_document_nodes(graph, file_path, "program", sections)
    info = parse_program_info(file_path, sections)
    program_id = info["program_id"]

    graph.add_node(
        program_id,
        "Program",
        program_id=program_id,
        program_code=info["program_code"],
        name_vi=info["name_vi"],
        name_en=info["name_en"],
        cohort=info["cohort"],
        degree_level=info["degree_level"],
        duration_years=info["duration_years"],
        total_credits=info["total_credits"],
        source_file=file_path,
        parser_version=PARSER_VERSION,
    )

    if info["general_heading"]:
        graph.add_evidence(program_id, section_ids[info["general_heading"]], file_path, info["general_heading"], PARSER_VERSION)

    clo_heading, clo_lines = find_section(sections, "clos")
    for plo in parse_plos(program_id, clo_lines):
        plo_id = plo["plo_id"]
        graph.add_node(plo_id, "PLO", source_file=file_path, parser_version=PARSER_VERSION, **plo)
        graph.add_edge(
            program_id,
            plo_id,
            "HAS_PLO",
            source_file=file_path,
            source_section=clo_heading,
            parser_version=PARSER_VERSION,
        )
        if clo_heading:
            graph.add_evidence(plo_id, section_ids[clo_heading], file_path, clo_heading, PARSER_VERSION)

    for course_ref in parse_program_course_refs(program_id, sections):
        course_id = course_ref["course_id"]
        graph.add_node(
            course_id,
            "Course",
            course_id=course_id,
            course_code=course_ref["course_code"],
            name_vi=course_ref["name_vi"],
            credits=course_ref["credits"],
            is_reference=True,
            source_file=file_path,
        )
        graph.add_edge(
            course_id,
            program_id,
            "BELONGS_TO_PROGRAM",
            source_file=file_path,
            source_section=course_ref["source_section"],
            parser_version=PARSER_VERSION,
        )

    return graph, ProgramContext(
        program_id=program_id,
        program_name=info["name_vi"],
        cohort=info["cohort"],
    )


def is_program_file(file_path: str) -> bool:
    return os.path.basename(file_path).startswith("CTDT_")
