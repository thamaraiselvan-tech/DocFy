"""
CATEGORY 7:  PDF Forensics (8 checks)
CATEGORY 8:  Metadata Forensics (5 checks)
CATEGORY 9:  Signature & Stamp Intelligence (7 checks)
CATEGORY 10: QR/Barcode Intelligence
CATEGORY 11: Language & OCR Quality
CATEGORY 12: Duplication & Cloning
"""
import cv2, numpy as np, re, fitz, os
from PIL import Image
import re
from datetime import datetime
import fitz

SUSPICIOUS_SW = ["photoshop","gimp","paint","inkscape","canva","pixelmator","affinity","krita"]
TRUSTED_DOMAINS = ["nitt.edu","annauniv.edu","cbse.gov.in","ugc.ac.in","gov.in","ac.in","edu.in","nic.in","uidai.gov.in","digilocker.gov.in"]

# ═════════════════════════════════════
# CATEGORY 7: PDF FORENSICS
# ═════════════════════════════════════

def check_text_layer_presence(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        has_text = any(page.get_text().strip() for page in doc)
        doc.close()
        return {"score":0 if has_text else 5,"has_text_layer":has_text,
                "detail":"✅ Text layer present" if has_text else "ℹ️ Scanned PDF — no text layer"}
    except Exception as e: return {"score":0,"has_text_layer":False,"detail":str(e)}

def check_hidden_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        hidden = []
        for pn,page in enumerate(doc):
            for block in page.get_text("rawdict").get("blocks",[]):
                for line in block.get("lines",[]):
                    for span in line.get("spans",[]):
                        txt = span.get("text","").strip()
                        if txt:
                            if span.get("color",0)==16777215: hidden.append(f"White text p{pn+1}: '{txt[:20]}'")
                            if span.get("size",12)<1: hidden.append(f"Invisible text p{pn+1}")
        doc.close()
        score = min(100,len(hidden)*60)
        return {"score":score,"hidden_items":hidden[:5],
                "detail":" | ".join(hidden[:2]) if hidden else "✅ No hidden text"}
    except Exception as e: return {"score":0,"hidden_items":[],"detail":str(e)}

def check_object_count(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        total_xrefs = doc.xref_length()
        doc.close()
        # Unusually high object count = complex/suspicious structure
        score = min(100,max(0,(total_xrefs-200)/10)) if total_xrefs>200 else 0
        return {"score":round(score,2),"xref_count":total_xrefs,
                "detail":f"PDF objects: {total_xrefs} {'⚠️ Unusually complex' if total_xrefs>500 else '✅ Normal'}"}
    except Exception as e: return {"score":0,"detail":str(e)}

def check_layer_depth(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        max_depth = 0
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            y_map = {}
            for block in blocks:
                for line in block.get("lines",[]):
                    y = round(line["bbox"][1])
                    y_map[y] = y_map.get(y,0)+1
            depth = max(y_map.values()) if y_map else 0
            max_depth = max(max_depth, depth)
        doc.close()
        score = min(100,max(0,(max_depth-3)*25))
        return {"score":score,"max_layer_depth":max_depth,
                "detail":f"Max layer depth: {max_depth} {'⚠️ Deep stacking' if max_depth>4 else '✅ Normal'}"}
    except Exception as e: return {"score":0,"detail":str(e)}

def check_font_embed_mismatch(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        issues = []
        for pn,page in enumerate(doc):
            for font in page.get_fonts(full=True):
                if font[2]=="Type3": issues.append(f"Type3 font p{pn+1}: {font[3]}")
        doc.close()
        score = min(100,len(issues)*30)
        return {"score":score,"font_issues":issues[:4],
                "detail":" | ".join(issues[:2]) if issues else "✅ Fonts properly embedded"}
    except Exception as e: return {"score":0,"detail":str(e)}

def check_incremental_save(pdf_path):
    try:
        with open(pdf_path,"rb") as f: raw = f.read()
        # Count %%EOF markers — multiple = incremental saves
        eof_count = raw.count(b"%%EOF")
        score = 0 if eof_count<=1 else min(100,(eof_count-1)*25)
        return {"score":score,"eof_count":eof_count,
                "detail":f"PDF saves: {eof_count} {'⚠️ Incremental edits detected' if eof_count>1 else '✅ Single save'}"}
    except Exception as e: return {"score":0,"detail":str(e)}

def check_suspicious_software(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        meta = doc.metadata; doc.close()
        prod = meta.get("producer","").lower()
        crea = meta.get("creator","").lower()
        found = [sw for sw in SUSPICIOUS_SW if sw in prod or sw in crea]
        score = 80 if found else 0
        return {"score":score,"found_software":found,
                "detail":f"⚠️ Edited with: {', '.join(found)}" if found else "✅ Normal software"}
    except Exception as e: return {"score":0,"detail":str(e)}

def check_text_image_overlay(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        overlaps = 0
        for page in doc:
            imgs = page.get_images(full=True)
            if not imgs: continue
            txt_blocks = page.get_text("blocks")
            for img in imgs[:5]:
                try:
                    ib = page.get_image_bbox(img[7])
                    if ib:
                        for tb in txt_blocks:
                            tb_rect = fitz.Rect(tb[:4])
                            if ib.intersects(tb_rect): overlaps+=1
                except: pass
        doc.close()
        score = min(100,overlaps*25)
        return {"score":score,"overlap_count":overlaps,
                "detail":f"{overlaps} text-image overlaps {'⚠️' if overlaps>2 else '✅ Normal'}"}
    except Exception as e: return {"score":0,"detail":str(e)}

def run_pdf_forensics(pdf_path):
    results = {}
    r1=check_text_layer_presence(pdf_path); results["text_layer"]=r1["score"];      results["text_layer_detail"]=r1["detail"]
    r2=check_hidden_text(pdf_path);         results["hidden_text"]=r2["score"];      results["hidden_text_detail"]=r2["detail"]
    r3=check_object_count(pdf_path);        results["object_count"]=r3["score"];     results["object_detail"]=r3["detail"]
    r4=check_layer_depth(pdf_path);         results["layer_depth"]=r4["score"];      results["layer_detail"]=r4["detail"]
    r5=check_font_embed_mismatch(pdf_path); results["font_embed"]=r5["score"];       results["font_embed_detail"]=r5["detail"]
    r6=check_incremental_save(pdf_path);    results["incremental_save"]=r6["score"]; results["incr_save_detail"]=r6["detail"]
    r7=check_suspicious_software(pdf_path); results["suspicious_sw"]=r7["score"];   results["sw_detail"]=r7["detail"]
    r8=check_text_image_overlay(pdf_path);  results["text_img_overlay"]=r8["score"]; results["overlay_detail"]=r8["detail"]
    return results

# ═════════════════════════════════════
# CATEGORY 8: METADATA FORENSICS
# ═════════════════════════════════════

def run_metadata_forensics(pdf_path, text=""):
    import re
    from datetime import datetime
    import fitz

    # Helper: parse PDF date safely
    def parse_pdf_date(date_str):
        try:
            if date_str.startswith("D:"):
                date_str = date_str[2:]
            return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
        except:
            return None

    try:
        doc = fitz.open(pdf_path)
        meta = doc.metadata
        doc.close()

        results = {}
        anomalies = []

        created  = meta.get("creationDate", "")
        modified = meta.get("modDate", "")
        producer = meta.get("producer", "").lower()
        creator  = meta.get("creator", "").lower()
        author   = meta.get("author", "").strip()

        # ─────────────────────────────
        # 1. DATE MISMATCH (FIXED)
        # ─────────────────────────────
        dm_score = 0
        created_dt = parse_pdf_date(created)
        modified_dt = parse_pdf_date(modified)

        if created_dt and modified_dt:
            diff_days = (modified_dt - created_dt).days

            if diff_days > 1:
                anomalies.append(f"Modified {diff_days} days after creation ⚠️")
                dm_score = min(100, diff_days * 2)

            elif diff_days < 0:
                anomalies.append("Modified before creation ⚠️")
                dm_score = 80

        results["date_mismatch"] = dm_score
        results["created"] = created
        results["modified"] = modified

        # ─────────────────────────────
        # 2. SOFTWARE CHECK (IMPROVED)
        # ─────────────────────────────
        SUSPICIOUS_SW = ["photoshop","gimp","paint","inkscape","canva","krita"]
        NORMAL_SW = ["acrobat","pdf","word","libreoffice"]

        found_suspicious = [sw for sw in SUSPICIOUS_SW if sw in producer or sw in creator]
        found_normal     = [sw for sw in NORMAL_SW if sw in producer or sw in creator]

        if found_suspicious:
            sw_score = 80
            anomalies.append(f"Edited with suspicious software: {', '.join(found_suspicious)} ⚠️")
        elif not found_normal:
            sw_score = 30  # unknown tool
            anomalies.append("Unknown PDF software ⚠️")
        else:
            sw_score = 0

        results["metadata_software"] = sw_score
        results["software_found"] = found_suspicious + found_normal

        # ─────────────────────────────
        # 3. CREATOR vs PRODUCER (NEW)
        # ─────────────────────────────
        if creator and producer and creator != producer:
            results["creator_producer_mismatch"] = 40
            anomalies.append(f"Creator ≠ Producer ({creator} vs {producer}) ⚠️")
        else:
            results["creator_producer_mismatch"] = 0

        # ─────────────────────────────
        # 4. MISSING METADATA
        # ─────────────────────────────
        missing = [k for k in ["creationDate","author","producer"] if not meta.get(k,"").strip()]
        results["missing_metadata"] = min(100, len(missing) * 25)

        if missing:
            anomalies.append(f"Missing fields: {missing}")

        # ─────────────────────────────
        # 5. TIMEZONE CHECK (IMPROVED)
        # ─────────────────────────────
        tz_score = 0
        tz_pat = r"[+-]\d{2}'\d{2}'"

        tzc = re.search(tz_pat, created)
        tzm = re.search(tz_pat, modified)

        if not tzc or not tzm:
            anomalies.append("Missing timezone info ⚠️")
            tz_score = 20
        elif tzc.group() != tzm.group():
            anomalies.append(f"TZ changed {tzc.group()} → {tzm.group()} ⚠️")
            tz_score = 50

        results["timezone_mismatch"] = tz_score

        # ─────────────────────────────
        # 6. AUTHOR CHECK (IMPROVED)
        # ─────────────────────────────
        SUSPICIOUS_AUTHORS = ["admin","user","test","unknown"]

        if not author:
            auth_score = 30
            anomalies.append("Missing author ⚠️")
        elif author.lower() in SUSPICIOUS_AUTHORS:
            auth_score = 40
            anomalies.append(f"Suspicious author: {author} ⚠️")
        else:
            auth_score = 0

        results["author_check"] = auth_score
        results["author"] = author

        # ─────────────────────────────
        # 7. YEAR MISMATCH (NEW FEATURE)
        # ─────────────────────────────
        year_score = 0
        years_in_text = re.findall(r'20\d{2}', text)

        if created and years_in_text:
            try:
                created_year = created[2:6]
                if created_year not in years_in_text:
                    anomalies.append("Year mismatch between metadata & content ⚠️")
                    year_score = 40
            except:
                pass

        results["year_mismatch"] = year_score

        # ─────────────────────────────
        # FINAL OUTPUT
        # ─────────────────────────────
        results["metadata_anomalies"] = anomalies

        results["metadata_raw"] = {
            "created": created,
            "modified": modified,
            "author": author,
            "producer": meta.get("producer", ""),
            "creator": meta.get("creator", "")
        }

        return results

    except Exception as e:
        return {
            "date_mismatch": 0,
            "metadata_software": 0,
            "missing_metadata": 0,
            "timezone_mismatch": 0,
            "author_check": 0,
            "creator_producer_mismatch": 0,
            "year_mismatch": 0,
            "metadata_anomalies": [str(e)],
            "metadata_raw": {}
        }
# ═════════════════════════════════════
# CATEGORY 9: SIGNATURE & STAMP
# ═════════════════════════════════════

def run_signature_stamp(image_path=None, pdf_path=None):
    results = {}
    if image_path:
        img = cv2.imread(image_path)
        gray = cv2.imread(image_path,cv2.IMREAD_GRAYSCALE) if img is not None else None
        if gray is not None:
            h,w = gray.shape
            # Presence
            bot = gray[int(h*0.75):,:]
            _,bin_img = cv2.threshold(bot,200,255,cv2.THRESH_BINARY_INV)
            results["sig_presence"] = 0 if np.sum(bin_img>0)/bin_img.size>0.005 else 30
            # Blank detection
            bottom_region = gray[int(h*0.7):,int(w*0.5):]
            blank = np.mean(bottom_region)>245
            results["sig_blank"] = 50 if blank else 0
            # Anomaly (pasted sig = too sharp)
            sig_lap = float(np.var(cv2.Laplacian(bottom_region,cv2.CV_64F)))
            results["sig_anomaly"] = min(100,max(0,(sig_lap-600)/60)) if sig_lap>600 else 0
            # Stamp duplication
            orb = cv2.ORB_create(500); kp,des = orb.detectAndCompute(gray,None)
            dup=0
            if des is not None and len(des)>1:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True)
                matches = bf.match(des,des)
                dup = sum(1 for m in matches if m.queryIdx!=m.trainIdx and np.sqrt(sum((np.array(kp[m.queryIdx].pt)-np.array(kp[m.trainIdx].pt))**2))>100)
            results["stamp_duplication"] = min(100,dup*0.5)
            # Stamp position
            hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
            masks=cv2.inRange(hsv,np.array([100,50,50]),np.array([140,255,255]))|cv2.inRange(hsv,np.array([0,50,50]),np.array([20,255,255]))
            cnts,_=cv2.findContours(masks,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            stamps=[cv2.boundingRect(c) for c in cnts if cv2.contourArea(c)>800]
            results["stamp_position"] = 30 if not stamps else (40 if any(s[1]<h*0.5 for s in stamps) else 0)
            # Sharpness inconsistency
            results["sig_sharpness"] = round(sig_lap/100,1)
            # Sig vs name alignment (basic)
            results["sig_name_align"] = 0  # requires OCR box alignment
            results["sig_detail"] = f"Sig region sharpness:{sig_lap:.0f}, stamps:{len(stamps)}"
    if pdf_path:
        doc = fitz.open(pdf_path)
        sigs = []
        for pn,page in enumerate(doc):
            for w in page.widgets():
                if w.field_type_string=="Sig": sigs.append({"page":pn+1,"name":w.field_name})
        doc.close()
        results["digital_signature"] = 0 if sigs else 40
        results["digital_sig_detail"] = f"✅ {len(sigs)} digital sig(s)" if sigs else "⚠️ No digital signature"
    return results

# ═════════════════════════════════════
# CATEGORY 10: QR/BARCODE
# ═════════════════════════════════════

def run_qr_barcode(image_path, doc_text=""):
    if not image_path: return {"qr_check":0,"qr_detail":"No image"}
    try:
        img = cv2.imread(image_path)
        if img is None: return {"qr_check":20,"qr_detail":"Cannot read"}
        qrd = cv2.QRCodeDetector()
        data,bbox,_ = qrd.detectAndDecode(img)
        if not data:
            return {"qr_check":15,"qr_found":False,"qr_detail":"No QR (mild concern for official docs)"}
        data=data.strip()
        trusted=any(d in data.lower() for d in TRUSTED_DOMAINS)
        # Compare QR content with doc text
        qr_vs_doc=0
        if doc_text:
            # Check if any number in QR appears in doc
            qr_nums=set(re.findall(r'\d{4,}',data))
            doc_nums=set(re.findall(r'\d{4,}',doc_text))
            if qr_nums and not qr_nums&doc_nums: qr_vs_doc=40
        score=0 if trusted else (70 if data else 15)
        score=max(score,qr_vs_doc)
        return {"qr_check":score,"qr_found":True,"qr_data":data[:80],
                "qr_detail":f"QR→{'trusted ✅' if trusted else 'untrusted ⚠️'}: {data[:50]}"}
    except Exception as e:
        return {"qr_check":0,"qr_detail":str(e)}

# ═════════════════════════════════════
# CATEGORY 11: LANGUAGE & OCR QUALITY
# ═════════════════════════════════════

def run_language_quality(text, ocr_confidence=1.0):
    results = {}
    # Language detection
    tamil   = len(re.findall(r'[\u0B80-\u0BFF]',text))
    english = len(re.findall(r'[a-zA-Z]',text))
    lang = "Tamil+English" if tamil>0 and english>0 else "Tamil" if tamil>0 else "English" if english>0 else "Unknown"
    results["detected_lang"] = lang
    # Anomalies
    anom=[]
    arabic=len(re.findall(r'[\u0600-\u06FF]',text))
    if arabic>20: anom.append("Unexpected Arabic script ⚠️")
    if tamil>0:
        bad=re.findall(r'[\u0B80-\u0B82]{2}',text)
        if bad: anom.append(f"Invalid Tamil sequences: {len(bad)} ⚠️")
    results["language_anomaly"] = min(100,len(anom)*40)
    # OCR confidence
    results["ocr_quality"] = max(0,(0.55-ocr_confidence)*120) if ocr_confidence<0.55 else 0
    results["lang_detail"] = f"Lang:{lang} | " + (" | ".join(anom) if anom else "✅ Consistent")
    return results

# ═════════════════════════════════════
# CATEGORY 12: DUPLICATION & CLONING
# ═════════════════════════════════════

def run_duplication_detection(image_path=None, text=""):
    results = {}
    if image_path:
        try:
            img = cv2.imread(image_path,cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img = cv2.resize(img,(600,400))
                h,w=img.shape; bs=60; blocks={}; dups=0
                for y in range(0,h-bs,bs//2):
                    for x in range(0,w-bs,bs//2):
                        key=hash(img[y:y+bs,x:x+bs].tobytes())
                        if key in blocks and (abs(y-blocks[key][0])>bs or abs(x-blocks[key][1])>bs): dups+=1
                        else: blocks[key]=(y,x)
                results["region_duplication"]=min(100,dups*3)
                # Logo circles
                circles=cv2.HoughCircles(img,cv2.HOUGH_GRADIENT,1,50,param1=50,param2=30,minRadius=20,maxRadius=100)
                cc=0 if circles is None else len(circles[0])
                results["logo_duplication"]=0 if cc<=2 else min(100,(cc-2)*25)
                results["dup_detail"]=f"Dup regions:{dups}, circles:{cc}"
        except Exception as e:
            results["region_duplication"]=0; results["logo_duplication"]=0; results["dup_detail"]=str(e)
    # Text block repetition
    if text:
        words=text.split()
        from collections import Counter
        rep=[f"{w}×{c}" for w,c in Counter(words).items() if w.isdigit() and len(w)>=3 and c>3]
        results["text_repetition"]=min(100,len(rep)*30)
    return results
