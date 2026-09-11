import argparse
import re
from pathlib import Path

URL_REGEX = re.compile(r"https?://(?:www\.)?examtopics\.com/[^\s)\]>]+")


def extract_links(text, unique=False):
    links = URL_REGEX.findall(text)
    if not unique:
        return links

    seen = set()
    deduped = []
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped


def main():
    parser = argparse.ArgumentParser(
        description="Extract all URLs from a text file into a newline-separated output file."
    )
    parser.add_argument("input_file", help="Path to the input .txt file")
    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Optional output file path (default: <input>.urls.txt)",
    )
    parser.add_argument(
        "--unique",
        action="store_true",
        help="Remove duplicate URLs while preserving first-seen order",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    output_path = Path(args.output_file) if args.output_file else input_path.with_suffix(".urls.txt")

    text = input_path.read_text(encoding="utf-8-sig", errors="replace")
    links = extract_links(text, unique=args.unique)

    output_path.write_text("\n".join(links) + ("\n" if links else ""), encoding="utf-8")

    print(f"Extracted {len(links)} URLs to {output_path}")


if __name__ == "__main__":
    main()
