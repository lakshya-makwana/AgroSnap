# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

Model versions are recorded separately in `docs/MODEL_CARD.md` and are included in release notes when they change.

## [Unreleased]

### Added
- Project documentation set: README, PHASES, CONTRIBUTING, and docs for architecture, API, database, model card, uncertainty policy, scan flow, offline handling, UI/UX, advisory content, security and privacy, testing, deployment, decisions and i18n.

- `ml/training/AgroSnap_Training_v3.ipynb`: improved training pipeline (full-data support, leakage-safe grouped split, stronger augmentation with MixUp/CutMix, full fine-tuning with warm-up + cosine LR, validation-macro-F1 checkpointing, TTA, temperature calibration, uncertainty thresholds, export bundle with parity fixtures).
- Partial Phase 1 audit (`docs/AUDIT.md`) from the Models_II notebook.
- Motion and worst-case-data guidelines from emilkowalski/skills (`docs/UI_UX.md` §9–10).

### Pending
- Phase 1 audit of the existing Colab notebook, checkpoints and class mapping.
