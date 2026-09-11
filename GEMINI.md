# Certifi URL Fetcher - Repository Memory & Guide

## 1. Overview & Purpose
**Certifi URL Fetcher** (`certifi-url-fetcher`) is a Python-based automation and utility toolkit designed for collecting, verifying, extracting, and post-processing ExamTopics discussion URLs and exam question data.

---

## 2. Technology Stack & Dependencies
- **Language**: Python 3.x
- **Virtual Environment**: `.venv/` (Windows PowerShell / Python environment)
- **External Dependencies** (`requirements.txt`):
  - `requests >= 2.31.0` — HTTP fetching and page content verification
  - `ddgs >= 9.0.0` — DuckDuckGo Search API integration (`from ddgs import DDGS`)
- **Standard Library Modules**: `re`, `json`, `pathlib.Path`, `sys`, `time`, `argparse`

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

## 4. Script Details & Usage Guidelines

### 4.1. `main.py` — URL Search & Verification Pipeline
Searches DuckDuckGo for ExamTopics discussion links for a range of question numbers, validates them, and writes results to `urls.txt`.

- **Key Functions**:
  - `fetch_specific_question_url(cert_name, question_number)`: Discovers URLs for a given certification question across topics.
  - `fetch_specific_question_url_for_topic(cert_name, question_number, topic_number)`: Scoped discovery for a specific topic number.
  - `verify_question_on_page(url, question_number, topic_number, retries, retry_delay)`: Performs an HTTP GET request to check whether `<title>` or page content matches the requested question and topic.
  - `_score_snippet_for_question` & `_score_snippet_for_question_and_topic`: Ranks DuckDuckGo search result snippets before deep verification.
- **Verification Hierarchy**:
  1. *Strict Slug Match*: Direct match on URL pattern with cert and question (trusted immediately).
  2. *Relaxed Match + Page Verification*: Fetches HTML and scans `<title>` / page headers for `question #<num>` and `topic #<num>`.
  3. *Fallback Snippet Confidence*: If page verification is inconclusive but snippet score is $\ge 2$, accepted as a valid match.
- **Usage**:
  ```powershell
  # General question search
  python main.py "<cert_name>" <start_question> <end_question>
  # Example:
  python main.py "AZ-900" 1 200

  # Specific topic search
  python main.py "<cert_name>" <start_question> <end_question> -t <topic_number>
  # Example:
  python main.py "microsoft-ai" 1 200 -t 1
  ```
- **Outputs**:
  - `urls.txt` — Appends successfully discovered URLs (flushed after each hit).
  - `failed.txt` — Appends question numbers that failed resolution.

### 4.2. `retry_failed.py` — Retry Pipeline for Failed Questions
Iterates through all question numbers in `failed.txt`, executes targeted search & verification queries, appends found URLs to `urls.txt`, and removes resolved question numbers from `failed.txt` immediately (persisted after each success).

- **Key Functions**:
  - `detect_cert_and_topic_from_urls(urls_file)`: Infers certification name and topic number from existing entries in `urls.txt`.
  - `read_failed_questions(failed_file)`: Parses unique integer question numbers.
  - `save_failed_questions(failed_file, remaining_questions)`: Rewrites `failed.txt` with remaining unresolved questions.
  - `retry_failed(cert_name, topic_number, ...)`: Core retry execution loop.
- **Usage**:
  ```powershell
  # Interactive mode (prompts / auto-detects from urls.txt)
  python retry_failed.py

  # Direct CLI arguments
  python retry_failed.py "Professional Data Engineer" -t 1
  ```

### 4.3. `extract_links.py` — Raw Text Link Extractor
Scans any text file for ExamTopics URLs using regular expressions.

- **Key Function**:
  - `extract_links(text, unique=False)`: Uses `https?://(?:www\.)?examtopics\.com/[^\s)\]>]+` regex to extract links. Deduplicates while preserving first-seen order if `--unique` is passed.
- **Usage**:
  ```powershell
  python extract_links.py <input_file> [output_file] [--unique]

  # Example (generates input.urls.txt):
  python extract_links.py input.txt --unique
  ```

### 4.4. `json_formatter.py` — Question JSON Cleaner
In-place batch sanitization for downloaded/scraped question JSON files.

- **Key Functions**:
  - `clean_answer_prefix(text)`: Removes answer prefixes matching `^[A-D]\.\s*` (e.g. `A. Answer` -> `Answer`, `B.Answer` -> `Answer`).
  - `clean_answer(answer)`: Supports string answers or dict objects (`{"text": "..."}`).
  - `process_json_file(file_path)`: Reads, cleans, and saves formatted JSON back with indentation (`indent=4`, `ensure_ascii=False`).
  - `process_folder(folder_path)`: Scans all `*.json` in the specified directory.
- **Usage**:
  ```powershell
  python json_formatter.py
  # Enter the target folder path when prompted.
  ```

---

## 5. Coding & Development Standards

1. **Rate Limiting & Network Resilience**:
   - Always retain delays (e.g. `time.sleep(1)` between iterations, `retry_delay=30` on network/search errors) to prevent HTTP 429 rate limiting and IP blocking by DuckDuckGo and ExamTopics.
   - Use standard browser headers (`User-Agent`, `Accept-Language`, `Referer`) defined in `HEADERS`.
2. **File I/O & Encodings**:
   - Always use `encoding="utf-8"` or `utf-8-sig` when reading/writing text and JSON files.
   - Use `Path` from `pathlib` for path operations where possible.
3. **Data Persistence**:
   - Output logs (`urls.txt`, `failed.txt`) use append mode (`"a"`) with `.flush()` to ensure partial progress is not lost upon interruption.
