# %% [markdown]
# # AgroSnap — Training Pipeline v3 (accuracy improvements)
#
# This notebook **does not touch** your v1/v2 artifacts. Everything is written to new folders
# (`results_v3/`, `best_models_v3/`). It is a clean, single-pass pipeline: run the cells top to bottom.
#
# ## Why v1 plateaued at ~77% (findings from `Models_II.ipynb`)
#
# | # | Finding | Effect | v3 fix |
# |---|---|---|---|
# | 1 | Training used `/MyDrive/sampled` — **2,095 images, 52 classes, ~28 train images/class** (max 50/class). The project brief describes a 13,464-image / 99-class dataset. | Biggest limit on accuracy. | `SOURCE_DIR` points at the full dataset; the sampled set is still supported for an apples-to-apples comparison. |
# | 2 | Fine-tuning unfroze only the last 20–40 layers at LR 1e-5, decayed to 3e-6. Train acc ~0.92 vs val ~0.76. | Backbone barely adapted to leaf textures. | Unfreeze the whole backbone (BatchNorm kept frozen), warm-up + cosine LR. |
# | 3 | v1 augmentation was rotation + zoom only. | Overfitting on a tiny dataset. | Random-resized crop, flips, 90° rotations, colour jitter, MixUp/CutMix. |
# | 4 | Checkpoints chosen on `val_loss` (with label smoothing) from 314 val images. | Noisy, misaligned with the selection metric. | Checkpoint + early stop on **validation macro F1**. |
# | 5 | The v2 cells never ran: `train_one_v2` sits in a *Markdown* cell, so `run_all_v2()` would raise `NameError`. v2 distillation also used teacher predictions on the teachers' own training images. | No v2 results exist. | Replaced by one tested pipeline. Distillation dropped. |
# | 6 | Preprocessing lived in four separate functions outside the models. | High risk of a train/serve mismatch in the FastAPI backend. | Preprocessing is **built into each model**: every exported model takes RGB float32 **0–255** at 224×224. |
# | 7 | Splits were random, not grouped by near-duplicates. | Possible leakage → optimistic test scores. | Perceptual-hash grouping keeps near-duplicates in the same split. |
#
# Also note: the notebook's MobileNetV2 result is 73.97% acc / 0.7593 macro F1 on 52 classes — not the
# 77.72% / 0.7548 quoted in the brief, so that figure came from a different run. v1's best was ResNet50
# (77.14% acc, 0.7928 macro F1, 315 test images, 95% CI roughly ±4.6 pts).
#
# **Expected gains are not guaranteed.** Every number this notebook prints is produced by the evaluation cell; record those, not estimates.

# %% [markdown]
# ## 0. Configuration
# Edit this cell only.

# %%
import os, sys, json, math, time, hashlib, random, gc, shutil
from pathlib import Path

SMOKE = False  # True = tiny synthetic run on CPU to test the code (no Drive, no ImageNet weights)

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB and not SMOKE:
    from google.colab import drive
    drive.mount("/content/drive")

DRIVE = Path("/content/drive/MyDrive")

# --- Data ---------------------------------------------------------------
# Point this at the FULL dataset root (one sub-folder per class). Fall back to the sampled subset.
SOURCE_DIR = DRIVE / "full_dataset"          # <-- CHANGE to your 13,464-image folder
FALLBACK_SOURCE_DIR = DRIVE / "sampled"
EXCLUDE_DIRS = {"blurry", "md5_duplicate", "phash_near_duplicate", "duplicates",
                "removed_images", "cleaning_logs"}
MIN_IMAGES_PER_CLASS = 10
# Reuse the v1 split CSV when training on the sampled set, so results are directly comparable to v1.
REUSE_V1_SPLIT_FOR_SAMPLED = True
V1_SPLIT_CSV = DRIVE / "results" / "dataset_splits.csv"
V1_METRICS_CSV = DRIVE / "results" / "baseline_metrics.csv"

# --- Image / training ---------------------------------------------------
STORE_SIZE = 256        # images are cached locally at 256x256 (Lanczos)
IMG_SIZE = 224          # model input
BATCH = 32
HEAD_EPOCHS = 6
FT_EPOCHS = 35
PATIENCE = 8
SEED = 42
USE_MIXUP_CUTMIX = True
LABEL_SMOOTHING = 0.05

# Which backbones to train. The first three are the original candidates;
# EfficientNetV2B0 and ConvNeXtTiny are stronger small-data options worth comparing.
ARCHS = ["efficientnetv2b0", "efficientnetb0", "mobilenetv2", "resnet50", "convnext_tiny"]
FT_LR = {"mobilenetv2": 2e-4, "efficientnetb0": 2e-4, "efficientnetv2b0": 2e-4,
         "resnet50": 1e-4, "convnext_tiny": 5e-5}

# --- Outputs (new folders; v1/v2 are never overwritten) -----------------
LOCAL = Path("/content") if Path("/content").exists() else Path.cwd()
OUT = DRIVE / "results_v3"
BEST = DRIVE / "best_models_v3"
LOCAL_DATA = LOCAL / f"data_v3_{STORE_SIZE}"
CACHE_DIR = LOCAL / "tfcache_v3"
CKPT_DIR = LOCAL / "checkpoints_v3"

if SMOKE:
    SCRATCH = Path(os.environ.get("SMOKE_DIR", "/tmp/agrosnap_smoke"))
    SOURCE_DIR = SCRATCH / "src"; FALLBACK_SOURCE_DIR = SOURCE_DIR
    OUT, BEST = SCRATCH / "results_v3", SCRATCH / "best_models_v3"
    LOCAL_DATA, CACHE_DIR, CKPT_DIR = SCRATCH / "data", SCRATCH / "cache", SCRATCH / "ckpt"
    V1_SPLIT_CSV = SCRATCH / "none.csv"; V1_METRICS_CSV = SCRATCH / "none.csv"
    ARCHS = ["mobilenetv2", "efficientnetv2b0", "resnet50"]
    HEAD_EPOCHS, FT_EPOCHS, PATIENCE, BATCH = 1, 2, 2, 8
    STORE_SIZE, IMG_SIZE = 72, 64

for p in (OUT, BEST, LOCAL_DATA, CACHE_DIR, CKPT_DIR):
    p.mkdir(parents=True, exist_ok=True)
print("Outputs ->", OUT, "|", BEST)

# %% [markdown]
# ## 1. Environment, seeds, mixed precision

# %%
import numpy as np
import pandas as pd
import tensorflow as tf
import keras
from keras import layers

os.environ["PYTHONHASHSEED"] = str(SEED)
random.seed(SEED); np.random.seed(SEED); tf.random.set_seed(SEED)

