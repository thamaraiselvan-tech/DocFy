"""
CATEGORY 2: TEXT INTELLIGENCE (UPGRADED)
9 checks:
1. OCR extraction (multi-language: English + Tamil)
2. Native PDF text extraction
3. Text layer vs OCR mismatch (CRITICAL)
4. OCR confidence scoring
5. Text completeness score
6. Character-level anomaly detection
7. Font-style inconsistency
8. Language consistency check
9. Mixed-language anomaly detection
"""
import cv2
import numpy as np
import re
import fitz
import pdfplumber
import easyocr
import os

_reader = None

def get_reader():
    global _reader
    if _reader is None:
        print("[OCR] Loading EasyOCR (en+ta)...")
        _reader = easyocr.Reader(["en", "ta"], gpu=False)
    return _reader

# ─── 1. OCR Extraction ────────────────────────────────────
def ocr_extract(image_path: str) -> dict:
    """Multi-language OCR extraction with confidence scoring."""
    try:
        r = get_reader()
        raw = r.readtext(image_path, detail=1, paragraph=False)
        texts, confs, boxes = [], [], []
        for (box, text, conf) in raw:
            texts.append(text)
            confs.append(float(conf))
            boxes.append([[int(p[0]), int(p[1])] for p in box])
        avg_conf = float(np.mean(confs)) if confs else 0.0
        full_text = " ".join(texts)
        # Low confidence = tampered or garbled text
        conf_score = max(0, (0.55 - avg_conf) * 120) if avg_conf < 0.55 else 0
        return {
            "text": full_text,
            "word_count": len(texts),
            "avg_confidence": round(avg_conf, 3),
            "score": round(conf_score, 2),
            "boxes": boxes,
            "detail": f"OCR: {len(texts)} words, confidence {avg_conf:.1%}"
                      + (" ⚠️ Low confidence" if avg_conf < 0.55 else " ✅")
        }
    except Exception as e:
        return {"text":"","word_count":0,"avg_confidence":0,"score":0,"boxes":[],"detail":str(e)}

# ─── 2. Native PDF Text Extraction ───────────────────────
def pdf_native_text(pdf_path: str) -> dict:
    """Extract text directly from PDF text layer."""
    try:
        doc = fitz.open(pdf_path)
        pages_text = [page.get_text().strip() for page in doc]
        doc.close()
        full = " ".join(pages_text)
        return {"native_text": full, "has_text_layer": bool(full.strip()),
                "detail": f"Native text: {len(full)} chars"}
    except Exception as e:
        return {"native_text":"","has_text_layer":False,"detail":str(e)}

# ─── 3. Text Layer vs OCR Mismatch ───────────────────────
def check_text_layer_mismatch(native_text: str, ocr_text: str) -> dict:
    """CRITICAL: Compare PDF text layer vs OCR result."""
    if not native_text or not ocr_text:
        return {"score":10,"match_ratio":0,"detail":"Cannot compare — missing text"}
    def tokenize(t):
        return set(re.sub(r'[^a-zA-Z0-9\u0B80-\u0BFF]', ' ', t).lower().split())
    n_words = tokenize(native_text)
    o_words = tokenize(ocr_text)
    if not n_words or not o_words:
        return {"score":0,"match_ratio":1.0,"detail":"Insufficient words"}
    common = n_words & o_words
    total  = n_words | o_words
    ratio  = len(common) / len(total)
    score  = max(0, (1 - ratio) * 100)
    return {"score":round(score,2), "match_ratio":round(ratio,3),
            "detail": f"Layer match: {ratio:.1%} {'⚠️ MISMATCH — possible hidden text layer' if ratio<0.65 else '✅ Layers match'}"}

# ─── 4+5. OCR Confidence + Completeness ──────────────────
def check_text_completeness(text: str, expected_fields: list = None) -> dict:
    """Check if document text contains expected sections."""
    if not expected_fields:
        expected_fields = ["name", "date", "number"]
    missing = [f for f in expected_fields if f.lower() not in text.lower()]
    score = len(missing) / len(expected_fields) * 40
    return {"score":round(score,2), "missing_fields": missing,
            "detail": f"Missing fields: {missing} ⚠️" if missing else "✅ Key fields present"}

