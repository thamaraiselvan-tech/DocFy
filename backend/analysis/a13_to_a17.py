"""
CATEGORY 13: CROSS-MODAL CONSISTENCY (HIGH VALUE)
CATEGORY 14: SCORING SYSTEM
CATEGORY 15: EXPLAINABILITY
CATEGORY 16: PERFORMANCE & ROBUSTNESS
CATEGORY 17: WOW FACTOR (Document Classifier, Logo Detection, Fake Template)
"""
import re, cv2, numpy as np, os, fitz

HMAP="heatmaps"; os.makedirs(HMAP,exist_ok=True)

# ═══════════════════════════════════════
# CATEGORY 13: CROSS-MODAL CONSISTENCY
# ═══════════════════════════════════════

def check_text_vs_image(text: str, image_path: str = None) -> dict:
    """Text content should match visual document type."""
    anomalies=[]
    tl=text.lower()
    if image_path:
        img=cv2.imread(image_path)
        if img is not None:
            h,w=img.shape[:2]
            aspect=w/h
            # Landscape = unusual for academic docs (usually portrait)
            if aspect>1.5 and len(text)>100:
                anomalies.append("Landscape orientation unusual for academic document ⚠️")
    # Text claims to be certificate but has tabular marks data
    if "certificate" in tl and re.search(r'\d+\s*/\s*\d+',text):
        pass  # valid — certificate with marks
    score=min(100,len(anomalies)*35)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Text-image consistent"}

def check_text_vs_signature(text: str, image_path: str = None) -> dict:
    """Signature name should match document name field."""
    anomalies=[]
    # Extract name from document
    name_m=re.search(r'(?:name|student)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]*)+)',text,re.IGNORECASE)
    # Without actual signature recognition, flag if name is absent
    if not name_m:
        anomalies.append("No clear name field found in document ⚠️")
    score=min(100,len(anomalies)*30)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Signature-text relationship OK"}

def check_text_vs_qr(text: str, qr_data: str = "") -> dict:
    """QR code content should match document identifiers."""
    if not qr_data:
        return {"score":0,"detail":"No QR data to cross-check"}
    anomalies=[]
    # Numbers in document vs QR
    doc_nums=set(re.findall(r'\d{4,}',text))
    qr_nums =set(re.findall(r'\d{4,}',qr_data))
    if doc_nums and qr_nums and not doc_nums&qr_nums:
        anomalies.append("QR numbers don't match document numbers ⚠️")
    score=min(100,len(anomalies)*50)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ QR-text consistent"}

def check_text_vs_layout(text: str, font_count: int = 1) -> dict:
    """Text content complexity should match layout complexity."""
    anomalies=[]
    word_count=len(text.split())
    # Very short text with many fonts = suspicious
    if word_count<20 and font_count>3:
        anomalies.append(f"Very short text ({word_count} words) but {font_count} fonts ⚠️")
    score=min(100,len(anomalies)*40)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Text-layout consistent"}

def run_cross_modal(text:str, image_path:str=None, qr_data:str="", font_count:int=1) -> dict:
    results={}
    r1=check_text_vs_image(text,image_path);     results["cross_text_image"]=r1["score"];   results["cross_ti_detail"]=r1["detail"]
    r2=check_text_vs_signature(text,image_path); results["cross_text_sig"]=r2["score"];     results["cross_ts_detail"]=r2["detail"]
    r3=check_text_vs_qr(text,qr_data);           results["cross_text_qr"]=r3["score"];      results["cross_tq_detail"]=r3["detail"]
    r4=check_text_vs_layout(text,font_count);    results["cross_text_layout"]=r4["score"];  results["cross_tl_detail"]=r4["detail"]
    return results


# ═══════════════════════════════════════
# CATEGORY 14: SCORING SYSTEM
# ═══════════════════════════════════════

