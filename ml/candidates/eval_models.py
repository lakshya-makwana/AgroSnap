"""Compare the trained AgroSnap models on the held-out split and install the best one in ml/artifacts.

Selection follows the v3 notebook: best VALIDATION macro F1 (test is reported, never used to choose).
Preprocessing is the notebook's eval path: 256x256 cached JPEG -> tf.image.resize 224 bilinear, 0-255 float32.
"""
import hashlib, json, shutil, sys, time
from pathlib import Path

import numpy as np
import tensorflow as tf
import keras

ROOT = Path(__file__).resolve().parents[2]          # AgroSnap/
CAND = ROOT / "ml" / "candidates"
ART = ROOT / "ml" / "artifacts"
EVAL = CAND / "eval_set"
IMG = 224
SEED = 42

rows = [l.rstrip("\n").split(",") for l in (EVAL / "eval_set.csv").read_text().splitlines()]
head, rows = rows[0], rows[1:]
ci = {k: i for i, k in enumerate(head)}
mapping = json.loads((EVAL / "class_mapping.json").read_text())
NUM = mapping["num_classes"]
split = {s: [(EVAL / "images" / r[ci["image_path"]], int(r[ci["label"]])) for r in rows if r[ci["split"]] == s]
         for s in ("val", "test")}
print(f"{NUM} classes | val {len(split['val'])} | test {len(split['test'])} images")


def load_batch(items):
    x = [tf.image.resize(tf.cast(tf.io.decode_jpeg(tf.io.read_file(str(p)), channels=3), tf.float32),
                         [IMG, IMG], method="bilinear") for p, _ in items]
    return tf.stack(x)


def probs(model, items, tta, bs=32):
    out = []
    for i in range(0, len(items), bs):
        x = load_batch(items[i:i + bs])
        p = model(x, training=False).numpy().astype(np.float64)
        if tta:
            p = (p + model(tf.image.flip_left_right(x), training=False).numpy()) / 2.0
        out.append(p)
    return np.concatenate(out)


def macro_f1(y, yp):
    f = []
    for c in range(NUM):
        tp = np.sum((yp == c) & (y == c)); fp = np.sum((yp == c) & (y != c)); fn = np.sum((yp != c) & (y == c))
        if tp + fp + fn == 0:
            continue
        f.append(2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f))


def weighted_f1(y, yp):
    tot = 0.0
    for c in range(NUM):
        n = np.sum(y == c)
        if n == 0:
            continue
        tp = np.sum((yp == c) & (y == c)); fp = np.sum((yp == c) & (y != c)); fn = n - tp
        tot += n * (2 * tp / (2 * tp + fp + fn))
    return float(tot / len(y))


def ci95(y, yp, fn, n=1000):
    r = np.random.default_rng(SEED)
    v = [fn(y[i], yp[i]) for i in (r.integers(0, len(y), len(y)) for _ in range(n))]
    lo, hi = np.percentile(v, [2.5, 97.5])
    return f"{lo:.3f}-{hi:.3f}"


def acc(y, yp): return float(np.mean(y == yp))
def top3(y, p): return float(np.mean([y[i] in np.argsort(p[i])[-3:] for i in range(len(y))]))


def cpu_ms(model, n=20):
    x = tf.random.uniform([1, IMG, IMG, 3], 0, 255)
    model(x, training=False)
    t = time.perf_counter()
    for _ in range(n):
        model(x, training=False)
    return (time.perf_counter() - t) / n * 1000


yv = np.array([l for _, l in split["val"]]); yt = np.array([l for _, l in split["test"]])
results, cache = [], {}
for f in sorted(CAND.glob("*_best.keras")):
    arch = f.name.replace("_best.keras", "")
    print(f"\n== {arch} ({f.stat().st_size / 2**20:.0f} MB): loading...", flush=True)
    m = keras.models.load_model(f, compile=False)
    assert m.output_shape[-1] == NUM, f"{arch}: {m.output_shape[-1]} outputs, mapping has {NUM}"
    t0 = time.time()
    pv = probs(m, split["val"], tta=True)
    pt0 = probs(m, split["test"], tta=False)
    pt1 = probs(m, split["test"], tta=True)
    cache[arch] = (pv, pt0, pt1)
    r = {"model": arch, "file": f.name, "val_macro_f1": macro_f1(yv, pv.argmax(1)), "val_acc": acc(yv, pv.argmax(1)),
         "test_acc": acc(yt, pt0.argmax(1)), "test_macro_f1": macro_f1(yt, pt0.argmax(1)),
         "test_weighted_f1": weighted_f1(yt, pt0.argmax(1)), "top3": top3(yt, pt0),
         "acc_ci": ci95(yt, pt0.argmax(1), acc), "f1_ci": ci95(yt, pt0.argmax(1), macro_f1),
         "test_acc_tta": acc(yt, pt1.argmax(1)), "test_macro_f1_tta": macro_f1(yt, pt1.argmax(1)),
         "params_M": m.count_params() / 1e6, "size_MB": f.stat().st_size / 2**20, "cpu_ms": cpu_ms(m)}
    results.append(r)
    print(f"   val macro F1 {r['val_macro_f1']:.4f} | test acc {r['test_acc']:.4f} (CI {r['acc_ci']}) | "
          f"test macro F1 {r['test_macro_f1']:.4f} | top-3 {r['top3']:.4f} | {r['cpu_ms']:.0f} ms/image "
          f"[{time.time() - t0:.0f}s]", flush=True)
    del m; keras.backend.clear_session()

