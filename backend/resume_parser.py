import os
from PyPDF2 import PdfReader

RESUMES_DIR = os.path.join(os.path.dirname(__file__), "resumes")

def load_all_resumes(resumes_dir: str = RESUMES_DIR) -> list[dict]:

    resumes = []

    if not os.path.exists(resumes_dir):
        print(f"Resumes folder not found: {resumes_dir}")
        return resumes

    for filename in os.listdir(resumes_dir):
        if filename.endswith(".pdf"):
            filepath = os.path.join(resumes_dir, filename)
            text = extract_text_from_pdf(filepath)
            if text.strip():
                resumes.append({
                    "filename": filename,
                    "text": text
                })
                print(f"Loaded: {filename} ({len(text)} chars)")

    print(f"\nTotal resumes loaded: {len(resumes)}")
    return resumes


def extract_text_from_pdf(filepath: str) -> str:
    try:
        reader = PdfReader(filepath)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""
        return full_text
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


if __name__ == "__main__":
    resumes = load_all_resumes()
    for r in resumes:
        print(f"\n--- {r['filename']} ---")
        print(r['text'][:500])  