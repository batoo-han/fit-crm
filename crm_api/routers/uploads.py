"""Uploads router for handling media uploads (images, documents)."""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger

router = APIRouter()

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
ALLOWED_DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
MAX_FILE_SIZE_MB = 20


def ensure_upload_dir() -> str:
    upload_dir = os.path.join("uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(None)
):
    """
    Handle file upload and return public URL.
    
    Args:
        file: File to upload
        file_type: Type of file (logo_widget, logo_site, etc.) for meaningful naming
    """
    try:
        filename = file.filename or ""
        _, ext = os.path.splitext(filename.lower())
        if ext not in (ALLOWED_IMAGE_EXT | ALLOWED_DOC_EXT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимый тип файла",
            )
        # Read content to check size
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Файл слишком большой (> {MAX_FILE_SIZE_MB}MB)",
            )
        
        upload_dir = ensure_upload_dir()
        
        # Generate meaningful filename based on file_type
        if file_type in ["logo_widget", "logo_site"]:
            # For logos, use simple name: logo_widget.ext or logo_site.ext
            # Replace old file if exists (delete all variants with timestamp)
            base_name = file_type
            new_name = f"{base_name}{ext}"
            target_path = os.path.join(upload_dir, new_name)
            
            # Delete old logo files (with and without timestamp)
            import glob
            pattern = os.path.join(upload_dir, f"{base_name}*{ext}")
            old_files = glob.glob(pattern)
            for old_file in old_files:
                try:
                    if os.path.exists(old_file):
                        os.remove(old_file)
                        logger.info(f"Deleted old logo file: {old_file}")
                except Exception as e:
                    logger.warning(f"Could not delete old logo file {old_file}: {e}")
        else:
            # For other files, use UUID to avoid collisions
            new_name = f"{uuid.uuid4().hex}{ext}"
            target_path = os.path.join(upload_dir, new_name)
        
        with open(target_path, "wb") as f:
            f.write(content)
        public_url = f"/uploads/{new_name}"
        logger.info(f"Uploaded file saved to {target_path} -> {public_url} (type: {file_type})")
        return JSONResponse({"url": public_url, "filename": filename})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке файла",
        )