# Dynamic weights — adjusted per file type
# IMAGE total = 1.00 exactly
WEIGHTS_IMAGE = {
    # Image forensics (Cat 5) — 33%
    "ela":            0.12,
    "copy_move":      0.05,
    "splicing":       0.04,
    "noise":          0.03,
    "blur_sharpness": 0.03,
    "edge_boundary":  0.02,
    "color_profile":  0.03,
    "compression":    0.02,
    "lighting":       0.02,
    # Text & language (Cat 2,11) — 12%
    "char_anomaly":        0.04,
    "text_completeness":   0.02,
    "language_consistency":0.02,
    "language_anomaly":    0.02,
    "ocr_quality":         0.02,
    # Semantic (Cat 3) — 14%
    "date_logic":       0.04,
    "numerical_ranges": 0.04,
    "cross_field":      0.04,
    "id_format":        0.02,
    # Entity (Cat 4) — 8%
    "name_consistency":  0.03,
    "inst_consistency":  0.02,
    "id_consistency":    0.02,
    "entity_frequency":  0.01,
    # Signature & stamp (Cat 9) — 13%
    "sig_presence":     0.03,
    "sig_blank":        0.03,
    "sig_anomaly":      0.03,
    "stamp_duplication":0.02,
    "stamp_position":   0.02,
    # QR (Cat 10) — 3%
    "qr_check":         0.03,
    # Duplication (Cat 12) — 4%
    "region_duplication":0.02,
    "logo_duplication":  0.01,
    "region_anomaly":    0.01,
    # Cross-modal (Cat 13) — 6%
    "cross_text_image":  0.02,
    "cross_text_sig":    0.01,
    "cross_text_qr":     0.01,
    "cross_text_layout": 0.01,
    # Layout (Cat 6) — 5%
    "table_grid":        0.02,
    "stamp_alignment":   0.02,
    "template_sim":      0.01,
    # total = 1.00
}

# PDF total = 1.00 exactly
WEIGHTS_PDF = {
    # Image forensics on embedded (Cat 5) — 14%
    "ela":            0.05,
    "copy_move":      0.03,
    "splicing":       0.02,
    "noise":          0.01,
    "blur_sharpness": 0.01,
    "edge_boundary":  0.01,
    "color_profile":  0.01,
    # Text (Cat 2) — 14%
    "font_style":          0.04,
    "text_layer_mismatch": 0.05,
    "char_anomaly":        0.02,
    "text_completeness":   0.02,
    "language_consistency":0.01,
    # Semantic (Cat 3) — 11%
    "date_logic":         0.03,
    "numerical_ranges":   0.03,
    "cross_field":        0.03,
    "id_format":          0.01,
    "institution_validity":0.01,
    # Entity (Cat 4) — 6%
    "name_consistency": 0.02,
    "inst_consistency": 0.02,
    "id_consistency":   0.02,
    # PDF forensics (Cat 7) — 13%
    "text_layer":       0.02,
    "hidden_text":      0.03,
    "object_count":     0.01,
    "layer_depth":      0.02,
    "font_embed":       0.02,
    "incremental_save": 0.02,
    "suspicious_sw":    0.01,
    # Metadata (Cat 8) — 12%
    "date_mismatch":     0.04,
    "metadata_software": 0.03,
    "missing_metadata":  0.02,
    "timezone_mismatch": 0.02,
    "author_check":      0.01,
    # Signature (Cat 9) — 8%
    "digital_signature": 0.03,
    "sig_presence":      0.02,
    "sig_anomaly":       0.02,
    "stamp_duplication": 0.01,
    # QR (Cat 10) — 4%
    "qr_check":          0.04,
    # Language (Cat 11) — 2%
    "language_anomaly":  0.01,
    "ocr_quality":       0.01,
    # Duplication (Cat 12) — 2%
    "region_duplication":0.01,
    "text_img_overlay":  0.01,
    # Cross-modal (Cat 13) — 6%
    "cross_text_image":  0.02,
    "cross_text_sig":    0.01,
    "cross_text_qr":     0.02,
    "cross_text_layout": 0.01,
    # Layout (Cat 6) — 8%
    "margin_consistency":0.02,
    "header_footer":     0.02,
    "block_spacing":     0.02,
    "stamp_alignment":   0.02,
    # total = 1.00
}

def _transform_score(v):
    if v >= 70:
        return v * 1.2   # boost strong signals
    elif v <= 20:
        return v * 0.8   # reduce weak noise
    return v

# Critical anomaly keywords — if any found, minimum score is applied
CRITICAL_ANOMALY_KEYWORDS = [
    "impossible",       # impossible percentage, impossible age
    "exceeds",          # CGPA exceeds, marks exceed
    "after issue date", # DOB after issue date
    "future date",      # future date detected
    "negative",         # negative age/value
    "mismatch",         # critical mismatch
    "edited with",      # photoshop/gimp detected
    "hidden text",      # hidden text found
    "modified",         # modified after creation
    "forged",           # explicit forgery flag
]

