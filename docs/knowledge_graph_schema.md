# Knowledge Graph Schema for `lecture_chatbot`

This document defines the initial schema-first Knowledge Graph (KG) design for the syllabus corpus in this repository.

The current dataset is highly structured. Most JSON files under `BM_*` follow the same syllabus layout and can be parsed with rules before introducing heavier LLM-based extraction. The POC therefore prioritizes:

1. Structural graph extraction from syllabus sections.
2. Provenance on every important node and edge.
3. JSONL graph output that can later be loaded into Neo4j, Memgraph, or another graph engine.

## Design Principles

- Use stable synthetic identifiers instead of raw course codes alone.
- Preserve provenance with `source_file`, `source_section`, and `parser_version`.
- Parse structural entities first and add semantic concept extraction later.
- Keep graph output engine-agnostic.

## Node Types

### `Program`

Represents a training program or curriculum document such as `CTDT_K2024_Toan_hoc.json`.

Core properties:

- `program_id`
- `program_code`
- `name_vi`
- `name_en`
- `cohort`
- `degree_level`
- `duration_years`
- `total_credits`
- `source_file`

### `Department`

Represents an academic department or subject area.

Core properties:

- `department_id`
- `name_vi`
- `name_raw`
- `faculty`
- `source_file`

### `Course`

Represents a single syllabus/course document.

Core properties:

- `course_id`
- `course_code`
- `name_vi`
- `name_en`
- `credits`
- `theory_hours`
- `practice_hours`
- `exercise_hours`
- `knowledge_type`
- `is_project`
- `is_thesis`
- `is_reference`
- `source_file`

### `Lecturer`

Represents a lecturer or instructor mentioned in the syllabus.

Core properties:

- `lecturer_id`
- `full_name`
- `title`
- `degree`
- `email`
- `affiliation`
- `source_file`

### `Objective`

Represents course objectives such as `MH1.1`.

Core properties:

- `objective_id`
- `code`
- `category`
- `description`
- `bloom_level`
- `course_id`
- `source_file`

### `CLO`

Represents course learning outcomes such as `CHP1`.

Core properties:

- `clo_id`
- `code`
- `category`
- `description`
- `teaching_level`
- `course_id`
- `source_file`

### `PLO`

Represents program learning outcomes such as `CCT1.4`.

Core properties:

- `plo_id`
- `code`
- `category`
- `description`
- `bloom_level`
- `program_id`
- `source_file`

### `Topic`

Represents a chapter, subtopic, or teaching plan item.

Core properties:

- `topic_id`
- `code`
- `title`
- `level`
- `week_range`
- `theory_hours`
- `practice_hours`
- `exercise_hours`
- `self_study_hours`
- `teaching_method_raw`
- `course_id`
- `source_file`

### `Assessment`

Represents an assessment item such as `ĐG1.1` or `DG2`.

Core properties:

- `assessment_id`
- `code`
- `name`
- `assessment_group`
- `weight`
- `method_written`
- `method_mcq`
- `method_oral`
- `method_other`
- `note`
- `course_id`
- `source_file`

### `Material`

Represents a textbook or reference material.

Core properties:

- `material_id`
- `title`
- `authors_raw`
- `year`
- `publisher`
- `material_type`
- `location`
- `source_file`

### `Document`

Represents the original JSON file.

Core properties:

- `document_id`
- `doc_type`
- `file_name`
- `file_path`

### `Section`

Represents a parsed section inside a document.

Core properties:

- `section_id`
- `heading_raw`
- `heading_norm`
- `content_raw`
- `file_path`

## Edge Types

### Structural edges

- `HAS_SECTION`: `Document -> Section`
- `OFFERS`: `Department -> Course`
- `BELONGS_TO_PROGRAM`: `Course -> Program`
- `TAUGHT_BY`: `Course -> Lecturer`
- `AFFILIATED_WITH`: `Lecturer -> Department`
- `HAS_OBJECTIVE`: `Course -> Objective`
- `HAS_CLO`: `Course -> CLO`
- `HAS_PLO`: `Program -> PLO`
- `HAS_TOPIC`: `Course -> Topic`
- `HAS_ASSESSMENT`: `Course -> Assessment`
- `USES_MATERIAL`: `Course -> Material`

### Alignment edges

- `ALIGNS_WITH_OBJECTIVE`: `CLO -> Objective`
- `ALIGNS_WITH_PLO`: `CLO -> PLO`
- `SUPPORTS_CLO`: `Topic -> CLO`
- `ASSESSES_TOPIC`: `Assessment -> Topic`

### Dependency edges

- `REQUIRES`: `Course -> Course`
- `PRECEDED_BY`: `Course -> Course`
- `COREQUISITE_WITH`: `Course -> Course`

### Provenance edges

- `EVIDENCED_BY`: `Entity -> Section`

## ID Strategy

The graph should not rely on `course_code` as a unique identifier because some source files use placeholders such as `MTHxxxxx`.

Recommended IDs:

- `program_id = program:{slug(program_name)}:{cohort}`
- `department_id = department:{slug(department_name)}`
- `course_id = course:{slug(file_stem)}`
- `lecturer_id = lecturer:{slug(full_name)}`
- `objective_id = objective:{course_id}:{slug(code)}`
- `clo_id = clo:{course_id}:{slug(code)}`
- `plo_id = plo:{program_id}:{slug(code)}`
- `topic_id = topic:{course_id}:{slug(code_or_title)}`
- `assessment_id = assessment:{course_id}:{slug(code)}`
- `material_id = material:{sha1(author|title|year)}`

## Parsing Priorities

### Phase 1: structural sections

- `Thông tin chung về học phần`
- `Thông tin về giảng viên`
- `Mục tiêu của học phần`
- `Chuẩn đầu ra`
- `Hình thức, phương pháp và trọng số đánh giá kết quả học phần`
- `Kế hoạch giảng dạy chi tiết`
- `Tài liệu học tập`
- `Quy định của môn học`
- Program-level `CTDT_*` sections

### Phase 2: semantic enrichment

- course concepts
- inferred skills
- teaching methods
- topic similarity

## Output Contract

The builder script should emit:

- `index/knowledge_graph/nodes.jsonl`
- `index/knowledge_graph/edges.jsonl`
- `index/knowledge_graph/stats.json`

Each JSONL record should contain:

- `id`
- `label` or `type`
- `properties`
- provenance fields where available

## Current POC Assumption

This repository currently appears to focus on a single main program dataset. The initial builder is allowed to use the only detected `Program` as the default `program_id` when linking course-level `CLO -> PLO` mappings. If more programs are added later, the builder should be upgraded to explicit course-to-program resolution.
