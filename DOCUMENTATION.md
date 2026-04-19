# ForgeGuard Pro v3.0
## Complete Project Documentation
### ThinkRoot × Vortex Hackathon 2026 | NIT Trichy

---

## Table of Contents
1. Project Overview
2. Problem Statement
3. Why This Matters
4. System Architecture
5. All 17 Analysis Categories (Detailed)
6. Tech Stack
7. File Structure
8. How to Run
9. API Reference
10. Scoring System
11. Limitations & Future Work

---

## 1. Project Overview

ForgeGuard Pro is an AI-powered document forgery detection system that analyses academic and government documents using 17 distinct analysis categories and 40+ individual checks. It supports both image (JPG/PNG) and PDF inputs, performs multi-language OCR (English + Tamil), and generates human-readable explainability reports using Google Gemini AI.

**Key Differentiators:**
- 17 analysis categories vs typical 2-3 in existing tools
- Cross-modal consistency checking (text vs image vs QR vs signature)
- Fuzzy entity matching — catches subtle name/ID changes
- Tamil + English OCR support (critical for South Indian documents)
- Region-wise anomaly scoring (not just global)
- Document type classifier (marksheet, ID, certificate, degree, etc.)
- Async pipeline via FastAPI for fast response

---

## 2. Problem Statement

Forgery and fake document submission are major issues in:
- College admissions (fake marksheets, fake certificates)
- Scholarship applications (inflated CGPA, fake institution names)
- Government verification (Aadhaar, PAN, employment records)
- Job applications (fake degrees, experience letters)

Existing solutions are either too expensive (commercial APIs), language-limited (no Tamil/regional support), or black-box (no explainability). ForgeGuard Pro fills this gap.

---

## 3. Why This Matters

- India processes millions of academic documents annually
- Manual verification is slow, error-prone, and doesn't scale
- Regional language documents (Tamil) are underserved by existing tools
- Forgery detection must explain *why* a document is flagged — not just give a verdict
- Institutions need a free, open, privacy-preserving local solution

---

## 4. System Architecture

```
Input (PDF or Image)
       │
       ▼
┌──────────────────────────────────────────────┐
│          CAT 1: Input Understanding           │
│  File type, DPI, resolution, quality score    │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   Image path            PDF path
        │                     │
        ▼                     ▼
┌──────────────┐    ┌─────────────────────┐
│  CAT 5       │    │  CAT 7: PDF         │
│  Image       │    │  Forensics          │
│  Forensics   │    │  (hidden text,      │
│  (ELA,       │    │  layers, objects)   │
│  copy-move,  │    ├─────────────────────┤
│  splicing,   │    │  CAT 8: Metadata    │
│  noise, etc) │    │  Forensics          │
└──────────────┘    └─────────────────────┘
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 2: Text         │
        │  Intelligence        │
        │  (OCR + native PDF   │
        │   extraction)        │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 3: Semantic     │
        │  Validation          │
        │  (dates, CGPA,       │
        │   cross-fields)      │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 4: Entity       │
        │  Intelligence        │
        │  (fuzzy name/ID      │
        │   matching)          │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 6: Layout       │
        │  CAT 9: Signature    │
        │  CAT 10: QR/Barcode  │
        │  CAT 11: Language    │
        │  CAT 12: Duplication │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 13: Cross-Modal │
        │  Consistency         │
        │  (text↔image,        │
        │   text↔QR,           │
        │   text↔signature)    │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 14: Scoring     │
        │  (weighted, dynamic) │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 15: Explaina-   │
        │  bility (heatmap,    │
        │  section breakdown)  │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 16: Robustness  │
        │  (safe_run wrappers) │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  CAT 17: Wow Factor  │
        │  (doc classifier,    │
        │   logo detection)    │
        └──────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │  Gemini AI Report    │
        │  Generation          │
        └──────────┬───────────┘
                   │
                   ▼
         JSON Response to Frontend
         (verdict, score, heatmap,
          section analysis, report)
```

---

## 5. All 17 Analysis Categories (Detailed)

---

### Category 1: Input Understanding Layer
**File:** `analysis/a01_input.py`

This layer runs BEFORE any forgery analysis. It characterises the input document so downstream modules can calibrate their confidence accordingly.