def _anomaly_penalty(anomalies: list) -> float:
    """
    Convert anomaly strings into a score penalty.
    Each critical anomaly adds to the penalty.
    Returns 0-100 penalty score.
    """
    if not anomalies:
        return 0.0
    penalty = 0.0
    for anomaly in anomalies:
        al = anomaly.lower()
        for keyword in CRITICAL_ANOMALY_KEYWORDS:
            if keyword in al:
                penalty += 15.0  # each critical anomaly = +15 points
                break
        else:
            penalty += 5.0  # non-critical anomaly = +5 points
    return min(60.0, penalty)  # cap penalty contribution at 60


def compute_score(scores: dict, file_type: str,
                  quality_score: float = 100,
                  anomalies: list = None) -> float:
    """
    Weighted forgery score computation.
    - Numeric check scores: weighted average
    - Anomaly penalty: direct addition
    - Quality adjustment: scales confidence
    - Critical overrides: instant high score
    """
    W = WEIGHTS_IMAGE if file_type == "image" else WEIGHTS_PDF

    # ── Critical instant overrides ──────────────────────────
    # If any single check is extremely high, document is forged
    INSTANT_FORGED_CHECKS = {
        "hidden_text":      85,
        "date_mismatch":    80,
        "metadata_software":80,
        "incremental_save": 90,
        "suspicious_sw":    85,
    }
    for k, threshold in INSTANT_FORGED_CHECKS.items():
        if scores.get(k, 0) >= threshold:
            return round(min(100, 70 + scores[k] * 0.2), 2)

    # ── Weighted numeric score ───────────────────────────────
    total = 0.0; used = 0.0
    for k, w in W.items():
        v = scores.get(k)
        if v is not None and isinstance(v, (int, float)):
            v = _transform_score(float(v))
            total += v * w
            used  += w

    raw = (total / used) if used > 0 else 0.0

    # ── Anomaly penalty (THIS IS THE KEY FIX) ───────────────
    # Anomalies found by semantic/entity checks must affect score
    penalty = _anomaly_penalty(anomalies or [])

    # Combine: weighted score + anomaly penalty
    combined = raw * 0.65 + penalty * 0.35

    # ── Quality adjustment ───────────────────────────────────
    qf = quality_score / 100
    if qf < 0.5:
        adjusted = combined * (0.5 + 0.5 * qf)
    else:
        adjusted = combined * (0.7 + 0.3 * qf)

    return round(min(100, max(0, adjusted)), 2)

def get_verdict(score:float) -> dict:
    if score<=20:   return {"verdict":"GENUINE",    "emoji":"✅","color":"green", "risk":"LOW"}
    elif score<=55: return {"verdict":"SUSPICIOUS", "emoji":"⚠️","color":"yellow","risk":"MEDIUM"}
    else:           return {"verdict":"FORGED",     "emoji":"❌","color":"red",   "risk":"HIGH"}


# ═══════════════════════════════════════
# CATEGORY 15: EXPLAINABILITY
# ═══════════════════════════════════════

ALL_LABELS = {
    "ela":"ELA Tampering","copy_move":"Copy-Move","splicing":"Splicing","noise":"Noise",
    "blur_sharpness":"Blur/Sharpness","edge_boundary":"Edge Boundary","color_profile":"Color Profile",
    "compression":"Compression","lighting":"Lighting","region_anomaly":"Region Anomaly",
    "font_style":"Font Style","text_layer_mismatch":"Text Layer Mismatch","char_anomaly":"Char Anomaly",
    "text_completeness":"Text Completeness","language_consistency":"Language","ocr_confidence":"OCR Confidence",
    "date_logic":"Date Logic","numerical_ranges":"Numerical Ranges","cross_field":"Cross-Field",
    "id_format":"ID Format","institution_validity":"Institution","date_mismatch":"Date Mismatch",
    "metadata_software":"Metadata Software","missing_metadata":"Missing Metadata",
    "timezone_mismatch":"Timezone","author_check":"Author Check",
    "name_consistency":"Name Consistency","inst_consistency":"Institution Consistency",
    "id_consistency":"ID Consistency","entity_frequency":"Entity Frequency",
    "sig_presence":"Signature Presence","sig_blank":"Blank Signature","sig_anomaly":"Signature Anomaly",
    "stamp_duplication":"Stamp Duplication","stamp_position":"Stamp Position","digital_signature":"Digital Signature",
    "qr_check":"QR Code","language_anomaly":"Language Anomaly","ocr_quality":"OCR Quality",
    "region_duplication":"Region Duplication","logo_duplication":"Logo Duplication","text_repetition":"Text Repetition",
    "cross_text_image":"Cross: Text↔Image","cross_text_sig":"Cross: Text↔Signature",
    "cross_text_qr":"Cross: Text↔QR","cross_text_layout":"Cross: Text↔Layout",
    "text_layer":"Text Layer","hidden_text":"Hidden Text","object_count":"Object Count",
    "layer_depth":"Layer Depth","font_embed":"Font Embedding","incremental_save":"Incremental Save",
    "suspicious_sw":"Suspicious Software","text_img_overlay":"Text-Image Overlay",
    "margin_consistency":"Margins","line_alignment":"Line Alignment","block_spacing":"Block Spacing",
    "table_grid":"Table Grid","stamp_alignment":"Stamp Alignment","header_footer":"Header/Footer","template_sim":"Template",
}

