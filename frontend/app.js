// ─────────────────────────────────────────────────────────
// CHANGE THIS URL:
// Local development:  http://localhost:8000
// After Render deploy: https://your-app-name.onrender.com
// ─────────────────────────────────────────────────────────
const API = "http://localhost:8000";
const STEPS=["📁 Input analysis & quality check","📝 OCR extraction (Tamil+English)","🔢 Semantic content validation","🧩 Entity intelligence (fuzzy match)","🖼️ Image forensics (ELA+9 checks)","📐 Layout intelligence","📄 PDF forensics","🗂️ Metadata forensics","✍️ Signature & stamp analysis","📱 QR/barcode validation","🌐 Language & OCR quality","🔁 Duplication detection","🔗 Cross-modal consistency","📊 Confidence scoring","🧠 Explainability layer","⚡ Pipeline robustness","🔥 Document classification & logo detection + Gemini report"];

document.getElementById("fi").addEventListener("change",function(){
  if(this.files[0]){document.getElementById("fn").textContent=this.files[0].name;document.getElementById("ab").disabled=false}
});

async function go(){
  const file=document.getElementById("fi").files[0]; if(!file)return;
  show("loading"); buildSteps(); animSteps();
  try{
    const fd=new FormData(); fd.append("file",file);
    const res=await fetch(`${API}/analyse`,{method:"POST",body:fd});
    if(!res.ok){const e=await res.json();throw new Error(e.detail||"Failed")}
    R=await res.json(); render(R); show("results");
  }catch(e){alert("Error: "+e.message);show("upload")}
}

function buildSteps(){
  const c=document.getElementById("steps"); c.innerHTML="";
  STEPS.forEach((s,i)=>{const d=document.createElement("div");d.className="step";d.id="st"+i;d.textContent=s;c.appendChild(d)})
}

function animSteps(){
  let i=0;
  const iv=setInterval(()=>{
    if(i>0)document.getElementById("st"+(i-1)).className="step done";
    const el=document.getElementById("st"+i);
    if(el){el.className="step active";i++}else clearInterval(iv);
  },900);
}