GPUS = tf.config.list_physical_devices("GPU")
for g in GPUS:
    tf.config.experimental.set_memory_growth(g, True)
if GPUS:
    keras.mixed_precision.set_global_policy("mixed_float16")
print(f"TF {tf.__version__} | Keras {keras.__version__} | GPUs: {len(GPUS)} | policy: {keras.mixed_precision.global_policy().name}")

# %% [markdown]
# ## 2. (Smoke mode only) create a tiny synthetic dataset

# %%
if SMOKE:
    from PIL import Image
    rng = np.random.default_rng(SEED)
    for c in range(6):
        d = SOURCE_DIR / f"Crop{c}_Disease{c}"; d.mkdir(parents=True, exist_ok=True)
        for i in range(24):
            base = np.zeros((90, 120, 3), np.uint8); base[..., c % 3] = 40 * c + 30
            noise = rng.integers(0, 120, (90, 120, 3), dtype=np.uint8)
            Image.fromarray(np.clip(base + noise, 0, 255).astype(np.uint8)).save(d / f"img_{i}.jpg")
    # one tiny class to test the minimum-images filter, one corrupt file
    d = SOURCE_DIR / "Tiny_Class"; d.mkdir(exist_ok=True)
    Image.fromarray(np.zeros((50, 50, 3), np.uint8)).save(d / "a.jpg")
    (SOURCE_DIR / "Crop0_Disease0" / "broken.jpg").write_bytes(b"not an image")
    print("Synthetic dataset ready at", SOURCE_DIR)

# %% [markdown]
# ## 3. Build the local image cache (RGB, 256×256 Lanczos) and the manifest
# Corrupt files are skipped and logged. Each image gets an MD5 and a 64-bit difference hash (dHash) for leakage checks.

# %%
from PIL import Image, ImageOps
from tqdm.auto import tqdm

src = SOURCE_DIR if SOURCE_DIR.exists() else FALLBACK_SOURCE_DIR
USING_SAMPLED = (src == FALLBACK_SOURCE_DIR) and not SMOKE
print("Reading images from:", src, "(sampled subset)" if USING_SAMPLED else "")

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def dhash(img, size=8):
    g = img.convert("L").resize((size + 1, size), Image.Resampling.BOX)
    a = np.asarray(g, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)

records, skipped = [], []
for root, dirs, files in os.walk(src):
    dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
    if any(part in EXCLUDE_DIRS for part in Path(root).parts):
        continue
    for f in sorted(files):
        if Path(f).suffix.lower() not in IMG_EXT:
            continue
        sp = Path(root) / f
        cls = sp.parent.name
        rel = f"{cls}/{sp.stem}.jpg"
        dst = LOCAL_DATA / rel
        try:
            if not dst.exists():
                with Image.open(sp) as im:
                    im.verify()
                with Image.open(sp) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im = im.resize((STORE_SIZE, STORE_SIZE), Image.Resampling.LANCZOS)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    im.save(dst, "JPEG", quality=95)
            raw = dst.read_bytes()
            with Image.open(dst) as im:
                h = dhash(im)
            records.append({"image_path": rel, "class_label": cls,
                            "md5": hashlib.md5(raw).hexdigest(), "dhash": h})
        except Exception as e:
            skipped.append((str(sp), repr(e)[:120]))

df = pd.DataFrame(records)
counts = df["class_label"].value_counts()
dropped = counts[counts < MIN_IMAGES_PER_CLASS]
df = df[~df["class_label"].isin(dropped.index)].reset_index(drop=True)
print(f"Images: {len(df)} | classes: {df['class_label'].nunique()} | skipped corrupt: {len(skipped)}")
if len(dropped):
    print("Dropped classes (<%d images):" % MIN_IMAGES_PER_CLASS, dict(dropped))
pd.DataFrame(skipped, columns=["path", "error"]).to_csv(OUT / "skipped_images.csv", index=False)

# %% [markdown]
# ## 4. Leakage-safe split
# Exact duplicates (same MD5) and near-duplicates (dHash Hamming distance ≤ 6, within a class) are put in the same **group**,
# and a stratified *group* split keeps each group inside one split. When training on the sampled set we reuse the v1 split
# (for comparability) and only *report* cross-split duplicates.

# %%
from sklearn.model_selection import StratifiedGroupKFold