**Checks:**
- **File type detection:** Distinguishes between digital PDF, scanned PDF, photo, and screenshot
- **Page count:** Multi-page documents get more comprehensive analysis
- **Resolution/DPI check:** Low DPI (<100) reduces OCR accuracy and ELA reliability
- **Blurriness score:** Uses Laplacian variance — a blurry image makes visual forensics less accurate
- **File size sanity:** Unusually small PDFs may indicate stripped/fake documents
- **Quality score (0-100):** Composite score that adjusts all downstream check weights

**Why it matters:** A 72-DPI blurry photo will produce unreliable ELA results. This layer flags it so the final verdict is appropriately calibrated.

---

### Category 2: Text Intelligence
**File:** `analysis/a02_text.py`

9 checks covering all aspects of text extraction and consistency.

**Checks:**

1. **OCR Extraction (multi-language):**
   Uses EasyOCR with English + Tamil language models. Returns word-level confidence scores. Low confidence (<55%) on critical regions flags potential tampering.

2. **Native PDF Text Extraction:**
   PyMuPDF extracts text directly from PDF text layer — faster and more accurate than OCR for digital PDFs.

3. **Text Layer vs OCR Mismatch (CRITICAL):**
   Compares words from native PDF text layer vs OCR result. A mismatch (e.g., PDF says "85%" but image shows "45%") is a strong forgery indicator. Word-level Jaccard similarity is computed.

4. **OCR Confidence Scoring:**
   Per-character confidence from EasyOCR is averaged. Documents with regions of very low OCR confidence (possible overwriting or erasure) are flagged.

5. **Text Completeness Score:**
   Checks if expected fields (name, date, number) are present. Missing fields on official documents = suspicious.

6. **Character-Level Anomaly Detection:**
   Analyses bounding boxes of detected characters using OpenCV. Measures height variance and gap outliers — substituted characters often have slightly different heights or spacing.

7. **Font-Style Inconsistency (PDF):**
   PyMuPDF enumerates all font families used. Normal documents use 1-2 fonts. More than 3 font families indicates text was added/modified separately.

8. **Language Consistency:**
   Detects Tamil Unicode range (U+0B80–U+0BFF) vs English characters. Flags unexpected foreign scripts (Arabic, Cyrillic) in Indian academic documents.

9. **Mixed-Language Anomaly:**
   Checks if Tamil character sequences are linguistically valid. Invalid Tamil Unicode combinations (common when someone copies random Unicode) are flagged.

---

### Category 3: Semantic Content Validation
**File:** `analysis/a03_semantic.py`

Goes beyond simple regex — applies logical rules to document content.

**Checks:**

1. **Date Validation (DOB < issue < expiry):**
   Uses `python-dateutil` to parse multiple date formats (DD/MM/YYYY, YYYY-MM-DD, "15 Jan 2020"). Checks DOB is before issue date, and no dates are in the future.

2. **Age vs Document Type:**
   Detects document type (degree, ID, marksheet) then validates age. A 10-year-old cannot have a degree. A 200-year-old cannot have a valid Aadhaar.

3. **Marks/CGPA Range Validation:**
   - Percentage cannot exceed 100
   - CGPA cannot exceed 10 (on 10-point scale)
   - Marks cannot exceed total (e.g., 110/100 is impossible)

4. **ID Format Validation:**
   - Aadhaar: must be exactly 12 digits
   - Roll numbers: 5-15 alphanumeric characters
   - PAN card: must match AAAAA9999A pattern

5. **Institution Name Validity:**
   Dictionary of 30+ known Indian institutions. If no recognized institution is found in document text, it's flagged.

6. **Cross-Field Validation (CRITICAL):**
   Detects contradictions between fields:
   - Engineering degree + school-level terminology = impossible
   - Bonafide certificate without year of study = suspicious
   - Marksheet with no marks/score pattern = suspicious

---

### Category 4: Entity Intelligence
**File:** `analysis/a04_entity.py`

Smart entity checking with fuzzy matching — catches subtle changes that exact string matching misses.

**Checks:**

1. **Name Consistency:**
   Extracts all person name candidates (2-4 capitalized word sequences). Uses fuzzy string similarity (fuzzywuzzy) to detect variant spellings. A similarity of 75-99% between two names is suspicious (too similar to be coincidental, too different to be the same person).

