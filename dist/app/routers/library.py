from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
import json
import os
import time
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from xhtml2pdf import pisa
from ..config import library_file, content_dir, settings_file
from ..models import LibraryItem, ContentItem
from ..utils import safe_save_json
import sys
from pathlib import Path

# Add app logic to path for imports if needed
base_dir = Path(__file__).parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

try:
    from logic.smart_content_detector import (
        find_content_start_page,
        detect_headers_footers,
        apply_header_footer_filter,
    )
except ImportError:
    # Add parent dir to path to find logic module
    sys.path.append(str(base_dir))
    try:
        from logic.smart_content_detector import (
            find_content_start_page,
            detect_headers_footers,
            apply_header_footer_filter,
        )
    except ImportError:
        # Fallback if logic folder is in a different relative location
        pass

router = APIRouter()


@router.post("/api/convert/epub")
async def convert_epub(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="Not an EPUB file")

    pid = os.getpid()
    timestamp = int(time.time() * 1000)
    temp_epub = content_dir / f"temp_{pid}_{timestamp}.epub"
    temp_pdf = content_dir / f"converted_{pid}_{timestamp}.pdf"

    def cleanup_files():
        try:
            if temp_epub.exists():
                temp_epub.unlink()
            if temp_pdf.exists():
                temp_pdf.unlink()
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")

    try:
        with open(temp_epub, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            book = epub.read_epub(str(temp_epub))
        except Exception:
            cleanup_files()
            raise HTTPException(
                status_code=400, detail="Cannot read protected file (DRM)"
            )

        html_content = "<html><body>"
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                body = soup.find("body")
                if body:
                    html_content += str(body)
                else:
                    html_content += str(soup)
        html_content += "</body></html>"

        with open(temp_pdf, "wb") as f:
            pisa_status = pisa.CreatePDF(html_content, dest=f)

        if pisa_status.err:
            cleanup_files()
            raise HTTPException(status_code=500, detail="PDF conversion failed")

        background_tasks.add_task(cleanup_files)
        return FileResponse(
            temp_pdf, media_type="application/pdf", filename=temp_pdf.name
        )

    except HTTPException:
        cleanup_files()
        raise
    except Exception as e:
        cleanup_files()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/library")
async def get_library():
    try:
        with open(library_file, "r") as f:
            return json.load(f)
    except Exception:
        return []


@router.post("/api/library")
async def save_library_item(item: LibraryItem):
    try:
        with open(library_file, "r") as f:
            library = json.load(f)
    except Exception:
        library = []

    found = False
    for i, existing in enumerate(library):
        if existing.get("id") == item.id:
            library[i] = item.model_dump()
            found = True
            break
    if not found:
        library.append(item.model_dump())

    safe_save_json(library_file, library)
    return {"status": "ok"}


@router.delete("/api/library/{doc_id}")
async def delete_library_item(doc_id: str):
    try:
        with open(library_file, "r") as f:
            library = json.load(f)

        len_before = len(library)
        library = [item for item in library if item.get("id") != doc_id]

        if len(library) < len_before:
            safe_save_json(library_file, library)
            for ext in [".json", ".pdf", ".epub"]:
                file_path = content_dir / f"{doc_id}{ext}"
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
            return {"status": "deleted"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/library/content/{doc_id}")
async def get_content(doc_id: str):
    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404)
    with open(file_path, "r") as f:
        data = json.load(f)

    pages = data.get("pages", [])
    if pages:
        # Import needs to happen or be available
        from logic.smart_content_detector import find_content_start_page

        smart_start = find_content_start_page(pages)
        data["smart_start_page"] = smart_start

    return data


@router.post("/api/library/content")
async def save_content(item: ContentItem):
    safe_save_json(content_dir / f"{item.id}.json", item.model_dump())
    return {"status": "ok"}


@router.get("/api/library/content/{doc_id}/page/{page_index}")
async def get_page_with_filter(doc_id: str, page_index: int):
    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    with open(file_path, "r") as f:
        data = json.load(f)

    pages = data.get("pages", [])
    if page_index < 0 or page_index >= len(pages):
        raise HTTPException(status_code=400, detail="Invalid page index")

    with open(settings_file, "r") as f:
        settings = json.load(f)

    mode = settings.get("header_footer_mode", "off")
    page_text = pages[page_index]

    from logic.smart_content_detector import (
        detect_headers_footers,
        apply_header_footer_filter,
    )

    noise = detect_headers_footers(pages, page_index)

    if mode in ["clean", "dim"]:
        filtered_text = apply_header_footer_filter(
            page_text, noise["headers"], noise["footers"], mode
        )
    else:
        filtered_text = page_text

    return {
        "page_index": page_index,
        "original_text": page_text,
        "filtered_text": filtered_text,
        "headers": noise["headers"],
        "footers": noise["footers"],
        "mode": mode,
    }


@router.get("/api/library/search/{doc_id}")
async def search_book(doc_id: str, q: str):
    if not q or len(q) < 2:
        return {"results": [], "total_matches": 0, "query": q}

    file_path = content_dir / f"{doc_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    with open(file_path, "r") as f:
        data = json.load(f)

    pages = data.get("pages", [])
    query_lower = q.lower()
    results = []
    total_matches = 0

    for page_index, page_text in enumerate(pages):
        page_lower = page_text.lower()
        match_count = page_lower.count(query_lower)

        if match_count > 0:
            matches = []
            start = 0
            while True:
                pos = page_lower.find(query_lower, start)
                if pos == -1:
                    break
                context_start = max(0, pos - 50)
                context_end = min(len(page_text), pos + len(q) + 50)
                snippet = page_text[context_start:context_end]
                if context_start > 0:
                    snippet = "..." + snippet
                if context_end < len(page_text):
                    snippet = snippet + "..."
                matches.append({"position": pos, "snippet": snippet})
                start = pos + 1

            results.append(
                {
                    "page_index": page_index,
                    "match_count": match_count,
                    "matches": matches[:3],
                }
            )
            total_matches += match_count

    return {
        "results": results,
        "total_matches": total_matches,
        "query": q,
        "pages_with_matches": len(results),
    }
