# Advisory Content Policy

Disease guidance can affect a farmer's crop, health and income. AgroSnap shows **only reviewed content drawn from reliable sources**.

## 1. Hard rules

1. **Never invent** pesticide names, dosages, mixing ratios, spray intervals or pre-harvest intervals.
2. Chemical guidance may appear **only** if it is taken from a reviewed source, with the source linked, and it must say to follow the product label and local regulations.
3. Every advisory displays its source(s) and its review date.
4. Every advisory includes: *"Confirm with your local Krishi Vigyan Kendra (KVK) or agriculture officer before applying any chemical treatment."*
5. AI-generated text may be used only as a **draft** for a human reviewer. It is never published directly.
6. If no reviewed advisory exists for a class, show generic guidance (photo tips, isolate affected plants, contact KVK) and do not show disease-specific treatment.

## 2. Preferred sources

Prefer Indian and official agricultural sources, for example:
- ICAR institutes and their published crop/disease guides.
- State Agricultural Universities (SAUs) and their extension publications.
- Krishi Vigyan Kendra (KVK) advisories.
- Government of India agriculture portals and Integrated Pest Management (IPM) packages from the Directorate of Plant Protection, Quarantine & Storage.
- Peer-reviewed plant-pathology literature (for symptoms).

For chemical recommendations, confirm that the product is registered for that crop in India (Central Insecticides Board & Registration Committee lists) before including it.

## 3. Content structure per class

| Section | Content | Chemical info allowed? |
|---|---|---|
| Symptoms | What the farmer sees on the leaf or plant | No |
| Prevention | Cultural practices: spacing, resistant varieties, crop rotation, sanitation, irrigation | No |
| What to do | Non-chemical first steps, then (optionally) chemical guidance **as stated in the source** | Only if quoted from a reviewed source |
| Sources | Title + URL for each source | — |

Use plain English at about a Class 8 reading level, with short bullets.

## 4. Review workflow

```
draft ──(reviewer checks every claim against the cited source)──▶ reviewed ──▶ (periodic re-check / source changed) ──▶ retired
```

| Step | Who | Output |
|---|---|---|
| Draft | Content contributor | `status = draft`, `source_url` filled |
| Review | Qualified reviewer (agronomist or plant pathologist; see DECISIONS.md) | `reviewed_by`, `reviewed_at`, `status = reviewed` |
| Re-review | Yearly, or when a source changes | New reviewed version; old one retired |

Store advisory source files in `content/advisories/<class_key>.en.md` (with front-matter) and load them with a script. Changes then go through pull-request review.

### Front-matter template
```yaml
class_key: tomato___early_blight
language: en
sources:
  - title: "<source title>"
    url: "https://..."
reviewed_by: ""
reviewed_at: ""
status: draft
```

## 5. Healthy classes
For `*___healthy` classes, show "No disease signs were detected on this leaf", general crop-care tips and a reminder that a single photo may not show the whole plant's condition.