2. **Institution Consistency:**
   Extracts institution names from document and cross-checks against each other. If the same institution is referred to as "Anna University" and "A University" on the same document, it flags inconsistency.

3. **ID Consistency:**
   Extracts all ID/roll number sequences. Checks they are consistent throughout (the same number must appear the same way every time).

4. **Entity Frequency Anomaly:**
   Counts frequency of numeric values. If a number like "85" appears 8+ times on a marksheet, it may indicate all marks were changed to the same value.

---

### Category 5: Image Forensics
**File:** `analysis/a05_a06_image_layout.py`

10 computer vision checks running on the image (or rendered PDF page).

**Checks:**

1. **ELA (Error Level Analysis):**
   Saves image at known JPEG quality (90%), then computes pixel-level difference between original and re-saved. Edited regions compress differently = brighter spots in ELA visualization. Score = mean brightness of ELA image.

2. **Copy-Move Detection (ORB + RANSAC):**
   Uses ORB (Oriented FAST and Rotated BRIEF) keypoint detector to find 5000 feature points. Matches features against each other — if the same feature appears in two different locations, a region was copy-pasted. RANSAC-style filtering removes self-matches.

3. **Splicing Detection:**
   Divides image into 4 quadrants. Computes Laplacian variance (sharpness) per quadrant. High variance between quadrants indicates spliced content from different sources.

4. **Noise Inconsistency:**
   Divides image into 50×50 blocks. Computes noise level (difference between raw block and Gaussian-blurred version) per block. Variance across blocks = edited regions have different noise characteristics.

5. **Blur/Sharpness Inconsistency:**
   Computes Laplacian variance (sharpness) per 60×60 block. Finds outlier blocks (more than 2 standard deviations from mean). A pasted region is often blurrier or sharper than the surrounding document.

6. **Edge Boundary Detection:**
   Uses Canny edge detection then Hough Line Transform to find long straight lines. Cut-paste boundaries often create unnatural straight edges invisible to the naked eye.

7. **Color Profile Mismatch:**
   Computes mean pixel intensity in each quadrant. High variance between quadrant means suggests different colour sources (printed+photographed vs digitally inserted).

8. **Compression Inconsistency:**
   Analyses JPEG block boundaries (every 8 pixels). In an original image, these boundaries have uniform compression artifacts. In an edited image, some regions show different compression levels.

9. **Shadow/Lighting Inconsistency:**
   Converts to LAB colour space and analyses luminance gradient angles per quadrant. Real documents have consistent lighting from one direction. Pasted content often has lighting from a different angle.

10. **Region-Wise Anomaly Scoring:**
    Divides image into 80×80 blocks and scores each block individually. Returns count of anomalous blocks vs total — this gives a localised forgery map, not just a global score.

---

### Category 6: Layout Intelligence
**File:** `analysis/a05_a06_image_layout.py`

7 checks on document structure and layout.

**Checks:**

1. **Margin Consistency:** Left and right margins should be uniform across pages.
2. **Line Alignment:** Words on the same line should share a common baseline (bottom of text).
3. **Text Block Spacing:** Gap between words should be consistent — outliers suggest inserted/deleted text.
4. **Table/Grid Validation:** Uses morphological operations to find horizontal+vertical lines forming tables. Irregular cell widths flag tampered tables.
5. **Header/Footer Pattern:** Headers should be consistent across all pages. Variation flags possible page substitution.
6. **Stamp/Seal Alignment:** Stamps/seals are detected using HSV color masking (blue/red/purple). They should be in the bottom half of official documents.
7. **Template Similarity:** Checks for structured header (common in official templates) using frequency analysis.

---

### Category 7: PDF Forensics
**File:** `analysis/a07_to_a12.py`

8 PDF-specific checks using PyMuPDF's low-level PDF object access.

**Checks:**