function render(r){
  // Verdict
  const vc=document.getElementById("vc"); vc.className="verdict-card verdict-"+r.verdict;
  document.getElementById("ve").textContent=r.emoji;
  document.getElementById("vl").textContent=r.verdict;
  document.getElementById("dt").textContent=(r.doc_type||"unknown").replace(/_/g," ").toUpperCase()+(r.doc_confidence?` (${r.doc_confidence}% conf)`:"");
  document.getElementById("fs").textContent=r.final_score;
  document.getElementById("qs").textContent=r.quality_score||100;
  const rb=document.getElementById("rb"); rb.textContent="RISK: "+r.risk; rb.className="rbadge risk-"+r.risk;
  setTimeout(()=>document.getElementById("sf").style.width=r.final_score+"%",100);
  // Heatmap
  const hc=document.getElementById("hc");
  hc.innerHTML=r.heatmap?`<img src="${API}${r.heatmap}" alt="ELA Heatmap"/>`:`<p class="muted">No heatmap available</p>`;
  // Top risks
  const tr=document.getElementById("tr");
  const risks=r.explainability?.top_risk_factors||[];
  tr.innerHTML=risks.length?risks.map(x=>{
    const l=x.score>60?"H":x.score>30?"M":"L";
    const c=l==="H"?"#f87171":l==="M"?"#fbbf24":"#4ade80";
    return`<div class="ri ${l}"><span style="font-size:12px;color:#c0c8d8">${x.check}</span><span style="font-size:13px;font-weight:700;color:${c}">${Math.round(x.score)}/100</span></div>`;
  }).join(""):`<p class="muted">✅ No major risks</p>`;
  // Doc intelligence
  const di=document.getElementById("di");
  di.innerHTML=`<div style="font-size:12px;color:#c0c8d8;line-height:1.8">
    ${r.logo_detected?`<div>✅ Institution logo/emblem detected</div>`:`<div>⚠️ No logo detected</div>`}
    ${r.logo_detail?`<div style="color:#8892a4;font-size:11px">${r.logo_detail}</div>`:""}
  </div>`;
  // Sections
  const sa=document.getElementById("sa");
  const secs=r.explainability?.section_analysis||{};
  sa.innerHTML=Object.entries(secs).map(([nm,d])=>{
    const inner=Object.entries(d.checks).map(([cn,cs])=>{
      const l=cs>60?"H":cs>30?"M":"L";
      return`<div class="ci l-${l}"><div class="cr"><span class="cn">${cn}</span><span class="cs">${cs}/100</span></div><div class="cb"><div class="cf" style="width:${cs}%"></div></div></div>`;
    }).join("");
    return`<div class="sg"><div class="sh" onclick="tog(this)"><span class="sn">${nm}</span><span class="sa2 ${d.risk}">${d.average}/100 — ${d.risk}</span></div><div class="sb2">${inner}</div></div>`;
  }).join("")||`<p class="muted">No section data</p>`;
  // All checks
  const cl=document.getElementById("cl");
  const lbs=r.check_labels||{};
  cl.innerHTML=Object.entries(r.scores||{})
    .filter(([k,v])=>typeof v==="number")
    .sort(([,a],[,b])=>b-a)
    .map(([k,v])=>{
      const lb=lbs[k]||k.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
      const l=v>60?"H":v>30?"M":"L";
      return`<div class="ci l-${l}"><div class="cr"><span class="cn">${lb}</span><span class="cs">${Math.round(v)}/100</span></div><div class="cb"><div class="cf" style="width:${v}%"></div></div></div>`;
    }).join("")||`<p class="muted">No checks</p>`;
  // Anomalies
  const al=document.getElementById("al");
  al.innerHTML=(r.anomalies||[]).length?(r.anomalies||[]).map(a=>`<div class="an">${a}</div>`).join(""):`<p style="color:#4ade80;font-size:13px">✅ No anomalies detected</p>`;
  // Report
  document.getElementById("rt").textContent=r.gemini_report||"No report generated";
  document.getElementById("ot").textContent=r.ocr_text||"No text extracted";
  // Metadata
  const md=document.getElementById("md");
  const meta=r.metadata||{};
  if(Object.keys(meta).length){
    md.innerHTML=Object.entries(meta).map(([k,v])=>`<div class="mrow"><span class="mk">${k}</span><span class="mv">${v||"N/A"}</span></div>`).join("");
    document.getElementById("mc").classList.remove("hidden");
  }else document.getElementById("mc").classList.add("hidden");
}

function tog(el){el.nextElementSibling.classList.toggle("open")}
function show(n){["upload","loading","results"].forEach(s=>document.getElementById(s+"Section").classList.add("hidden"));document.getElementById(n+"Section").classList.remove("hidden")}
function reset(){document.getElementById("fi").value="";document.getElementById("fn").textContent="No file chosen";document.getElementById("ab").disabled=true;R=null;show("upload")}
function dl(){
  if(!R)return;
  const txt=`FORGEGUARD PRO v3.0 — DOCUMENT FORENSICS REPORT\n${"=".repeat(55)}\nFile: ${R.filename}\nType: ${(R.file_type||"").toUpperCase()} (${R.sub_type||""})\nDocument: ${(R.doc_type||"unknown").replace(/_/g," ").toUpperCase()}\nVerdict: ${R.verdict} ${R.emoji}\nScore: ${R.final_score}/100\nRisk: ${R.risk}\nQuality: ${R.quality_score}/100\n\nTOP RISKS:\n${(R.explainability?.top_risk_factors||[]).map(x=>`  - ${x.check}: ${Math.round(x.score)}/100`).join("\n")||"  None"}\n\nANOMALIES:\n${(R.anomalies||[]).map(a=>`  - ${a}`).join("\n")||"  None"}\n\nAI REPORT:\n${R.gemini_report||"N/A"}\n\nEXTRACTED TEXT:\n${R.ocr_text||"N/A"}\n\nForgeGuard Pro v3.0 | ThinkRoot × Vortex 2026 | NIT Trichy`;
  const a=Object.assign(document.createElement("a"),{href:URL.createObjectURL(new Blob([txt],{type:"text/plain"})),download:"forgeguard_report.txt"});
  a.click();
}
