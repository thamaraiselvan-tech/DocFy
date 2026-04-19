"""
CATEGORY 5: IMAGE FORENSICS (10 checks)
CATEGORY 6: LAYOUT INTELLIGENCE (7 checks)
"""
import cv2
import numpy as np
import os
import pdfplumber
from PIL import Image, ImageChops, ImageEnhance

HMAP = "heatmaps"
os.makedirs(HMAP, exist_ok=True)

# ═══════════════════════════════════════
# CATEGORY 5: IMAGE FORENSICS
# ═══════════════════════════════════════

def check_ela(image_path: str, quality: int = 90) -> dict:
    """ELA — detects edited pixel regions via compression difference."""
    try:
        orig = Image.open(image_path).convert("RGB")
        orig.save("_tmp_ela.jpg","JPEG",quality=quality)
        diff = ImageChops.difference(orig, Image.open("_tmp_ela.jpg"))
        ela  = ImageEnhance.Brightness(diff).enhance(20)
        arr  = np.array(ela)
        mean = float(np.mean(arr))
        score= min(100, mean*2.3)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        heat = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        hp   = os.path.join(HMAP, "ela_"+os.path.basename(image_path)+".jpg")
        cv2.imwrite(hp, heat)
        if os.path.exists("_tmp_ela.jpg"): os.remove("_tmp_ela.jpg")
        return {"score":round(score,2),"heatmap":hp,"detail":f"ELA mean brightness: {mean:.2f} {'⚠️ Tampered regions detected' if score>40 else '✅ Normal'}"}
    except Exception as e:
        return {"score":0,"heatmap":None,"detail":str(e)}

