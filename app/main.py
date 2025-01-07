from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import logging
import os
from pathlib import Path
from .utils import AIDataProcessor
from .database import log_operation, init_db
from .config import OPENAI_API_KEY, BASE_DIR, UPLOAD_DIR
from .test_routes import router as test_router

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files with absolute paths
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Create upload directory
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize AI processor with API key
try:
    AI_PROCESSOR = AIDataProcessor(OPENAI_API_KEY)
    logger.info("AI Processor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AI Processor: {str(e)}")
    raise

app.include_router(test_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

@app.get("/")
async def home(request: Request):
    logger.debug("Handling home page request")
    try:
        response = templates.TemplateResponse(
            "index.html", 
            {"request": request}
        )
        logger.debug("Home page template rendered successfully")
        return response
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy"}

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    instructions: str = Form(default="")
):
    logger.info(f"Received file upload request: {file.filename}")
    
    try:
        # Read the file
        logger.debug("Reading file...")
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file.file)
        else:
            logger.warning(f"Unsupported file format: {file.filename}")
            return JSONResponse(
                status_code=400,
                content={"message": "Unsupported file format"}
            )
        
        logger.info(f"File read successfully. Shape: {df.shape}")
        
        try:
            # Process the dataframe (will automatically fall back to basic processing if AI fails)
            processed_df, logs = AI_PROCESSOR.process_dataframe(df, instructions)
            logger.info("Processing completed")
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"message": f"Processing error: {str(e)}"}
            )
        
        # Save processed file
        output_filename = f"processed_{file.filename}"
        output_path = UPLOAD_DIR / output_filename
        
        if file.filename.endswith('.csv'):
            processed_df.to_csv(output_path, index=False)
        else:
            processed_df.to_excel(output_path, index=False)
        
        log_operation(
            file.filename, 
            "process",
            f"Instructions: {instructions}\nLogs: {'; '.join(logs)}"
        )
        
        return {
            "message": "File processed successfully",
            "rows": len(processed_df),
            "logs": logs,
            "download_url": f"/download/{output_filename}"
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": f"Error processing file: {str(e)}"}
        )

@app.get("/download/{filename}")
async def download_file(filename: str):
    logger.debug(f"Download requested for file: {filename}")
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        logger.info(f"Serving file: {filename}")
        return FileResponse(
            str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
    logger.warning(f"File not found: {filename}")
    return JSONResponse(
        status_code=404,
        content={"message": "File not found"}
    )

@app.post("/analyze-text/")
async def analyze_text(text: str):
    try:
        analysis = analyze_text_with_openai(text)
        log_operation("text_analysis", "analyze_text")
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"Error analyzing text: {str(e)}"}
        ) 