import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class MemoryRecord:
    task_id: str
    node_id: str
    role: str
    content: str
    metadata: dict
    created_at: str


class JsonlMemoryStore:
    def __init__(self, path: str | Path = ".rlm_memory.jsonl"):
        self.path = Path(path)

    def append(self, task_id: str, node_id: str, role: str, content: str, metadata: dict | None = None) -> MemoryRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = MemoryRecord(
            task_id=task_id,
            node_id=node_id,
            role=role,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def search(self, query: str, limit: int = 8) -> list[dict]:
        terms = {part.lower() for part in query.split() if len(part) > 2}
        scored: list[tuple[int, dict]] = []
        for record in self._iter_records():
            haystack = f"{record.get('role', '')} {record.get('content', '')}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
        return [record for _, record in scored[:limit]]

    def _iter_records(self) -> Iterable[dict]:
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records
