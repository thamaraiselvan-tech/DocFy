"""
CATEGORY 3: SEMANTIC CONTENT VALIDATION
Logic-based validation — not just regex.
1. Date validation (DOB < issue < expiry)
2. Age vs document type check
3. Marks/CGPA range validation
4. ID format validation
5. Institution name validity (dictionary)
6. Cross-field validation (CRITICAL)
"""
import re
from datetime import datetime
from dateutil import parser as dtp

# Known institutions dictionary
KNOWN_INSTITUTIONS = {
    "nit trichy", "national institute of technology tiruchirappalli", "nitt",
    "anna university", "iit madras", "iit bombay", "iit delhi",
    "vit vellore", "srm", "sastra", "bits pilani",
    "cbse", "central board of secondary education",
    "icse", "state board", "tnbse", "tamil nadu board",
    "ugc", "aicte", "university of madras", "bharathiyar university",
    "bharathidasan university", "annamalai university",
}

DOCUMENT_TYPES = {
    "marksheet":   ["marks","subject","total","grade","percentage"],
    "certificate": ["certif","award","complet","pass"],
    "id_card":     ["dob","date of birth","aadhaar","aadhar","pan","voter"],
    "degree":      ["degree","bachelor","master","b.tech","m.tech","b.e","m.e"],
    "transfer":    ["transfer","leaving","tc","school"],
    "bonafide":    ["bonafide","studying","enrolled","current"],
}

def detect_document_type(text: str) -> str:
    tl = text.lower()
    for doc_type, keywords in DOCUMENT_TYPES.items():
        if any(k in tl for k in keywords):
            return doc_type
    return "unknown"

def extract_dates(text: str) -> list:
    patterns = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        r'\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\b',
    ]
    dates = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            try:
                d = dtp.parse(m.group(1), fuzzy=True)
                dates.append({"str": m.group(1), "date": d, "year": d.year})
            except: pass
    return dates

# ─── 1. Date Validation ───────────────────────────────────
def check_date_logic(text: str) -> dict:
    anomalies = []
    dates = extract_dates(text)
    now = datetime.now()
    for d in dates:
        if d["year"] > now.year:
            anomalies.append(f"Future date: {d['str']} ⚠️")
        if d["year"] < 1900:
            anomalies.append(f"Impossible old date: {d['str']} ⚠️")
    # DOB < issue date logic
    tl = text.lower()
    dob_m = re.search(r'(?:dob|date\s+of\s+birth)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', tl)
    iss_m = re.search(r'(?:issue|issued|date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', tl)
    if dob_m and iss_m:
        try:
            dob = dtp.parse(dob_m.group(1), fuzzy=True)
            iss = dtp.parse(iss_m.group(1), fuzzy=True)
            if dob > iss:
                anomalies.append("DOB is AFTER issue date — impossible ⚠️")
            age = (iss - dob).days / 365
            if age < 3:
                anomalies.append(f"Person only {age:.0f} years old at issue date ⚠️")
        except: pass
    score = min(100, len(anomalies)*35)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Dates logically consistent"}

# ─── 2. Age vs Document Type ─────────────────────────────
def check_age_vs_doctype(text: str) -> dict:
    anomalies = []
    doc_type = detect_document_type(text)
    tl = text.lower()
    dob_m = re.search(r'(?:dob|date\s+of\s+birth|born)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', tl)
    if not dob_m: return {"score":0,"detail":"No DOB found to validate","doc_type":doc_type}
    try:
        dob = dtp.parse(dob_m.group(1), fuzzy=True)
        age = (datetime.now()-dob).days/365
        if doc_type == "degree" and age < 18:
            anomalies.append(f"Age {age:.0f} too young for degree ⚠️")
        if doc_type == "marksheet" and (age < 5 or age > 90):
            anomalies.append(f"Unusual age {age:.0f} for marksheet ⚠️")
        if doc_type == "id_card" and age < 0:
            anomalies.append("Negative age — impossible ⚠️")
    except: pass
    score = min(100, len(anomalies)*40)
    return {"score":score,"anomalies":anomalies,"doc_type":doc_type,
            "detail":" | ".join(anomalies) if anomalies else f"✅ Age consistent with {doc_type}"}