def build_groups(frame, max_dist=6):
    parent = list(range(len(frame)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    for _, idx in frame.groupby("md5").groups.items():
        idx = list(idx)
        for j in idx[1:]: union(idx[0], j)
    for _, sub in frame.groupby("class_label"):
        ids = sub.index.to_numpy(); hs = sub["dhash"].to_numpy(dtype=object)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                if bin(hs[a] ^ hs[b]).count("1") <= max_dist:
                    union(ids[a], ids[b])
    return np.array([find(i) for i in range(len(frame))])

df["group"] = build_groups(df)
n_groups_dup = (df["group"].value_counts() > 1).sum()
print(f"Near-duplicate groups (size>1): {n_groups_dup}")

def grouped_split(frame, frac, seed):
    k = max(2, round(1 / frac))
    sgkf = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    rest_idx, hold_idx = next(sgkf.split(frame, frame["class_label"], frame["group"]))
    return frame.iloc[rest_idx], frame.iloc[hold_idx]

if USING_SAMPLED and REUSE_V1_SPLIT_FOR_SAMPLED and V1_SPLIT_CSV.exists():
    v1 = pd.read_csv(V1_SPLIT_CSV)[["image_path", "split"]]
    df = df.merge(v1, on="image_path", how="inner")
    print("Reusing v1 split:", df["split"].value_counts().to_dict())
else:
    trval, test = grouped_split(df, 0.15, SEED)
    train, val = grouped_split(trval, 0.15 / 0.85, SEED + 1)
    df["split"] = "train"
    df.loc[val.index, "split"] = "val"; df.loc[test.index, "split"] = "test"
    print("New grouped split:", df["split"].value_counts().to_dict())

leaky = df.groupby("group")["split"].nunique()
print("Groups spanning more than one split (leakage):", int((leaky > 1).sum()))
missing = set(df["class_label"]) - set(df[df.split == "val"]["class_label"])
if missing: print("WARNING: classes with no validation images:", sorted(missing))

CLASS_NAMES = sorted(df["class_label"].unique())
NUM_CLASSES = len(CLASS_NAMES)
CLS2IDX = {c: i for i, c in enumerate(CLASS_NAMES)}
df["label"] = df["class_label"].map(CLS2IDX)
df.to_csv(OUT / "dataset_splits_v3.csv", index=False)

# class_mapping.json in the format the backend expects (docs/../ml/README.md)
def split_name(key):
    crop, _, dis = key.partition("_")
    dis = dis.replace("_", " ").strip() or key
    healthy = any(w in key.lower() for w in ("healthy", "normal"))
    return crop, dis, healthy
mapping = {"version": f"v3-{NUM_CLASSES}c", "num_classes": NUM_CLASSES, "classes": [
    {"index": i, "class_key": k, "crop": split_name(k)[0], "disease": split_name(k)[1],
     "is_healthy": split_name(k)[2]} for i, k in enumerate(CLASS_NAMES)]}
# [A1] crop -> class indices, used by the backend's crop filter and by §12b
CROP_OF = np.array([split_name(k)[0] for k in CLASS_NAMES])
CROPS = {c: [int(i) for i in np.flatnonzero(CROP_OF == c)] for c in sorted(set(CROP_OF))}
mapping["crops"] = [{"crop": c, "class_indices": idx} for c, idx in CROPS.items()]
print(f"{len(CROPS)} crops:", {c: len(i) for c, i in CROPS.items()})
(OUT / "class_mapping.json").write_text(json.dumps(mapping, indent=2))
print(f"{NUM_CLASSES} classes | train/val/test:",
      [int((df.split == s).sum()) for s in ("train", "val", "test")])

# %% [markdown]
# ## 5. Class weights (only if the training set is imbalanced)

# %%
from sklearn.utils.class_weight import compute_class_weight
tr_labels = df[df.split == "train"]["label"].to_numpy()
tr_counts = np.bincount(tr_labels, minlength=NUM_CLASSES)
imbalance = tr_counts.max() / max(1, tr_counts.min())
if imbalance > 2.0:
    cw = compute_class_weight("balanced", classes=np.arange(NUM_CLASSES), y=tr_labels)
    CLASS_W = np.clip(cw, 0.25, 5.0).astype("float32")
else:
    CLASS_W = np.ones(NUM_CLASSES, "float32")
print(f"Train imbalance ratio {imbalance:.1f} -> class weights {'ON' if imbalance > 2 else 'OFF'}")

# %% [markdown]
# ## 6. tf.data pipeline
# Images stay in **0–255 float** all the way to the model. The model itself does the architecture-specific preprocessing.
# Train: random-resized crop → flips → 90° rotations → colour jitter → (batch) MixUp / CutMix.
# Eval: full image resized 256 → 224 (bilinear). This is exactly what the backend must do.

# %%
AUTOTUNE = tf.data.AUTOTUNE

def _decode(path):
    img = tf.io.decode_jpeg(tf.io.read_file(path), channels=3)
    img.set_shape([None, None, 3])
    return img

def eval_resize(img):
    return tf.image.resize(tf.cast(img, tf.float32), [IMG_SIZE, IMG_SIZE], method="bilinear")

def train_augment(img):
    img = tf.cast(img, tf.float32)
    h = tf.cast(tf.shape(img)[0], tf.float32)
    scale = tf.random.uniform([], 0.55, 1.0)
    ratio = tf.exp(tf.random.uniform([], math.log(3 / 4), math.log(4 / 3)))
    ch = tf.cast(tf.clip_by_value(h * tf.sqrt(scale / ratio), 16.0, h), tf.int32)
    cw = tf.cast(tf.clip_by_value(h * tf.sqrt(scale * ratio), 16.0, h), tf.int32)
    img = tf.image.random_crop(img, tf.stack([ch, cw, 3]))
    img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE], method="bilinear")
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_flip_up_down(img)
    img = tf.image.rot90(img, k=tf.random.uniform([], 0, 4, dtype=tf.int32))
    x = img / 255.0
    x = tf.image.random_brightness(x, 0.15)
    x = tf.image.random_contrast(x, 0.8, 1.2)
    x = tf.image.random_saturation(x, 0.8, 1.2)
    x = tf.image.random_hue(x, 0.03)
    return tf.clip_by_value(x, 0.0, 1.0) * 255.0

def _sample_beta(alpha):
    g1 = tf.random.gamma([], alpha); g2 = tf.random.gamma([], alpha)
    return g1 / (g1 + g2)