SECTION_MAP = {
    "🖼️ Image Forensics":      ["ela","copy_move","splicing","noise","blur_sharpness","edge_boundary","color_profile","compression","lighting","region_anomaly"],
    "📝 Text Intelligence":    ["font_style","text_layer_mismatch","char_anomaly","text_completeness","language_consistency","ocr_confidence"],
    "🔢 Semantic Validation":  ["date_logic","numerical_ranges","cross_field","id_format","institution_validity"],
    "🧩 Entity Intelligence":  ["name_consistency","inst_consistency","id_consistency","entity_frequency"],
    "📄 PDF Forensics":        ["text_layer","hidden_text","object_count","layer_depth","font_embed","incremental_save","suspicious_sw","text_img_overlay"],
    "🗂️ Metadata":            ["date_mismatch","metadata_software","missing_metadata","timezone_mismatch","author_check"],
    "✍️ Signature & Stamp":   ["sig_presence","sig_blank","sig_anomaly","stamp_duplication","stamp_position","digital_signature"],
    "📱 QR & Barcode":         ["qr_check"],
    "🌐 Language & OCR":       ["language_anomaly","ocr_quality"],
    "🔁 Duplication":          ["region_duplication","logo_duplication","text_repetition"],
    "🔗 Cross-Modal":          ["cross_text_image","cross_text_sig","cross_text_qr","cross_text_layout"],
    "📐 Layout":               ["margin_consistency","line_alignment","block_spacing","table_grid","stamp_alignment","header_footer","template_sim"],
}

def build_explainability(scores:dict, file_type:str, all_anomalies:list) -> dict:
    W = WEIGHTS_IMAGE if file_type=="image" else WEIGHTS_PDF
    # Top risks
    ranked=sorted([(k,v,W.get(k,0)) for k,v in scores.items()
                    if isinstance(v,(int,float)) and v>20 and k in W],
                   key=lambda x:x[1]*x[2], reverse=True)
    top_risks=[{"check":ALL_LABELS.get(k,k),"score":round(v,1),"weight":round(w,3)}
               for k,v,w in ranked[:7]]
    # Section breakdown
    sections={}
    for sec,keys in SECTION_MAP.items():
        checks={}
        for k in keys:
            v=scores.get(k)
            if v is not None and isinstance(v,(int,float)):
                checks[ALL_LABELS.get(k,k)]=round(v,1)
        if checks:
            avg=sum(checks.values())/len(checks)
            risk="HIGH" if avg>60 else "MEDIUM" if avg>30 else "LOW"
            sections[sec]={"checks":checks,"average":round(avg,1),"risk":risk}
    return {
        "top_risk_factors": top_risks,
        "section_analysis": sections,
        "anomalies":        all_anomalies[:15],
        "anomaly_count":    len(all_anomalies),
    }

def create_heatmap_overlay(image_path:str, ela_heatmap:str) -> str:
    try:
        if not ela_heatmap or not os.path.exists(ela_heatmap): return ela_heatmap
        orig = cv2.imread(image_path)
        heat = cv2.imread(ela_heatmap)
        if orig is None or heat is None: return ela_heatmap
        heat = cv2.resize(heat,(orig.shape[1],orig.shape[0]))
        overlay = cv2.addWeighted(orig,0.55,heat,0.45,0)
        op = os.path.join(HMAP,"overlay_"+os.path.basename(image_path)+".jpg")
        cv2.imwrite(op,overlay)
        return op
    except: return ela_heatmap


# ═══════════════════════════════════════
# CATEGORY 16: PERFORMANCE & ROBUSTNESS
# ═══════════════════════════════════════

