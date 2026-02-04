# FAQ Data Directory

This directory contains FAQ data organized by date and program.

## Structure

```
FAQ_Data/
├── old_bootcamp_2025-12-22/          # Original bootcamp FAQ data (54 FAQs)
│   ├── Unified_FAQ.txt
│   ├── NPTEL Internship -FAQ .txt
│   └── Frequently Asked Questions.txt
│
├── new_pinternship_2026-01-19/       # Pinternship FAQ data v1 (68 FAQs)
│   └── pinternship_faqs.json
│
FAQ_Data/
├── new_pinternship_2026-01-24/       # Pinternship FAQ data v2 (71 FAQs)
│   └── pinternship_faqs.json
│
├── new_pinternship_2026-02-01/       # Pinternship FAQ data v3 (66 FAQs)
│   └── pinternship_faqs.json
│
└── new_pinternship_2026-02-04/       # Pinternship FAQ data v4 (73 FAQs)
    └── pinternship_faqs.json         # Active Source Data
```

## Migration Process

To migrate FAQ data to MongoDB:

```bash
# Run migration script via automation controller (Recommended)
python3 scripts/automate_faq_update.py

# Or manually via Docker
docker exec faq-mcp-server python scripts/migrate_pinternship_faqs.py
```

## Automation (New)

You can now automate the entire update process from a local `FAQ.md` file:

```bash
python3 scripts/automate_faq_update.py FAQ.md
```

This script will:
1. Parse the Markdown file
2. Generate the JSON dataset with automatically assigned category IDs
3. Deploy to Docker and execute migration in one step

## Data Format

The JSON file contains:
- **source**: URL of original FAQ documentation
- **migration_date**: Date of migration
- **program**: Program name
- **total_faqs**: Total number of FAQs
- **faqs**: Array of FAQ objects with `category_id`, `question`, `answer`.

## Current Data

**Active**: new_pinternship_2026-02-04 (73 FAQs, 12 categories)
- Pinternship program by VLED Lab, IIT Ropar
- Source: Local FAQ.md
- Combined text embeddings enabled
