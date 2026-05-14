import os
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.services.analytics import TransactionAnalytics

router = APIRouter()


@router.post("/upload", summary="Upload a transaction CSV or Excel file and get analysis")
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Accepts a .csv or .xlsx file.
    Returns the full analytics report as JSON.
    """
    allowed = {".csv", ".xlsx", ".xls"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported. Use CSV or Excel.")

    # Save uploaded file temporarily
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / file.filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        analytics = TransactionAnalytics(str(save_path))
        report = analytics.full_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp file
        if save_path.exists():
            os.remove(save_path)

    return {"status": "success", "data": report}


@router.post("/summary", summary="Quick summary only — faster than full report")
async def quick_summary(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / file.filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        analytics = TransactionAnalytics(str(save_path))
        return {"status": "success", "data": analytics.summary()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if save_path.exists():
            os.remove(save_path)