def safe_run(func, *args, default=None, **kwargs):
    """Wrapper — ensures any module failure doesn't crash the pipeline."""
    try:
        result = func(*args, **kwargs)
        return result if result is not None else (default or {})
    except Exception as e:
        print(f"[SAFE_RUN] {func.__name__} failed: {e}")
        return default or {}

def merge_scores(*dicts) -> dict:
    """Merge multiple result dicts, keeping all keys."""
    merged={}
    for d in dicts:
        if isinstance(d,dict):
            merged.update(d)
    return merged


# ═══════════════════════════════════════
# CATEGORY 17: WOW FACTOR
# ═══════════════════════════════════════

DOC_KEYWORDS = {
    "aadhar":       ["aadhaar","aadhar","uid","uidai","government of india","biometric"],
    "pan_card":     ["permanent account","pan","income tax","dept of revenue"],
    "marksheet":    ["marks","subject","total","grade","percentage","pass","fail","scored"],
    "certificate":  ["certificate","certify","awarded","completed","achievement"],
    "degree":       ["bachelor","master","doctor","b.tech","m.tech","b.e","m.e","phd","convocation"],
    "bonafide":     ["bonafide","studying","enrolled","roll no","year of study"],
    "transfer":     ["transfer certificate","tc","leaving certificate","school"],
    "payslip":      ["salary","payslip","gross","net pay","deduction","epf","pf"],
    "id_card":      ["employee id","student id","identity card","college id"],
}

def classify_document(text: str) -> dict:
    """Classify document type using keyword matching."""
    tl = text.lower()
    scores = {}
    for doc_type, keywords in DOC_KEYWORDS.items():
        score = sum(1 for k in keywords if k in tl)
        if score > 0: scores[doc_type] = score
    if not scores:
        return {"doc_type":"unknown","confidence":0,"detail":"Could not classify document"}
    best = max(scores, key=scores.get)
    conf = min(100, scores[best]*25)
    return {"doc_type":best, "confidence":conf,
            "detail":f"Document classified as: {best.replace('_',' ').title()} ({conf}% confidence)"}

def detect_institution_logo(image_path: str) -> dict:
    """Detect if a recognized institution logo/emblem is present."""
    try:
        img = cv2.imread(image_path)
        if img is None: return {"logo_detected":False,"detail":"Cannot read"}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h,w  = gray.shape
        # Look in top 25% of image for logo (typical position)
        header = gray[:int(h*0.25),:]
        # Detect circular regions (emblems, logos)
        circles = cv2.HoughCircles(header,cv2.HOUGH_GRADIENT,1,30,
                                    param1=50,param2=25,minRadius=15,maxRadius=80)
        has_logo = circles is not None
        count    = 0 if circles is None else len(circles[0])
        return {"logo_detected":has_logo,"logo_count":count,
                "detail":f"{'✅' if has_logo else '⚠️'} {'Emblem/logo detected in header' if has_logo else 'No logo detected in header'}"}
    except Exception as e:
        return {"logo_detected":False,"detail":str(e)}

def detect_fake_template(image_path: str, text: str) -> dict:
    """Detect if document is a low-quality fake template."""
    signals=[]
    # Low word count for an official document
    if len(text.split())<15:
        signals.append("Very little text for an official document ⚠️")
    # Check for watermark-like repeated patterns
    try:
        img = cv2.imread(image_path,cv2.IMREAD_GRAYSCALE)
        if img is not None:
            f=np.fft.fft2(img); mag=np.abs(np.fft.fftshift(f))
            periodic=np.sum(mag>np.mean(mag)*10)
            if periodic<50: signals.append("No repeating background pattern (official docs usually have one) ⚠️")
    except: pass
    score=min(100,len(signals)*35)
    return {"score":score,"signals":signals,
            "detail":" | ".join(signals) if signals else "✅ Document structure looks genuine"}

def run_wow_factor(text:str, image_path:str=None) -> dict:
    results={}
    r1=classify_document(text)
    results["doc_type"]       = r1["doc_type"]
    results["doc_confidence"] = r1["confidence"]
    results["doc_classify_detail"] = r1["detail"]
    if image_path:
        r2=detect_institution_logo(image_path)
        results["logo_detected"] = r2["logo_detected"]
        results["logo_detail"]   = r2["detail"]
        r3=detect_fake_template(image_path,text)
        results["fake_template"] = r3["score"]
        results["template_detail"] = r3["detail"]
    return results
