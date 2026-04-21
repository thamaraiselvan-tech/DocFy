"""
MASTER PIPELINE — Orchestrates all 17 categories.
Runs with safe_run wrappers for robustness.
Supports image and PDF inputs.
"""
import os, fitz, cv2

from analysis.a01_input       import analyse_input
from analysis.a02_text        import run_text_intelligence
from analysis.a03_semantic    import run_semantic_validation
from analysis.a04_entity      import run_entity_intelligence
from analysis.a05_a06_image_layout import run_image_forensics, run_layout_intelligence
from analysis.a07_to_a12      import (run_pdf_forensics, run_metadata_forensics,
                                       run_signature_stamp, run_qr_barcode,
                                       run_language_quality, run_duplication_detection)
from analysis.a13_to_a17      import (run_cross_modal, compute_score, get_verdict,
                                       build_explainability, create_heatmap_overlay,
                                       safe_run, merge_scores, run_wow_factor)

TEMP="temp"; os.makedirs(TEMP,exist_ok=True)

def _pdf_to_image(pdf_path:str) -> str:
    """Render first page of PDF as image."""
    try:
        doc=fitz.open(pdf_path)
        pix=doc[0].get_pixmap(dpi=150)
        p=os.path.join(TEMP,"render.png")
        pix.save(p); doc.close()
        return p
    except: return None

def _collect_anomalies(scores:dict) -> list:
    """Gather all anomaly lists from the scores dict."""
    anom=[]
    for k in ["semantic_anomalies","entity_anomalies","metadata_anomalies"]:
        v=scores.pop(k,[])
        if isinstance(v,list): anom.extend(v)
    return anom


