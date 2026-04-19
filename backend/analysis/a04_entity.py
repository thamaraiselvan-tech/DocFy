"""
CATEGORY 4: ENTITY INTELLIGENCE
1. Name consistency across document
2. Institution consistency
3. ID consistency
4. Fuzzy matching (not exact — catches subtle changes)
5. Repeated entity detection
6. Entity frequency anomaly
"""
import re
from collections import Counter

try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

def _fuzzy_sim(a: str, b: str) -> float:
    if not a or not b: return 0.0
    if FUZZY_AVAILABLE:
        return fuzz.ratio(a.lower(), b.lower()) / 100.0
    # Simple fallback: character overlap
    sa, sb = set(a.lower()), set(b.lower())
    return len(sa&sb)/max(len(sa|sb),1)

def extract_all_names(text: str) -> list:
    """Extract all potential person names from text."""
    # Capitalized word sequences (2-4 words)
    pattern = r'\b([A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]{1,15}){1,3})\b'
    candidates = re.findall(pattern, text)
    # Filter common non-names
    stopwords = {"Government","India","Tamil","Nadu","National","Institute",
                 "University","College","Board","Department","Certificate",
                 "Date","Issue","Signature","Authority","Registrar"}
    return [c for c in candidates if not any(w in c for w in stopwords)]

def check_name_consistency(text: str) -> dict:
    """Check if the person's name appears consistently throughout document."""
    names = extract_all_names(text)
    if len(names) < 2:
        return {"score":0,"detail":"Insufficient name occurrences to compare"}
    # Find the most frequent name (likely the real one)
    counter = Counter(names)
    primary = counter.most_common(1)[0][0]
    anomalies = []
    for name in set(names):
        sim = _fuzzy_sim(primary, name)
        if sim < 0.75 and sim > 0.3:  # Similar but not same = suspicious variant
            anomalies.append(f"Name variant '{name}' vs '{primary}' (sim:{sim:.0%}) ⚠️")
    score = min(100, len(anomalies)*35)
    return {"score":score,"primary_name":primary,"name_variants":list(set(names))[:5],
            "anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else f"✅ Name '{primary}' consistent"}

def check_institution_consistency(text: str) -> dict:
    """Check if institution name is used consistently."""
    inst_keywords = r'(?:university|college|institute|board|school|academy)'
    matches = re.findall(
        r'([A-Z][A-Za-z\s]{3,40}(?:University|College|Institute|Board|School))',
        text)
    if len(matches) < 2:
        return {"score":0,"detail":"Single institution reference — cannot check consistency"}
    primary = matches[0]
    anomalies = []
    for m in matches[1:]:
        sim = _fuzzy_sim(primary, m)
        if sim < 0.7:
            anomalies.append(f"Institution mismatch: '{m}' vs '{primary}' ⚠️")
    score = min(100, len(anomalies)*40)
    return {"score":score,"institutions_found":list(set(matches))[:5],"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else "✅ Institution consistent"}

def check_id_consistency(text: str) -> dict:
    """Check if ID/roll/register number appears consistently."""
    # Extract number sequences that look like IDs (5+ digits or alphanumeric)
    ids = re.findall(r'\b([A-Z0-9]{6,20})\b', text)
    ids = [i for i in ids if not i.isalpha()]  # must have digits
    if len(ids) < 2:
        return {"score":0,"detail":"Single ID reference — cannot check consistency"}
    counter = Counter(ids)
    primary = counter.most_common(1)[0][0]
    variants = [i for i in set(ids) if i != primary and _fuzzy_sim(i, primary) > 0.5]
    anomalies = [f"ID variant '{v}' vs primary '{primary}' ⚠️" for v in variants]
    score = min(100, len(anomalies)*50)
    return {"score":score,"primary_id":primary,"anomalies":anomalies,
            "detail":" | ".join(anomalies) if anomalies else f"✅ ID '{primary}' consistent"}

def check_entity_frequency(text: str) -> dict:
    """Detect suspiciously repeated or missing entities."""
    anomalies = []
    words = text.split()
    counter = Counter(words)
    # Numbers repeated many times = suspicious (e.g., same marks everywhere)
    repeated_nums = [(w,c) for w,c in counter.items()
                     if w.isdigit() and len(w)>=2 and c>4]
    for w, c in repeated_nums:
        anomalies.append(f"Number '{w}' appears {c} times ⚠️")
    score = min(100, len(anomalies)*30)
    return {"score":score,"anomalies":anomalies,
            "detail":" | ".join(anomalies[:3]) if anomalies else "✅ No entity frequency anomaly"}


def run_entity_intelligence(text: str) -> dict:
    results = {}
    all_anom = []
    r1 = check_name_consistency(text);        results["name_consistency"] = r1["score"];    results["name_detail"] = r1["detail"];    all_anom+=r1.get("anomalies",[])
    r2 = check_institution_consistency(text); results["inst_consistency"] = r2["score"];    results["inst_detail"] = r2["detail"];    all_anom+=r2.get("anomalies",[])
    r3 = check_id_consistency(text);          results["id_consistency"] = r3["score"];      results["id_detail"] = r3["detail"];      all_anom+=r3.get("anomalies",[])
    r4 = check_entity_frequency(text);        results["entity_frequency"] = r4["score"];    results["freq_detail"] = r4["detail"];    all_anom+=r4.get("anomalies",[])
    results["entity_anomalies"] = all_anom
    return results
