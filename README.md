# Kestrel Home — Service Request Routing Engine

An automated service-request classification and triage system built for **Kestrel Home Appliances** (Pune, India). This project replaces a legacy vendor routing bot (contracted at ₹3.2 Lakh/year) with a self-hosted, calibrated NLP pipeline running locally with zero marginal API cost.

---

## 1. Problem Overview & Findings

Kestrel receives ~700 service requests per month across 7 product lines (Water Purifiers, Air Fryers, Mixer Grinders, Induction Cooktops, Room Heaters, Ceiling Fans, and Robot Vacuums) and 4 communication channels (Chat, WhatsApp, IVR Voice Transcripts, Email).

### The Flaw in the Baseline Bot
An analysis of 18 months of historical tickets (`train.csv` merged with `resolution_log.csv`) revealed that the existing vendor bot achieved only **77.17% routing accuracy**, triggering human transfers on **22.83%** of all inbound cases.

Key systemic failure modes in the baseline bot included:
1. **The "Payment" Trap (Billing Overload):** Customers saying *"paid by EMI"*, *"paid via UPI"*, or *"already paid"* for a repair or installation visit were blindly dumped into the **Billing** queue. In reality, 35.3% of tickets routed to Billing were physical breakdowns or installation queries.
2. **The "Purifier" Trap (Consumables Overload):** Generic purifier breakdowns (e.g., *"purifier not turning on"*, *"buzzing noise"*) were routed to **Consumables** rather than **Repairs**.
3. **Generic Keyword Collisions:** Ambiguous opening lines like *"need help with mixer grinder"* were routed without context.

### Business & Financial Impact
Under Kestrel's Operations Policy (§4):
* Each internal department transfer costs **₹305** in agent handling time.
* Each misrouted ticket generates on average one avoidable customer follow-up contact at **₹260**.
* **Cost per misrouted ticket = ₹565.**
* At ~165 misroutes/month under the vendor bot, Kestrel was incurring **~₹93,500/month (₹11.2 Lakh/year)** in avoidable transfer waste in addition to the **₹3.2 Lakh/year** software license.

---

## 2. Solution Architecture

We built a lightweight, deterministic, and calibrated classification service:

* **Feature Pipeline:**
  * Sublinear word n-grams (1–3) capturing phrase-level intent.
  * Sublinear character n-grams (3–5) capturing spelling variations, typos, and phonetic speech-to-text transcript noise.
  * One-hot encoded categorical metadata (`channel`, `product_family`, `warranty_status`).
* **Classifier:** Calibrated Linear Support Vector Classifier (Primal formulation, Platt scaling calibration) mapping to the 7 canonical department queues:
  * `Installations` (handles installs, demo, wall-mounting)
  * `Repairs` (handles mechanical/electrical faults, breakdown, leaks, noise)
  * `Consumables` (handles filters, candles, membranes, blades, jars)
  * `Billing` (handles double charges, refunds, GST invoices, EMI issues)
  * `Returns & Replacement` (handles transit damage, wrong/missing items, return window)
  * `Warranty Claims` (handles warranty/shield registration, certificate lookup, claim status)
  * `Product Advice` (handles pre/post-purchase usage, recipes, specifications)
* **Policy Reasoning Layer:** Automatically disambiguates payment mentions vs genuine payment disputes per Operations Policy §3, providing actionable human-readable explanations.

---

## 3. Performance & Validation

Evaluated via **5-Fold Stratified Cross-Validation** across all 10,822 historical records using out-of-fold predictions against true resolution outcomes (`final_team`):

```
                       Precision    Recall    F1-Score    Support
-----------------------------------------------------------------
Billing                 0.8711      0.8255     0.8477       1,318
Consumables             0.8824      0.8096     0.8444       1,066
Installations           0.8122      0.8402     0.8260       1,596
Product Advice          0.8647      0.8324     0.8482       1,390
Repairs                 0.8236      0.8919     0.8564       2,534
Returns & Replacement   0.8538      0.8421     0.8479       1,539
Warranty Claims         0.8438      0.8223     0.8329       1,379
-----------------------------------------------------------------
Overall Accuracy                               0.8445      10,822
Macro Average           0.8502      0.8377     0.8434      10,822
```

