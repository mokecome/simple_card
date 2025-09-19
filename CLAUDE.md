# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Business Card OCR Management System (名片OCR管理系統) that provides intelligent OCR recognition, data management, and batch processing capabilities for business cards.

## Development Commands

### Starting the Application

```bash
# Full system startup (both frontend and backend)
./start.sh

# Or manually:
# Backend (FastAPI)
python main.py  # Runs on port 8006

# Frontend (React)
cd frontend && npm start  # Runs on port 1002
```

### Frontend Development

```bash
cd frontend
npm install        # Install dependencies
npm start          # Start development server (port 1002)
npm run build      # Build for production
npm test           # Run tests
```

### Backend Development

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Run backend server
python main.py     # FastAPI server on port 8006

# Database initialization
python init_db.py  # Initialize SQLite database
```

## Architecture Overview

### System Components

The system follows a 3-tier architecture:

1. **Frontend (React + Antd Mobile)**
   - Mobile-first responsive design
   - Camera integration for card scanning
   - Batch upload capabilities
   - Real-time OCR result editing

2. **Backend (FastAPI)**
   - RESTful API endpoints under `/api/v1`
   - OCR service integration with OpenAI Vision API
   - Card enhancement service using OpenCV
   - Batch processing with memory management

3. **Database (SQLAlchemy + SQLite)**
   - Business card storage with 25 standardized fields
   - Support for bilingual data (Chinese/English)
   - Health status tracking for data quality

### Key Services and Modules

**Backend Services (`backend/services/`):**
- `ocr_service.py`: Main OCR service integrating OpenAI Vision API, handles image-to-text conversion and field parsing
- `card_enhancement_service.py`: Image enhancement using OpenCV (3x upscaling, denoising, contrast adjustment)
- `card_detector.py`: Automatic card boundary detection and cropping
- `card_service.py`: Business logic for card CRUD operations
- `text_import_service.py`: Excel/CSV batch import with intelligent field mapping

**API Endpoints (`backend/api/v1/`):**
- `/api/v1/cards`: Card management endpoints (CRUD, search, statistics)
- `/api/v1/ocr`: OCR processing endpoints (scan, batch process)

**Frontend Pages (`frontend/src/pages/`):**
- `ScanUploadPage.js`: Camera/upload interface with real-time preview
- `CardManagerPage.js`: Card list with search, filter, and statistics
- `CardDetailPage.js`: Individual card view and editing
- `AddCardPage.js`: Manual card addition interface

### Data Flow

1. **Image Capture** → Camera/Upload → Frontend validation
2. **Image Processing** → Backend enhancement service → OpenCV processing
3. **OCR Recognition** → OpenAI Vision API → Text extraction
4. **Field Parsing** → LLM-based intelligent parsing → 25 standardized fields
5. **Data Storage** → SQLAlchemy ORM → SQLite database
6. **Result Display** → React components → User editing/confirmation

## Field Structure

The system processes business cards into 25 standardized fields:

```python
# Basic Information (8 fields)
name_zh, name_en, company_name_zh, company_name_en,
position_zh, position_en, position1_zh, position1_en

# Department/Organization (6 fields)
department1_zh, department1_en, department2_zh, department2_en,
department3_zh, department3_en

# Contact Information (5 fields)
mobile_phone, company_phone1, company_phone2, email, line_id

# Address Information (4 fields)
company_address1_zh, company_address1_en,
company_address2_zh, company_address2_en

# Notes (2 fields)
note1, note2
```

## OCR Processing Pipeline

1. **Image Enhancement**:
   - OpenCV-based card detection and cropping
   - 3x resolution upscaling
   - Contrast and sharpness optimization

2. **OCR Recognition**:
   - OpenAI Vision API for text extraction
   - Support for Chinese/English mixed content
   - Retry mechanism with timeout handling

3. **Field Parsing**:
   - LLM-based intelligent field classification
   - Bilingual field mapping
   - Empty field handling (returns empty string)

## Memory and Performance Management

- **Batch Processing**: Memory monitoring with 85% threshold
- **Dynamic Batch Size**: Adjusts based on available memory
- **Garbage Collection**: Automatic cleanup after processing
- **File Size Limits**: 10MB per image, 50MB for batch imports

## Configuration

Key environment variables in `.env`:
- `PORT=8006`: Backend server port
- `REACT_APP_PORT=1002`: Frontend server port
- `DATABASE_URL=sqlite:///./cards.db`: Database connection
- `OCR_API_URL`: OpenAI API endpoint
- `OCR_BATCH_API_URL`: Batch processing endpoint
- `MAX_FILE_SIZE=10485760`: 10MB file size limit

## Testing and Quality

- Frontend tests: `cd frontend && npm test`
- API health check: `GET /health`
- Configuration check: `GET /config` (development only)
- Card health status: Validates required fields (name, company, position/department, contact)

## Common Development Tasks

### Adding New Card Fields
1. Update `CARD_FIELDS` in `backend/services/ocr_service.py`
2. Add column to model in `backend/models/card.py`
3. Update schema in `backend/schemas/card.py`
4. Run database migration
5. Update frontend form in `frontend/src/components/common/CardFormSection.js`

### Modifying OCR Logic
- Field parsing: Edit prompt in `ocr_service.py::parse_ocr_to_fields()`
- Image enhancement: Modify `card_enhancement_service.py`
- Batch processing: Adjust memory thresholds in `ocr_service.py::process_batch_images()`

### Debugging OCR Issues
- Check logs in `backend/nohup_backend.log`
- Use simulation mode: `is_simulation=true` in OCR service
- Verify OpenAI API connection and credentials
- Test with sample images in `cards/` directory