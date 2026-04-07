"""
Smoke test for the local FastAPI backend.

Examples:
    python test_server_smoke.py --start-server --limit 1
    python test_server_smoke.py --all
    python test_server_smoke.py --all --isolate-sessions
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


DEFAULT_BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:7860")

TEST_QUERIES = [
    "giảng viên môn giải tích 2A",
    "cách tính điểm môn đó là gì",
    "cho tôi thông tin về môn toán rời rạc 1A",
    "Tài liệu môn học Phương trình toán lý",
    "số tín chỉ của môn chuyên đề giải tích số",
    "Thông tin về môn topo",
    "ai dạy môn giải toán sơ cấp, và số tính chỉ của môn này",
    "Môn Giải tích 2A có bao nhiêu tín chỉ và mã môn học là gì?",
    "Học phần thực hành của Toán rời rạc 1A có bắt buộc không?",
    "Danh sách các giảng viên dạy môn Phương trình Toán lý trong học kỳ này?",
    "Tỷ lệ điểm giữa kỳ và cuối kỳ của môn Giải toán sơ cấp là bao nhiêu?",
    "Nếu vắng thi giữa kỳ môn Giải tích 2A thì có được thi cuối kỳ không?",
    "Tài liệu nào là bắt buộc cho môn Phương trình Toán lý?",
]

PROBLEMATIC_QUERIES = [
    "Tài liệu môn học Phương trình toán lý",
    "Thông tin về môn topo",
    "Danh sách các giảng viên dạy môn Phương trình Toán lý trong học kỳ này?",
    "Tài liệu nào là bắt buộc cho môn Phương trình Toán lý?",
]


def request_json(method: str, url: str, payload: dict | None = None, timeout: float = 60.0) -> dict:
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def health_check(base_url: str, timeout: float = 5.0) -> dict | None:
    try:
        return request_json("GET", f"{base_url}/health", timeout=timeout)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def wait_for_health(base_url: str, timeout: float) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        health = health_check(base_url)
        if health:
            return health
        time.sleep(2)
    raise RuntimeError(f"Backend did not become healthy within {timeout:.0f}s: {base_url}")


def start_server(base_url: str) -> subprocess.Popen:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 7860)

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            host,
            "--port",
            port,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def pick_queries(limit: int | None, run_all: bool) -> list[str]:
    if run_all:
        return TEST_QUERIES
    if limit is None:
        limit = 1
    return TEST_QUERIES[: max(limit, 0)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the local course Q&A backend.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--start-server", action="store_true", help="Start uvicorn temporarily if the backend is not already running.")
    parser.add_argument("--all", action="store_true", help="Run all sample questions.")
    parser.add_argument("--problematic", action="store_true", help="Run the previously problematic retrieval queries.")
    parser.add_argument("--query", action="append", help="Run one custom query. Can be provided multiple times.")
    parser.add_argument("--limit", type=int, default=1, help="Number of sample questions to run when --all is not set.")
    parser.add_argument("--session-id", default="smoke-test")
    parser.add_argument("--isolate-sessions", action="store_true", help="Use a different session_id for each query.")
    parser.add_argument("--startup-timeout", type=float, default=150.0)
    parser.add_argument("--request-timeout", type=float, default=180.0)
    args = parser.parse_args()

    server_process = None
    try:
        health = health_check(args.base_url)
        if health is None:
            if not args.start_server:
                print(f"Backend is not reachable at {args.base_url}.")
                print("Start it with: python backend/main.py")
                print("Or run this smoke test with: python test_server_smoke.py --start-server")
                return 1

            print(f"Starting temporary backend at {args.base_url} ...")
            server_process = start_server(args.base_url)
            health = wait_for_health(args.base_url, args.startup_timeout)

        print("Health OK:", json.dumps(health, ensure_ascii=False))

        if args.query:
            queries = args.query
        elif args.problematic:
            queries = PROBLEMATIC_QUERIES
        else:
            queries = pick_queries(args.limit, args.all)
        if not queries:
            print("No /ask queries requested; server startup smoke test passed.")
            return 0

        for index, question in enumerate(queries, start=1):
            session_id = f"{args.session_id}-{index}" if args.isolate_sessions else args.session_id
            payload = {
                "question": question,
                "session_id": session_id,
                "use_advanced": True,
                "model_mode": "detail",
                "chat_history": [],
            }
            response = request_json(
                "POST",
                f"{args.base_url}/ask",
                payload=payload,
                timeout=args.request_timeout,
            )

            answer = response.get("answer", "")
            print(f"\n[{index}/{len(queries)}] {question}")
            print("search_method:", response.get("search_method"))
            print("need_clarification:", response.get("need_clarification", False))
            print("timing_ms:", round(float(response.get("timing_ms", 0)), 2))
            print("answer_preview:", answer[:300].replace("\n", " "))
            if response.get("candidates"):
                print("candidates:", response["candidates"])

        return 0
    finally:
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
