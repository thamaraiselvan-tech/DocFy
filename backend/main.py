from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, shutil, asyncio
from concurrent.futures import ThreadPoolExecutor

from pipelines.master import run_full_pipeline
from analysis.gemini_report import generate_report
from analysis.a13_to_a17 import ALL_LABELS

app=FastAPI(title="ForgeGuard Pro",version="3.0.0",
            description="17-Category AI Document Forgery Detection System")

app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

os.makedirs("heatmaps",exist_ok=True)
os.makedirs("uploads",exist_ok=True)
app.mount("/heatmaps",StaticFiles(directory="heatmaps"),name="heatmaps")

ALLOWED={".pdf",".jpg",".jpeg",".png"}
executor=ThreadPoolExecutor(max_workers=2)

@app.get("/")
def root():
    return {"message":"ForgeGuard Pro v3.0 ✅","categories":17,"checks":"40+"}

@app.post("/analyse")
async def analyse(file: UploadFile=File(...)):
    fp=None
    try:
        ext=os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED:
            raise HTTPException(400,f"Unsupported: {ext}. Use PDF/JPG/PNG")
        fp=os.path.join("uploads",file.filename)
        with open(fp,"wb") as f: shutil.copyfileobj(file.file,f)
        print(f"\n[API] {file.filename}")

        # Run pipeline in thread pool (non-blocking)
        loop=asyncio.get_event_loop()
        result=await loop.run_in_executor(executor, run_full_pipeline, fp)

        scores     =result["scores"]
        final_score=result["final_score"]
        verdict    =result["verdict"]
        explain    =result["explainability"]
        anomalies  =result["anomalies"]
        ocr_text   =result["ocr_text"]

        # Gemini report
        print("[API] Generating Gemini report...")
        gemini_report=await loop.run_in_executor(executor, generate_report,
            result["file_type"],final_score,verdict,scores,anomalies,ocr_text,
            explain,result.get("doc_type","unknown"))

        # Heatmap URL
        hm=result.get("heatmap")
        hm_url=("/"+hm.replace("\\","/")) if hm and os.path.exists(hm) else None

        return {
            "filename":     file.filename,
            "file_type":    result["file_type"],
            "sub_type":     result.get("sub_type",""),
            "doc_type":     result.get("doc_type","unknown"),
            "doc_confidence":result.get("doc_confidence",0),
            "verdict":      verdict,
            "emoji":        result["emoji"],
            "risk":         result["risk"],
            "final_score":  final_score,
            "quality_score":result.get("quality_score",100),
            "scores":       scores,
            "heatmap":      hm_url,
            "ocr_text":     ocr_text[:500],
            "anomalies":    anomalies,
            "explainability":explain,
            "gemini_report":gemini_report,
            "metadata":     result.get("metadata",{}),
            "logo_detected":result.get("logo_detected",False),
            "logo_detail":  result.get("logo_detail",""),
            "check_labels": ALL_LABELS,
        }
    except HTTPException: raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500,f"Analysis failed: {str(e)}")
    finally:
        if fp and os.path.exists(fp):
            try: os.remove(fp)
            except: pass
