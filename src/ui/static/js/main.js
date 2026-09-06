/**
 * Frontend logic for NeoStats Credit Risk Intelligence Platform
 * Handles tab navigation, applicant scoring, SHAP waterfall rendering,
 * and conversational Talk-to-Data chat interactions.
 */

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

  const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
  if (activeBtn) activeBtn.classList.add('active');

  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add('active');
}

// 5 Key Insights Switcher
const INSIGHTS_DATA = {
  1: {
    title: "Insight 1: External Credit Bureau Score Gradient",
    text: "External credit bureau composite scores create a massive monotonic risk gradient. Applicants in the Critical tier (<0.35) suffer a 22.4% default rate, representing a >10x default risk multiplier over Prime borrowers (>0.60, 1.8% default rate).",
    img: "/static/plots/insight1_ext_scores.png"
  },
  2: {
    title: "Insight 2: Debt-to-Income (DTI) & Payment Stress Zones",
    text: "Applicants with Debt-to-Income ratios above 40% experience severe default acceleration (12.4% vs 6.1% for healthy DTI). Monthly annuities exceeding 8% of total credit line create severe liquidity strain.",
    img: "/static/plots/insight2_debt_stress.png"
  },
  3: {
    title: "Insight 3: Age Demographics & Career Tenure",
    text: "Young borrowers under 25 default at nearly 3x the rate of established senior applicants (>50 years). Borrowers with fewer than 1 year of employment tenure carry an elevated 11.2% default likelihood.",
    img: "/static/plots/insight3_age_employment.png"
  },
  4: {
    title: "Insight 4: Educational Attainment Risk Profiling",
    text: "Academic degree holders maintain an exceptional 1.8% default rate versus 10.9% for lower secondary education applicants, demonstrating educational credentialing as a durable credit proxy.",
    img: "/static/plots/insight4_education_income.png"
  },
  5: {
    title: "Insight 5: Past Bureau Delinquency Ripple Effect",
    text: "Any active overdue debt with external financial institutions doubles current default hazard (16.2% vs 8.0%), making prior delinquency the single strongest behavioral red flag.",
    img: "/static/plots/insight5_bureau_delinquency.png"
  },
  0: {
    title: "Data Audit: Missing Values & Class Imbalance",
    text: "The portfolio displays an 11.39:1 class imbalance (91.93% non-default vs 8.07% default). High-missingness columns (e.g., EXT_SOURCE_1 at 56%) are robustly handled by LightGBM's native missing split routing.",
    img: "/static/plots/missing_values.png"
  }
};

