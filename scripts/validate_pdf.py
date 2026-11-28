import hashlib
import sys
from pathlib import Path

import pymupdf


def validate_pdf(file_path):
    path = Path(file_path)

    errors = []

    if not path.exists():
        errors.append("File does not exist")
    elif not path.is_file():
        errors.append("Path is not a file")
    else:
        if path.stat().st_size == 0:
            errors.append("PDF is empty")

        if path.suffix.lower() != ".pdf":
            errors.append("Invalid file extension")

        if not errors:
            with path.open("rb") as f:
                signature = f.read(5)

            if signature != b"%PDF-":
                errors.append("Invalid PDF signature")

    if errors:
        return {"valid": False, "errors": errors}

    try:
        with pymupdf.open(path) as doc:
            if doc.is_encrypted:
                errors.append("PDF is encrypted")

            if len(doc) == 0:
                errors.append("PDF has no pages")

            if not errors:
                extracted_text = sum(len(page.get_text().strip()) for page in doc)

                sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

                return {
                    "valid": True,
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "pages": len(doc),
                    "extracted_characters": extracted_text,
                    "sha256": sha256,
                    "errors": [],
                }

    except Exception as exc:
        errors.append(f"PDF parsing failed: {exc}")

    return {"valid": False, "errors": errors}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_pdf.py <file.pdf>")
        sys.exit(1)

    result = validate_pdf(sys.argv[1])

    print(result)

    sys.exit(0 if result["valid"] else 1)
