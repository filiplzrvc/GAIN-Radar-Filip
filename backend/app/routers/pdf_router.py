from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@router.get("/api/pdf/{course}/{filename}")
async def get_pdf(course: str, filename: str):
    safe_course = Path(course).name
    if safe_course != course:
        raise HTTPException(status_code=400, detail="Ungültiges Fach")

    safe_filename = Path(filename).name
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")

    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien erlaubt")

    course_dir = DATA_DIR / safe_course

    if not course_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fach-Ordner nicht gefunden: {safe_course}. Gesucht wurde hier: {course_dir}"
        )

    # 1. Exakt suchen
    pdf_path = course_dir / safe_filename

    # 2. Falls exakt nicht gefunden: tolerant suchen
    if not pdf_path.exists():
        for file in course_dir.glob("*.pdf"):
            if file.name.lower() == safe_filename.lower():
                pdf_path = file
                break

    if not pdf_path.exists():
        available_pdfs = [file.name for file in course_dir.glob("*.pdf")]

        raise HTTPException(
            status_code=404,
            detail={
                "message": f"PDF nicht gefunden: {safe_course}/{safe_filename}",
                "gesucht_wurde": str(course_dir / safe_filename),
                "verfügbare_pdfs": available_pdfs,
            },
        )

    encoded_filename = quote(pdf_path.name)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
        },
    )


@router.get("/api/pdf-test")
async def pdf_test():
    return {
        "data_dir": str(DATA_DIR),
        "exists": DATA_DIR.exists(),
        "courses": {
            course_dir.name: [file.name for file in course_dir.glob("*.pdf")]
            for course_dir in DATA_DIR.iterdir()
            if course_dir.is_dir()
        } if DATA_DIR.exists() else {},
    }