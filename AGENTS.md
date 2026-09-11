# Certifi URL Fetcher - Repository Memory & Agent Guidelines

## 1. Overview & Purpose
**Certifi URL Fetcher** (`certifi-url-fetcher`) is a Python automation toolkit used to search, extract, verify, and clean ExamTopics discussion URLs and exam question data.

---

## 2. Technology Stack & Dependencies
- **Language**: Python 3.x
- **Virtual Environment**: `.venv/`
- **Dependencies** (`requirements.txt`):
  - `requests >= 2.31.0` (HTTP requests & page verification)
  - `ddgs >= 9.0.0` (DuckDuckGo search queries)
- **Standard Library Modules**: `re`, `json`, `pathlib`, `sys`, `time`, `argparse`

---

## 3. Project Structure & Core Scripts

```
certifi-url-fetcher/
├── .venv/               # Virtual environment directory
├── extract_links.py     # Regex-based ExamTopics URL extractor from text files
├── failed.txt           # Output log containing question numbers that could not be resolved
├── json_formatter.py    # Batch JSON cleaner removing answer prefixes (A., B., C., D.)
├── main.py              # Automated URL search, ranking, verification, and output pipeline
├── requirements.txt     # Project dependencies (requests, ddgs)
├── retry_failed.py      # Retries failed questions, appends to urls.txt and updates failed.txt
├── README.md            # Basic documentation
└── urls.txt             # Output file containing discovered ExamTopics discussion URLs
```

---

## 4. Scripts & Workflows

### 4.1. `main.py`
Automated pipeline for searching ExamTopics discussion URLs via DuckDuckGo and verifying them before recording.
- **Verification Strategy**:
  1. *Strict Slug Match*: Direct match on URL pattern with cert and question (trusted immediately).
  2. *Relaxed Match + Page Verification*: Fetches HTML and scans `<title>` / page headers for `question #<num>` and `topic #<num>`.
  3. *Snippet Fallback*: Inconclusive page fetch trusts high-confidence snippet score ($\ge 2$).
- **CLI Commands**:
  ```powershell
  # General search across question numbers
  python main.py "<cert_name>" <start_question> <end_question>
  # Example: python main.py "AZ-900" 1 200

  # Specific topic search
  python main.py "<cert_name>" <start_question> <end_question> -t <topic_number>
  # Example: python main.py "microsoft-ai" 1 200 -t 1
  ```
- **Outputs**:
  - `urls.txt` (appends found links, flushed after each write)
  - `failed.txt` (appends failed question numbers)

### 4.2. `retry_failed.py`
Re-runs verification queries for unresolved question numbers from `failed.txt`. Found URLs are appended to `urls.txt` and removed from `failed.txt` immediately in real time.
- **CLI Commands**:
  ```powershell
  # Interactive mode (auto-detects certification / topic)
  python retry_failed.py

  # Direct CLI arguments
  python retry_failed.py "<cert_name>" -t <topic_number>
  # Example: python retry_failed.py "Professional Data Engineer" -t 1
  ```

### 4.3. `extract_links.py`
Extracts and deduplicates ExamTopics discussion URLs from arbitrary text files.
- **CLI Command**:
  ```powershell
  python extract_links.py <input_file> [output_file] [--unique]
  # Example: python extract_links.py input.txt --unique
  ```

### 4.3. `json_formatter.py`
Cleans answer option prefixes (e.g. `A. `, `B. `, `C. `, `D. `) in-place across all `.json` files in a given directory.
- **Usage**:
  ```powershell
  python json_formatter.py
  ```

---

## 5. Development Conventions & Rules
1. **Delays & Anti-Scraping Compliance**: Maintain rate-limiting pauses (`time.sleep(1)` between searches, `30s` on retries) and standard browser headers (`HEADERS`).
2. **Encodings**: Use `utf-8` or `utf-8-sig` across all file reads and writes.
3. **Data Integrity**: Append to output files incrementally with `.flush()` to prevent data loss on cancellation.