* **5-Fold CV Accuracy:** **84.45%** (vs 77.17% baseline bot).
* **Misroute Reduction:** **32%** reduction in desk transfers.
* **Inference Latency:** **~3.8 ms** on standard CPU.
* **Inference Cost:** **₹0.00** (Zero external paid API calls).
* **Annualized Net Savings:** **₹6,80,000 / year** (₹3.20L license saved + ₹3.60L handling waste prevented).

---

## 4. Getting Started & Running Locally

### Prerequisites
* Python 3.10+
* pip

### Installation
```bash
# Clone the repository
git clone https://github.com/SubhadeepBhadra/kestrel-home-routing.git
cd kestrel-home-routing

# Install dependencies
pip install -r requirements.txt
```

### Running the Web Service & Dashboard
```bash
python app.py
```

The service will start on **`http://127.0.0.1:8000`**.
* **Interactive Web Dashboard:** Open `http://127.0.0.1:8000` in your browser.
* **OpenAPI / Swagger Documentation:** Open `http://127.0.0.1:8000/docs`.

---

## 5. API Usage

### Single Request Routing: `POST /api/route`

#### cURL Example
```bash
curl -X POST http://127.0.0.1:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "SR510999",
    "channel": "chat",
    "product_family": "Water Purifier",
    "warranty_status": "in_warranty",
    "request_text": "water purifier not turning on, making loud buzzing noise and burnt smell. paid by emi last week please send technician."
  }'
```

#### JSON Response
```json
{
  "request_id": "SR510999",
  "predicted_team": "Repairs",
  "confidence": 0.9807,
  "all_probabilities": {
    "Repairs": 0.9807,
    "Installations": 0.0047,
    "Returns & Replacement": 0.0046,
    "Warranty Claims": 0.0037,
    "Consumables": 0.0032,
    "Billing": 0.0017,
    "Product Advice": 0.0014
  },
  "reasoning": "Routed to Repairs with 98.1% model confidence. Product faults, breakdowns, error codes, noise, leaks, sparking, motor failure - technician repair visits. Key signals identified: Payment Mention Disambiguated (Ops Policy §3: Mentioning 'paid' does not make it a billing request), Physical/Operational Breakdown Keyword Detected. Complies with Ops Policy §3: Operational breakdown or physical defect detected. Requires technician visit.",
  "key_signals": [
    "Payment Mention Disambiguated (Ops Policy §3: Mentioning 'paid' does not make it a billing request)",
    "Physical/Operational Breakdown Keyword Detected"
  ],
  "policy_reference": "Ops Policy §3: Operational breakdown or physical defect detected. Requires technician visit.",
  "team_description": "Product faults, breakdowns, error codes, noise, leaks, sparking, motor failure - technician repair visits.",
  "latency_ms": 3.82
}
```

---

## 6. Training & Reproducibility

If you have the data pack placed in the `data/` directory:
```bash
python train.py --data_dir data --model_out model.joblib --pred_out predictions.csv
```

---

## 7. Repository Structure

```
.
├── app.py                  # Production FastAPI service with policy reasoning
├── train.py                # Standalone training & cross-validation script
├── model.joblib            # Trained calibrated classifier pipeline
├── predictions.csv         # Out-of-sample predictions for test_unlabelled.csv
├── requirements.txt        # Python package dependencies
├── README.md               # Architecture, setup & API documentation
├── evidence.md             # Empirical benchmarks, slice analysis & financial ROI
├── memo_to_ritu.md         # 1-page non-technical executive memo for Ritu Deshpande
├── submission-form.md      # Comprehensive answers to review form questions
└── static/                 # Frontend dashboard assets
    ├── index.html          # Interactive triage dashboard
    ├── style.css           # Glassmorphic UI stylesheet
    └── app.js              # Client-side asynchronous interaction logic
```
