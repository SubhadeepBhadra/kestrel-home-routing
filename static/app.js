document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("routing-form");
  const requestIdInput = document.getElementById("request_id");
  const channelSelect = document.getElementById("channel");
  const productSelect = document.getElementById("product_family");
  const warrantySelect = document.getElementById("warranty_status");
  const requestTextArea = document.getElementById("request_text");
  
  const loadingState = document.getElementById("loading-state");
  const decisionContent = document.getElementById("decision-content");
  const latencyTag = document.getElementById("latency-tag");
  const predictedTeamEl = document.getElementById("predicted-team");
  const teamDescEl = document.getElementById("team-desc");
  const confidenceValEl = document.getElementById("confidence-val");
  const reasoningTextEl = document.getElementById("reasoning-text");
  const policyTextEl = document.getElementById("policy-text");
  const probBarsContainer = document.getElementById("prob-bars");
  const resetBtn = document.getElementById("reset-btn");

  const teamColors = {
    "Repairs": "#ef4444",
    "Installations": "#3b82f6",
    "Consumables": "#10b981",
    "Billing": "#f59e0b",
    "Returns & Replacement": "#8b5cf6",
    "Warranty Claims": "#06b6d4",
    "Product Advice": "#ec4899"
  };

  const presets = {
    repair_paid: {
      channel: "chat",
      product: "Water Purifier",
      warranty: "in_warranty",
      text: "water purifier not turning on, making buzzing noise and burnt smell. paid by emi last week please send technician."
    },
    consumable: {
      channel: "whatsapp",
      product: "Water Purifier",
      warranty: "out_of_warranty",
      text: "need to replace sediment and carbon filter candle set for my ro purifier. what is price and how to order?"
    },
    true_billing: {
      channel: "email",
      product: "Air Fryer",
      warranty: "in_warranty",
      text: "my account was charged twice for order KO2609812 on my hdfc card. kindly process the duplicate refund immediately and send updated gst invoice."
    },
    install: {
      channel: "ivr",
      product: "Induction Cooktop",
      warranty: "in_warranty",
      text: "good morning, received induction cooktop yesterday, need technician visit for wall mounting and demo at my home."
    },
    return_damage: {
      channel: "chat",
      product: "Mixer Grinder",
      warranty: "in_warranty",
      text: "received mixer grinder with broken jar lid and cracked base right out of the delivery box. request immediate return pickup and exchange."
    },
    warranty: {
      channel: "whatsapp",
      product: "Robot Vacuum",
      warranty: "shield",
      text: "hello, bought kestrel shield 2 year plan yesterday. need to register warranty certificate and verify coverage policy."
    }
  };

  // Preset buttons
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const p = presets[btn.dataset.preset];
      if (p) {
        channelSelect.value = p.channel;
        productSelect.value = p.product;
        warrantySelect.value = p.warranty;
        requestTextArea.value = p.text;
        requestIdInput.value = `SR-TEST-${Math.floor(100000 + Math.random() * 900000)}`;
        submitForm();
      }
    });
  });

  resetBtn.addEventListener("click", () => {
    form.reset();
    requestIdInput.value = `SR-LIVE-${Math.floor(100000 + Math.random() * 900000)}`;
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitForm();
  });

  async function submitForm() {
    const payload = {
      request_id: requestIdInput.value.trim() || "SR-LIVE",
      channel: channelSelect.value,
      product_family: productSelect.value,
      warranty_status: warrantySelect.value,
      request_text: requestTextArea.value.trim()
    };

    if (!payload.request_text) return;

    loadingState.style.display = "flex";
    decisionContent.style.opacity = "0.3";
    latencyTag.textContent = "Routing...";

    try {
      const resp = await fetch("/api/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Routing request failed");
      }

      const data = await resp.json();
      renderDecision(data);
    } catch (err) {
      alert("Error routing request: " + err.message);
    } finally {
      loadingState.style.display = "none";
      decisionContent.style.opacity = "1";
    }
  }

  function renderDecision(data) {
    latencyTag.textContent = `Inference: ${data.latency_ms} ms`;
    
    // Team badge & color
    predictedTeamEl.textContent = data.predicted_team;
    const color = teamColors[data.predicted_team] || "#6366f1";
    predictedTeamEl.style.color = color;
    teamDescEl.textContent = data.team_description;

    // Confidence
    const pct = (data.confidence * 100).toFixed(1);
    confidenceValEl.textContent = `${pct}%`;
    const ring = document.querySelector(".gauge-ring");
    if (ring) {
      ring.style.background = `conic-gradient(${color} 0% ${pct}%, rgba(255, 255, 255, 0.08) ${pct}% 100%)`;
      ring.style.boxShadow = `0 0 15px ${color}40`;
    }

    // Reasoning and Policy
    reasoningTextEl.innerHTML = data.reasoning.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    policyTextEl.textContent = data.policy_reference;

    // Probabilities
    probBarsContainer.innerHTML = "";
    const sortedProbs = Object.entries(data.all_probabilities).sort((a, b) => b[1] - a[1]);

    sortedProbs.forEach(([team, prob]) => {
      const probPct = (prob * 100).toFixed(1);
      const itemColor = teamColors[team] || "#6366f1";
      const isTop = team === data.predicted_team;

      const item = document.createElement("div");
      item.className = "prob-item";
      item.innerHTML = `
        <span class="prob-name" style="${isTop ? `color: ${itemColor}; font-weight: 700;` : ''}">${team}</span>
        <div class="prob-bar-track">
          <div class="prob-bar-fill" style="width: ${probPct}%; background: ${itemColor};"></div>
        </div>
        <span class="prob-pct">${probPct}%</span>
      `;
      probBarsContainer.appendChild(item);
    });
  }

  // Auto trigger initial route on load
  submitForm();
});
