# 🔍 ForgeGuard Pro v3.0
### AI-Powered Document Forgery Detection System
**ThinkRoot × Vortex Hackathon 2026 | NIT Trichy**

---

## 🏆 What It Does

ForgeGuard Pro detects forged academic documents (marksheets, certificates, IDs, degrees) using **17 analysis categories** and **40+ individual checks**.

- ✅ Supports PDF and Image (JPG/PNG)
- ✅ Tamil + English OCR
- ✅ ELA heatmap visualization
- ✅ Gemini AI forensics report
- ✅ Cross-modal consistency validation
- ✅ Async FastAPI backend

---

## 📊 17 Analysis Categories

| # | Category | Key Checks |
|---|---|---|
| 1 | Input Understanding | DPI, quality, file type |
| 2 | Text Intelligence | OCR, layer mismatch, font |
| 3 | Semantic Validation | Date logic, CGPA, cross-field |
| 4 | Entity Intelligence | Fuzzy name/ID matching |
| 5 | Image Forensics | ELA, copy-move, splicing |
| 6 | Layout Intelligence | Margins, spacing, tables |
| 7 | PDF Forensics | Hidden text, layers, incremental saves |
| 8 | Metadata Forensics | Created/modified date, software |
| 9 | Signature & Stamp | Presence, duplication, anomaly |
| 10 | QR/Barcode | Detection, trust validation |
| 11 | Language & OCR | Tamil validation, confidence |
| 12 | Duplication | Region cloning, logo detection |
| 13 | Cross-Modal | Text↔Image↔QR↔Signature |
| 14 | Scoring System | Dynamic weighted scoring |
| 15 | Explainability | Heatmap, section breakdown |
| 16 | Robustness | Safe wrappers, async pipeline |
| 17 | Wow Factor | Doc classifier, logo detection |

---

## 🚀 Quick Start (Local)

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install packages
pip install -r requirements.txt

# 4. Set your Gemini API key
# Copy .env.example → .env
# Edit .env → add your key

# 5. Start server
uvicorn main:app --reload

# 6. Open frontend
# Open frontend/index.html in browser
```

---

## 🌐 Deployment

### Backend → Render.com
1. Push repo to GitHub
2. Create Web Service on render.com
3. Set Root Directory: `backend`
4. Build: `pip install -r requirements.txt`
5. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add env variable: `GEMINI_API_KEY`

### Frontend → Netlify
1. Connect GitHub repo on netlify.com
2. Set publish directory: `frontend`
3. Deploy

### After deploy — update frontend/app.js line 4:
```javascript
const API = "https://your-app-name.onrender.com";
```

---

## 🔑 Getting Gemini API Key (Free)
1. Go to **aistudio.google.com**
2. Sign in with Google
3. Click **Get API Key** → **Create API Key**
4. Copy key → paste in `.env` file

---

## 📁 Project Structure

```
forgeguard_pro/
├── .gitignore
├── .env.example
├── DOCUMENTATION.md
├── README.md
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── render.yaml
│   ├── Procfile
│   ├── analysis/
│   │   ├── a01_input.py
│   │   ├── a02_text.py
│   │   ├── a03_semantic.py
│   │   ├── a04_entity.py
│   │   ├── a05_a06_image_layout.py
│   │   ├── a07_to_a12.py
│   │   ├── a13_to_a17.py
│   │   └── gemini_report.py
│   └── pipelines/
│       └── master.py
│
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML + CSS + Vanilla JS |
| Backend | FastAPI (Python, Async) |
| Image Analysis | OpenCV + Pillow |
| OCR | EasyOCR (Tamil + English) |
| PDF Analysis | PyMuPDF + pdfplumber |
| Date Parsing | python-dateutil |
| Fuzzy Matching | fuzzywuzzy |
| AI Report | Google Gemini 1.5 Flash |
| Deployment | Render + Netlify |

---

## ⚠️ Notes

- Render free tier sleeps after 15 mins — first request takes ~30s to wake
- EasyOCR downloads language models on first run (~200MB)
- Gemini API free tier: 15 requests/min

---

*ForgeGuard Pro v3.0 | Built for ThinkRoot × Vortex 2026*
