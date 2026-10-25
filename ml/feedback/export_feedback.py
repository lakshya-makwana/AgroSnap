"""[A2] Turn consented farmer feedback into labelled image folders for retraining / the independent test set.

Usage:
    python ml/feedback/export_feedback.py --db backend/agrosnap_local.db \
        --photos backend/feedback_store --mapping ml/artifacts/class_mapping.json --out ml/data/field_feedback

Output: <out>/<class_key>/<feedback_id>.jpg plus <out>/manifest.csv. Only rows with photo consent and a
known label ("correct" -> predicted class, "wrong" -> corrected class) are exported. Rows from a different
mapping version are skipped, because their class indices may mean something else.

Labels from farmers are noisy. Have an agronomist check them before using them as test labels.
"""

import argparse
import csv
import json
import shutil
import sqlite3
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True, help="SQLite file (for PostgreSQL, export the table to SQLite)")
    ap.add_argument("--photos", type=Path, required=True)
    ap.add_argument("--mapping", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    keys = {c["index"]: c["class_key"] for c in mapping["classes"]}
    con = sqlite3.connect(args.db)
    rows = con.execute(
        "SELECT id, verdict, predicted_class_id, correct_class_id, crop, model_version, mapping_version, image_key, "
        "created_at FROM feedback WHERE photo_consent = 1 AND image_key IS NOT NULL"
    ).fetchall()

    args.out.mkdir(parents=True, exist_ok=True)
    exported = skipped = 0
    with (args.out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["feedback_id", "class_key", "verdict", "crop", "model_version", "created_at", "path"])
        for fid, verdict, pred, corr, crop, model_version, mapping_version, image_key, created in rows:
            label = pred if verdict == "correct" else corr if verdict == "wrong" else None
            src = args.photos / image_key
            if label is None or mapping_version != mapping["version"] or label not in keys or not src.exists():
                skipped += 1
                continue
            dst = args.out / keys[label] / f"{fid}.jpg"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            w.writerow([fid, keys[label], verdict, crop, model_version, created, dst.relative_to(args.out)])
            exported += 1
    print(f"Exported {exported} photos, skipped {skipped} (unsure, other mapping version, or missing file).")


if __name__ == "__main__":
    main()
