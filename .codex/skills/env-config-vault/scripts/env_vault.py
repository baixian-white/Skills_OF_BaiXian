#!/usr/bin/env python3
"""Local environment configuration vault for Codex skills.

Normal commands never print raw secret values. Use write-env to materialize
values into a project file without echoing them to stdout.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_DIR = Path(os.environ.get("CODEX_ENV_VAULT_DIR", Path.home() / ".codex" / "env-config-vault"))
DEFAULT_FILE = Path(os.environ.get("CODEX_ENV_VAULT_FILE", DEFAULT_DIR / "vault.json"))

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    ".nuxt",
    ".turbo",
    "dist",
    "build",
    "target",
    "coverage",
    "vendor",
}

TEXT_EXTS = {
    "",
    ".env",
    ".example",
    ".sample",
    ".local",
    ".development",
    ".production",
    ".md",
    ".txt",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".py",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".php",
    ".rb",
    ".cs",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".bat",
    ".cmd",
    ".dockerfile",
}

ENV_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
PATTERNS = [
    ("dotenv", re.compile(rf"^\s*(?:export\s+)?({ENV_NAME})\s*=", re.MULTILINE)),
    ("process.env", re.compile(rf"process\.env\.({ENV_NAME})")),
    ("process.env[]", re.compile(rf"process\.env\[['\"]({ENV_NAME})['\"]\]")),
    ("import.meta.env", re.compile(rf"import\.meta\.env\.({ENV_NAME})")),
    ("os.getenv", re.compile(rf"os\.getenv\(\s*['\"]({ENV_NAME})['\"]")),
    ("getenv", re.compile(rf"\bgetenv\(\s*['\"]({ENV_NAME})['\"]")),
    ("env()", re.compile(rf"\benv\(\s*['\"]({ENV_NAME})['\"]")),
    ("config()", re.compile(rf"\bconfig\(\s*['\"]({ENV_NAME})['\"]")),
    ("Deno.env", re.compile(rf"Deno\.env\.get\(\s*['\"]({ENV_NAME})['\"]")),
]
UPPER_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

INTERESTING_PARTS = (
    "API_KEY",
    "ACCESS_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASS",
    "PWD",
    "DATABASE_URL",
    "DB_URL",
    "POSTGRES_URL",
    "MYSQL_URL",
    "REDIS_URL",
    "MONGO_URL",
    "BASE_URL",
    "_URL",
    "_URI",
    "DSN",
    "HOST",
    "PORT",
    "USER",
    "USERNAME",
    "REGION",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def eprint(*parts: Any) -> None:
    print(*parts, file=sys.stderr)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "entry"


def infer_kind(name: str) -> str:
    upper = name.upper()
    if upper in {"DATABASE_URL", "DB_URL"} or upper.endswith(("DATABASE_URL", "DB_URL")):
        return "database_url"
    if "BASE_URL" in upper:
        return "base_url"
    if upper.endswith(("_URL", "_URI")) or upper in {"URL", "URI"}:
        return "url"
    if "API_KEY" in upper or upper.endswith("ACCESS_KEY_ID") or upper.endswith("_KEY"):
        return "api_key"
    if "ACCESS_KEY_SECRET" in upper or "SECRET" in upper:
        return "secret"
    if "TOKEN" in upper:
        return "token"
    if "PASSWORD" in upper or upper.endswith("_PASS") or upper.endswith("_PWD"):
        return "password"
    if upper.endswith(("USERNAME", "_USER")) or upper == "USER":
        return "username"
    if upper.endswith("_HOST") or upper == "HOST":
        return "host"
    if upper.endswith("_PORT") or upper == "PORT":
        return "port"
    if upper.endswith("REGION") or upper.endswith("REGION_ID"):
        return "region"
    return "other"


def is_interesting_name(name: str) -> bool:
    upper = name.upper()
    if upper.startswith(("NEXT_PUBLIC_", "VITE_", "REACT_APP_")):
        return True
    return any(part in upper or upper.endswith(part) for part in INTERESTING_PARTS)


def mask_value(value: str) -> str:
    if value == "":
        return ""
    safe = re.sub(r"//([^/@:\s]+):([^/@\s]+)@", "//***:***@", value)
    if safe != value:
        if len(safe) <= 80:
            return safe
        return safe[:38] + "..." + safe[-18:]
    if len(value) <= 8:
        return "*" * min(len(value), 8)
    return value[:4] + "..." + value[-4:]


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, ctypes.Array[Any]]:
    buf = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    return blob, buf


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def protect_value(value: str) -> dict[str, str]:
    raw = value.encode("utf-8")
    if os.name != "nt":
        return {
            "provider": "base64-plaintext-non-windows",
            "ciphertext": base64.b64encode(raw).decode("ascii"),
        }

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, _buf = _blob_from_bytes(raw)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "codex-env-config-vault",
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        encrypted = _bytes_from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return {
        "provider": "windows-dpapi-current-user",
        "ciphertext": base64.b64encode(encrypted).decode("ascii"),
    }


def unprotect_value(payload: dict[str, str]) -> str:
    provider = payload.get("provider", "")
    data = base64.b64decode(payload.get("ciphertext", ""))
    if provider == "base64-plaintext-non-windows":
        return data.decode("utf-8")
    if provider != "windows-dpapi-current-user":
        raise ValueError(f"unsupported protected value provider: {provider}")
    if os.name != "nt":
        raise RuntimeError("windows DPAPI value cannot be decrypted on this OS")

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, _buf = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    description = ctypes.c_wchar_p()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        raw = _bytes_from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return raw.decode("utf-8")


def vault_path() -> Path:
    return DEFAULT_FILE.expanduser()


def load_vault(path: Path | None = None) -> dict[str, Any]:
    path = path or vault_path()
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "created_at": now_iso(), "updated_at": now_iso(), "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError(f"unsupported vault schema version in {path}")
    data.setdefault("entries", [])
    return data


def save_vault(data: dict[str, Any], path: Path | None = None) -> None:
    path = path or vault_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def make_entry_id(name: str, service: str, scope: str, project: str | None) -> str:
    seed = f"{service}|{name}|{scope}|{project or ''}".lower()
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return f"{slugify(service or 'global')}-{slugify(name)}-{digest}"


def normalize_tags(tags: list[str] | None) -> list[str]:
    result: list[str] = []
    for item in tags or []:
        for part in item.split(","):
            tag = part.strip().lower()
            if tag and tag not in result:
                result.append(tag)
    return result


def normalize_aliases(aliases: list[str] | None) -> list[str]:
    result: list[str] = []
    for item in aliases or []:
        for part in item.split(","):
            alias = part.strip()
            if alias and alias not in result:
                result.append(alias)
    return result


def upsert_entry(
    data: dict[str, Any],
    *,
    name: str,
    value: str,
    service: str,
    kind: str | None,
    scope: str,
    project: str | None,
    aliases: list[str] | None,
    tags: list[str] | None,
    note: str | None,
    sensitive: bool,
) -> tuple[dict[str, Any], bool]:
    name = name.strip()
    service = service.strip() if service else "global"
    kind = kind or infer_kind(name)
    project_norm = str(Path(project).resolve()) if project else None
    entry_id = make_entry_id(name, service, scope, project_norm)
    entries = data.setdefault("entries", [])
    existing = next((entry for entry in entries if entry.get("id") == entry_id), None)
    created = existing is None
    if existing is None:
        existing = {"id": entry_id, "created_at": now_iso()}
        entries.append(existing)
    existing.update(
        {
            "name": name,
            "service": service,
            "kind": kind,
            "scope": scope,
            "project": project_norm,
            "aliases": normalize_aliases(aliases),
            "tags": normalize_tags(tags),
            "note": note or "",
            "sensitive": bool(sensitive),
            "masked_value": mask_value(value),
            "protected_value": protect_value(value),
            "updated_at": now_iso(),
        }
    )
    return existing, created


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(ENV_NAME, key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            was_double_quoted = value[0] == '"'
            value = value[1:-1]
            if was_double_quoted:
                value = value.encode("utf-8").decode("unicode_escape")
        values[key] = value
    return values


def should_scan_file(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith(".env") or name in {
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "readme.md",
    }:
        return True
    suffixes = path.suffixes
    if suffixes and "".join(suffixes[-2:]).lower() in {".env.example", ".env.sample", ".env.local"}:
        return True
    return path.suffix.lower() in TEXT_EXTS


def iter_project_files(root: Path) -> list[Path]:
    files: list[Path] = []
    try:
        active_vault = vault_path().resolve()
    except OSError:
        active_vault = None
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        current_path = Path(current)
        for filename in filenames:
            path = current_path / filename
            if active_vault and path.resolve() == active_vault:
                continue
            if should_scan_file(path):
                files.append(path)
    return files


def scan_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    found: dict[str, dict[str, Any]] = {}
    files_scanned = 0
    files_skipped = 0
    for path in iter_project_files(root):
        try:
            if path.stat().st_size > 2_000_000:
                files_skipped += 1
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            files_skipped += 1
            continue
        files_scanned += 1
        rel = str(path.relative_to(root))
        for pattern_name, regex in PATTERNS:
            for match in regex.finditer(text):
                name = match.group(1)
                if is_interesting_name(name):
                    add_scan_hit(found, name, rel, text, match.start(1), pattern_name)
        for match in UPPER_TOKEN.finditer(text):
            name = match.group(0)
            if is_interesting_name(name):
                add_scan_hit(found, name, rel, text, match.start(0), "uppercase-token")
    variables = sorted(found.values(), key=lambda item: item["name"])
    return {
        "project": str(root),
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "variables": variables,
    }


def add_scan_hit(found: dict[str, dict[str, Any]], name: str, rel: str, text: str, pos: int, pattern_name: str) -> None:
    entry = found.setdefault(
        name,
        {
            "name": name,
            "kind": infer_kind(name),
            "sources": [],
        },
    )
    line = text.count("\n", 0, pos) + 1
    for source in entry["sources"]:
        if source["file"] == rel and source["line"] == line:
            if pattern_name not in source["pattern"].split("+"):
                source["pattern"] += f"+{pattern_name}"
            return
    entry["sources"].append({"file": rel, "line": line, "pattern": pattern_name})


def public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "service": entry.get("service"),
        "kind": entry.get("kind"),
        "scope": entry.get("scope"),
        "project": entry.get("project"),
        "aliases": entry.get("aliases", []),
        "tags": entry.get("tags", []),
        "sensitive": entry.get("sensitive", True),
        "masked_value": entry.get("masked_value", ""),
        "note": entry.get("note", ""),
        "updated_at": entry.get("updated_at"),
    }


def entry_matches_var(entry: dict[str, Any], var_name: str, service: str | None = None) -> int:
    if service and entry.get("service", "").lower() != service.lower():
        return 0
    name = entry.get("name", "")
    aliases = entry.get("aliases", [])
    upper_aliases = [alias.upper() for alias in aliases]
    if name == var_name:
        return 100
    if name.upper() == var_name.upper():
        return 95
    if var_name in aliases:
        return 90
    if var_name.upper() in upper_aliases:
        return 85
    if infer_kind(var_name) == entry.get("kind") and entry.get("service", "").lower() in var_name.lower():
        return 50
    return 0


def match_project(root: Path, service: str | None = None) -> dict[str, Any]:
    scan = scan_project(root)
    data = load_vault()
    result_vars = []
    for var in scan["variables"]:
        candidates = []
        for entry in data.get("entries", []):
            score = entry_matches_var(entry, var["name"], service=service)
            if score:
                item = public_entry(entry)
                item["score"] = score
                candidates.append(item)
        candidates.sort(key=lambda item: item["score"], reverse=True)
        result_vars.append({**var, "candidates": candidates})
    return {**scan, "variables": result_vars}


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_scan(scan: dict[str, Any]) -> None:
    print(f"Project: {scan['project']}")
    print(f"Files scanned: {scan['files_scanned']}  skipped: {scan['files_skipped']}")
    if not scan["variables"]:
        print("No interesting environment variables found.")
        return
    for var in scan["variables"]:
        sources = ", ".join(f"{src['file']}:{src['line']}" for src in var["sources"][:3])
        more = "" if len(var["sources"]) <= 3 else f" (+{len(var['sources']) - 3} more)"
        print(f"- {var['name']}  kind={var['kind']}  sources={sources}{more}")


def print_matches(matches: dict[str, Any]) -> None:
    print_scan({key: matches[key] for key in ["project", "files_scanned", "files_skipped", "variables"]})
    if not matches["variables"]:
        return
    print("")
    print("Matches:")
    for var in matches["variables"]:
        candidates = var.get("candidates", [])
        if not candidates:
            print(f"- {var['name']}: no saved entry")
            continue
        labels = [
            f"{cand['id']} service={cand['service']} masked={cand['masked_value']} score={cand['score']}"
            for cand in candidates[:3]
        ]
        print(f"- {var['name']}: " + " | ".join(labels))


def filter_entries(data: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    entries = data.get("entries", [])
    if getattr(args, "service", None):
        entries = [e for e in entries if e.get("service", "").lower() == args.service.lower()]
    if getattr(args, "name", None):
        target = args.name.upper()
        entries = [
            e
            for e in entries
            if e.get("name", "").upper() == target or target in [alias.upper() for alias in e.get("aliases", [])]
        ]
    if getattr(args, "tag", None):
        tag = args.tag.lower()
        entries = [e for e in entries if tag in [t.lower() for t in e.get("tags", [])]]
    return entries


def find_entry(data: dict[str, Any], ident: str) -> dict[str, Any]:
    matches = []
    ident_upper = ident.upper()
    for entry in data.get("entries", []):
        if entry.get("id") == ident or entry.get("name", "").upper() == ident_upper:
            matches.append(entry)
        elif ident_upper in [alias.upper() for alias in entry.get("aliases", [])]:
            matches.append(entry)
    if not matches:
        raise SystemExit(f"no entry found for {ident}")
    if len(matches) > 1:
        ids = ", ".join(entry["id"] for entry in matches)
        raise SystemExit(f"ambiguous entry {ident}; use one id: {ids}")
    return matches[0]


def gitignore_allows(project: Path, out_path: Path) -> bool:
    gitignore = project / ".gitignore"
    if not gitignore.exists():
        return False
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    try:
        rel = "/" + out_path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        rel = ""
    name = out_path.name
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line in {".env", ".env*", "*.env", name, "/" + name, rel}:
            return True
        if line.endswith("*") and name.startswith(line[:-1].lstrip("/")):
            return True
    return False


def existing_env_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(parse_dotenv(path).keys())


def build_env_lines(project: Path, args: argparse.Namespace) -> tuple[list[str], list[str], list[str]]:
    matches = match_project(project, service=args.service)
    data = load_vault()
    entries_by_id = {entry["id"]: entry for entry in data.get("entries", [])}
    lines: list[str] = []
    filled: list[str] = []
    unmatched: list[str] = []
    ambiguous: list[str] = []
    for var in matches["variables"]:
        name = var["name"]
        if args.mode == "example":
            lines.append(f"{name}=")
            continue
        candidates = [cand for cand in var.get("candidates", []) if cand.get("score", 0) >= 85]
        if len(candidates) == 1:
            entry = entries_by_id[candidates[0]["id"]]
            lines.append(f"{name}={dotenv_quote(unprotect_value(entry['protected_value']))}")
            filled.append(name)
        elif len(candidates) > 1:
            ambiguous.append(name)
            if args.include_unmatched:
                lines.append(f"{name}=")
        else:
            unmatched.append(name)
            if args.include_unmatched:
                lines.append(f"{name}=")
    return lines, filled, unmatched + ambiguous


def dotenv_quote(value: str) -> str:
    if value == "":
        return ""
    if re.search(r"\s|#|'|\"|\\|\n", value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return value


def cmd_init(_args: argparse.Namespace) -> None:
    path = vault_path()
    data = load_vault(path)
    save_vault(data, path)
    print(f"Vault: {path}")
    print(f"Entries: {len(data.get('entries', []))}")


def cmd_scan(args: argparse.Namespace) -> None:
    scan = scan_project(Path(args.project))
    print_json(scan) if args.json else print_scan(scan)


def cmd_match(args: argparse.Namespace) -> None:
    matches = match_project(Path(args.project), service=args.service)
    print_json(matches) if args.json else print_matches(matches)


def cmd_add(args: argparse.Namespace) -> None:
    if args.prompt:
        value = getpass.getpass(f"Value for {args.name}: ")
    elif args.value_stdin:
        value = sys.stdin.read().rstrip("\r\n")
    elif args.value is not None:
        value = args.value
    else:
        raise SystemExit("provide --prompt, --value-stdin, or --value")
    data = load_vault()
    entry, created = upsert_entry(
        data,
        name=args.name,
        value=value,
        service=args.service or "global",
        kind=args.kind,
        scope=args.scope,
        project=args.project,
        aliases=args.alias or [],
        tags=args.tag or [],
        note=args.note,
        sensitive=not args.non_sensitive,
    )
    save_vault(data)
    action = "created" if created else "updated"
    print(f"{action}: {entry['id']} name={entry['name']} service={entry['service']} masked={entry['masked_value']}")


def cmd_import_dotenv(args: argparse.Namespace) -> None:
    if not args.yes:
        raise SystemExit("importing real values requires --yes after user confirmation")
    source = Path(args.file)
    values = parse_dotenv(source)
    only = set(args.only or [])
    data = load_vault()
    imported = []
    for name, value in values.items():
        if only and name not in only:
            continue
        if value == "" and args.skip_empty:
            continue
        entry, _created = upsert_entry(
            data,
            name=name,
            value=value,
            service=args.service or source.parent.name,
            kind=None,
            scope=args.scope,
            project=args.project,
            aliases=[],
            tags=args.tag or [],
            note=args.note,
            sensitive=True,
        )
        imported.append(public_entry(entry))
    save_vault(data)
    print(f"Imported {len(imported)} values from {source}")
    for entry in imported:
        print(f"- {entry['name']} service={entry['service']} masked={entry['masked_value']}")


def cmd_list(args: argparse.Namespace) -> None:
    entries = [public_entry(e) for e in filter_entries(load_vault(), args)]
    entries.sort(key=lambda e: (e.get("service") or "", e.get("name") or ""))
    if args.json:
        print_json(entries)
        return
    if not entries:
        print("No entries.")
        return
    for entry in entries:
        tags = ",".join(entry.get("tags", []))
        print(
            f"- {entry['id']} name={entry['name']} service={entry['service']} "
            f"kind={entry['kind']} masked={entry['masked_value']} tags={tags}"
        )


def cmd_get(args: argparse.Namespace) -> None:
    entry = find_entry(load_vault(), args.ident)
    if args.reveal:
        print(unprotect_value(entry["protected_value"]))
    else:
        print_json(public_entry(entry))


def cmd_remove(args: argparse.Namespace) -> None:
    data = load_vault()
    entry = find_entry(data, args.ident)
    if not args.yes:
        raise SystemExit(f"removing {entry['id']} requires --yes")
    data["entries"] = [e for e in data.get("entries", []) if e.get("id") != entry["id"]]
    save_vault(data)
    print(f"removed: {entry['id']}")


def cmd_write_env(args: argparse.Namespace) -> None:
    project = Path(args.project).resolve()
    out = Path(args.out).resolve() if args.out else project / ".env"
    if args.mode == "fill" and not args.yes:
        raise SystemExit("writing real secret values requires --yes after user confirmation")
    if args.mode == "fill" and not args.allow_unignored and not gitignore_allows(project, out):
        raise SystemExit(f"refusing to write secrets to unignored file: {out}")
    if out.exists() and not args.overwrite and not args.append:
        raise SystemExit(f"{out} exists; use --overwrite or --append")
    lines, filled, unresolved = build_env_lines(project, args)
    if args.append:
        existing = existing_env_keys(out)
        lines = [line for line in lines if line.split("=", 1)[0] not in existing]
        prefix = out.read_text(encoding="utf-8") if out.exists() else ""
        content = prefix
        if content and not content.endswith("\n"):
            content += "\n"
        if lines:
            content += "\n".join(lines) + "\n"
    else:
        content = "\n".join(lines) + ("\n" if lines else "")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"Wrote {out}")
    if args.mode == "fill":
        print(f"Filled: {', '.join(filled) if filled else 'none'}")
        print(f"Unresolved or ambiguous: {', '.join(unresolved) if unresolved else 'none'}")
    else:
        print(f"Example variables: {len(lines)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a local encrypted environment config vault.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create or inspect the vault")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("scan", help="scan a project for environment variable names")
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("match", help="scan a project and match variables to saved vault entries")
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--service")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_match)

    p = sub.add_parser("add", help="add or update one vault entry")
    p.add_argument("--name", required=True)
    p.add_argument("--value")
    p.add_argument("--value-stdin", action="store_true")
    p.add_argument("--prompt", action="store_true")
    p.add_argument("--service", default="global")
    p.add_argument("--kind", choices=["api_key", "base_url", "database_url", "url", "secret", "token", "password", "username", "host", "port", "region", "other"])
    p.add_argument("--scope", default="global", choices=["global", "service", "project"])
    p.add_argument("--project")
    p.add_argument("--alias", action="append")
    p.add_argument("--tag", action="append")
    p.add_argument("--note")
    p.add_argument("--non-sensitive", action="store_true")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("import-dotenv", help="import real values from a trusted dotenv file")
    p.add_argument("file")
    p.add_argument("--service")
    p.add_argument("--scope", default="project", choices=["global", "service", "project"])
    p.add_argument("--project")
    p.add_argument("--only", action="append")
    p.add_argument("--tag", action="append")
    p.add_argument("--note")
    p.add_argument("--skip-empty", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_import_dotenv)

    p = sub.add_parser("list", help="list masked entries")
    p.add_argument("--service")
    p.add_argument("--name")
    p.add_argument("--tag")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("get", help="show one entry; reveal only with --reveal")
    p.add_argument("ident")
    p.add_argument("--reveal", action="store_true")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("remove", help="remove one entry")
    p.add_argument("ident")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("write-env", help="write .env or .env.example from scan results")
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--out")
    p.add_argument("--mode", choices=["fill", "example"], default="fill")
    p.add_argument("--service")
    p.add_argument("--include-unmatched", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--append", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--allow-unignored", action="store_true")
    p.set_defaults(func=cmd_write_env)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        eprint("cancelled")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
