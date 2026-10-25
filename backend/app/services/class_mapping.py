"""Model output index -> class names. The server is the only place labels come from (ARCHITECTURE §2.1)."""

import json
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_LANGUAGES = ("en", "hi")


@dataclass(frozen=True)
class DiseaseClass:
    index: int
    class_key: str
    crop: str
    disease: str
    is_healthy: bool
    is_supported: bool = True
    names: dict[str, dict[str, str]] = field(default_factory=dict)  # lang -> {crop, disease}

    def display(self, lang: str) -> tuple[str, str]:
        n = self.names.get(lang, {})
        return n.get("crop", self.crop), n.get("disease", self.disease)


@dataclass(frozen=True)
class ClassMapping:
    version: str
    classes: list[DiseaseClass]
    crops: dict[str, list[int]]  # crop display name (English) -> class indices
    crop_names: dict[str, dict[str, str]]  # crop -> lang -> name

    @property
    def num_classes(self) -> int:
        return len(self.classes)

    def crop_display(self, crop: str, lang: str) -> str:
        return self.crop_names.get(crop, {}).get(lang, crop)

    def find_crop(self, name: str) -> str | None:
        wanted = name.strip().lower()
        return next((c for c in self.crops if c.lower() == wanted), None)


def _load_translations(directory: Path | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if directory and directory.is_dir():
        for lang in SUPPORTED_LANGUAGES:
            p = directory / f"{lang}.json"
            if p.exists():
                out[lang] = json.loads(p.read_text(encoding="utf-8"))
    return out


def load_class_mapping(path: Path, translations_dir: Path | None = None) -> ClassMapping:
    raw = json.loads(path.read_text(encoding="utf-8"))
    tr = _load_translations(translations_dir)
    classes: list[DiseaseClass] = []
    for i, c in enumerate(sorted(raw["classes"], key=lambda c: c["index"])):
        if c["index"] != i:
            raise ValueError(f"class_mapping.json: indices must be 0..N-1 without gaps (found {c['index']} at {i})")
        names: dict[str, dict[str, str]] = {}
        for lang, t in tr.items():
            entry = dict(t.get("classes", {}).get(c["class_key"], {}))
            entry.setdefault("crop", t.get("crops", {}).get(c["crop"], c["crop"]))
            entry.setdefault("disease", t.get("diseases", {}).get(c["disease"], c["disease"]))
            names[lang] = entry
        classes.append(DiseaseClass(
            index=c["index"], class_key=c["class_key"], crop=c["crop"], disease=c["disease"],
            is_healthy=bool(c.get("is_healthy", False)), is_supported=bool(c.get("is_supported", True)),
            names=names,
        ))
    if "num_classes" in raw and raw["num_classes"] != len(classes):
        raise ValueError("class_mapping.json: num_classes does not match the number of classes")

    crops: dict[str, list[int]] = {}
    if raw.get("crops"):
        for entry in raw["crops"]:
            crops[entry["crop"]] = sorted(int(i) for i in entry["class_indices"])
    else:
        for c in classes:
            crops.setdefault(c.crop, []).append(c.index)
    crop_names = {crop: {lang: t.get("crops", {}).get(crop, crop) for lang, t in tr.items()} for crop in crops}
    return ClassMapping(version=str(raw.get("version", "unknown")), classes=classes, crops=crops,
                        crop_names=crop_names)
