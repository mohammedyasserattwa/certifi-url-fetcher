import argparse
import io
import re
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals to avoid charmap UnicodeEncodeErrors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from main import fetch_specific_question_url, fetch_specific_question_url_for_topic


def detect_cert_and_topic_from_urls(urls_file: Path):
    """
    Attempts to infer the certification name and topic number from existing URLs in urls.txt.
    Example URL:
    https://www.examtopics.com/discussions/google/view/79414-exam-professional-data-engineer-topic-1-question-1/
    """
    if not urls_file.exists():
        return None, None

    try:
        content = urls_file.read_text(encoding="utf-8-sig", errors="replace")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        for line in lines:
            match = re.search(
                r"exam-(?P<cert>.+?)-topic-(?P<topic>\d+)-question-\d+",
                line,
                re.IGNORECASE,
            )
            if match:
                cert = match.group("cert").replace("-", " ")
                topic = int(match.group("topic"))
                return cert, topic
    except Exception:
        pass

    return None, None


def read_failed_questions(failed_file: Path):
    """
    Reads question numbers from the failed file.
    Returns a list of unique integers preserving their original order.
    """
    if not failed_file.exists():
        return []

    content = failed_file.read_text(encoding="utf-8-sig", errors="replace")
    questions = []
    seen = set()

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            q_num = int(line)
            if q_num not in seen:
                seen.add(q_num)
                questions.append(q_num)
        except ValueError:
            print(f"Warning: Skipping non-integer line in {failed_file.name}: {line}")

    return questions


def save_failed_questions(failed_file: Path, remaining_questions: list):
    """
    Rewrites the failed file with the remaining failed question numbers.
    """
    if remaining_questions:
        content = "\n".join(str(q) for q in remaining_questions) + "\n"
    else:
        content = ""
    failed_file.write_text(content, encoding="utf-8")


def append_url_to_file(urls_file: Path, url: str):
    """
    Appends a verified URL to urls.txt and flushes immediately.
    """
    with urls_file.open("a", encoding="utf-8") as f:
        f.write(f"{url}\n")
        f.flush()


def retry_failed(
    cert_name: str,
    topic_number: int | None = None,
    failed_file_path: str = "failed.txt",
    urls_file_path: str = "urls.txt",
    delay_between_requests: float = 1.0,
):
    failed_file = Path(failed_file_path)
    urls_file = Path(urls_file_path)

    questions = read_failed_questions(failed_file)
    if not questions:
        print(f"No failed questions found in '{failed_file}'. Nothing to retry.")
        return

    total_failed = len(questions)
    topic_info = f" (Topic {topic_number})" if topic_number is not None else ""
    print(f"Loaded {total_failed} failed question(s) from '{failed_file}'.")
    print(f"Starting retry for '{cert_name}'{topic_info}...\n")

    resolved_count = 0
    remaining_questions = list(questions)

    for q in questions:
        print(f"[RETRY] Searching for Q{q}...")
        if topic_number is not None:
            url = fetch_specific_question_url_for_topic(cert_name, q, topic_number)
        else:
            url = fetch_specific_question_url(cert_name, q)

        if url:
            print(f"[FOUND] Q{q}: {url}")
            append_url_to_file(urls_file, url)
            remaining_questions.remove(q)
            save_failed_questions(failed_file, remaining_questions)
            resolved_count += 1
            print(f"[UPDATED] Added Q{q} to {urls_file.name} and removed from {failed_file.name}.\n")
        else:
            print(f"[FAILED] Could not find URL for Q{q}\n")

        time.sleep(delay_between_requests)

    print("-" * 50)
    print(f"Retry completed: Resolved {resolved_count}/{total_failed} questions.")
    print(f"Remaining failed questions: {len(remaining_questions)} (saved in {failed_file})")
    print(f"URLs saved in {urls_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Retry fetching URLs for failed question numbers from failed.txt, adding found URLs to urls.txt and removing them from failed.txt."
    )
    parser.add_argument(
        "cert_name",
        nargs="?",
        default=None,
        help="Certification name (e.g. 'Professional Data Engineer' or 'AZ-900')",
    )
    parser.add_argument(
        "-t",
        "--topic",
        type=int,
        default=None,
        help="Specific topic number (optional)",
    )
    parser.add_argument(
        "--failed-file",
        default="failed.txt",
        help="Path to the failed questions file (default: failed.txt)",
    )
    parser.add_argument(
        "--urls-file",
        default="urls.txt",
        help="Path to the URLs output file (default: urls.txt)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between search requests (default: 1.0)",
    )

    args = parser.parse_args()

    cert_name = args.cert_name
    topic_number = args.topic
    failed_file = Path(args.failed_file)
    urls_file = Path(args.urls_file)

    # Interactive fallback if certification name is not passed as CLI argument
    if not cert_name:
        detected_cert, detected_topic = detect_cert_and_topic_from_urls(urls_file)
        if detected_cert:
            prompt_str = f"Enter certification name [default: {detected_cert}]: "
            user_cert = input(prompt_str).strip()
            cert_name = user_cert if user_cert else detected_cert

            if topic_number is None and detected_topic is not None:
                topic_prompt = f"Enter topic number [default: {detected_topic}]: "
                user_topic = input(topic_prompt).strip()
                if user_topic:
                    try:
                        topic_number = int(user_topic)
                    except ValueError:
                        print("Invalid topic number; proceeding without topic filter.")
                        topic_number = None
                else:
                    topic_number = detected_topic
        else:
            cert_name = input("Enter certification name (e.g. 'AZ-900'): ").strip()
            if not cert_name:
                print("Error: Certification name is required.")
                sys.exit(1)

            if topic_number is None:
                user_topic = input("Enter topic number (optional, press Enter to skip): ").strip()
                if user_topic:
                    try:
                        topic_number = int(user_topic)
                    except ValueError:
                        print("Invalid topic number; proceeding without topic filter.")
                        topic_number = None

    retry_failed(
        cert_name=cert_name,
        topic_number=topic_number,
        failed_file_path=args.failed_file,
        urls_file_path=args.urls_file,
        delay_between_requests=args.delay,
    )


if __name__ == "__main__":
    main()
