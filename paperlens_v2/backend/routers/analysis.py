import logging
"""
Analysis Router
-----------------
POST /analysis/upload   → Upload doc, run AI detection + plagiarism check
GET  /analysis/{id}     → Get analysis result
GET  /analysis/history  → List user's past analyses
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
import uuid
import json
from datetime import datetime
from database import get_db
from routers.auth import require_auth
from utils.extractor import extract_text
from services.ai_detector import detect_ai_content
from services.plagiarism import check_plagiarism

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_analysis(analysis_id: str, text: str, word_count: int, db_path: str):
    """Background task: run AI + plag detection and update DB."""
    import aiosqlite
    
    try:
        ai_result = await detect_ai_content(text)
        plag_result = await check_plagiarism(text)

        result_json = json.dumps({
            "ai": ai_result,
            "plagiarism": plag_result,
        })

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """UPDATE analyses
                   SET status = 'done',
                       ai_score = ?,
                       plag_score = ?,
                       word_count = ?,
                       result_json = ?
                   WHERE id = ?""",
                (
                    ai_result["ai_score"],
                    plag_result["plag_score"],
                    word_count,
                    result_json,
                    analysis_id,
                ),
            )
            await db.commit()

    except Exception as e:
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE analyses SET status = 'error' WHERE id = ?",
                (analysis_id,),
            )
            await db.commit()
        logger.error("Analysis %s failed: %s", analysis_id, e)


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """
    Upload a document for analysis.
    - Checks credits: 1 free doc, then 1 credit per doc
    - Creates analysis record, starts background detection
    - Returns analysis_id immediately (poll /analysis/{id} for result)
    """
    user_id = current_user["id"]
    credits = current_user["credits"]
    free_used = current_user["free_used"]

    # Credit eligibility check — do NOT deduct yet (file may be invalid)
    if free_used == 0:
        pass  # free first doc — no deduction needed
    elif credits <= 0:
        raise HTTPException(
            status_code=402,
            detail="No credits remaining. Please purchase credits to continue.",
        )

    # Extract text FIRST — if file is corrupt, no credit is lost
    text, word_count = await extract_text(file)

    # File is valid — now deduct credit safely
    if free_used == 0:
        # Mark free doc as used (still no credit deduction)
        await db.execute(
            "UPDATE users SET free_used = 1 WHERE id = ?", (user_id,)
        )
    else:
        # Deduct 1 credit only after confirmed valid file
        await db.execute(
            "UPDATE users SET credits = credits - 1 WHERE id = ?", (user_id,)
        )

    await db.commit()

    # Create analysis record
    analysis_id = str(uuid.uuid4())
    filename = file.filename or "document"

    await db.execute(
        """INSERT INTO analyses (id, user_id, filename, status, word_count)
           VALUES (?, ?, ?, 'processing', ?)""",
        (analysis_id, user_id, filename, word_count),
    )
    await db.commit()

    # Run detection in background
    from config import get_settings
    settings = get_settings()
    background_tasks.add_task(
        _run_analysis, analysis_id, text, word_count, settings.DB_PATH
    )

    return {
        "analysis_id": analysis_id,
        "status": "processing",
        "filename": filename,
        "word_count": word_count,
        "message": "Analysis started. Poll /analysis/{id} for results (usually 10–30s).",
    }


@router.get("/history")
async def get_history(
    current_user: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """Return user's past analyses (last 20)."""
    user_id = current_user["id"]
    async with db.execute(
        """SELECT id, filename, status, ai_score, plag_score, word_count, created_at
           FROM analyses
           WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT 20""",
        (user_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    return {"analyses": [dict(r) for r in rows]}


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    current_user: dict = Depends(require_auth),
    db=Depends(get_db),
):
    """Get a specific analysis result. Only owner can access."""
    user_id = current_user["id"]
    async with db.execute(
        "SELECT * FROM analyses WHERE id = ? AND user_id = ?",
        (analysis_id, user_id),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = dict(row)
    if result.get("result_json"):
        result["result"] = json.loads(result["result_json"])
        del result["result_json"]

    return result
