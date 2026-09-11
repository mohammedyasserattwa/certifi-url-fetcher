# Certifi URL Fetcher

A Python automation toolkit for finding, verifying, extracting, and formatting ExamTopics certification discussion links and question datasets.

---

## Features

- **Automated URL Search & Verification (`main.py`)**:
  - Automatically queries DuckDuckGo for ExamTopics discussion links across a range of question numbers.
  - Multi-tier verification: strict URL pattern matching, snippet scoring, and deep page content verification (`<title>` and header matching).
  - Handles network timeouts and rate-limiting gracefully.
  - Logs verified URLs to `urls.txt` and missing question numbers to `failed.txt`.
- **Retry Failed Questions (`retry_failed.py`)**:
  - Automatically reads unresolved question numbers from `failed.txt` and attempts to refetch them.
  - Upon finding each missing URL, appends it to `urls.txt` and immediately removes the resolved question from `failed.txt` (persisted in real time).
  - Supports CLI arguments or auto-detecting certification and topic from existing `urls.txt`.
- **Text File Link Extraction (`extract_links.py`)**:
  - Regex-based extraction of ExamTopics URLs from raw text/logs with optional deduplication.
- **Answer Prefix Cleaner (`json_formatter.py`)**:
  - Batch sanitization tool to strip answer option prefixes (`A.`, `B.`, `C.`, `D.`) from question JSON files in place.

---

## Installation & Setup

1. **Activate virtual environment** (if not already active):
   ```powershell
   .venv\Scripts\activate
   ```

2. **Install requirements**:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Usage

### 1. Fetching URLs for a Certification (`main.py`)

Search for ExamTopics discussion URLs across a question number range:

```powershell
python main.py "<cert_name>" <start_question_number> <end_question_number> [-t <topic_number>]
```

#### Examples:
```powershell
# Search AZ-900 questions 1 to 200
python main.py "AZ-900" 1 200

# Search Microsoft AI topic 1 questions 1 to 200
python main.py "microsoft-ai" 1 200 -t 1
```

- Results are written to `urls.txt`.
- Unresolved questions are logged to `failed.txt`.

---

### 2. Retrying Failed Questions (`retry_failed.py`)

Reads unresolved question numbers from `failed.txt`, attempts to fetch them, appends found URLs to `urls.txt`, and removes resolved items from `failed.txt` in real time:

```powershell
python retry_failed.py ["<cert_name>"] [-t <topic_number>] [--failed-file <path>] [--urls-file <path>] [--delay <seconds>]
```

#### Examples:
```powershell
# Interactive mode (auto-detects certification & topic from urls.txt if available)
python retry_failed.py

# Explicit certification and topic
python retry_failed.py "Professional Data Engineer" -t 1

# Custom delay between retries
python retry_failed.py "AZ-900" --delay 1.5
```

---

### 3. Extracting URLs from a Text File (`extract_links.py`)

Extract all ExamTopics URLs from an existing text file:

```powershell
python extract_links.py <input_file> [output_file] [--unique]
```

#### Example:
```powershell
python extract_links.py input.txt --unique
```

This writes deduplicated URLs in original order to `input.urls.txt`.

---

### 4. Cleaning Answer Prefixes in JSON Datasets (`json_formatter.py`)

Sanitizes question choices by stripping leading `A.`, `B.`, `C.`, `D.` prefixes in all `.json` files in a given folder:

```powershell
python json_formatter.py
```
*(Prompts for target folder path upon launch)*

---

## Project Structure

```
certifi-url-fetcher/
├── .venv/               # Python virtual environment
├── AGENTS.md            # Agent memory & developer guidelines
├── GEMINI.md            # Gemini / Antigravity workspace memory
├── README.md            # Project documentation
├── extract_links.py     # ExamTopics link extractor
├── failed.txt           # Unresolved question numbers
├── json_formatter.py    # JSON answer prefix cleaner
├── main.py              # Main URL discovery & verification pipeline
├── requirements.txt     # Python package dependencies
├── retry_failed.py      # Retries failed questions & syncs urls.txt / failed.txt
└── urls.txt             # Collected ExamTopics URLs
```
