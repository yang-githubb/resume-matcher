from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import db
from app.config import settings
from app.parsers.document import extract_text, structure_text
from app.schemas import (
    JobSummary,
    ParseResponse,
    StructuredDocument,
    TextDocumentRequest,
    UpdateDocumentRequest,
)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_SUFFIXES = {".pdf", ".docx"}


@router.get("/jobs", response_model=list[JobSummary])
async def list_jobs() -> list[JobSummary]:
    return [JobSummary(**job) for job in db.list_jobs()]


@router.delete("/{doc_id}")
async def delete_document(doc_id: str) -> dict[str, str]:
    doc = db.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not db.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "deleted", "id": doc_id}


@router.post("/upload", response_model=ParseResponse)
async def upload_document(
    doc_type: Literal["resume", "job"] = Form(...),
    file: UploadFile = File(...),
) -> ParseResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    stored_name = f"{uuid4()}{suffix}"
    stored_path = settings.upload_dir / stored_name

    with stored_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        raw_text = extract_text(stored_path)
    except ValueError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text.strip():
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Could not extract text. Try a different file or paste-ready PDF.",
        )

    structured = structure_text(raw_text)
    doc_id = db.insert_document(doc_type, file.filename, raw_text, structured)

    return ParseResponse(
        id=doc_id,
        doc_type=doc_type,
        filename=file.filename,
        raw_text=raw_text,
        structured=StructuredDocument(**structured),
    )


@router.get("/{doc_id}", response_model=ParseResponse)
async def get_document(doc_id: str) -> ParseResponse:
    doc = db.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return ParseResponse(
        id=doc["id"],
        doc_type=doc["doc_type"],
        filename=doc["filename"],
        raw_text=doc["raw_text"],
        structured=StructuredDocument(**doc["structured"]),
    )


@router.post("/text", response_model=ParseResponse)
async def create_from_text(request: TextDocumentRequest) -> ParseResponse:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    structured = structure_text(text)
    doc_id = db.insert_document(request.doc_type, request.label, text, structured)

    return ParseResponse(
        id=doc_id,
        doc_type=request.doc_type,
        filename=request.label,
        raw_text=text,
        structured=StructuredDocument(**structured),
    )


@router.patch("/{doc_id}", response_model=ParseResponse)
async def update_document_text(doc_id: str, request: UpdateDocumentRequest) -> ParseResponse:
    doc = db.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    text = request.raw_text.strip()
    structured = structure_text(text)
    updated = db.update_document(doc_id, text, structured)
    if not updated:
        raise HTTPException(status_code=404, detail="Document not found.")

    return ParseResponse(
        id=doc_id,
        doc_type=doc["doc_type"],
        filename=doc["filename"],
        raw_text=text,
        structured=StructuredDocument(**structured),
    )