def mix_batch(x, y, w):
    """MixUp (alpha 0.2) or CutMix (alpha 1.0) on half of the batches."""
    bs = tf.shape(x)[0]
    perm = tf.random.shuffle(tf.range(bs))
    x2, y2, w2 = tf.gather(x, perm), tf.gather(y, perm), tf.gather(w, perm)
    r = tf.random.uniform([])
    def mixup():
        lam = _sample_beta(0.2)
        return lam * x + (1 - lam) * x2, lam
    def cutmix():
        lam = _sample_beta(1.0)
        cut = tf.sqrt(1.0 - lam)
        ch = tf.cast(IMG_SIZE * cut, tf.int32); cw = ch
        cy = tf.random.uniform([], 0, IMG_SIZE, dtype=tf.int32)
        cx = tf.random.uniform([], 0, IMG_SIZE, dtype=tf.int32)
        y0 = tf.clip_by_value(cy - ch // 2, 0, IMG_SIZE); y1 = tf.clip_by_value(cy + ch // 2, 0, IMG_SIZE)
        x0 = tf.clip_by_value(cx - cw // 2, 0, IMG_SIZE); x1 = tf.clip_by_value(cx + cw // 2, 0, IMG_SIZE)
        rows = tf.range(IMG_SIZE)[:, None]; cols = tf.range(IMG_SIZE)[None, :]
        box = tf.cast((rows >= y0) & (rows < y1) & (cols >= x0) & (cols < x1), x.dtype)[None, :, :, None]
        lam_adj = 1.0 - tf.cast((y1 - y0) * (x1 - x0), tf.float32) / float(IMG_SIZE * IMG_SIZE)
        return x * (1 - box) + x2 * box, lam_adj
    def none():
        return x, tf.constant(1.0)
    xm, lam = tf.case([(r < 0.25, mixup), (r < 0.5, cutmix)], default=none)
    ym = lam * y + (1 - lam) * y2
    wm = lam * w + (1 - lam) * w2
    return xm, ym, wm

def make_ds(split, training=False, batch=BATCH):
    sub = df[df.split == split]
    paths = [str(LOCAL_DATA / p) for p in sub["image_path"]]
    labels = sub["label"].to_numpy()
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    ds = ds.map(lambda p, l: (_decode(p), l), num_parallel_calls=AUTOTUNE)
    ds = ds.cache()  # decoded uint8 in RAM (~2.6 GB for 13k images at 256 px; freed when the dataset is released)
    cw = tf.constant(CLASS_W)
    if training:
        ds = ds.shuffle(2048, seed=SEED, reshuffle_each_iteration=True).repeat()
        ds = ds.map(lambda i, l: (train_augment(i), tf.one_hot(l, NUM_CLASSES), tf.gather(cw, l)),
                    num_parallel_calls=AUTOTUNE)
        ds = ds.batch(batch, drop_remainder=True)
        if USE_MIXUP_CUTMIX:
            ds = ds.map(mix_batch, num_parallel_calls=AUTOTUNE)
    else:
        ds = ds.map(lambda i, l: (eval_resize(i), tf.one_hot(l, NUM_CLASSES)), num_parallel_calls=AUTOTUNE)
        ds = ds.batch(batch)
    return ds.prefetch(AUTOTUNE)

xb, yb, wb = next(iter(make_ds("train", training=True)))
print("train batch:", xb.shape, yb.shape, wb.shape, "range", float(tf.reduce_min(xb)), float(tf.reduce_max(xb)))
xe, ye = next(iter(make_ds("val")))
print("val batch:", xe.shape, ye.shape, "range", float(tf.reduce_min(xe)), float(tf.reduce_max(xe)))

# %% [markdown]
# ## 7. Models with preprocessing built in
# Every model takes **RGB float32, 0–255, 224×224**. The preprocessing layer is a standard Keras layer, so the saved
# `.keras` file loads in the backend without custom objects.

# %%
A = keras.applications

def caffe_bgr_layer():
    """ResNet50 'caffe' preprocessing (RGB->BGR, subtract ImageNet mean) as a frozen 1x1 conv."""
    conv = layers.Conv2D(3, 1, use_bias=True, trainable=False, dtype="float32", name="resnet_caffe_preprocess")
    conv.build((None, None, None, 3))
    k = np.zeros((1, 1, 3, 3), "float32")
    for out_c, in_c in enumerate([2, 1, 0]):
        k[0, 0, in_c, out_c] = 1.0
    conv.set_weights([k, -np.array([103.939, 116.779, 123.68], "float32")])
    return conv

def build(arch, weights="imagenet"):
    shape = (IMG_SIZE, IMG_SIZE, 3)
    inp = layers.Input(shape, name="image_rgb_0_255")
    if arch == "mobilenetv2":
        x = layers.Rescaling(1 / 127.5, offset=-1.0, name="mnv2_preprocess")(inp)
        base = A.MobileNetV2(include_top=False, weights=weights, input_shape=shape)
    elif arch == "resnet50":
        x = caffe_bgr_layer()(inp)
        base = A.ResNet50(include_top=False, weights=weights, input_shape=shape)
    elif arch == "efficientnetb0":       # includes its own rescaling/normalisation
        x = inp; base = A.EfficientNetB0(include_top=False, weights=weights, input_shape=shape)
    elif arch == "efficientnetv2b0":     # include_preprocessing=True by default
        x = inp; base = A.EfficientNetV2B0(include_top=False, weights=weights, input_shape=shape)
    elif arch == "convnext_tiny":        # include_preprocessing=True by default
        x = inp; base = A.ConvNeXtTiny(include_top=False, weights=weights, input_shape=shape)
    else:
        raise ValueError(arch)
    base.trainable = False
    x = base(x, training=False)           # BN stays in inference mode during fine-tuning
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dropout(0.3, name="head_dropout")(x)
    out = layers.Dense(NUM_CLASSES, activation="softmax", dtype="float32", name="probs")(x)
    return keras.Model(inp, out, name=f"agrosnap_{arch}"), base

# Parity check: built-in ResNet preprocessing == keras resnet50.preprocess_input
_t = tf.random.uniform([2, 8, 8, 3], 0, 255)
_ref = A.resnet50.preprocess_input(tf.identity(_t))
_got = caffe_bgr_layer()(_t)
print("ResNet preprocessing max abs diff:", float(tf.reduce_max(tf.abs(_ref - _got))))
_ref = A.mobilenet_v2.preprocess_input(tf.identity(_t))
_got = layers.Rescaling(1 / 127.5, offset=-1.0)(_t)
print("MobileNetV2 preprocessing max abs diff:", float(tf.reduce_max(tf.abs(_ref - _got))))

# %% [markdown]
# ## 8. Training: head warm-up → full fine-tune, checkpoint on validation macro F1

# %%
from sklearn.metrics import f1_score, accuracy_score

def predict_probs(model, split, tta=False):
    ys, ps = [], []
    for x, y in make_ds(split):
        p = model(x, training=False).numpy()
        if tta:
            p = (p + model(tf.image.flip_left_right(x), training=False).numpy()) / 2.0
        ys.append(np.argmax(y.numpy(), 1)); ps.append(p)
    return np.concatenate(ys), np.concatenate(ps)

class MacroF1Checkpoint(keras.callbacks.Callback):
    def __init__(self, path, patience):
        super().__init__(); self.path, self.patience = str(path), patience
        self.best, self.wait, self.log = -1.0, 0, []
    def on_epoch_end(self, epoch, logs=None):
        y, p = predict_probs(self.model, "val")
        f1 = f1_score(y, p.argmax(1), average="macro", zero_division=0)
        acc = accuracy_score(y, p.argmax(1))
        self.log.append({"epoch": epoch + 1, "val_macro_f1": f1, "val_acc": acc,
                         "loss": float(logs.get("loss", np.nan))})
        print(f"  val_macro_f1={f1:.4f} val_acc={acc:.4f}")
        if f1 > self.best:
            self.best, self.wait = f1, 0
            self.model.save(self.path)
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.model.stop_training = True

@keras.saving.register_keras_serializable(package="agrosnap")
class WarmupCosine(keras.optimizers.schedules.LearningRateSchedule):
    def __init__(self, peak, total, warmup):
        self.peak, self.total, self.warmup = peak, float(total), float(warmup)
    def __call__(self, step):
        s = tf.cast(step, tf.float32)
        warm = self.peak * s / tf.maximum(1.0, self.warmup)
        prog = tf.clip_by_value((s - self.warmup) / tf.maximum(1.0, self.total - self.warmup), 0.0, 1.0)
        cos = self.peak * (0.02 + 0.98 * 0.5 * (1 + tf.cos(math.pi * prog)))
        return tf.where(s < self.warmup, warm, cos)
    def get_config(self):
        return {"peak": self.peak, "total": self.total, "warmup": self.warmup}

def train(arch, weights="imagenet"):
    tf.keras.backend.clear_session(); gc.collect()
    model, base = build(arch, weights)
    n_train = int((df.split == "train").sum())
    steps = max(1, n_train // BATCH)
    ds_tr = make_ds("train", training=True)
    loss = keras.losses.CategoricalCrossentropy(label_smoothing=LABEL_SMOOTHING)
    ckpt = CKPT_DIR / f"{arch}_best.keras"
    cb = MacroF1Checkpoint(ckpt, PATIENCE)

    print(f"\n=== {arch}: stage 1 (head only) ===")
    model.compile(keras.optimizers.AdamW(1e-3, weight_decay=1e-4), loss, metrics=["accuracy"])
    h1 = model.fit(ds_tr, epochs=HEAD_EPOCHS, steps_per_epoch=steps, callbacks=[cb], verbose=2)

    print(f"=== {arch}: stage 2 (full fine-tune, BN frozen) ===")
    base.trainable = True
    for l in base.layers:
        if isinstance(l, layers.BatchNormalization):
            l.trainable = False
    sched = WarmupCosine(FT_LR[arch], FT_EPOCHS * steps, 2 * steps)
    model.compile(keras.optimizers.AdamW(sched, weight_decay=5e-5, clipnorm=1.0), loss, metrics=["accuracy"])
    cb.wait = 0
    h2 = model.fit(ds_tr, epochs=FT_EPOCHS, steps_per_epoch=steps, callbacks=[cb], verbose=2)

    pd.DataFrame(cb.log).to_csv(OUT / f"history_{arch}.csv", index=False)
    print(f"{arch}: best val macro F1 = {cb.best:.4f} -> {ckpt}")
    del model, base; tf.keras.backend.clear_session(); gc.collect()
    return ckpt, cb.best

# %% [markdown]
# ## 9. Train all architectures (resumable)
# Already-finished architectures are skipped, so a Colab disconnect only loses the model in progress.

# %%
WEIGHTS = None if SMOKE else "imagenet"
status_file = OUT / "train_status.json"
status = json.loads(status_file.read_text()) if status_file.exists() else {}
for arch in ARCHS:
    if arch in status and Path(status[arch]["ckpt"]).exists():
        print("skip", arch, status[arch]); continue
    ckpt, best = train(arch, WEIGHTS)
    dst = BEST / ckpt.name
    shutil.copy(ckpt, dst)
    status[arch] = {"ckpt": str(dst), "val_macro_f1": float(best)}
    status_file.write_text(json.dumps(status, indent=2))
print(json.dumps(status, indent=2))

# %% [markdown]
# ## 10. Evaluate: test metrics, TTA, bootstrap CI, per-class report, latency

# %%
from sklearn.metrics import classification_report, confusion_matrix

def bootstrap_ci(y, yp, n=1000, seed=SEED):
    r = np.random.default_rng(seed); acc, f1 = [], []
    for _ in range(n):
        i = r.integers(0, len(y), len(y))
        acc.append(accuracy_score(y[i], yp[i])); f1.append(f1_score(y[i], yp[i], average="macro", zero_division=0))
    return np.percentile(acc, [2.5, 97.5]), np.percentile(f1, [2.5, 97.5])

def topk(y, p, k):
    return float(np.mean([y[i] in np.argsort(p[i])[-k:] for i in range(len(y))]))

def cpu_latency_ms(path, n=20):
    with tf.device("/CPU:0"):
        m = keras.models.load_model(path, compile=False)
        x = tf.random.uniform([1, IMG_SIZE, IMG_SIZE, 3], 0, 255)
        m(x, training=False)
        t = time.perf_counter()
        for _ in range(n): m(x, training=False)
        ms = (time.perf_counter() - t) / n * 1000
    del m; gc.collect()
    return ms

rows, PROBS = [], {}
for arch, info in status.items():
    m = keras.models.load_model(info["ckpt"], compile=False)
    for tta in (False, True):
        y, p = predict_probs(m, "test", tta=tta)
        yp = p.argmax(1)
        (alo, ahi), (flo, fhi) = bootstrap_ci(y, yp)
        rows.append({"model": arch, "tta": tta, "test_acc": accuracy_score(y, yp),
                     "test_macro_f1": f1_score(y, yp, average="macro", zero_division=0),
                     "test_weighted_f1": f1_score(y, yp, average="weighted", zero_division=0),
                     "top3": topk(y, p, 3), "acc_ci": f"{alo:.3f}-{ahi:.3f}", "f1_ci": f"{flo:.3f}-{fhi:.3f}",
                     "val_macro_f1": info["val_macro_f1"], "params_M": m.count_params() / 1e6,
                     "size_MB": os.path.getsize(info["ckpt"]) / 2**20})
        PROBS[(arch, tta)] = p
    Y_TEST = y
    # val probabilities (TTA) for ensembling / calibration
    yv, pv = predict_probs(m, "val", tta=True); PROBS[(arch, "val")] = pv; Y_VAL = yv
    del m; tf.keras.backend.clear_session(); gc.collect()

res = pd.DataFrame(rows)
res["cpu_ms"] = res["model"].map({a: cpu_latency_ms(status[a]["ckpt"]) for a in status})
res = res.sort_values(["test_macro_f1"], ascending=False)
res.to_csv(OUT / "metrics_v3.csv", index=False)
try:
    display(res)
except NameError:
    print(res.to_string())

if V1_METRICS_CSV.exists():
    v1 = pd.read_csv(V1_METRICS_CSV)[["model_name", "test_accuracy", "macro_f1"]]
    print("\nv1 baseline for comparison:\n", v1.to_string(index=False))

# %% [markdown]
# ## 11. Ensemble (members chosen on **validation**, reported on test)

# %%
from itertools import combinations
archs = list(status)
best_combo, best_val = None, -1
for r in range(2, min(3, len(archs)) + 1):
    for combo in combinations(archs, r):
        pv = np.mean([PROBS[(a, "val")] for a in combo], 0)
        f = f1_score(Y_VAL, pv.argmax(1), average="macro", zero_division=0)
        if f > best_val: best_val, best_combo = f, combo
if best_combo:
    pt = np.mean([PROBS[(a, True)] for a in best_combo], 0)
    ens = {"members": list(best_combo), "val_macro_f1": float(best_val),
           "test_acc": float(accuracy_score(Y_TEST, pt.argmax(1))),
           "test_macro_f1": float(f1_score(Y_TEST, pt.argmax(1), average="macro", zero_division=0))}
    (OUT / "ensemble_v3.json").write_text(json.dumps(ens, indent=2))
    print("Best ensemble:", ens)
    print("Note: an ensemble multiplies server latency and memory. Ship it only if the gain is outside the CI.")

# %% [markdown]
# ## 12. Pick the production model, calibrate, derive uncertainty thresholds
# Selection = best **validation** macro F1 (not test accuracy). Temperature scaling and thresholds are fitted on validation only.

# %%
from scipy.optimize import minimize_scalar

PROD = max(status, key=lambda a: status[a]["val_macro_f1"])
print("Production candidate (by val macro F1):", PROD)
pv, pt = PROBS[(PROD, "val")], PROBS[(PROD, True)]

def apply_T(p, T):
    z = np.log(np.clip(p, 1e-12, 1)) / T
    z -= z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)

def nll(T, p, y): return -np.mean(np.log(np.clip(apply_T(p, T)[np.arange(len(y)), y], 1e-12, 1)))

def ece(p, y, bins=15):
    conf, pred = p.max(1), p.argmax(1); e = 0.0
    for lo in np.linspace(0, 1, bins, endpoint=False):
        m = (conf > lo) & (conf <= lo + 1 / bins)
        if m.any(): e += m.mean() * abs((pred[m] == y[m]).mean() - conf[m].mean())
    return float(e)

T = float(minimize_scalar(lambda t: nll(t, pv, Y_VAL), bounds=(0.5, 5.0), method="bounded").x)
print(f"Temperature T={T:.3f} | val ECE before {ece(pv, Y_VAL):.3f} after {ece(apply_T(pv, T), Y_VAL):.3f}")

TARGET = 0.90
M_MIN = 0.10

def threshold_table(p, y, m_min=M_MIN):
    """Coverage / accuracy of the 'confident' subset under the backend rule: p1 >= t AND p1 - p2 >= m_min."""
    srt = np.sort(p, 1); conf, margin = srt[:, -1], srt[:, -1] - srt[:, -2]
    correct = p.argmax(1) == y; rows = []
    for t in np.round(np.arange(0.30, 0.96, 0.05), 2):
        m = (conf >= t) & (margin >= m_min)
        rows.append({"T_conf": t, "coverage": m.mean(), "acc_on_confident": correct[m].mean() if m.any() else np.nan})
    return pd.DataFrame(rows)

def pick_threshold(tbl):
    ok = tbl[tbl.acc_on_confident >= TARGET]
    return float(ok.T_conf.min()) if len(ok) else 0.95

def confident_mask(p, t_conf, m_min=M_MIN):
    srt = np.sort(p, 1); return (srt[:, -1] >= t_conf) & (srt[:, -1] - srt[:, -2] >= m_min)

pvc = apply_T(pv, T)
thr = threshold_table(pvc, Y_VAL); thr.to_csv(OUT / "threshold_table_val.csv", index=False)
print(thr.to_string(index=False))
T_CONF = pick_threshold(thr)
print(f"Chosen T_conf={T_CONF} (smallest with >= {TARGET:.0%} val accuracy on confident subset), M_min={M_MIN}")
ptc = apply_T(pt, T); mt = confident_mask(ptc, T_CONF)
print(f"TEST check: coverage {mt.mean():.2%}, accuracy on confident {(ptc.argmax(1)[mt] == Y_TEST[mt]).mean():.2%}")

# %% [markdown]
# ## 12b. [A1] Crop-first scan: crop-conditioned accuracy and thresholds
# In the app the farmer picks the crop first, and the backend keeps only that crop's classes and renormalises
# (`backend/app/services/inference.py`). Scores renormalised this way are higher than the unrestricted ones, so the
# thresholds above are **not** valid for them. Here we simulate the farmer picking the **true** crop and fit separate
# thresholds on validation. Reported on test. (Wrong crop picks are caught by the backend's mismatch check.)

# %%
def restrict_to_crop(p, y):
    out = np.zeros_like(p)
    for i, label in enumerate(y):
        idx = CROPS[CROP_OF[label]]
        out[i, idx] = p[i, idx] / max(p[i, idx].sum(), 1e-12)
    return out

pvc_crop, ptc_crop = restrict_to_crop(pvc, Y_VAL), restrict_to_crop(ptc, Y_TEST)
thr_crop = threshold_table(pvc_crop, Y_VAL); thr_crop.to_csv(OUT / "threshold_table_val_crop.csv", index=False)
T_CONF_CROP = pick_threshold(thr_crop)
mtc = confident_mask(ptc_crop, T_CONF_CROP)
CROP_METRICS = {
    "test_acc_all_classes": float(accuracy_score(Y_TEST, ptc.argmax(1))),
    "test_acc_crop_first": float(accuracy_score(Y_TEST, ptc_crop.argmax(1))),
    "test_macro_f1_crop_first": float(f1_score(Y_TEST, ptc_crop.argmax(1), average="macro", zero_division=0)),
    "test_coverage_confident_crop_first": float(mtc.mean()),
    "test_acc_on_confident_crop_first": float((ptc_crop.argmax(1)[mtc] == Y_TEST[mtc]).mean()) if mtc.any() else None,
}
print(thr_crop.to_string(index=False))
print(f"Chosen T_conf_crop={T_CONF_CROP}")
print(json.dumps(CROP_METRICS, indent=2))

# %% [markdown]
# ## 13. Per-class report and most-confused pairs (production model)

# %%
yp = pt.argmax(1)
rep = classification_report(Y_TEST, yp, labels=range(NUM_CLASSES), target_names=CLASS_NAMES,
                            output_dict=True, zero_division=0)
per_class = pd.DataFrame(rep).T.iloc[:NUM_CLASSES].sort_values("f1-score")
per_class.to_csv(OUT / f"per_class_{PROD}.csv")
print("10 weakest classes:\n", per_class.head(10)[["precision", "recall", "f1-score", "support"]].to_string())
cm = confusion_matrix(Y_TEST, yp, labels=range(NUM_CLASSES)); np.fill_diagonal(cm, 0)
pairs = sorted(((cm[i, j], CLASS_NAMES[i], CLASS_NAMES[j]) for i in range(NUM_CLASSES)
                for j in range(NUM_CLASSES) if cm[i, j]), reverse=True)[:10]
print("\nMost confused (count, true -> predicted):"); [print(" ", p) for p in pairs]

# %% [markdown]
# ## 13b. [A6] Model compression (project novelty)
# Post-training quantization of the production model to TFLite, then the **same** evaluation as the full model:
#
# | Variant | What it does |
# |---|---|
# | `tflite_fp32` | Plain conversion (baseline for the converter itself) |
# | `tflite_fp16` | Weights stored as float16 (~2× smaller) |
# | `tflite_dynamic_int8` | Weights int8, activations float at run time (~4× smaller) |
# | `tflite_full_int8` | Weights **and** activations int8, calibrated on training images (~4× smaller, fastest on CPU) |
#
# Input and output stay float32 (RGB 0–255 in, softmax out), so the backend preprocessing is unchanged.
# The deployed variant is the **smallest** one whose validation macro F1 is within `MAX_F1_DROP` of the full
# model. Selection uses validation only. Because quantization changes the scores, the temperature and all
# thresholds are **re-fitted on the chosen variant**. Thresholds always belong to the exact model file shipped.

# %%
MAX_F1_DROP = 0.01          # at most 1 macro-F1 point lost on validation
REP_IMAGES = 16 if SMOKE else 300
COMPRESS_DIR = OUT / "compression"; COMPRESS_DIR.mkdir(exist_ok=True)

keras_prod = keras.models.load_model(status[PROD]["ckpt"], compile=False)
saved_dir = LOCAL / f"savedmodel_{PROD}"
keras_prod.export(str(saved_dir))  # Keras 3: SavedModel for the TFLite converter

def representative_dataset():
    paths = df[df.split == "train"].sample(min(REP_IMAGES, int((df.split == "train").sum())), random_state=SEED)
    for p in paths.image_path:
        yield [eval_resize(_decode(str(LOCAL_DATA / p)))[None]]

def convert(kind):
    conv = tf.lite.TFLiteConverter.from_saved_model(str(saved_dir))
    if kind == "tflite_fp16":
        conv.optimizations = [tf.lite.Optimize.DEFAULT]; conv.target_spec.supported_types = [tf.float16]
    elif kind == "tflite_dynamic_int8":
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
    elif kind == "tflite_full_int8":
        conv.optimizations = [tf.lite.Optimize.DEFAULT]; conv.representative_dataset = representative_dataset
    path = COMPRESS_DIR / f"{PROD}_{kind}.tflite"
    path.write_bytes(conv.convert())
    return path

class TFLitePredictor:
    """Runs a .tflite model one image at a time; same call contract as the Keras model (float 0-255 in)."""
    def __init__(self, path, threads=2):
        self.it = tf.lite.Interpreter(model_path=str(path), num_threads=threads)
        self.inp = self.it.get_input_details()[0]; self.out = self.it.get_output_details()[0]
        self.it.resize_tensor_input(self.inp["index"], [1, IMG_SIZE, IMG_SIZE, 3]); self.it.allocate_tensors()
    def __call__(self, x):
        x = np.asarray(x, np.float32); outs = []
        for i in range(len(x)):
            self.it.set_tensor(self.inp["index"], x[i:i + 1]); self.it.invoke()
            outs.append(self.it.get_tensor(self.out["index"])[0].astype(np.float32))
        return np.stack(outs)

def probs_with(predict, split):
    """TTA probabilities (original + horizontal flip), exactly like predict_probs(tta=True)."""
    ys, ps = [], []
    for x, y in make_ds(split):
        x = x.numpy()
        ps.append((predict(x) + predict(x[:, :, ::-1, :])) / 2.0); ys.append(np.argmax(y.numpy(), 1))
    return np.concatenate(ys), np.concatenate(ps)

def latency_ms(predict, n=30):
    x = np.random.default_rng(0).uniform(0, 255, (1, IMG_SIZE, IMG_SIZE, 3)).astype(np.float32)
    predict(x); t = time.perf_counter()
    for _ in range(n): predict(x)
    return (time.perf_counter() - t) / n * 1000

keras_pred = lambda x: keras_prod(x, training=False).numpy()
keras_path = COMPRESS_DIR / f"{PROD}_keras.keras"; keras_prod.save(keras_path)
variants = {"keras_fp32": (keras_path, keras_pred)}
for kind in ["tflite_fp32", "tflite_fp16", "tflite_dynamic_int8", "tflite_full_int8"]:
    try:
        path = convert(kind); variants[kind] = (path, TFLitePredictor(path))
    except Exception as e:  # a converter failure for one variant must not stop the pipeline
        print(f"{kind}: conversion failed -> {repr(e)[:200]}")

COMP_PROBS, comp_rows = {}, []
for kind, (path, pred) in variants.items():
    yv, pv_k = (Y_VAL, PROBS[(PROD, "val")]) if kind == "keras_fp32" else probs_with(pred, "val")
    yt, pt_k = (Y_TEST, PROBS[(PROD, True)]) if kind == "keras_fp32" else probs_with(pred, "test")
    COMP_PROBS[kind] = (pv_k, pt_k)
    with tf.device("/CPU:0"):
        ms = latency_ms(pred)
    comp_rows.append({
        "variant": kind, "size_MB": os.path.getsize(path) / 2**20, "cpu_ms_per_img": ms,
        "val_macro_f1": f1_score(yv, pv_k.argmax(1), average="macro", zero_division=0),
        "test_acc": accuracy_score(yt, pt_k.argmax(1)),
        "test_macro_f1": f1_score(yt, pt_k.argmax(1), average="macro", zero_division=0),
        "test_top1_agreement_with_keras": float((pt_k.argmax(1) == PROBS[(PROD, True)].argmax(1)).mean()),
        "test_max_abs_prob_diff": float(np.abs(pt_k - PROBS[(PROD, True)]).max()),
    })
comp = pd.DataFrame(comp_rows)
base_size = float(comp.loc[comp.variant == "keras_fp32", "size_MB"].iloc[0])
comp["compression_x"] = base_size / comp["size_MB"]
comp.to_csv(OUT / "compression_v3.csv", index=False)
try:
    display(comp)
except NameError:
    print(comp.to_string())

base_f1 = float(comp.loc[comp.variant == "keras_fp32", "val_macro_f1"].iloc[0])
eligible = comp[(comp.variant != "keras_fp32") & (comp.val_macro_f1 >= base_f1 - MAX_F1_DROP)]
DEPLOY = eligible.sort_values(["size_MB", "cpu_ms_per_img"]).iloc[0].variant if len(eligible) else "keras_fp32"
print(f"Deploying: {DEPLOY} (smallest variant within {MAX_F1_DROP:.0%} val macro F1 of the full model)")

# Re-fit calibration and thresholds on the variant that will actually be shipped (validation only).
pv, pt = COMP_PROBS[DEPLOY]
T = float(minimize_scalar(lambda t: nll(t, pv, Y_VAL), bounds=(0.5, 5.0), method="bounded").x)
pvc, ptc = apply_T(pv, T), apply_T(pt, T)
thr = threshold_table(pvc, Y_VAL); thr.to_csv(OUT / "threshold_table_val.csv", index=False)
T_CONF = pick_threshold(thr)
pvc_crop, ptc_crop = restrict_to_crop(pvc, Y_VAL), restrict_to_crop(ptc, Y_TEST)
thr_crop = threshold_table(pvc_crop, Y_VAL); thr_crop.to_csv(OUT / "threshold_table_val_crop.csv", index=False)
T_CONF_CROP = pick_threshold(thr_crop)
mt, mtc = confident_mask(ptc, T_CONF), confident_mask(ptc_crop, T_CONF_CROP)
CROP_METRICS = {
    "test_acc_all_classes": float(accuracy_score(Y_TEST, ptc.argmax(1))),
    "test_acc_crop_first": float(accuracy_score(Y_TEST, ptc_crop.argmax(1))),
    "test_macro_f1_crop_first": float(f1_score(Y_TEST, ptc_crop.argmax(1), average="macro", zero_division=0)),
    "test_coverage_confident_crop_first": float(mtc.mean()),
    "test_acc_on_confident_crop_first": float((ptc_crop.argmax(1)[mtc] == Y_TEST[mtc]).mean()) if mtc.any() else None,
}
print(f"[{DEPLOY}] T={T:.3f}  T_conf={T_CONF}  T_conf_crop={T_CONF_CROP}  "
      f"test coverage {mt.mean():.2%}, acc on confident {(ptc.argmax(1)[mt] == Y_TEST[mt]).mean():.2%}")
print(json.dumps(CROP_METRICS, indent=2))
DEPLOY_PATH, deploy_predict = variants[DEPLOY]
DEPLOY_ROW = comp[comp.variant == DEPLOY].iloc[0].to_dict()

# %% [markdown]
# ## 14. Export the production bundle for the backend
# The deployed model file (`model.tflite` or `model.keras`) + `class_mapping.json` + `model_meta.json` +
# parity fixtures (20 test images with expected top-3 from the deployed file). `model_full.keras` is kept for reference.

# %%
bundle = BEST / "production"
bundle.mkdir(exist_ok=True)
for old in ("model.keras", "model.tflite"):
    if (bundle / old).exists(): (bundle / old).unlink()
# re-save without optimizer state so the backend needs no custom objects
keras_prod.save(bundle / "model_full.keras")
model_file = bundle / ("model.tflite" if DEPLOY.startswith("tflite") else "model.keras")
shutil.copy(DEPLOY_PATH, model_file)
shutil.copy(OUT / "class_mapping.json", bundle / "class_mapping.json")
sha = hashlib.sha256(model_file.read_bytes()).hexdigest()
prow = {"test_acc": float(accuracy_score(Y_TEST, pt.argmax(1))),
        "test_macro_f1": float(f1_score(Y_TEST, pt.argmax(1), average="macro", zero_division=0)),
        "top3": topk(Y_TEST, pt, 3)}
meta = {
    "model_version": f"agrosnap-{PROD}-{DEPLOY}-{time.strftime('%Y%m%d')}-{sha[:8]}",
    "architecture": PROD, "format": model_file.suffix.lstrip("."), "file": model_file.name,
    "compression": {"variant": DEPLOY, "size_MB": DEPLOY_ROW["size_MB"], "compression_x": DEPLOY_ROW["compression_x"],
                    "cpu_ms_per_img": DEPLOY_ROW["cpu_ms_per_img"], "max_f1_drop_allowed": MAX_F1_DROP,
                    "table": "results_v3/compression_v3.csv"},
    "sha256": sha, "tf_version": tf.__version__, "keras_version": keras.__version__,
    "num_classes": NUM_CLASSES, "mapping_version": mapping["version"],
    "input": {"size": [IMG_SIZE, IMG_SIZE], "color": "RGB", "dtype": "float32", "range": [0, 255],
              "steps": ["PIL open", "ImageOps.exif_transpose", "convert('RGB')",
                        f"resize({STORE_SIZE},{STORE_SIZE}) LANCZOS",
                        "save JPEG quality 95, decode again (training cache format)",
                        f"tf.image.resize to {IMG_SIZE}x{IMG_SIZE} bilinear (float32)",
                        "NO further scaling: preprocessing is inside the model"]},
    # Temperature and thresholds were fitted on horizontal-flip-averaged probabilities,
    # so the backend must average with the flip too, or the thresholds do not apply.
    "inference": {"tta_hflip": True},
    "calibration": {"temperature": T},
    "uncertainty": {"T_conf": T_CONF, "M_min": M_MIN, "T_conf_crop": T_CONF_CROP, "M_min_crop": M_MIN,
                    "target_acc_on_confident": TARGET},
    "metrics_crop_first": CROP_METRICS,
    "metrics_test_tta": prow,  # metrics of the deployed file, with the same flip-TTA the backend uses
    "data": {"images": int(len(df)), "split_counts": df.split.value_counts().to_dict(),
             "source": str(src), "sampled_subset": bool(USING_SAMPLED)},
}
(bundle / "model_meta.json").write_text(json.dumps(meta, indent=2, default=str))

# parity fixtures, produced with the exact inference steps above
fx = bundle / "parity_fixtures"; fx.mkdir(exist_ok=True)
if model_file.suffix == ".tflite":
    m = TFLitePredictor(model_file)
else:
    _k = keras.models.load_model(model_file, compile=False); m = lambda x: _k(x, training=False).numpy()
sample = df[df.split == "test"].groupby("label").head(1).head(20)
expected = []
for _, r in sample.iterrows():
    shutil.copy(LOCAL_DATA / r.image_path, fx / Path(r.image_path).name.replace(".jpg", f"_{r.label}.jpg"))
    x = eval_resize(_decode(str(LOCAL_DATA / r.image_path)))[None].numpy()
    p = m(x)[0]  # raw softmax of the deployed file, no TTA / temperature
    top = np.argsort(p)[::-1][:3]
    expected.append({"file": Path(r.image_path).name.replace(".jpg", f"_{r.label}.jpg"), "true": int(r.label),
                     "top3": [int(i) for i in top], "scores": [float(p[i]) for i in top]})
(fx / "expected.json").write_text(json.dumps(expected, indent=2))
print("Exported:", sorted(os.listdir(bundle)), "| version:", meta["model_version"])

# Reload check: the exported file gives identical outputs when loaded again
x = eval_resize(_decode(str(LOCAL_DATA / sample.iloc[0].image_path)))[None].numpy()
if model_file.suffix == ".tflite":
    m2 = TFLitePredictor(model_file)
else:
    _k2 = keras.models.load_model(model_file, compile=False); m2 = lambda x: _k2(x, training=False).numpy()
print("Reload max abs diff:", float(np.max(np.abs(m(x) - m2(x)))))

# %% [markdown]
# ## 15. What to record
# Copy these into `docs/MODEL_CARD.md` and `docs/AUDIT.md`:
# - `results_v3/metrics_v3.csv` (all models, with/without TTA, CIs, latency)
# - `results_v3/per_class_<model>.csv` and the confused pairs printed above
# - `results_v3/threshold_table_val.csv` and `threshold_table_val_crop.csv` → `UNCERTAINTY_POLICY.md`
# - `results_v3/compression_v3.csv` → `MODEL_CARD.md` §5b (size, latency, accuracy of every compressed variant)
# - `best_models_v3/production/model_meta.json`
#
# Next accuracy levers, in order: (1) train on the full dataset; (2) collect 20–50 **real field photos** per priority
# class and add them to training *and* to an independent test set; (3) fix or drop non-leaf classes (tubers, pests) if the
# app is leaf-only; (4) try 288 px input for EfficientNetV2/ConvNeXt; (5) 5-fold CV ensembles only if latency allows.
