from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz


FIGURE_RE = re.compile(
    r"\b(?:figure|fig\.?|capture|diagramme|sch[ée]ma|tableau)\s*(?:n[°o]\s*)?[\dIVX]+(?:[.\-]\d+)?",
    re.IGNORECASE,
)
DIAGRAM_RE = re.compile(
    r"\b(?:diagramme\s+(?:de\s+)?(?:classes?|s[ée]quence|cas\s+d.?utilisation|use\s*case)|use\s*case|classe|s[ée]quence)\b",
    re.IGNORECASE,
)
CHAPTER_RE = re.compile(r"^\s*(?:chapitre|chapter)\s+([0-9IVXLC]+)\b[:\s-]*(.*)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+){0,4})\s+(.{3,120})$")


def normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def page_words(text: str) -> int:
    return len(re.findall(r"\w+", text, re.UNICODE))


def find_visual_context(page_text: str) -> list[dict]:
    lines = [normalize(line) for line in page_text.splitlines()]
    lines = [line for line in lines if line]
    hits: list[dict] = []
    for index, line in enumerate(lines):
        if not (FIGURE_RE.search(line) or DIAGRAM_RE.search(line)):
            continue
        before = " ".join(lines[max(0, index - 8) : index])
        hits.append(
            {
                "line": line[:220],
                "before_words": page_words(before),
                "before_excerpt": before[-450:],
                "kind": "diagram" if DIAGRAM_RE.search(line) else "figure",
            }
        )
    return hits


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python tools/analyze_report_pdf.py INPUT.pdf OUTPUT.json", file=sys.stderr)
        return 2

    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    doc = fitz.open(pdf_path)

    pages: list[dict] = []
    chapters: list[dict] = []
    sections: list[dict] = []
    visual_hits: list[dict] = []

    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        words = page_words(text)
        first_lines = [normalize(line) for line in text.splitlines() if normalize(line)][:8]
        for line in first_lines:
            chapter_match = CHAPTER_RE.match(line)
            if chapter_match:
                chapters.append(
                    {
                        "page": page_index,
                        "chapter": chapter_match.group(1),
                        "title": normalize(chapter_match.group(2)),
                    }
                )
            section_match = SECTION_RE.match(line)
            if section_match:
                title = normalize(section_match.group(2))
                if not title.lower().startswith(("figure", "tableau")):
                    sections.append({"page": page_index, "number": section_match.group(1), "title": title})

        contexts = find_visual_context(text)
        for context in contexts:
            context["page"] = page_index
            visual_hits.append(context)

        pages.append(
            {
                "page": page_index,
                "words": words,
                "chars": len(text),
                "first_lines": first_lines,
                "visual_hits": len(contexts),
            }
        )

    heavy_pages = sorted(pages, key=lambda item: item["words"], reverse=True)[:20]
    long_visual_contexts = sorted(
        [hit for hit in visual_hits if hit["before_words"] >= 45],
        key=lambda item: item["before_words"],
        reverse=True,
    )[:80]

    result = {
        "pdf": str(pdf_path),
        "page_count": len(doc),
        "total_words": sum(page["words"] for page in pages),
        "avg_words_per_page": round(sum(page["words"] for page in pages) / max(len(pages), 1), 1),
        "chapters": chapters,
        "sections_sample": sections[:160],
        "visual_hit_count": len(visual_hits),
        "long_visual_contexts": long_visual_contexts,
        "heavy_pages": heavy_pages,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["page_count", "total_words", "avg_words_per_page", "visual_hit_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