def check_copy_move(image_path: str) -> dict:
    """ORB+RANSAC copy-move forgery detection."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read"}
        img = cv2.resize(img,(800,600))
        orb = cv2.ORB_create(nfeatures=5000)
        kp, des = orb.detectAndCompute(img, None)
        if des is None or len(des)<2: return {"score":0,"detail":"No features"}
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(des,des,k=3)
        sus = [m for m in matches if len(m)>=2
               and m[0].queryIdx!=m[0].trainIdx
               and m[0].distance<0.7*m[1].distance]
        c = len(sus)
        score = 0 if c<10 else 30 if c<50 else 60 if c<100 else 90
        return {"score":score,"match_count":c,"detail":f"Copy-move matches: {c} {'⚠️' if c>20 else '✅'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_splicing(image_path: str) -> dict:
    """Detect image splicing via region-wise Laplacian variance."""
    try:
        img = cv2.imread(image_path)
        if img is None: return {"score":0,"detail":"Cannot read"}
        h,w = img.shape[:2]
        quads = [img[:h//2,:w//2],img[:h//2,w//2:],img[h//2:,:w//2],img[h//2:,w//2:]]
        scores = [float(np.var(cv2.Laplacian(cv2.cvtColor(q,cv2.COLOR_BGR2GRAY),cv2.CV_64F))) for q in quads]
        variance = float(np.var(scores))
        score = min(100, variance/600)
        return {"score":round(score,2),"region_variances":[round(s,1) for s in scores],
                "detail":f"Splicing variance: {variance:.0f} {'⚠️ Possible splicing' if variance>15000 else '✅ Consistent'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_noise(image_path: str) -> dict:
    """Detect noise inconsistency across blocks."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read"}
        img = cv2.resize(img,(600,400))
        bs  = 50
        nl  = [float(np.std((img[y:y+bs,x:x+bs].astype(float)-cv2.GaussianBlur(img[y:y+bs,x:x+bs],(5,5),0).astype(float))))
               for y in range(0,img.shape[0]-bs,bs) for x in range(0,img.shape[1]-bs,bs)]
        if len(nl)<2: return {"score":0,"detail":"Insufficient blocks"}
        std = float(np.std(nl))
        score = min(100, std*3.5)
        return {"score":round(score,2),"noise_std":round(std,2),
                "detail":f"Noise std: {std:.2f} {'⚠️ Inconsistent noise' if std>12 else '✅ Uniform noise'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_blur_sharpness(image_path: str) -> dict:
    """Detect sharpness inconsistency — pasted regions are often blurry/sharp outliers."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read"}
        h,w = img.shape; bs=60
        sh  = [float(np.var(cv2.Laplacian(img[y:y+bs,x:x+bs],cv2.CV_64F)))
               for y in range(0,h-bs,bs) for x in range(0,w-bs,bs)]
        if len(sh)<4: return {"score":0,"detail":"Insufficient blocks"}
        arr = np.array(sh); m,s = np.mean(arr),np.std(arr)
        outliers = float(np.sum(np.abs(arr-m)>2*s)/len(arr))
        score = min(100,outliers*220)
        return {"score":round(score,2),"outlier_ratio":round(outliers,3),
                "detail":f"Sharpness outliers: {outliers:.1%} {'⚠️ Blur/sharp inconsistency' if outliers>0.08 else '✅ Consistent'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_edge_boundary(image_path: str) -> dict:
    """Detect unnatural sharp edges — cut-paste boundaries."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read"}
        edges = cv2.Canny(img,50,150)
        lines = cv2.HoughLinesP(edges,1,np.pi/180,60,minLineLength=120,maxLineGap=5)
        if lines is None: return {"score":0,"detail":"✅ No suspicious boundaries"}
        long_lines = len([l for l in lines if np.sqrt((l[0][2]-l[0][0])**2+(l[0][3]-l[0][1])**2)>160])
        score = min(100, long_lines*6)
        return {"score":round(score,2),"boundary_count":long_lines,
                "detail":f"Sharp boundaries: {long_lines} {'⚠️ Cut-paste detected' if long_lines>6 else '✅ Normal'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_color_profile(image_path: str) -> dict:
    """Detect color inconsistency across document regions."""
    try:
        img = cv2.imread(image_path)
        if img is None: return {"score":0,"detail":"Cannot read"}
        h,w = img.shape[:2]
        quads = [img[:h//2,:w//2],img[:h//2,w//2:],img[h//2:,:w//2],img[h//2:,w//2:]]
        means = [float(np.mean(q)) for q in quads]
        var   = float(np.var(means))
        score = min(100, var*0.6)
        return {"score":round(score,2),"region_means":[round(m,1) for m in means],
                "detail":f"Color variance: {var:.1f} {'⚠️ Inconsistent colors' if var>60 else '✅ Consistent'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_compression(image_path: str) -> dict:
    """Detect JPEG blocking artifacts — inconsistency signals re-compression."""
    try:
        img  = cv2.imread(image_path)
        if img is None: return {"score":0,"detail":"Cannot read"}
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY).astype(float)
        h,w  = gray.shape
        hd   = [float(np.mean(np.abs(gray[y,:]-gray[y-1,:]))) for y in range(8,h,8)]
        vd   = [float(np.mean(np.abs(gray[:,x]-gray[:,x-1]))) for x in range(8,w,8)]
        nb   = [float(np.mean(np.abs(gray[y,:]-gray[y-1,:]))) for y in range(1,h) if y%8!=0]
        avg_b= (np.mean(hd)+np.mean(vd))/2
        avg_n= np.mean(nb) if nb else 1
        ratio= avg_b/(avg_n+1e-5)
        score= min(100,max(0,(ratio-1.4)*45))
        return {"score":round(score,2),"block_ratio":round(ratio,2),
                "detail":f"Compression ratio: {ratio:.2f} {'⚠️ Artifact anomaly' if ratio>2.0 else '✅ Normal'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_lighting(image_path: str) -> dict:
    """Detect shadow/lighting inconsistency — pasted items have different lighting."""
    try:
        img = cv2.imread(image_path)
        if img is None: return {"score":0,"detail":"Cannot read"}
        lab = cv2.cvtColor(img,cv2.COLOR_BGR2LAB)
        l   = lab[:,:,0].astype(float)
        h,w = l.shape
        quads = [l[:h//2,:w//2],l[:h//2,w//2:],l[h//2:,:w//2],l[h//2:,w//2:]]
        angles= []
        for q in quads:
            gx = cv2.Sobel(q,cv2.CV_64F,1,0,ksize=3)
            gy = cv2.Sobel(q,cv2.CV_64F,0,1,ksize=3)
            angles.append(float(np.mean(np.arctan2(gy,gx+1e-5))))
        var   = float(np.var(angles))
        score = min(100, var*28)
        return {"score":round(score,2),"angle_variance":round(var,3),
                "detail":f"Lighting variance: {var:.3f} {'⚠️ Inconsistent lighting' if var>1.5 else '✅ Consistent'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_region_anomaly(image_path: str) -> dict:
    """Region-wise anomaly scoring (not global) — locates tampered area."""
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read","regions":[]}
        h,w = img.shape; bs=80
        region_scores = []
        for y in range(0,h-bs,bs):
            for x in range(0,w-bs,bs):
                block = img[y:y+bs,x:x+bs]
                lap   = float(np.var(cv2.Laplacian(block,cv2.CV_64F)))
                noise = float(np.std(block.astype(float)-cv2.GaussianBlur(block,(5,5),0).astype(float)))
                region_scores.append({"y":y,"x":x,"sharpness":round(lap,1),"noise":round(noise,1)})
        if not region_scores: return {"score":0,"detail":"No regions","regions":[]}
        sharps = np.array([r["sharpness"] for r in region_scores])
        m,s    = np.mean(sharps),np.std(sharps)
        for r in region_scores:
            r["anomaly"] = abs(r["sharpness"]-m) > 2*s
        anomalous = [r for r in region_scores if r["anomaly"]]
        ratio  = len(anomalous)/max(len(region_scores),1)
        score  = min(100, ratio*180)
        return {"score":round(score,2),"anomalous_regions":len(anomalous),
                "total_regions":len(region_scores),
                "detail":f"{len(anomalous)}/{len(region_scores)} regions anomalous {'⚠️' if ratio>0.15 else '✅'}"}
    except Exception as e:
        return {"score":0,"detail":str(e),"regions":[]}


def run_image_forensics(image_path: str) -> dict:
    results = {}
    r1  = check_ela(image_path);            results["ela"]=r1["score"];          results["ela_heatmap"]=r1.get("heatmap"); results["ela_detail"]=r1["detail"]
    r2  = check_copy_move(image_path);      results["copy_move"]=r2["score"];    results["copy_move_detail"]=r2["detail"]
    r3  = check_splicing(image_path);       results["splicing"]=r3["score"];     results["splicing_detail"]=r3["detail"]
    r4  = check_noise(image_path);          results["noise"]=r4["score"];        results["noise_detail"]=r4["detail"]
    r5  = check_blur_sharpness(image_path); results["blur_sharpness"]=r5["score"]; results["blur_detail"]=r5["detail"]
    r6  = check_edge_boundary(image_path);  results["edge_boundary"]=r6["score"]; results["edge_detail"]=r6["detail"]
    r7  = check_color_profile(image_path);  results["color_profile"]=r7["score"]; results["color_detail"]=r7["detail"]
    r8  = check_compression(image_path);    results["compression"]=r8["score"];  results["compression_detail"]=r8["detail"]
    r9  = check_lighting(image_path);       results["lighting"]=r9["score"];     results["lighting_detail"]=r9["detail"]
    r10 = check_region_anomaly(image_path); results["region_anomaly"]=r10["score"]; results["region_detail"]=r10["detail"]
    return results


# ═══════════════════════════════════════
# CATEGORY 6: LAYOUT INTELLIGENCE
# ═══════════════════════════════════════

def check_margin_consistency(pdf_path: str) -> dict:
    try:
        margins = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                if not words: continue
                margins.append({"left":min(w["x0"] for w in words),
                                 "right":page.width-max(w["x1"] for w in words)})
        if not margins: return {"score":0,"detail":"No text for margin analysis"}
        lv = float(np.std([m["left"] for m in margins]))
        rv = float(np.std([m["right"] for m in margins]))
        score = min(100,(lv+rv)*2)
        return {"score":round(score,2),
                "detail":f"Margin std L:{lv:.1f} R:{rv:.1f} {'⚠️ Inconsistent' if lv>12 else '✅ Consistent'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_line_alignment(pdf_path: str) -> dict:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()
        if not words: return {"score":0,"detail":"No words"}
        tops = [round(w["top"]) for w in words]
        from collections import Counter
        freq = Counter(tops)
        lines = [{"y":y,"words":[w for w in words if round(w["top"])==y]} for y,_ in freq.most_common(20)]
        anomalies = []
        for line in lines:
            if len(line["words"])>1:
                bottoms = [w["bottom"] for w in line["words"]]
                if float(np.std(bottoms))>4:
                    anomalies.append(f"Baseline jitter at y≈{line['y']} ⚠️")
        score = min(100,len(anomalies)*30)
        return {"score":score,"anomalies":anomalies,
                "detail":" | ".join(anomalies[:2]) if anomalies else "✅ Lines aligned"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_text_block_spacing(pdf_path: str) -> dict:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            words = pdf.pages[0].extract_words() if pdf.pages else []
        if not words: return {"score":0,"detail":"No words"}
        gaps = []
        ws   = sorted(words,key=lambda w:w["x0"])
        for i in range(1,len(ws)):
            g = ws[i]["x0"]-(ws[i-1]["x0"]+ws[i-1]["width"])
            if 0<g<100: gaps.append(g)
        if not gaps: return {"score":0,"detail":"No gaps"}
        g_arr = np.array(gaps)
        outliers = float(np.sum(np.abs(g_arr-np.mean(g_arr))>2.5*np.std(g_arr))/len(gaps))
        score = min(100,outliers*220)
        return {"score":round(score,2),"outlier_ratio":round(outliers,3),
                "detail":f"Spacing outliers: {outliers:.1%} {'⚠️' if outliers>0.12 else '✅'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_table_grid(image_path: str) -> dict:
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return {"score":0,"detail":"Cannot read"}
        _,bin_img = cv2.threshold(img,180,255,cv2.THRESH_BINARY_INV)
        h_ker = cv2.getStructuringElement(cv2.MORPH_RECT,(40,1))
        v_ker = cv2.getStructuringElement(cv2.MORPH_RECT,(1,40))
        grid  = cv2.add(cv2.morphologyEx(bin_img,cv2.MORPH_OPEN,h_ker),
                        cv2.morphologyEx(bin_img,cv2.MORPH_OPEN,v_ker))
        cnts,_ = cv2.findContours(grid,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cells  = [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c)>300]
        if len(cells)<2: return {"score":0,"detail":"No table structure found"}
        wvar = float(np.std([c[2] for c in cells]))
        score= min(100,wvar/8)
        return {"score":round(score,2),"cell_count":len(cells),
                "detail":f"{len(cells)} cells, width variance {wvar:.1f} {'⚠️ Irregular' if wvar>40 else '✅ Consistent'}"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_header_footer_pattern(pdf_path: str) -> dict:
    try:
        headers = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                if not words: continue
                top = " ".join(w["text"] for w in words if w["top"]<page.height*0.12)
                headers.append(top)
        if len(set(headers))>2:
            return {"score":40,"detail":"Header inconsistent across pages ⚠️"}
        return {"score":0,"detail":"✅ Header/footer consistent"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_stamp_alignment(image_path: str) -> dict:
    try:
        img = cv2.imread(image_path)
        if img is None: return {"score":0,"detail":"Cannot read"}
        hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
        h,w = img.shape[:2]
        masks = [cv2.inRange(hsv,np.array([100,50,50]),np.array([140,255,255])),
                 cv2.inRange(hsv,np.array([0,50,50]),  np.array([20,255,255]))]
        combined = masks[0]|masks[1]
        cnts,_ = cv2.findContours(combined,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        stamps = [cv2.boundingRect(c) for c in cnts if cv2.contourArea(c)>800]
        if not stamps: return {"score":15,"detail":"No stamp/seal detected (expected on official docs) ⚠️"}
        anom = [f"Stamp in top half (y={s[1]}) ⚠️" for s in stamps if s[1]<h*0.5]
        score= min(100,len(anom)*50)
        return {"score":score,"stamp_count":len(stamps),
                "detail":" | ".join(anom) if anom else f"✅ {len(stamps)} stamp(s) in correct position"}
    except Exception as e:
        return {"score":0,"detail":str(e)}

def check_template_similarity(image_path: str) -> dict:
    """Detect if document looks like a clone/reuse of a standard template."""
    try:
        img = cv2.imread(image_path)
        if img is None: return {"score":0,"detail":"Cannot read"}
        gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        h,w  = gray.shape
        # Check top-center for header logo (common in official templates)
        header_region = gray[:int(h*0.15), int(w*0.2):int(w*0.8)]
        lap = float(np.var(cv2.Laplacian(header_region,cv2.CV_64F)))
        # Well-formatted templates have structured headers
        is_structured = lap > 200
        return {"score":0 if is_structured else 20,
                "detail":"✅ Document has structured header (official template)" if is_structured
                         else "⚠️ Unstructured header — may be low-quality fake"}
    except Exception as e:
        return {"score":0,"detail":str(e)}


def run_layout_intelligence(image_path:str=None, pdf_path:str=None) -> dict:
    results = {}
    if pdf_path:
        r1=check_margin_consistency(pdf_path);   results["margin_consistency"]=r1["score"]; results["margin_detail"]=r1["detail"]
        r2=check_line_alignment(pdf_path);       results["line_alignment"]=r2["score"];     results["line_align_detail"]=r2["detail"]
        r3=check_text_block_spacing(pdf_path);   results["block_spacing"]=r3["score"];      results["block_spacing_detail"]=r3["detail"]
        r5=check_header_footer_pattern(pdf_path);results["header_footer"]=r5["score"];      results["header_footer_detail"]=r5["detail"]
    if image_path:
        r4=check_table_grid(image_path);    results["table_grid"]=r4["score"];    results["table_detail"]=r4["detail"]
        r6=check_stamp_alignment(image_path); results["stamp_alignment"]=r6["score"]; results["stamp_detail"]=r6["detail"]
        r7=check_template_similarity(image_path); results["template_sim"]=r7["score"]; results["template_detail"]=r7["detail"]
    return results