1. **Text Layer Presence:** Detects if PDF has a native text layer or is a scanned image.
2. **Hidden Text Detection:** Checks for white-on-white text (color = #FFFFFF) and invisible text (font size < 1pt). These are common techniques to hide forged content.
3. **Object Count Analysis:** Counts total PDF objects (xref table size). Unusually high counts indicate complex/suspicious structure.
4. **Layer Depth Analysis:** Checks how many text blocks are stacked at the same Y position. Multiple overlapping text blocks = content was added on top.
5. **Font Embedding Inconsistency:** Type3 fonts are often generated by editing tools and indicate non-standard document creation.
6. **Incremental Save Detection:** Counts %%EOF markers in raw PDF bytes. Multiple %%EOF = document was saved multiple times (incremental updates = edits).
7. **Suspicious Software Detection:** Checks Producer and Creator metadata fields for image editing software (Photoshop, GIMP, etc.).
8. **Text-Image Overlay Mismatch:** Checks if image bounding boxes overlap with text blocks — a common technique to cover original text with a white rectangle and type new text on top.

---

### Category 8: Metadata Forensics
**File:** `analysis/a07_to_a12.py`

5 checks on PDF metadata fields.

**Checks:**

1. **Creation vs Modification Date:** Modification year significantly later than creation year = document was edited after issue.
2. **Software Origin Detection:** Checks Producer/Creator for image editing software names.
3. **Missing Metadata Flag:** Official documents should have Author, Creation date, and Producer. Missing fields suggest scrubbed metadata.
4. **Timezone Mismatch:** Creation timezone vs modification timezone. A document created in IST (+05'30') but modified in UTC (Z) indicates it was edited on a different system/country.
5. **Author Check:** Missing author field on official document = suspicious.

---

### Category 9: Signature & Stamp Intelligence
**File:** `analysis/a07_to_a12.py`

7 checks on signature and stamp authenticity.

**Checks:**

1. **Signature Presence:** Checks bottom 25% of document for dark pixels (ink). No content in signature region = suspicious.
2. **Blank Signature Detection:** Mean pixel value >245 in signature region = almost blank = forged blank signature field.
3. **Signature Region Anomaly:** High Laplacian variance (sharpness) in signature region suggests pasted digital signature.
4. **Stamp Duplication:** ORB features in stamp region — if same features appear far apart, the stamp was copy-pasted.
5. **Stamp Position Validation:** Stamps in the top half of the document are in unusual positions for official Indian documents.
6. **Digital Signature (PDF):** PyMuPDF checks for cryptographic signature widgets. Missing digital signature on official PDFs is flagged.
7. **Signature Sharpness Inconsistency:** A photographed document should have some blur in the signature. Perfectly sharp signatures suggest digital insertion.

---

### Category 10: QR/Barcode Intelligence
**File:** `analysis/a07_to_a12.py`

**Checks:**
- QR code detection using OpenCV QRCodeDetector
- Decodes QR content
- Validates URL against trusted domain list (nitt.edu, gov.in, uidai.gov.in, etc.)
- Cross-checks QR numbers with document numbers — mismatch = forged QR
- Broken/missing QR detection (mild penalty — not all documents have QR)

---

### Category 11: Language & OCR Quality
**File:** `analysis/a07_to_a12.py`

**Checks:**
- Language detection (Tamil Unicode range U+0B80-U+0BFF vs English A-Z)
- Multi-language support validation
- OCR confidence scoring (below 55% = suspicious region)
- Invalid Tamil Unicode sequence detection (forged Tamil text often uses random Unicode)
- Unexpected script detection (Arabic, Cyrillic in Indian documents)

---

### Category 12: Duplication & Cloning Detection
**File:** `analysis/a07_to_a12.py`

**Checks:**
- **Region Duplication:** Divides image into 60×60 blocks, hashes each block, detects identical blocks that are far apart (same region used twice).
- **Logo Duplication:** Hough circle detection for circular logos/seals. More than 2 circular regions = excessive logos.
- **Text Block Repetition:** Counts numeric value frequencies in OCR text. A number appearing 4+ times = suspicious.

---

### Category 13: Cross-Modal Consistency (HIGH VALUE)
**File:** `analysis/a13_to_a17.py`

This is what makes ForgeGuard Pro an AI system, not just a collection of checks. It validates consistency *across* different modalities of the document.

**Checks:**

1. **Text vs Image Consistency:**
   Document orientation, image aspect ratio vs text content complexity. A landscape-format image with rich text is unusual for academic documents.

2. **Text vs Signature Consistency:**
   Checks if the document contains a clear name field. No name = signature has nothing to align to = suspicious.

3. **Text vs QR Consistency:**
   Extracts numeric sequences (4+ digits) from both document text and QR code content. If they share no common numbers, the QR may have been transplanted from another document.

4. **Text vs Layout Consistency:**
   If a document has very little text but many font families, something is wrong — possibly a template was filled with altered content.

---

### Category 14: Scoring System
**File:** `analysis/a13_to_a17.py`

**Weighted Scoring:**
- Each check has a pre-defined weight (e.g., ELA = 8%, hidden text = 4%)
- Weights are different for image vs PDF inputs (dynamic weighting)
- Confidence-adjusted: low quality input → score weighted down by quality factor

**Formula:**
```
raw_score = Σ (check_score × weight) / Σ (used_weights)
adjusted  = raw_score × (0.7 + 0.3 × quality_factor)
```

**Verdict thresholds:**
- 0–25:   GENUINE ✅
- 26–55:  SUSPICIOUS ⚠️
- 56–100: FORGED ❌

---

### Category 15: Explainability Layer
**File:** `analysis/a13_to_a17.py`

**Components:**

1. **Top Risk Factors:** Top 7 checks weighted by (score × weight) — shows which checks contributed most to the verdict.

2. **Section-wise Breakdown:** All 40+ checks organized into 12 sections with average risk per section (LOW/MEDIUM/HIGH).

3. **Anomaly List:** Collects all human-readable anomaly strings from every check (deduplicated).

4. **ELA Heatmap Overlay:** Original image blended with ELA heatmap at 55%/45% opacity — creates annotated view showing exactly where tampering was detected.

5. **Gemini AI Report:** Sends all detection data to Gemini 1.5 Flash. Generates structured forensics report with: Executive Summary, Key Findings, Suspicious Regions, Risk Assessment, Recommended Action.

---

### Category 16: Performance & Robustness
**File:** `analysis/a13_to_a17.py`, `pipelines/master.py`

**Features:**
- `safe_run()` wrapper: Every module call is wrapped in try-catch with graceful fallback. If ELA fails, the pipeline continues with the remaining checks.
- **Async pipeline:** FastAPI uses `ThreadPoolExecutor` with `run_in_executor` — the analysis runs in a background thread, keeping the server responsive.
- **Graceful OCR fallback:** If native PDF text extraction fails, falls back to OCR on rendered page.
- **Temp file cleanup:** All temporary images and renders are cleaned up after analysis.
- **Module isolation:** Each category is a separate module — any single module failure doesn't affect others.

---

### Category 17: Wow Factor
**File:** `analysis/a13_to_a17.py`

Three unique features that set ForgeGuard Pro apart:

1. **Document Type Classifier:**
   Keyword-based classification into 9 document types: Aadhaar, PAN, marksheet, certificate, degree, bonafide, transfer certificate, payslip, ID card. Confidence score provided.

2. **Institution Logo Detection:**
   Uses Hough Circle Transform on the top 25% of the document. Detects circular emblems/logos (common in official Indian institutional documents). Missing logo = possible fake.

3. **Fake Template Detection:**
   - Checks text density (too few words for an official document)
   - Checks for background watermark patterns via FFT frequency analysis
   - Official documents have periodic background patterns (watermarks, fine print)

---

## 6. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | HTML + CSS + Vanilla JS | Upload UI, results display |
| Backend | FastAPI (Python) | Async REST API |
| Image Analysis | OpenCV 4.x | ELA, copy-move, edge detection |
| Image Processing | Pillow (PIL) | ELA computation, image manipulation |
| OCR | EasyOCR | Multi-language text extraction (Tamil+English) |
| PDF Analysis | PyMuPDF (fitz) | Text layer, metadata, object inspection |
| PDF Layout | pdfplumber | Word positions, spacing analysis |
| Date Parsing | python-dateutil | Flexible date format parsing |
| Fuzzy Matching | fuzzywuzzy | Name/entity similarity matching |
| AI Report | Google Gemini 1.5 Flash | Human-readable forensics report |
| Vector DB | FAISS + HuggingFace | (optional RAG layer) |
| Async | Python asyncio + ThreadPoolExecutor | Non-blocking pipeline |

---

## 7. File Structure

```
forgeguard_final/
├── backend/
│   ├── main.py                   ← FastAPI entry point
│   ├── requirements.txt          ← All dependencies
│   ├── analysis/
│   │   ├── a01_input.py          ← Cat 1: Input Understanding
│   │   ├── a02_text.py           ← Cat 2: Text Intelligence
│   │   ├── a03_semantic.py       ← Cat 3: Semantic Validation
│   │   ├── a04_entity.py         ← Cat 4: Entity Intelligence
│   │   ├── a05_a06_image_layout.py ← Cat 5+6: Image+Layout
│   │   ├── a07_to_a12.py         ← Cat 7-12: PDF+Meta+Sig+QR+Lang+Dup
│   │   ├── a13_to_a17.py         ← Cat 13-17: Cross+Score+Explain+Perf+Wow
│   │   └── gemini_report.py      ← Gemini AI integration
│   └── pipelines/
│       └── master.py             ← Orchestrates all 17 categories
│
└── frontend/
    ├── index.html                ← Main page
    ├── style.css                 ← Dark theme styling
    └── app.js                   ← Upload, API call, render results
```

---

## 8. How to Run

### Prerequisites
- Python 3.8+
- Windows / Mac / Linux

### Setup

```bash
# 1. Extract zip and navigate to backend
cd forgeguard_final/backend

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Mac/Linux

# 3. Install packages
pip install -r requirements.txt

# 4. Add Gemini API key
# Open analysis/gemini_report.py → line 5
# Replace "your_gemini_api_key_here" with your actual key
# Get key free from: aistudio.google.com

# 5. Start server
uvicorn main:app --reload

# 6. Open frontend
# Double-click frontend/index.html in browser
```

---

## 9. API Reference

### POST /analyse

Upload a document for analysis.

**Request:** `multipart/form-data` with `file` field (PDF/JPG/PNG)

**Response:**
```json
{
  "filename": "marksheet.pdf",
  "file_type": "pdf",
  "doc_type": "marksheet",
  "verdict": "FORGED",
  "emoji": "❌",
  "risk": "HIGH",
  "final_score": 78.5,
  "quality_score": 95,
  "scores": {
    "ela": 72.3,
    "hidden_text": 60.0,
    "date_mismatch": 40.0,
    ...
  },
  "heatmap": "/heatmaps/ela_file.jpg",
  "ocr_text": "Raghul N | DOB: 12/02/2006 ...",
  "anomalies": ["Modified 4yr after creation ⚠️", ...],
  "explainability": {
    "top_risk_factors": [...],
    "section_analysis": {...}
  },
  "gemini_report": "EXECUTIVE SUMMARY: ...",
  "metadata": {"created": "D:20200615", ...}
}
```

---

## 10. Scoring System

All check scores are 0-100 where 100 = most suspicious.

Checks are grouped and weighted as follows (for PDF):

| Category | Weight Range | Key Checks |
|---|---|---|
| Image Forensics | 1-6% each | ELA (5%), Copy-move (3%) |
| Text Intelligence | 1-5% each | Layer mismatch (5%), Font style (4%) |
| Semantic Validation | 2-3% each | Date logic, Numerical ranges |
| PDF Forensics | 2-4% each | Hidden text (4%), Incremental save (3%) |
| Metadata | 2-4% each | Date mismatch (4%), Software (3%) |
| Signature/Stamp | 1-3% each | Digital signature (3%) |
| Cross-Modal | 1-2% each | Text↔QR (2%) |

Final score is quality-adjusted:
- 100% quality input: score = raw weighted score
- 50% quality input: score = raw × 0.85 (slightly discounted)

---

## 11. Limitations & Future Work

### Current Limitations
- No CNN/ML model (requires training data we don't have in 36hrs)
- QR validation limited to domain whitelist (no live UIDAI API)
- Signature-name alignment is not implemented at character level
- Expert-level forgery (matching compression, font, noise exactly) may evade detection

### Future Improvements
- Train CNN on domain-specific forged document dataset
- Integrate with DigiLocker API for real-time verification
- Add handwriting analysis for signature comparison
- Database cross-verification against institution registries
- GPU-accelerated ELA for real-time processing
- Mobile app with camera-based document capture

---

*ForgeGuard Pro v3.0 | Built for ThinkRoot × Vortex Hackathon 2026 | NIT Trichy*
*All 17 categories implemented | 40+ checks | Tamil + English | Gemini AI powered*
