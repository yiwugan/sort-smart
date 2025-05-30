import logging
import json
import os
from pathlib import Path
from typing import Optional
from tempfile import NamedTemporaryFile

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from llm_service import query_recycle_method_from_image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# Configuration
class Config:
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/temp-data"))
    MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 80000))
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8090))


# Ensure upload directory exists
Config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="EcoSort API",
    description="API for recycling instructions based on image analysis",
    version="1.0.0"
)

# Configure CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Pydantic model for metadata
class ImageMetadata(BaseModel):
    city: Optional[str] = None
    region: str


@app.get("/", summary="Redirect to index page")
async def redirect_to_index():
    """Redirects to the static index2.html page."""
    return RedirectResponse(url="/static/index.html")


@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Returns the health status of the API."""
    return {"status": "healthy"}


@app.post("/upload-image", summary="Upload image and metadata for recycling instructions")
async def upload_image(
        image: UploadFile = File(...),
        metadata: str = Form(...)
):
    """
    Upload an image and metadata to get recycling instructions.

    Args:
        image: Uploaded image file
        metadata: JSON string containing city (optional) and region

    Returns:
        Dictionary containing filename, content type, metadata, and recycling instructions

    Raises:
        HTTPException: If image size exceeds limit or location data is invalid
    """
    try:
        # Parse JSON metadata
        metadata_dict = json.loads(metadata)
        logger.info(f"Received metadata: {metadata_dict}")

        # Validate metadata
        metadata_model = ImageMetadata(**metadata_dict)

        # Read and validate image
        image_content = await image.read()
        logger.info(f"Received image: {image.filename}, size: {len(image_content)} bytes")

        if len(image_content) > Config.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image too large, must be smaller than {Config.MAX_IMAGE_SIZE} bytes"
            )

        # Determine city or region
        city_or_region = metadata_model.city or metadata_model.region
        city_or_region = city_or_region.lower().replace(" region", "")

        # Check if summary file exists
        file_path = Path(f"./data/{city_or_region}-summary.txt")
        if not file_path.exists():
            logger.error(f"Summary file not found: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instruction not found for specified city or region"
            )

        # Save image temporarily for processing
        with NamedTemporaryFile(delete=False, dir=Config.UPLOAD_DIR, suffix=".jpg") as tmp_file:
            tmp_file.write(image_content)
            tmp_file_path = Path(tmp_file.name)

        try:
            # Query recycling instructions
            result = query_recycle_method_from_image(image_content, city_or_region)
            logger.info(f"Recycling instructions retrieved: {result}")

            return {
                "filename": image.filename,
                "content_type": image.content_type,
                "metadata": metadata_dict,
                "response": result
            }
        finally:
            # Clean up temporary file
            try:
                tmp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_file_path}: {e}")

    except json.JSONDecodeError:
        logger.error("Invalid JSON metadata")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON metadata"
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    uvicorn.run(
        "main_app:app",
        host=Config.HOST,
        port=Config.PORT,
        log_level="info",
        reload=True  # Enable auto-reload for development
    )