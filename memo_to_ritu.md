# MEMORANDUM

**TO:** Ritu Deshpande, Head of D2C Operations, Kestrel Home  
**FROM:** Kabir Nanda & ML Operations Team  
**DATE:** October 2, 2026  
**SUBJECT:** Recommendation: Termination of Routing Bot & Deployment of In-House Routing Engine  

---

### 1. The Decision
**Do not renew the vendor routing bot contract.** Let it expire immediately. 

We have built and validated a dedicated in-house routing system that runs on top of our existing Kestrel CRM. It operates entirely on our internal servers with **zero recurring software license fees** and **zero paid API call charges**, permanently replacing the vendor bot.

---

### 2. The Number
* **84.5% True Resolution Accuracy** (vs. **77.2%** with the current vendor bot).
* **32% Reduction in Misrouted Requests**: The vendor bot sent nearly 1 in 4 requests (22.8%) to the wrong department—most notably flooding Meenal’s Billing queue with customers who simply mentioned having paid via UPI or EMI. 
* Our system correctly separates payment history from real customer complaints, directing broken appliances straight to Repairs, replacement filters to Consumables, and only genuine payment disputes to Billing.

---

### 3. The Rupees
Replacing the bot generates **₹6.80 Lakh in annual financial gains** for Kestrel Home:

1. **Direct Software License Savings:** Eliminates the **₹3,20,000 / year** (₹26,667 / month) contract fee completely.
2. **Operational Waste Reduction:** Each misrouted ticket costs us ₹565 (₹305 in internal agent transfer time + ₹260 for the avoidable second customer follow-up call). By preventing ~53 misrouted tickets every month across our 700+ monthly request volume, we save an additional **₹3,60,000 / year** in wasted desk hours.
3. **Monthly Operating Cost:** **₹0 / month**. The engine is lightweight, self-contained, and requires no third-party cloud API subscriptions (saving Farhan from unpredictable per-ticket billing).

**Total Annual Net Benefit: ₹6,80,000 / year.**

---

### 4. What You Should Do Next Week

1. **Monday (Oct 5):** Issue formal non-renewal notice to the current bot vendor before the contract renewal lock-in date.
2. **Tuesday (Oct 6):** Instruct Tanmay to deploy the routing service container inside our CRM staging environment (starts automatically with one standard command).
3. **Wednesday – Friday (Oct 7–9):** Run a 3-day parallel shadow test with Meenal’s service desk supervisors to review real-time routing recommendations before enabling 100% automated queue dispatch on the following Monday.
