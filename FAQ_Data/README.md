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
└── new_pinternship_2026-01-19/       # New Pinternship FAQ data (68 FAQs)
    └── pinternship_faqs.json         # Source data for migration
```

## Migration Process

To migrate FAQ data to MongoDB:

```bash
# Run migration script
python scripts/migrate_pinternship_faqs.py

# Or via Docker
docker exec faq-mcp-server python migrate_pinternship_faqs.py
```

The script will:
1. Load FAQ data from `new_pinternship_2026-01-19/pinternship_faqs.json`
2. Clear existing MongoDB data
3. Generate embeddings using BGE-large-en-v1.5
4. Insert new FAQs into MongoDB

## Data Format

The JSON file contains:
- **source**: URL of original FAQ documentation
- **migration_date**: Date of migration
- **program**: Program name
- **total_faqs**: Total number of FAQs
- **categories**: Number of categories
- **faqs**: Array of FAQ objects with:
  - `category`: FAQ category
  - `question`: Question text
  - `answer`: Answer text

## Adding New FAQ Data

To add new FAQ data:

1. Create a new dated folder: `FAQ_Data/new_program_YYYY-MM-DD/`
2. Add FAQ data as JSON file following the format in `pinternship_faqs.json`
3. Update `FAQ_DATA_FILE` path in `scripts/migrate_pinternship_faqs.py`
4. Run migration script

## Current Data

**Active**: new_pinternship_2026-01-19 (68 FAQs, 11 categories)
- Pinternship program by VLED Lab, IIT Ropar
- Source: https://github.com/sudarshansudarshan/pinternship/blob/main/Faq.md
