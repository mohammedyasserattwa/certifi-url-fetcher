import sys
import time
import re
import requests
from ddgs import DDGS

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

def verify_question_on_page(url, question_number, topic_number=None, retries=3, retry_delay=30):
    """
    Fetches the ExamTopics page and checks whether it is actually for the given question number.
    Looks for patterns like "Topic 1 Question 5" in the page title or breadcrumb/heading.
    Returns True if confirmed, False if wrong question, None if unable to determine.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            text = resp.text

            # Look in the page title tag first — most reliable
            title_match = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
            page_title = title_match.group(1).lower() if title_match else ""

            # Also grab the first ~3000 chars where breadcrumbs/headings appear
            page_head = text[:3000].lower()

            combined = page_title + " " + page_head

            # Pattern: "question 5" or "question #5" anywhere
            found_qs = set(re.findall(r'question\s*#?\s*(\d+)', combined))
            found_topics = set(re.findall(r'topic\s*#?\s*(\d+)', combined))

            if str(question_number) in found_qs:
                if topic_number is None:
                    return True
                if str(topic_number) in found_topics:
                    return True
                if found_topics:
                    return False
                return None

            if topic_number is not None and found_topics and str(topic_number) not in found_topics:
                return False

            # If other question numbers are mentioned but not ours — definitely wrong
            if found_qs:
                return False

            # Could not determine from page content
            return None

        except Exception as e:
            print(f"  [Page verify attempt {attempt}/{retries}] Error fetching {url}: {e}")
            if attempt < retries:
                print(f"  Waiting {retry_delay}s before retrying...")
                time.sleep(retry_delay)

    return None  # Could not verify after all retries


def fetch_specific_question_url_for_topic(cert_name, question_number, topic_number):
    """
    Searches for a specific question of a certification within a specific topic.
    """
    cert_query = cert_name.lower().replace(" ", "-")
    cert_query_escaped = re.escape(cert_query)
    cert_parts = re.split(r'[\s\-]+', cert_name.lower())

    queries = [
        f'site:examtopics.com "{cert_name}" "topic {topic_number} question {question_number}" discussion',
        f'site:examtopics.com {cert_name} "question {question_number}" "topic {topic_number}" discussion',
        f'site:examtopics.com {cert_name} "topic {topic_number} question {question_number}" discussion',
        f'examtopics.com {cert_name} "question {question_number}" "topic {topic_number}" discussion',
    ]

    # Strict: topic + question number in URL slug — trust it immediately
    pattern_strict = rf"exam-.*{cert_query_escaped}.*-topic-{topic_number}-question-{question_number}-discussion"
    pattern_parts_strict = rf"exam-.*-topic-{topic_number}-question-{question_number}-discussion"

    # Relaxed: topic in URL slug, question number not in URL — verify by page fetch
    pattern_relaxed = rf"exam-.*{cert_query_escaped}.*-topic-{topic_number}"
    pattern_parts_relaxed = rf"exam-.*-topic-{topic_number}"

    def _url_contains_cert_parts(url_lower):
        return all(part in url_lower for part in cert_parts if len(part) >= 2)

    relaxed_candidates = []
    seen_candidates = set()

    max_retries = 3
    retry_delay = 30

    for attempt in range(1, max_retries + 1):
        try:
            ddgs = DDGS()
            for query in queries:
                results = ddgs.text(query, max_results=15)
                if not results:
                    continue
                for r in results:
                    href = r.get('href', '')
                    title = r.get('title', '').lower()
                    body = r.get('body', '').lower()

                    if "examtopics.com/discussions" not in href:
                        continue

                    href_lower = href.lower()

                    if re.search(pattern_strict, href_lower):
                        return href
                    if re.search(pattern_parts_strict, href_lower) and _url_contains_cert_parts(href_lower):
                        return href

                    is_relaxed = re.search(pattern_relaxed, href_lower) or (
                        re.search(pattern_parts_relaxed, href_lower) and _url_contains_cert_parts(href_lower)
                    )
                    if is_relaxed and href not in seen_candidates:
                        score = _score_snippet_for_question_and_topic(title, body, question_number, topic_number)
                        relaxed_candidates.append((score, href))
                        seen_candidates.add(href)

            break

        except Exception as e:
            print(f"  [Attempt {attempt}/{max_retries}] Error searching for Q{question_number} (topic {topic_number}): {e}")
            if attempt < max_retries:
                print(f"  Waiting {retry_delay}s before retrying...")
                time.sleep(retry_delay)
            else:
                print(f"  All {max_retries} attempts failed for Q{question_number} (topic {topic_number}).")

    relaxed_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, href in relaxed_candidates:
        print(f"  Verifying page for Q{question_number} (topic {topic_number}): {href}")
        result = verify_question_on_page(href, question_number, topic_number=topic_number)
        if result is True:
            return href
        elif result is False:
            print(f"  ✗ Wrong question on page, skipping.")
        else:
            if score >= 2:
                print(f"  ~ Could not verify from page content, trusting snippet match.")
                return href
            print(f"  ~ Could not verify, skipping.")

    return None


def fetch_specific_question_url(cert_name, question_number):
    """
    Searches for a specific question of a certification and returns the correct ExamTopics URL.
    """
    cert_query = cert_name.lower().replace(" ", "-")
    cert_query_escaped = re.escape(cert_query)
    cert_parts = re.split(r'[\s\-]+', cert_name.lower())

    queries = [
        f'site:examtopics.com "{cert_name}" "question {question_number}" discussion',
        f'site:examtopics.com {cert_name} "topic 1 question {question_number}" discussion',
        f'site:examtopics.com {cert_name} question {question_number} discussion',
        f'examtopics.com {cert_name} "question {question_number}" topic discussion',
    ]

    # Pattern 1: full cert name + question number in URL slug — 100% reliable, no page fetch needed
    pattern_strict = rf"exam-.*{cert_query_escaped}.*-topic-\d+-question-{question_number}-discussion"

    # Pattern 2: question number in URL slug, cert parts in URL — reliable, no page fetch needed
    pattern_parts_strict = rf"exam-.*-topic-\d+-question-{question_number}-discussion"

    # Pattern 3 & 4: no question number in URL — need page verification
    pattern_relaxed = rf"exam-.*{cert_query_escaped}.*-topic-\d+"
    pattern_parts_relaxed = rf"exam-.*-topic-\d+"

    def _url_contains_cert_parts(url_lower):
        return all(part in url_lower for part in cert_parts if len(part) >= 2)

    # Ordered list of relaxed candidates to verify via page fetch
    relaxed_candidates = []
    seen_candidates = set()

    max_retries = 3
    retry_delay = 30

    for attempt in range(1, max_retries + 1):
        try:
            ddgs = DDGS()
            for query in queries:
                results = ddgs.text(query, max_results=15)
                if not results:
                    continue
                for r in results:
                    href = r.get('href', '')
                    title = r.get('title', '').lower()
                    body = r.get('body', '').lower()

                    if "examtopics.com/discussions" not in href:
                        continue

                    href_lower = href.lower()

                    # Strict: question number IS in the URL — trust it immediately
                    if re.search(pattern_strict, href_lower):
                        return href
                    if re.search(pattern_parts_strict, href_lower) and _url_contains_cert_parts(href_lower):
                        return href

                    # Relaxed: question number NOT in URL — queue for page verification
                    is_relaxed = re.search(pattern_relaxed, href_lower) or (
                        re.search(pattern_parts_relaxed, href_lower) and _url_contains_cert_parts(href_lower)
                    )
                    if is_relaxed and href not in seen_candidates:
                        # Use snippet score to prioritise — higher score goes first
                        score = _score_snippet_for_question(title, body, question_number)
                        relaxed_candidates.append((score, href))
                        seen_candidates.add(href)

            break  # Finished all queries without exception

        except Exception as e:
            print(f"  [Attempt {attempt}/{max_retries}] Error searching for Q{question_number}: {e}")
            if attempt < max_retries:
                print(f"  Waiting {retry_delay}s before retrying...")
                time.sleep(retry_delay)
            else:
                print(f"  All {max_retries} attempts failed for Q{question_number}.")

    # Sort candidates: higher snippet score first, then try each with a real page fetch
    relaxed_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, href in relaxed_candidates:
        print(f"  Verifying page for Q{question_number}: {href}")
        result = verify_question_on_page(href, question_number)
        if result is True:
            return href
        elif result is False:
            print(f"  ✗ Wrong question on page, skipping.")
        else:
            # Could not determine — if snippet score was strong, trust it; otherwise skip
            if score >= 2:
                print(f"  ~ Could not verify from page content, trusting snippet match.")
                return href
            print(f"  ~ Could not verify, skipping.")

    return None


def _score_snippet_for_question(title, body, question_number):
    """
    Score how likely a search result snippet is for the given question number.
    Returns:
      2  - strong match (question number explicitly found in snippet)
      0  - no match or wrong question number
    """
    combined = title + " " + body

    any_q_pattern = r"question\s*[:#]?\s*(\d+)"
    found_qs = set(re.findall(any_q_pattern, combined))

    url_q_pattern = rf"topic-\d+-question-{question_number}"
    if re.search(url_q_pattern, combined):
        return 2

    if found_qs:
        if str(question_number) in found_qs:
            return 2
        else:
            return 0

    return 0


def _score_snippet_for_question_and_topic(title, body, question_number, topic_number):
    """
    Score how likely a snippet is for the given question number and topic.
    Returns:
      2  - strong match (question + topic found)
      0  - no match or mismatch
    """
    combined = title + " " + body

    any_q_pattern = r"question\s*[:#]?\s*(\d+)"
    any_t_pattern = r"topic\s*[:#]?\s*(\d+)"
    found_qs = set(re.findall(any_q_pattern, combined))
    found_topics = set(re.findall(any_t_pattern, combined))

    url_qt_pattern = rf"topic-{topic_number}-question-{question_number}"
    if re.search(url_qt_pattern, combined):
        return 2

    if found_qs and found_topics:
        if str(question_number) in found_qs and str(topic_number) in found_topics:
            return 2
        return 0

    return 0


def main():
    if len(sys.argv) < 4:
        print("Usage: python main.py <cert_name> <start_question_number> <end_question_number> [-t <topic_number>]")
        print("Example: python main.py \"AZ-900\" 1 200")
        print("Example (topic): python main.py \"microsoft-ai\" 1 200 -t 1")
        return

    cert_name = sys.argv[1]
    try:
        start_question = int(sys.argv[2])
        end_question = int(sys.argv[3])
    except ValueError:
        print("Error: question numbers must be integers.")
        return

    topic_number = None
    if "-t" in sys.argv:
        t_index = sys.argv.index("-t")
        if t_index + 1 >= len(sys.argv):
            print("Error: -t requires a topic number.")
            return
        try:
            topic_number = int(sys.argv[t_index + 1])
        except ValueError:
            print("Error: topic number must be an integer.")
            return

    if start_question > end_question:
        print("Error: start_question_number must be less than or equal to end_question_number.")
        return

    found_urls = []
    failed_questions = []
    if topic_number is not None:
        print(f"Starting search for {cert_name} topic {topic_number} from question {start_question} to {end_question}...")
    else:
        print(f"Starting search for {cert_name} from question {start_question} to {end_question}...")

    with open("urls.txt", "a", encoding="utf-8") as f:
        for i in range(start_question, end_question + 1):
            if topic_number is not None:
                url = fetch_specific_question_url_for_topic(cert_name, i, topic_number)
            else:
                url = fetch_specific_question_url(cert_name, i)
            if url:
                print(f"Found Q{i}: {url}")
                f.write(f"{url}\n")
                f.flush()
                found_urls.append(url)
            else:
                print(f"Could not find URL for Q{i}")
                failed_questions.append(i)

            # Avoid rate limiting
            time.sleep(1)

    if failed_questions:
        with open("failed.txt", "a", encoding="utf-8") as ff:
            for q in failed_questions:
                ff.write(f"{q}\n")
        print(f"\nFailed question numbers saved to failed.txt ({len(failed_questions)} total).")

    print(f"\nFinished. Found {len(found_urls)}/{(end_question - start_question) + 1} URLs.")
    print("Results are saved in urls.txt")

if __name__ == "__main__":
    main()
