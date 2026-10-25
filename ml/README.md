# AgroSnap ML

Training, evaluation and model-artifact management for the 99-class leaf-disease classifier.

## Layout
```
ml/
├── training/        Colab notebooks (exported .ipynb), training configs
├── evaluation/
│   ├── preprocess.py               single source of truth for inference preprocessing
│   ├── evaluate.py                 consistent evaluation of any checkpoint
│   ├── export_parity_fixtures.py   writes expected outputs for backend parity tests
│   └── reports/<model_version>/    metrics.json, per_class.csv, confusion_matrix.png
├── artifacts/       (git-ignored except small metadata)
│   ├── class_mapping.json   verified index → class_key
│   └── model_meta.json      version, sha256, input size, preprocessing, TF version
└── README.md
```

## Rules
1. **Do not overwrite or retrain existing checkpoints** without approval. Copy them to a versioned folder before experimenting.
2. Evaluate every candidate with the **same** script, splits and preprocessing.
3. Select the model on macro F1, worst-class F1, independent-image results and latency, not accuracy alone.
4. Every number in `docs/MODEL_CARD.md` must come from a report in `evaluation/reports/`.
5. Model files (`*.keras`, `*.h5`, `saved_model/`) are never committed to Git.

## Evaluate a checkpoint
```bash
python evaluation/evaluate.py \
  --model /path/to/model.keras \
  --manifest /path/to/manifest.csv \
  --mapping artifacts/class_mapping.json \
  --split test \
  --out evaluation/reports/<model_version>/
```

## `class_mapping.json` format
```json
{
  "version": "<mapping_version>",
  "num_classes": 99,
  "classes": [
    { "index": 0, "class_key": "<as used in training>", "crop": "<display>", "disease": "<display>", "is_healthy": false }
  ]
}
```

## `model_meta.json` format
```json
{
  "model_version": "agrosnap-<arch>-<yyyymmdd>-<shortsha>",
  "architecture": "<arch>",
  "sha256": "<hash of model file>",
  "tf_version": "<x.y.z>",
  "input_size": [224, 224],
  "color_mode": "rgb",
  "scaling": "<e.g. mobilenet_v2.preprocess_input | divide_255>",
  "resize_method": "<bilinear | nearest>",
  "mapping_version": "<mapping_version>"
}
```

## Colab → repository
Export notebooks to `training/`, with outputs cleared or kept small. Keep checkpoints in Drive or object storage and record their paths in `docs/AUDIT.md`.
