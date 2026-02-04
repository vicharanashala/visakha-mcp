#!/usr/bin/env python3
"""
FAQ Update Automation Script
Usage: python3 scripts/automate_faq_update.py [FAQ_FILE]

This script:
1. Parses a local FAQ.md file (extracting questions, answers, and category IDs)
2. Generates a JSON dataset in a new timestamped directory
3. Copies the data and updated migration script to the running Docker container
4. Executes the migration inside the container
"""

import sys
import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
CONTAINER_NAME = "faq-mcp-server"
DEFAULT_FAQ_FILE = "FAQ.md"

def parse_faq_md(file_path):
    """Parse FAQ.md and return list of FAQ objects with category IDs."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    faqs = []
    current_category = None
    current_category_id = 99
    
    # Regex patterns
    # Matches: ## 12. Dashboard
    category_pattern = re.compile(r'^##\s+(\d+)\.\s+(.+)$')
    # Matches: **1.1 What is this...** or **1.1 What...?**
    # We use a flexible pattern: starts with **digits.digits, captures text until **
    question_pattern = re.compile(r'^\*\*(\d+\.\d+)\s+(.+?)\*\*')

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for Category Header
        cat_match = category_pattern.match(line)
        if cat_match:
            current_category_id = int(cat_match.group(1))
            current_category = cat_match.group(2).strip()
            i += 1
            continue
            
        # Check for Question
        q_match = question_pattern.match(line)
        if q_match:
            question_num = q_match.group(1)
            question_text = q_match.group(2).strip()
            
            # Extract Answer
            answer_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                # Stop if next line is a header, new question, or separator
                if (category_pattern.match(next_line) or 
                    question_pattern.match(next_line) or 
                    next_line == '---'):
                    break
                if next_line:
                    answer_lines.append(next_line)
                i += 1
            
            # Continue outer loop from current position (i is already at next section)
            answer_text = '\n'.join(answer_lines).strip()
            
            if current_category:
                faqs.append({
                    "category": current_category,
                    "category_id": current_category_id,
                    "question": question_text,
                    "answer": answer_text
                })
            else:
                print(f"Warning: Found question '{question_text}' before any category header.")
            continue
            
        i += 1

    return faqs

def run_command(cmd, shell=True):
    """Run a shell command and return True if successful."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=shell, executable='/bin/bash')
    return result.returncode == 0

def main():
    # 1. Setup
    faq_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FAQ_FILE
    if not os.path.exists(faq_file):
        print(f"Error: File '{faq_file}' not found.")
        sys.exit(1)
        
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_dir_name = f"new_pinternship_{date_str}"
    output_dir = Path("FAQ_Data") / output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "pinternship_faqs.json"
    
    print(f"--- Step 1: Parsing {faq_file} ---")
    faqs = parse_faq_md(faq_file)
    print(f"✓ Parsed {len(faqs)} FAQs")
    
    # Save JSON
    data = {
        'source': 'FAQ.md (Local)',
        'migration_date': date_str,
        'program': 'Pinternship - VLED Lab, IIT Ropar',
        'total_faqs': len(faqs),
        'faqs': faqs
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved JSON to {output_file}")
    
    # 2. Docker Operations
    print(f"\n--- Step 2: Deploying to Container '{CONTAINER_NAME}' ---")
    
    # Path inside container
    container_data_dir = f"/app/FAQ_Data/{output_dir_name}"
    container_json_path = f"{container_data_dir}/pinternship_faqs.json"
    
    cmds = [
        # Create dir
        f"docker exec {CONTAINER_NAME} mkdir -p {container_data_dir}",
        
        # Copy JSON
        f"docker cp {output_file} {CONTAINER_NAME}:{container_json_path}",
        
        # Copy Updated Script (Vital step as we modified it!)
        f"docker cp scripts/migrate_pinternship_faqs.py {CONTAINER_NAME}:/app/scripts/migrate_pinternship_faqs.py",
        
        # Execute Migration (passing env var for path)
        f"docker exec -e FAQ_FILE_PATH={container_json_path} {CONTAINER_NAME} python scripts/migrate_pinternship_faqs.py"
    ]
    
    for cmd in cmds:
        if not run_command(cmd):
            print(f"❌ Command failed: {cmd}")
            sys.exit(1)
            
    print(f"\n✅ FAQ Update Completed Successfully!")

if __name__ == "__main__":
    main()
