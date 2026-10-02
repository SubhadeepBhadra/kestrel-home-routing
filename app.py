import os
import re
import sys
import argparse
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

app = FastAPI(title="Kestrel Home Service Routing Service", version="1.0.0")

# Load model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")
if not os.path.exists(MODEL_PATH):
    raise RuntimeError(f"Model file not found at {MODEL_PATH}. Run training first.")

pipeline = joblib.load(MODEL_PATH)

# Team policies and handles
TEAM_DESCRIPTIONS = {
    "Installations": "New-product installation, demo, wall-mounting visits, and unboxing requests.",
    "Repairs": "Product faults, breakdowns, error codes, noise, leaks, sparking, motor failure - technician repair visits.",
    "Consumables": "Filters, candles, membranes, jars, brushes, blades, AMC kits - selling and fitting spares (not product faults).",
    "Billing": "Invoices, GST discrepancies, double charges, refunds of payments, EMI conversions. Only when problem IS the payment.",
    "Returns & Replacement": "Damaged, wrong, missing, or incomplete deliveries; returns and exchanges within return window.",
    "Warranty Claims": "Warranty and Kestrel Shield registration, coverage questions, certificate requests, and claim status.",
    "Product Advice": "Pre- and post-purchase usage questions, recipe advice, power specs, cleaning guidance (no fault reported)."
}

POLICY_RULES = {
    "Installations": "Ops Policy §3/§5: First-time setup, unboxing, wall-mount or installation visit requested.",
    "Repairs": "Ops Policy §3: Operational breakdown or physical defect detected. Requires technician visit.",
    "Consumables": "Ops Policy §3/§5: Request is for consumable replacement/spares purchase, not machine failure.",
    "Billing": "Ops Policy §3: Core issue is payment/financial transaction. (Customer mentioning 'paid' alone does not qualify).",
    "Returns & Replacement": "Ops Policy §3: Delivery damage, missing parts, or request within the return/exchange window.",
    "Warranty Claims": "Ops Policy §3: Warranty/Shield registration, coverage validation, or active claim status.",
    "Product Advice": "Ops Policy §3: General product usage, recipe guidance, or specifications inquiry without defects."
}

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace('â€¦', '...').replace('â€™', "'").replace('â€œ', '"').replace('â€', '"').replace('hélp', 'help')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_reasoning(text: str, product: str, warranty: str, channel: str, predicted_team: str, prob: float) -> tuple[str, List[str]]:
    t = text.lower()
    signals = []
    
    # Check for payment mentions that aren't billing
    has_payment_mention = any(w in t for w in ['paid', 'payment', 'upi', 'emi', 'card', 'already paid', 'paid in full'])
    is_true_billing = any(w in t for w in ['double charge', 'gst invoice', 'refund of payment', 'deducted twice', 'emi conversion', 'invoice copy', 'money deducted'])
    
    if has_payment_mention and not is_true_billing and predicted_team != 'Billing':
        signals.append("Payment Mention Disambiguated (Ops Policy §3: Mentioning 'paid' does not make it a billing request)")

    # Check for repair vs consumable
    if any(w in t for w in ['not working', 'error code', 'spark', 'smoke', 'burnt', 'leak', 'fault', 'noise', 'not heating', 'not turning on', 'tripping']):
        signals.append("Physical/Operational Breakdown Keyword Detected")
    elif any(w in t for w in ['filter', 'candle', 'membrane', 'jar', 'blade', 'brush', 'spares', 'amc kit']):
        signals.append("Consumable/Spare Part Inquiry Detected")
    elif any(w in t for w in ['install', 'demo', 'mounting', 'wall mount', 'unboxing', 'setup']):
        signals.append("Installation/Demo Visit Request Detected")
    elif any(w in t for w in ['damage', 'broken', 'dent', 'scratch', 'missing parts', 'wrong item', 'return pickup']):
        signals.append("Delivery Damage / Missing Item / Return Signal Detected")
    elif any(w in t for w in ['warranty card', 'shield plan', 'register warranty', 'claim status', 'coverage', 'certificate']):
        signals.append("Warranty / Shield Registration or Coverage Claim Signal Detected")
    elif any(w in t for w in ['how to use', 'recipe', 'preset', 'wattage', 'power consumption', 'specs', 'query']):
        signals.append("Usage / Educational Advice Inquiry Detected")

    desc = TEAM_DESCRIPTIONS.get(predicted_team, "")
    policy = POLICY_RULES.get(predicted_team, "")
    
    explanation = f"Routed to **{predicted_team}** with {prob*100:.1f}% model confidence. {desc} "
    if signals:
        explanation += f"Key signals identified: {', '.join(signals)}. "
    explanation += f"Complies with {policy}"
    
    return explanation, signals

class RouteRequest(BaseModel):
    request_id: Optional[str] = Field(default="SR_LIVE_001", description="Service request identifier")
    channel: str = Field(default="chat", description="Inbound channel: ivr | chat | whatsapp | email")
    product_family: str = Field(default="Water Purifier", description="Product category name")
    warranty_status: str = Field(default="in_warranty", description="in_warranty | shield | out_of_warranty")
    request_text: str = Field(..., description="Customer opening message or IVR transcript")

class RouteResponse(BaseModel):
    request_id: str
    predicted_team: str
    confidence: float
    all_probabilities: Dict[str, float]
    reasoning: str
    key_signals: List[str]
    policy_reference: str
    team_description: str
    latency_ms: float

@app.post("/api/route", response_model=RouteResponse)
def route_service_request(req: RouteRequest):
    import time
    t0 = time.perf_counter()
    
    cleaned = clean_text(req.request_text)
    if not cleaned:
        raise HTTPException(status_code=400, detail="request_text cannot be empty")
        
    df = pd.DataFrame([{
        'clean_text': cleaned,
        'channel': req.channel.lower(),
        'product_family': req.product_family,
        'warranty_status': req.warranty_status.lower()
    }])
    
    if hasattr(pipeline, "predict_proba"):
        probs = pipeline.predict_proba(df)[0]
        classes = pipeline.classes_
        prob_dict = {str(c): round(float(p), 4) for c, p in zip(classes, probs)}
        best_idx = np.argmax(probs)
        pred_team = str(classes[best_idx])
        conf = float(probs[best_idx])
    else:
        pred_team = str(pipeline.predict(df)[0])
        conf = 1.0
        prob_dict = {pred_team: 1.0}
        
    latency = round((time.perf_counter() - t0) * 1000, 2)
    reasoning, signals = generate_reasoning(cleaned, req.product_family, req.warranty_status, req.channel, pred_team, conf)
    
    return RouteResponse(
        request_id=req.request_id or "SR_LIVE",
        predicted_team=pred_team,
        confidence=round(conf, 4),
        all_probabilities=prob_dict,
        reasoning=reasoning,
        key_signals=signals,
        policy_reference=POLICY_RULES.get(pred_team, "Ops Policy §3"),
        team_description=TEAM_DESCRIPTIONS.get(pred_team, ""),
        latency_ms=latency
    )

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def get_ui():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Kestrel Router API Running</h1><p>Visit /docs for API documentation.</p>")

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Start Kestrel Home Service Router")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    args = parser.parse_args()

    print(f"Starting Kestrel Home Service Router on http://{args.host}:{args.port} ...")
    uvicorn.run(app, host=args.host, port=args.port)