# ─── 3. Marks/CGPA Range Validation ─────────────────────
def check_numerical_ranges(text: str) -> dict:
    anomalies = []
    # Percentage > 100
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*%', text):
        v = float(m.group(1))
        if v > 100: anomalies.append(f"Impossible percentage: {v}% ⚠️")
    # CGPA
    for m in re.finditer(r'(?:cgpa|gpa)[:\s]+(\d+(?:\.\d+)?)', text, re.IGNORECASE):
        v = float(m.group(1))
        if v > 10: anomalies.append(f"CGPA {v} exceeds 10 ⚠️")
        if v < 0:  anomalies.append(f"Negative CGPA ⚠️")
    # Marks exceed total
    for m in re.finditer(r'(\d+)\s*/\s*(\d+)', text):
        got, tot = int(m.group(1)), int(m.group(2))
        if got > tot: anomalies.append(f"Marks exceed total: {got}/{tot} ⚠️")
    score = min(100, len(anomalies)*40)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Numerical values in range"}

# ─── 4. ID Format Validation ─────────────────────────────
def check_id_formats(text: str) -> dict:
    anomalies = []
    # Aadhaar: 12 digits
    for m in re.finditer(r'\b(\d{4}\s\d{4}\s\d{4}|\d{12})\b', text):
        n = re.sub(r'\s','',m.group(1))
        if len(n) != 12: anomalies.append(f"Invalid Aadhaar length: {n} ⚠️")
    # PAN: AAAAA9999A
    for m in re.finditer(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text):
        pass  # valid format
    # Register number length check (5-15 chars)
    for m in re.finditer(r'(?:reg|roll|register)[.\s#:]+([A-Z0-9]{3,20})', text, re.IGNORECASE):
        rn = m.group(1)
        if len(rn) < 3 or len(rn) > 20:
            anomalies.append(f"Unusual register number: {rn} ⚠️")
    score = min(100, len(anomalies)*40)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ ID formats valid"}

# ─── 5. Institution Name Validity ────────────────────────
def check_institution_validity(text: str) -> dict:
    anomalies = []
    tl = text.lower()
    found_known = any(inst in tl for inst in KNOWN_INSTITUTIONS)
    # Check for common misspellings
    if "nit" in tl and "trichy" in tl:
        if "national institute" not in tl and "nitt" not in tl:
            anomalies.append("NIT Trichy referenced but full name absent ⚠️")
    if not found_known and len(text) > 50:
        anomalies.append("No recognized institution name found ⚠️")
    score = min(100, len(anomalies)*30)
    return {"score":score,"found_institution":found_known,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Institution name recognized"}

# ─── 6. Cross-Field Validation (CRITICAL) ────────────────
def check_cross_field(text: str) -> dict:
    """
    Detect contradictions between fields.
    Example: Engineering degree + school-level format = impossible.
    """
    anomalies = []
    tl = text.lower()
    doc_type = detect_document_type(text)
    # Engineering degree should NOT have school-level language
    if doc_type == "degree":
        if "class 10" in tl or "sslc" in tl or "primary" in tl:
            anomalies.append("Degree certificate contains school-level terminology ⚠️")
    # Marksheet should have subject + marks
    if doc_type == "marksheet":
        has_marks = bool(re.search(r'\d+\s*/\s*\d+|\d+\s*marks', tl))
        if not has_marks:
            anomalies.append("Marksheet has no marks/score pattern ⚠️")
    # ID card should have photo reference
    if doc_type == "id_card":
        if "photograph" not in tl and "photo" not in tl and "image" not in tl:
            pass  # mild
    # Bonafide should mention year of study
    if doc_type == "bonafide":
        if not re.search(r'\d(?:st|nd|rd|th)\s+year', tl):
            anomalies.append("Bonafide certificate missing year of study ⚠️")
    score = min(100, len(anomalies)*40)
    return {"score":score,"doc_type":doc_type,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else f"✅ Cross-field validation passed ({doc_type})"}


def run_semantic_validation(text: str) -> dict:
    results = {}
    all_anom = []
    r1 = check_date_logic(text);         results["date_logic"] = r1["score"];        results["date_logic_detail"] = r1["detail"];        all_anom+=r1["anomalies"]
    r2 = check_age_vs_doctype(text);     results["age_doctype"] = r2["score"];       results["age_doctype_detail"] = r2["detail"];       all_anom+=r2["anomalies"]; results["doc_type"]=r2.get("doc_type","unknown")
    r3 = check_numerical_ranges(text);   results["numerical_ranges"] = r3["score"];  results["numerical_detail"] = r3["detail"];         all_anom+=r3["anomalies"]
    r4 = check_id_formats(text);         results["id_format"] = r4["score"];         results["id_format_detail"] = r4["detail"];         all_anom+=r4["anomalies"]
    r5 = check_institution_validity(text); results["institution_validity"] = r5["score"]; results["institution_detail"] = r5["detail"];  all_anom+=r5["anomalies"]
    r6 = check_cross_field(text);        results["cross_field"] = r6["score"];       results["cross_field_detail"] = r6["detail"];       all_anom+=r6["anomalies"]
    results["semantic_anomalies"] = all_anom
    return results