# ─── 6. Character-Level Anomaly Detection ────────────────
def check_char_anomalies(image_path: str) -> dict:
    """Detect character spacing, size, and alignment anomalies."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read"}
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        chars = [cv2.boundingRect(c) for c in contours if 4<cv2.boundingRect(c)[3]<90 and 2<cv2.boundingRect(c)[2]<70]
        if len(chars) < 8:
            return {"score":0,"detail":"Insufficient characters detected"}
        chars.sort(key=lambda b: b[0])
        heights = np.array([b[3] for b in chars])
        h_var   = float(np.std(heights) / (np.mean(heights)+1e-5))
        gaps    = [chars[i][0]-(chars[i-1][0]+chars[i-1][2]) for i in range(1,len(chars)) if -5<chars[i][0]-(chars[i-1][0]+chars[i-1][2])<80]
        g_arr   = np.array(gaps) if gaps else np.array([0])
        outlier_r = float(np.sum(np.abs(g_arr-np.mean(g_arr))>2.5*np.std(g_arr)) / max(len(g_arr),1))
        score = min(100, h_var*120 + outlier_r*80)
        return {"score":round(score,2), "height_variance":round(h_var,3),
                "detail": f"Char height var: {h_var:.3f}, spacing outliers: {outlier_r:.1%}"
                          + (" ⚠️ Anomalies detected" if score>30 else " ✅ Normal")}
    except Exception as e:
        return {"score":0,"detail":str(e)}

# ─── 7. Font-Style Inconsistency ─────────────────────────
def check_font_style(pdf_path: str) -> dict:
    """Detect font family/size inconsistencies across PDF."""
    try:
        doc = fitz.open(pdf_path)
        fonts, sizes = set(), []
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines",[]):
                    for span in line.get("spans",[]):
                        if span.get("text","").strip():
                            fonts.add(span["font"])
                            sizes.append(round(span["size"],1))
        doc.close()
        fc = len(fonts)
        size_var = float(np.std(sizes)) if sizes else 0
        outlier_r = float(np.sum(np.abs(np.array(sizes)-np.mean(sizes))>2*np.std(sizes)) / max(len(sizes),1)) if sizes else 0
        score = (0 if fc<=2 else 20 if fc<=3 else 50 if fc<=5 else 80) + min(30, outlier_r*100)
        return {"score":round(score,2), "font_count":fc, "fonts":list(fonts)[:10],
                "size_variance":round(size_var,2),
                "detail": f"{fc} font families, size variance {size_var:.1f} {'⚠️' if fc>3 else '✅'}"}
    except Exception as e:
        return {"score":0,"font_count":0,"fonts":[],"detail":str(e)}

# ─── 8+9. Language Consistency + Mixed-language ───────────
def check_language_consistency(text: str) -> dict:
    """Detect language and mixed-script anomalies."""
    if not text:
        return {"score":20,"language":"unknown","detail":"No text to analyse"}
    tamil   = len(re.findall(r'[\u0B80-\u0BFF]', text))
    english = len(re.findall(r'[a-zA-Z]', text))
    arabic  = len(re.findall(r'[\u0600-\u06FF]', text))
    total   = max(tamil+english+arabic, 1)
    anomalies = []
    if arabic/total > 0.15:
        anomalies.append("Unexpected Arabic/foreign script ⚠️")
    if tamil > 0:
        bad = re.findall(r'[\u0B80-\u0B82][\u0B80-\u0B82]', text)
        if bad: anomalies.append(f"Invalid Tamil character sequences: {len(bad)} ⚠️")
    lang = ("Tamil+English" if tamil>0 and english>0
            else "Tamil" if tamil>0
            else "English" if english>0 else "Unknown")
    score = min(100, len(anomalies)*40)
    return {"score":score, "language":lang, "tamil_chars":tamil, "english_chars":english,
            "detail": f"Lang: {lang} | " + (" | ".join(anomalies) if anomalies else "✅ Consistent")}


def run_text_intelligence(image_path:str=None, pdf_path:str=None) -> dict:
    results = {}
    # OCR
    if image_path:
        r1 = ocr_extract(image_path)
        results["ocr_text"]       = r1["text"]
        results["ocr_confidence"] = r1["score"]
        results["ocr_boxes"]      = r1["boxes"]
        results["ocr_avg_conf"]   = r1["avg_confidence"]
        results["ocr_detail"]     = r1["detail"]
        r6 = check_char_anomalies(image_path)
        results["char_anomaly"]   = r6["score"]
        results["char_detail"]    = r6["detail"]
    # Native PDF
    native_text = ""
    if pdf_path:
        r2 = pdf_native_text(pdf_path)
        native_text = r2["native_text"]
        results["has_text_layer"] = r2["has_text_layer"]
        # Mismatch
        r3 = check_text_layer_mismatch(native_text, results.get("ocr_text",""))
        results["text_layer_mismatch"] = r3["score"]
        results["text_layer_detail"]   = r3["detail"]
        # Font style
        r7 = check_font_style(pdf_path)
        results["font_style"]        = r7["score"]
        results["font_count"]        = r7.get("font_count",0)
        results["fonts_found"]       = r7.get("fonts",[])
        results["font_style_detail"] = r7["detail"]
    # Full text for language check
    full_text = (results.get("ocr_text","") + " " + native_text).strip()
    r4 = check_text_completeness(full_text)
    results["text_completeness"]        = r4["score"]
    results["text_completeness_detail"] = r4["detail"]
    r8 = check_language_consistency(full_text)
    results["language_consistency"]     = r8["score"]
    results["detected_language"]        = r8.get("language","unknown")
    results["language_detail"]          = r8["detail"]
    results["full_text"] = full_text
    return results
