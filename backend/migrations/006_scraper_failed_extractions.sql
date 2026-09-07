-- SCR-1: Add failed_extractions counter to scraper_runs
-- Tracks per-run count of PDFs that failed text extraction
-- (non-PDF content, corrupt files, empty after OCR, etc.)

ALTER TABLE scraper_runs
ADD COLUMN IF NOT EXISTS failed_extractions INTEGER NOT NULL DEFAULT 0;
