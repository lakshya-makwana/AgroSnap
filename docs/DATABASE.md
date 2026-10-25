# Database

PostgreSQL 15+, SQLAlchemy 2.x ORM, and Alembic migrations. All primary keys are UUIDs, except `disease_classes.id`, which equals the **model output index** (0–98), so that the mapping stays explicit.

## Entity overview

```
users 1──* farms 1──* farm_crops
  │          │
  │          └──* predictions (farm_id nullable)
  └──* predictions 1──* prediction_candidates *──1 disease_classes 1──* advisories
  └──* refresh_tokens
```

## Tables

### users
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| name | varchar(120) | not null |
| email | citext | unique, not null |
| password_hash | text | not null |
| preferred_language | varchar(10) | default `'en'` |
| created_at | timestamptz | default now() |
| deleted_at | timestamptz | null (soft-delete marker during the deletion job) |

### refresh_tokens
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK → users ON DELETE CASCADE, indexed |
| token_hash | text | unique (only the hash is stored) |
| expires_at | timestamptz | not null |
| revoked_at | timestamptz | null |

### farms
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK → users ON DELETE CASCADE, indexed |
| name | varchar(120) | not null |
| state | varchar(80) | |
| district | varchar(80) | |
| latitude | numeric(8,5) | CHECK between −90 and 90 |
| longitude | numeric(8,5) | CHECK between −180 and 180 |
| created_at / updated_at | timestamptz | |

Unique: `(user_id, name)`.

### farm_crops
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| farm_id | uuid | FK → farms ON DELETE CASCADE, indexed |
| crop_name | varchar(80) | not null |
| variety | varchar(80) | |
| sowing_date | date | |
| crop_stage | varchar(40) | e.g. `sowing`, `vegetative`, `flowering`, `harvest` |
| status | varchar(20) | `active` \| `harvested` \| `failed` |

### predictions
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK → users ON DELETE CASCADE, not null |
| farm_id | uuid | FK → farms ON DELETE SET NULL |
| image_key | text | object-storage key; null if the image was not retained |
| predicted_class_id | smallint | FK → disease_classes |
| confidence | real | CHECK 0–1 |
| status | varchar(20) | `confident` \| `uncertain` \| `unsupported` |
| model_version | varchar(80) | not null |
| source | varchar(10) | `camera` \| `gallery` |
| inference_ms | integer | |
| created_at | timestamptz | |

Index: `(user_id, created_at DESC)`.

**Ownership:** the farm-ownership check is enforced in the service layer. A trigger or composite FK can be added as defence in depth so that `farm_id`, when set, must belong to the same `user_id`.

### prediction_candidates
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| prediction_id | uuid | FK → predictions ON DELETE CASCADE |
| class_id | smallint | FK → disease_classes |
| score | real | |
| rank | smallint | 1..k; unique `(prediction_id, rank)` |

### disease_classes
| Column | Type | Constraints |
|---|---|---|
| id | smallint | PK = model output index |
| class_key | varchar(120) | unique, exactly as in `class_mapping.json` |
| crop_name | varchar(80) | display name |
| disease_name | varchar(120) | display name (`Healthy` for healthy classes) |
| is_healthy | boolean | |
| is_supported | boolean | false hides a class whose quality is too low to show confidently |
| mapping_version | varchar(40) | ties the rows to a model version |

The table is seeded by a script from the verified mapping, not by hand.

### advisories
| Column | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| disease_class_id | smallint | FK → disease_classes |
| language | varchar(10) | default `'en'` |
| symptoms | text | |
| prevention | text | |
| treatment_guidance | text | |
| source_url | text | not null |
| reviewed_by | varchar(120) | |
| reviewed_at | timestamptz | |
| status | varchar(20) | `draft` \| `reviewed` \| `retired` |

The API serves only `status = 'reviewed' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL`. Unique: `(disease_class_id, language)` where status is `reviewed`.

## Migrations

```bash
alembic revision --autogenerate -m "describe change"
# review the generated file before committing — autogenerate misses CHECKs, triggers and enums
alembic upgrade head
alembic downgrade -1   # must work for every migration
```

Rules:
- One logical change per migration.
- Never edit a migration that has already been applied to a shared environment.
- Seed data (`disease_classes`) lives in a separate, idempotent seed command, not in schema migrations.