results.sort(key=lambda r: r["val_macro_f1"], reverse=True)
best = results[0]
lines = ["model             val_F1  test_acc  95%CI        test_F1  F1_CI        top3   TTA_acc  size_MB  cpu_ms"]
for r in results:
    lines.append(f"{r['model']:<17} {r['val_macro_f1']:.4f}  {r['test_acc']:.4f}   {r['acc_ci']}  {r['test_macro_f1']:.4f}   "
                 f"{r['f1_ci']}  {r['top3']:.4f} {r['test_acc_tta']:.4f}   {r['size_MB']:6.0f}  {r['cpu_ms']:6.0f}")
lines.append(f"\nSELECTED (best validation macro F1): {best['model']}")
report = "\n".join(lines)
print("\n" + report)
(CAND / "comparison.json").write_text(json.dumps(results, indent=2))
(CAND / "comparison.txt").write_text(report + "\n")

# ---- calibration + uncertainty thresholds on validation (notebook step 12) ----
pv, pt0, pt1 = cache[best["model"]]
def apply_T(p, T):
    z = np.log(np.clip(p, 1e-12, 1)) / T; z -= z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)
def nll(T): return -np.mean(np.log(np.clip(apply_T(pv, T)[np.arange(len(yv)), yv], 1e-12, 1)))
a, b = 0.5, 5.0; g = (5 ** 0.5 - 1) / 2
for _ in range(80):                               # golden-section search, same bounds as the notebook
    c, d = b - g * (b - a), a + g * (b - a)
    a, b = (a, d) if nll(c) < nll(d) else (c, b)
T = (a + b) / 2
pvc = apply_T(pv, T); conf = pvc.max(1); correct = pvc.argmax(1) == yv
TARGET, T_CONF = 0.90, 0.90
for t in np.round(np.arange(0.30, 0.96, 0.05), 2):
    msk = conf >= t
    if msk.any() and correct[msk].mean() >= TARGET:
        T_CONF = float(t); break
ptc = apply_T(pt1, T); mt = ptc.max(1) >= T_CONF
print(f"Temperature {T:.3f} | T_conf {T_CONF} | test: {mt.mean():.1%} of photos confident, "
      f"{(ptc.argmax(1)[mt] == yt[mt]).mean():.1%} correct among them")

# ---- install into ml/artifacts (notebook step 14 format) ----
ART.mkdir(parents=True, exist_ok=True)
m = keras.models.load_model(CAND / best["file"], compile=False)
m.save(ART / "model.keras")                       # re-saved without optimizer state
shutil.copy(EVAL / "class_mapping.json", ART / "class_mapping.json")
sha = hashlib.sha256((ART / "model.keras").read_bytes()).hexdigest()
meta = {
    "model_version": f"agrosnap-{best['model']}-{time.strftime('%Y%m%d')}-{sha[:8]}",
    "architecture": best["model"], "sha256": sha, "tf_version": tf.__version__, "keras_version": keras.__version__,
    "num_classes": NUM, "mapping_version": mapping["version"],
    "input": {"size": [IMG, IMG], "color": "RGB", "dtype": "float32", "range": [0, 255],
              "steps": ["PIL open", "ImageOps.exif_transpose", "convert('RGB')", "resize(256,256) LANCZOS",
                        "JPEG q95 round-trip", "tf.image.resize to 224x224 bilinear (float32)",
                        "NO further scaling: preprocessing is inside the model"]},
    "inference": {"tta_hflip": True},
    "calibration": {"temperature": T},
    "uncertainty": {"T_conf": T_CONF, "M_min": 0.10, "target_acc_on_confident": TARGET},
    "metrics_test_no_tta": {k: best[k] for k in ("test_acc", "test_macro_f1", "test_weighted_f1", "top3", "acc_ci", "f1_ci")},
    "metrics_test_tta": {"test_acc": best["test_acc_tta"], "test_macro_f1": best["test_macro_f1_tta"]},
    "data": {"images": 13464, "split_counts": {"val": len(yv), "test": len(yt)},
             "note": "val/test re-derived from the v3 notebook's grouped split (seed 42) of new_sample.zip"},
    "selection": "best validation macro F1 among: " + ", ".join(r["model"] for r in results),
}
(ART / "model_meta.json").write_text(json.dumps(meta, indent=2))

# parity fixtures: 20 test images with expected top-3, for backend/tests/test_parity.py
fx = ART / "parity_fixtures"
if fx.exists():
    shutil.rmtree(fx)
fx.mkdir()
seen, expected = set(), []
for p, l in split["test"]:
    if l in seen or len(expected) >= 20:
        continue
    seen.add(l)
    name = p.name.replace(".jpg", f"_{l}.jpg"); shutil.copy(p, fx / name)
    pr = m(load_batch([(p, l)]), training=False).numpy()[0]; top = np.argsort(pr)[::-1][:3]
    expected.append({"file": name, "true": l, "top3": [int(i) for i in top], "scores": [float(pr[i]) for i in top]})
(fx / "expected.json").write_text(json.dumps(expected, indent=2))
print(f"\nInstalled {best['model']} -> {ART / 'model.keras'} (version {meta['model_version']})")