function showInsight(id) {
  const data = INSIGHTS_DATA[id];
  if (!data) return;

  document.getElementById('insight-title').textContent = data.title;
  document.getElementById('insight-text').textContent = data.text;
  document.getElementById('insight-img').src = data.img;

  const buttons = document.querySelectorAll('.insight-selector .btn');
  buttons.forEach(btn => {
    if (btn.getAttribute('onclick').includes(`(${id})`)) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

// Pre-loaded Applicant Personas
const PERSONAS = {
  prime: {
    income: 220000, credit: 450000, annuity: 18000, goods: 450000,
    age: 42, employed: 8.5, ext1: 0.72, ext2: 0.68, ext3: 0.70,
    overdue: 0, education: "Higher education", income_type: "State servant"
  },
  borderline: {
    income: 110000, credit: 400000, annuity: 28000, goods: 380000,
    age: 29, employed: 2.5, ext1: 0.42, ext2: 0.45, ext3: 0.38,
    overdue: 0, education: "Secondary / secondary special", income_type: "Working"
  },
  highrisk: {
    income: 60000, credit: 500000, annuity: 32000, goods: 480000,
    age: 22, employed: 0.5, ext1: 0.18, ext2: 0.20, ext3: 0.15,
    overdue: 25000, education: "Lower secondary", income_type: "Working"
  }
};

function loadPersona(type) {
  const p = PERSONAS[type];
  if (!p) return;

  document.getElementById('inp-income').value = p.income;
  document.getElementById('inp-credit').value = p.credit;
  document.getElementById('inp-annuity').value = p.annuity;
  document.getElementById('inp-goods').value = p.goods;
  document.getElementById('inp-age').value = p.age;
  document.getElementById('inp-employed').value = p.employed;
  document.getElementById('inp-ext1').value = p.ext1;
  document.getElementById('inp-ext2').value = p.ext2;
  document.getElementById('inp-ext3').value = p.ext3;
  document.getElementById('inp-overdue').value = p.overdue;
  document.getElementById('inp-education').value = p.education;
  document.getElementById('inp-income-type').value = p.income_type;

  // Trigger scoring automatically
  submitScoring();
}

// Underwriting Scoring Handler
async function submitScoring(event) {
  if (event) event.preventDefault();

  const payload = {
    SK_ID_CURR: 100001,
    AMT_INCOME_TOTAL: parseFloat(document.getElementById('inp-income').value),
    AMT_CREDIT: parseFloat(document.getElementById('inp-credit').value),
    AMT_ANNUITY: parseFloat(document.getElementById('inp-annuity').value),
    AMT_GOODS_PRICE: parseFloat(document.getElementById('inp-goods').value),
    AGE_YEARS: parseFloat(document.getElementById('inp-age').value),
    EMPLOYED_YEARS: parseFloat(document.getElementById('inp-employed').value),
    EXT_SOURCE_1: parseFloat(document.getElementById('inp-ext1').value),
    EXT_SOURCE_2: parseFloat(document.getElementById('inp-ext2').value),
    EXT_SOURCE_3: parseFloat(document.getElementById('inp-ext3').value),
    BUREAU_TOTAL_OVERDUE: parseFloat(document.getElementById('inp-overdue').value),
    NAME_EDUCATION_TYPE: document.getElementById('inp-education').value,
    NAME_INCOME_TYPE: document.getElementById('inp-income-type').value,
    CODE_GENDER: "M",
    NAME_CONTRACT_TYPE: "Cash loans"
  };

  try {
    const resp = await fetch('/api/underwriting/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await resp.json();
    if (result.error) {
      alert('Scoring Error: ' + result.error);
      return;
    }

    renderScoringResult(result);
  } catch (err) {
    console.error("Scoring failed:", err);
  }
}

function renderScoringResult(res) {
  // Update Score & Decision Box
  document.getElementById('res-score').textContent = res.risk_score;
  document.getElementById('res-prob').textContent = (res.calibrated_default_prob * 100).toFixed(2) + '%';
  document.getElementById('res-decision').textContent = res.underwriting_decision;
  document.getElementById('res-rationale').textContent = res.decision_rationale;

  const bandBadge = document.getElementById('res-band-badge');
  bandBadge.textContent = res.risk_band;
  bandBadge.className = 'decision-badge ' + res.badge_color;

  const circle = document.getElementById('score-circle-color');
  circle.className = 'score-circle ' + res.badge_color;

  // Policy flag
  const policyBadge = document.getElementById('res-policy-flag');
  if (res.policy_rules.all_passed) {
    policyBadge.textContent = 'PASSED (All 5 Rules)';
    policyBadge.className = 'badge badge-success';
  } else {
    policyBadge.textContent = `FLAGGED (${res.policy_rules.failed_count} Policy Alerts)`;
    policyBadge.className = 'badge badge-danger';
  }

  // Update SHAP Factor Lists
  const escList = document.getElementById('escalators-list');
  escList.innerHTML = '';
  res.top_risk_escalators.forEach(f => {
    const item = document.createElement('div');
    item.className = 'factor-item';
    item.innerHTML = `
      <span class="factor-name">${f.feature} (Val: ${f.feature_value})</span>
      <span class="factor-val text-danger">+${f.shap_value.toFixed(3)}</span>
    `;
    escList.appendChild(item);
  });

  const redList = document.getElementById('reducers-list');
  redList.innerHTML = '';
  res.top_risk_reducers.forEach(f => {
    const item = document.createElement('div');
    item.className = 'factor-item';
    item.innerHTML = `
      <span class="factor-name">${f.feature} (Val: ${f.feature_value})</span>
      <span class="factor-val text-success">${f.shap_value.toFixed(3)}</span>
    `;
    redList.appendChild(item);
  });

  // Business Bullets
  const bullets = document.getElementById('business-bullets');
  bullets.innerHTML = '';
  res.business_explanations.forEach(b => {
    const li = document.createElement('li');
    li.textContent = b;
    bullets.appendChild(li);
  });

  // Policy Rules Table
  const tbody = document.getElementById('policy-rules-tbody');
  tbody.innerHTML = '';
  res.policy_rules.rules.forEach(r => {
    const tr = document.createElement('tr');
    const statusClass = r.passed ? 'badge-success' : 'badge-danger';
    const statusText = r.passed ? 'PASS' : 'FLAGGED';
    tr.innerHTML = `
      <td><strong>${r.name}</strong></td>
      <td><code>${r.threshold}</code></td>
      <td><strong>${r.value}</strong></td>
      <td><span class="badge ${statusClass}">${statusText}</span></td>
      <td><span class="badge badge-warning">${r.severity}</span></td>
      <td>${r.rationale}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Talk-to-Data Chat Handler
async function sendChatMessage(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  appendUserMessage(question);

  const submitBtn = document.getElementById('chat-submit-btn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Thinking...';

  try {
    const resp = await fetch('/api/talk-to-data/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    const result = await resp.json();
    appendAssistantMessage(result);
  } catch (err) {
    appendErrorMessage("Failed to communicate with Talk-to-Data agent.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Send ↵';
  }
}

function askPreset(q) {
  switchTab('chat-tab');
  document.getElementById('chat-input').value = q;
  sendChatMessage();
}

function appendUserMessage(text) {
  const history = document.getElementById('chat-history');
  const msg = document.createElement('div');
  msg.className = 'chat-message user';
  msg.innerHTML = `
    <div class="msg-body">
      <div class="msg-text">${escapeHtml(text)}</div>
    </div>
    <div class="msg-avatar">👤</div>
  `;
  history.appendChild(msg);
  history.scrollTop = history.scrollHeight;
}

function appendAssistantMessage(res) {
  const history = document.getElementById('chat-history');
  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';

  let tableHtml = '';
  if (res.data && res.data.length > 0) {
    const cols = res.columns || Object.keys(res.data[0]);
    tableHtml = `
      <div class="table-container" style="max-height: 250px; overflow-y: auto; margin-top: 8px;">
        <table class="data-table">
          <thead>
            <tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${res.data.slice(0, 10).map(row => `<tr>${cols.map(c => `<td>${row[c] !== null ? row[c] : 'NULL'}</td>`).join('')}</tr>`).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  msg.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-body">
      <div class="insight-comment">💡 <strong>Insight:</strong> ${escapeHtml(res.business_insight)}</div>
      
      <div class="sql-preview-box">
        <span class="sql-badge">Validated SQLite SELECT</span>
        <code>${escapeHtml(res.sql)}</code>
      </div>

      ${tableHtml}

      <div class="chat-meta">
        <span>⚡ Latency: ${res.execution_time_ms}ms</span>
        <span>•</span>
        <span>Engine: ${res.provider} (${res.tier_used})</span>
      </div>
    </div>
  `;
  history.appendChild(msg);
  history.scrollTop = history.scrollHeight;
}

function appendErrorMessage(errText) {
  const history = document.getElementById('chat-history');
  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';
  msg.innerHTML = `
    <div class="msg-avatar">⚠️</div>
    <div class="msg-body" style="background: #FEE2E2; color: #991B1B;">
      <strong>Error:</strong> ${escapeHtml(errText)}
    </div>
  `;
  history.appendChild(msg);
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Initialize default applicant scoring on page load
window.addEventListener('DOMContentLoaded', () => {
  submitScoring();
});
