"""Gemini AI Report Generation"""
import google.generativeai as genai
import os, json

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_report(file_type,final_score,verdict,scores,anomalies,ocr_text,explain,doc_type) -> str:
    try:
        model=genai.GenerativeModel("gemini-1.5-flash")
        high={k:v for k,v in scores.items() if isinstance(v,(int,float)) and v>60}
        top=explain.get("top_risk_factors",[])
        prompt=f"""
You are a senior document forensics expert.
Analyse this automated forgery detection report and write a clear, professional report.

DOCUMENT TYPE: {doc_type.replace('_',' ').title()} ({file_type.upper()})
FORGERY SCORE: {final_score}/100
VERDICT: {verdict}

TOP RISK FACTORS:
{json.dumps(top[:5],indent=2)}

HIGH-RISK CHECKS (>60):
{json.dumps(high,indent=2) if high else 'None'}

ANOMALIES ({len(anomalies)} found):
{chr(10).join(f'- {a}' for a in anomalies[:8]) if anomalies else 'None'}

OCR TEXT SAMPLE:
{ocr_text[:300] if ocr_text else 'No text extracted'}

Write a structured forensics report with these sections:
EXECUTIVE SUMMARY: (2-3 sentences on overall authenticity)
KEY FINDINGS: (bullet points — only checks scoring above 40)
SUSPICIOUS REGIONS: (which parts of document are tampered and why)
RISK ASSESSMENT: (why this score/verdict)
RECOMMENDED ACTION: (specific steps for verification officer)

Be clear, professional, non-technical where possible. No markdown symbols.
"""
        return genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt).text
    except Exception as e:
        return _fallback(final_score,verdict,scores,anomalies)

def _fallback(score,verdict,scores,anomalies):
    high=[k for k,v in scores.items() if isinstance(v,(int,float)) and v>60]
    lines=[f"FORGEGUARD PRO — REPORT","="*40,f"Verdict: {verdict}",f"Score: {score}/100",""]
    if verdict=="GENUINE": lines.append("Document passed all major checks.")
    elif verdict=="SUSPICIOUS": lines.append("Document shows anomalies requiring review.")
    else: lines.append(f"Multiple forgery indicators across {len(high)} checks.")
    if high: lines+=["","HIGH RISK:"]+[f"  - {k}: {scores[k]:.0f}/100" for k in high[:5]]
    if anomalies: lines+=["","ANOMALIES:"]+[f"  - {a}" for a in anomalies[:6]]
    lines+=["","RECOMMENDATION:","Contact issuing institution to verify." if verdict!="GENUINE" else "Standard verification applies."]
    return "\n".join(lines)
