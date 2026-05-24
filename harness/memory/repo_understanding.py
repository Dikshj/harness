import ast
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".cs",
    ".swift",
}


@dataclass
class CodeSymbol:
    name: str
    kind: str
    path: str
    line: int
    signature: str = ""


@dataclass
class CodeSnippet:
    id: str
    path: str
    start_line: int
    end_line: int
    text: str
    symbols: list[str]
    embedding: list[float]


class RepositoryUnderstandingEngine:
    """Builds lightweight repository context without requiring external services."""

    def __init__(self, repo_path: str, memory_dir: str | None = None):
        self.repo_path = Path(repo_path).resolve()
        self.memory_dir = Path(memory_dir or self.repo_path / ".harness" / "memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def build_context(self) -> dict[str, Any]:
        files = list(self._iter_source_files())
        symbols: list[CodeSymbol] = []
        snippets: list[CodeSnippet] = []
        dependencies: dict[str, list[str]] = {}

        for path in files:
            rel = self._rel(path)
            text = path.read_text(errors="ignore")
            file_symbols = self._symbols_for_file(path, text)
            symbols.extend(file_symbols)
            dependencies[rel] = self._dependencies_for_file(path, text)
            snippets.extend(self._snippets_for_file(path, text, file_symbols))

        graph = self._reverse_dependency_graph(dependencies)
        context = {
            "repo_path": str(self.repo_path),
            "file_count": len(files),
            "symbols": [asdict(symbol) for symbol in symbols],
            "snippets": [asdict(snippet) for snippet in snippets],
            "dependencies": dependencies,
            "reverse_dependencies": graph,
        }
        self.persist(context)
        return context

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        context = self.load() or self.build_context()
        query_vec = self._embed(query)
        ranked = sorted(
            context["snippets"],
            key=lambda snippet: self._cosine(query_vec, snippet["embedding"]),
            reverse=True,
        )
        return ranked[:top_k]

    def persist(self, context: dict[str, Any]) -> None:
        (self.memory_dir / "repo_context.json").write_text(json.dumps(context, indent=2))

    def load(self) -> dict[str, Any] | None:
        path = self.memory_dir / "repo_context.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _iter_source_files(self) -> Iterable[Path]:
        ignored = {".git", ".venv", "node_modules", ".pytest_cache", ".harness", "__pycache__"}
        for path in self.repo_path.rglob("*"):
            if any(part in ignored for part in path.parts):
                continue
            if path.is_file() and path.suffix in CODE_EXTENSIONS and path.stat().st_size < 1_000_000:
                yield path

    def _symbols_for_file(self, path: Path, text: str) -> list[CodeSymbol]:
        if path.suffix != ".py":
            return self._line_symbols(path, text)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return self._line_symbols(path, text)

        symbols: list[CodeSymbol] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                args = ""
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = "(" + ", ".join(arg.arg for arg in node.args.args) + ")"
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        kind=node.__class__.__name__.replace("Def", "").lower(),
                        path=self._rel(path),
                        line=node.lineno,
                        signature=f"{node.name}{args}",
                    )
                )
        return symbols

    def _line_symbols(self, path: Path, text: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        for number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("function ", "class ", "export function ", "export class ")):
                name = stripped.replace("export ", "").split()[1].split("(", 1)[0]
                symbols.append(CodeSymbol(name=name, kind="symbol", path=self._rel(path), line=number, signature=stripped))
        return symbols

    def _dependencies_for_file(self, path: Path, text: str) -> list[str]:
        if path.suffix == ".py":
            return self._python_imports(text)
        deps: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or " from " in stripped and stripped.startswith("import"):
                deps.append(stripped)
        return deps[:100]

    def _python_imports(self, text: str) -> list[str]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        deps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                deps.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                deps.append(node.module)
        return sorted(set(deps))

    def _snippets_for_file(self, path: Path, text: str, symbols: list[CodeSymbol]) -> list[CodeSnippet]:
        lines = text.splitlines()
        if not lines:
            return []
        chunks: list[CodeSnippet] = []
        rel = self._rel(path)
        symbol_names = [symbol.name for symbol in symbols if symbol.path == rel]
        for start in range(0, len(lines), 80):
            chunk = "\n".join(lines[start : start + 80])
            digest = hashlib.sha1(f"{rel}:{start}".encode()).hexdigest()
            chunks.append(
                CodeSnippet(
                    id=digest,
                    path=rel,
                    start_line=start + 1,
                    end_line=min(start + 80, len(lines)),
                    text=chunk,
                    symbols=symbol_names,
                    embedding=self._embed(chunk),
                )
            )
        return chunks

    def _reverse_dependency_graph(self, dependencies: dict[str, list[str]]) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = defaultdict(list)
        for path, deps in dependencies.items():
            for dep in deps:
                graph[dep].append(path)
        return {key: sorted(value) for key, value in graph.items()}

    def _embed(self, text: str) -> list[float]:
        buckets = [0.0] * 64
        for token in re_tokens(text):
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % len(buckets)
            buckets[idx] += 1.0
        norm = sum(value * value for value in buckets) ** 0.5 or 1.0
        return [round(value / norm, 6) for value in buckets]

    def _cosine(self, left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.repo_path).as_posix()


def re_tokens(text: str) -> list[str]:
    current = []
    tokens = []
    for char in text.lower():
        if char.isalnum() or char == "_":
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens
