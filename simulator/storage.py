"""Sauvegarde et rechargement des scénarios (un fichier JSON par scénario).

Format du fichier :
    {"version": 1, "name": "...", "saved_at": "2026-10-02T12:00:00", "params": {...}}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .params import SimulationParams

FORMAT_VERSION = 1
SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios"
MAX_NAME_LENGTH = 60


@dataclass(frozen=True)
class ScenarioInfo:
    name: str
    saved_at: str
    path: Path


def clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not name:
        raise ValueError("Donnez un nom au scénario.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Le nom est trop long ({MAX_NAME_LENGTH} caractères maximum).")
    return name


def slugify(name: str) -> str:
    """Nom de fichier sûr : lettres, chiffres, tirets et underscores uniquement."""
    slug = re.sub(r"[^\w\-]+", "_", clean_name(name), flags=re.UNICODE).strip("_")
    return slug or "scenario"


def _path(name: str, directory: Path | None) -> Path:
    return (directory or SCENARIO_DIR) / f"{slugify(name)}.json"


def to_json(name: str, params: SimulationParams) -> str:
    payload = {
        "version": FORMAT_VERSION,
        "name": clean_name(name),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "params": params.to_dict(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def from_json(text: str) -> tuple[str, SimulationParams]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("Ce fichier n'est pas un scénario valide (JSON illisible).") from None
    if not isinstance(payload, dict) or "params" not in payload:
        raise ValueError("Ce fichier n'est pas un scénario du simulateur.")
    if payload.get("version", FORMAT_VERSION) > FORMAT_VERSION:
        raise ValueError("Ce scénario vient d'une version plus récente du simulateur.")
    name = clean_name(str(payload.get("name") or "Scénario importé"))
    return name, SimulationParams.from_dict(payload["params"])


def exists(name: str, directory: Path | None = None) -> bool:
    return _path(name, directory).exists()


def save(name: str, params: SimulationParams, directory: Path | None = None) -> Path:
    path = _path(name, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_json(name, params), encoding="utf-8")
    return path


def load(name: str, directory: Path | None = None) -> SimulationParams:
    path = _path(name, directory)
    if not path.exists():
        raise ValueError(f"Scénario « {name} » introuvable.")
    return from_json(path.read_text(encoding="utf-8"))[1]


def delete(name: str, directory: Path | None = None) -> None:
    _path(name, directory).unlink(missing_ok=True)


def list_scenarios(directory: Path | None = None) -> list[ScenarioInfo]:
    folder = directory or SCENARIO_DIR
    if not folder.exists():
        return []
    infos = []
    for path in folder.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            infos.append(ScenarioInfo(clean_name(str(payload["name"])), str(payload.get("saved_at", "")), path))
        except (OSError, ValueError, KeyError, TypeError):
            continue  # fichier étranger ou corrompu : ignoré
    return sorted(infos, key=lambda info: info.name.casefold())