def run_full_pipeline(file_path:str) -> dict:
    ext=os.path.splitext(file_path)[1].lower()
    file_type="pdf" if ext==".pdf" else "image"
    all_scores={}; all_anomalies=[]

    # ── CAT 1: INPUT UNDERSTANDING ───────────────────
    print("[1/17] Input understanding...")
    inp=safe_run(analyse_input, file_path)
    quality_score=inp.get("quality_score",100)
    doc_sub_type =inp.get("sub_type","unknown")
    all_anomalies+=inp.get("quality_flags",[])

    # Decide working image path
    image_path=file_path if file_type=="image" else _pdf_to_image(file_path)

    # ── CAT 2: TEXT INTELLIGENCE ─────────────────────
    print("[2/17] Text intelligence...")
    txt=safe_run(run_text_intelligence, image_path=image_path,
                 pdf_path=file_path if file_type=="pdf" else None)
    full_text=txt.pop("full_text","")
    ocr_text =txt.pop("ocr_text","")
    ocr_conf =txt.pop("ocr_avg_conf",1.0)
    ocr_boxes=txt.pop("ocr_boxes",[])
    all_scores.update(txt)

    # ── CAT 3: SEMANTIC VALIDATION ───────────────────
    print("[3/17] Semantic validation...")
    sem=safe_run(run_semantic_validation, full_text)
    all_anomalies+=sem.pop("semantic_anomalies",[])
    doc_type=sem.pop("doc_type","unknown")
    all_scores.update(sem)

    # ── CAT 4: ENTITY INTELLIGENCE ───────────────────
    print("[4/17] Entity intelligence...")
    ent=safe_run(run_entity_intelligence, full_text)
    all_anomalies+=ent.pop("entity_anomalies",[])
    all_scores.update(ent)

    # ── CAT 5: IMAGE FORENSICS ───────────────────────
    print("[5/17] Image forensics...")
    if image_path and os.path.exists(image_path):
        img_f=safe_run(run_image_forensics, image_path)
        ela_hm=img_f.pop("ela_heatmap",None)
        all_scores.update(img_f)
    else:
        ela_hm=None

    # ── CAT 6: LAYOUT INTELLIGENCE ───────────────────
    print("[6/17] Layout intelligence...")
    lay=safe_run(run_layout_intelligence,
                 image_path=image_path,
                 pdf_path=file_path if file_type=="pdf" else None)
    all_scores.update(lay)

    # ── CAT 7: PDF FORENSICS ─────────────────────────
    if file_type=="pdf":
        print("[7/17] PDF forensics...")
        pdf_f=safe_run(run_pdf_forensics, file_path)
        all_scores.update(pdf_f)

    # ── CAT 8: METADATA FORENSICS ────────────────────
    if file_type=="pdf":
        print("[8/17] Metadata forensics...")
        meta_f=safe_run(run_metadata_forensics, file_path)
        meta_anom=meta_f.pop("metadata_anomalies",[])
        meta_raw =meta_f.pop("metadata_raw",{})
        all_anomalies+=meta_anom
        all_scores.update(meta_f)
    else:
        meta_raw={}  # images have no PDF metadata

    # ── CAT 9: SIGNATURE & STAMP ─────────────────────
    print("[9/17] Signature & stamp...")
    sig=safe_run(run_signature_stamp,
                 image_path=image_path,
                 pdf_path=file_path if file_type=="pdf" else None)
    sig.pop("sig_detail",None)
    sig.pop("sig_sharpness",None)
    sig.pop("sig_name_align",None)
    all_scores.update(sig)

    # ── CAT 10: QR / BARCODE ─────────────────────────
    print("[10/17] QR/barcode...")
    qr=safe_run(run_qr_barcode, image_path, full_text)
    qr_data=qr.pop("qr_data","")
    all_scores.update(qr)

    # ── CAT 11: LANGUAGE & OCR QUALITY ───────────────
    print("[11/17] Language & OCR quality...")
    lang=safe_run(run_language_quality, full_text, ocr_conf)
    all_scores.update(lang)

    # ── CAT 12: DUPLICATION DETECTION ────────────────
    print("[12/17] Duplication detection...")
    dup=safe_run(run_duplication_detection, image_path=image_path, text=full_text)
    all_scores.update(dup)

    # ── CAT 13: CROSS-MODAL CONSISTENCY ──────────────
    print("[13/17] Cross-modal consistency...")
    font_count=all_scores.get("font_count",1)
    cross=safe_run(run_cross_modal, full_text, image_path, qr_data, font_count)
    all_scores.update(cross)

    # ── CAT 17: WOW FACTOR ───────────────────────────
    print("[17/17] Wow factor...")
    wow=safe_run(run_wow_factor, full_text, image_path)
    fake_t=wow.pop("fake_template",0)
    if fake_t>30: all_scores["fake_template"]=fake_t
    doc_type=wow.get("doc_type",doc_type)

    # ── CAT 14: SCORING ──────────────────────────────
    print("[14/17] Computing score...")
    final_score=compute_score(all_scores, file_type, quality_score, anomalies=all_anomalies)
    verdict_info=get_verdict(final_score)

    # ── CAT 15: EXPLAINABILITY ───────────────────────
    print("[15/17] Explainability...")
    explain=build_explainability(all_scores, file_type, all_anomalies)
    annotated=create_heatmap_overlay(image_path, ela_hm) if image_path and ela_hm else ela_hm

    # ── CAT 16: ROBUSTNESS — cleanup ─────────────────
    if file_type=="pdf" and image_path and os.path.exists(image_path):
        try: os.remove(image_path)
        except: pass

    print(f"[PIPELINE] ✅ Score:{final_score} Verdict:{verdict_info['verdict']}")
    return {
        # Core
        "file_type":      file_type,
        "sub_type":       doc_sub_type,
        "doc_type":       doc_type,
        "doc_confidence": wow.get("doc_confidence",0),
        "verdict":        verdict_info["verdict"],
        "emoji":          verdict_info["emoji"],
        "risk":           verdict_info["risk"],
        "final_score":    final_score,
        "quality_score":  quality_score,
        # Data
        "scores":         {k:round(v,1) for k,v in all_scores.items() if isinstance(v,(int,float))},
        "ocr_text":       full_text[:800],
        "anomalies":      list(dict.fromkeys(all_anomalies)),  # deduplicate
        "heatmap":        annotated,
        "metadata":       meta_raw,
        # Explainability
        "explainability": explain,
        # Wow
        "logo_detected":  wow.get("logo_detected",False),
        "logo_detail":    wow.get("logo_detail",""),
    }
