import json
import re
from pathlib import Path


def clean_answer_prefix(text: str) -> str:
    """
    Removes prefixes like:
    - A. Answer
    - A.Answer
    - B. Answer
    - C.Answer

    If no prefix exists, the text is returned unchanged.
    """
    return re.sub(r"^[A-D]\.\s*", "", text)


def clean_answer(answer):
    """
    Cleans an answer whether it is a string or an object with a text field.
    """
    if isinstance(answer, str):
        return clean_answer_prefix(answer)

    if isinstance(answer, dict):
        if isinstance(answer.get("text"), str):
            answer["text"] = clean_answer_prefix(answer["text"])
        return answer

    return answer


def process_json_file(file_path: Path) -> None:
    """
    Reads a JSON file, removes A./B./C./D. prefixes from answers,
    and writes the cleaned data back to the same file.
    """
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    for question in data:
        if "answers" in question and isinstance(question["answers"], list):
            question["answers"] = [
                clean_answer(answer)
                for answer in question["answers"]
            ]

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    print(f"Processed: {file_path}")


def process_folder(folder_path: str) -> None:
    """
    Processes all JSON files inside the given folder.
    """
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder_path}")

    json_files = list(folder.glob("*.json"))

    if not json_files:
        print("No JSON files found.")
        return

    for json_file in json_files:
        process_json_file(json_file)


if __name__ == "__main__":
    folder_path = input("Enter folder path containing JSON files: ").strip()
    process_folder(folder_path)