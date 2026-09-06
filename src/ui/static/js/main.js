/**
 * Credit Risk Intelligence Platform — Client-Side Application Controller
 * Handles 5-tab switching, Chart.js visualizations (bureau bar, portfolio donut, diverging SHAP),
 * Underwriting Simulator, Explainable AI profile sync, Credit Policy Rules audit,
 * Talk-to-Data conversational NL-to-SQL integration.
 */

// ============================================================================
// 1. Centralized Application State
// ============================================================================
const AppState = {
  currentApplicantId: null,
  currentApplicantLabel: "Manual profile",
  currentApplicantData: null,
  lastScoringResult: null,
  scoringRequestId: 0,
  activeSimulatorSubtab: 'manual',
  activeRiskFactorTab: 'decreases',
  charts: {
    bureauBar: null,
    portfolioDonut: null,
    shapDiverging: null
  }
};

// ============================================================================
// 2. Applicant Presets & Real Out-of-Sample Test Records
// ============================================================================
const TEST_APPLICANTS = {
  100001: {
    id: 100001,
    income: 135000,
    credit: 568800,
    annuity: 20560.5,
    goods: 450000,
    age: 52.7,
    employed: 6.4,
    gender: "Female",
    ext1: 0.753,
    ext2: 0.790,
    ext3: 0.160,
    overdue: 0,
    education: "Higher education",
    income_type: "Working",
    family: "Married",
    housing: "House / apartment",
    contract: "Cash loans",
    label: "Applicant #100001 (Unseen application_test.csv)"
  },
  100005: {
    id: 100005,
    income: 99000,
    credit: 222768,
    annuity: 17370,
    goods: 180000,
    age: 49.5,
    employed: 12.2,
    gender: "Male",
    ext1: 0.565,
    ext2: 0.292,
    ext3: 0.433,
    overdue: 0,
    education: "Secondary / secondary special",
    income_type: "Working",
    family: "Married",
    housing: "House / apartment",
    contract: "Cash loans",
    label: "Applicant #100005 (Unseen application_test.csv)"
  },
  100013: {
    id: 100013,
    income: 202500,
    credit: 663264,
    annuity: 69777,
    goods: 630000,
    age: 54.9,
    employed: 12.2,
    gender: "Male",
    ext1: 0.500,
    ext2: 0.700,
    ext3: 0.611,
    overdue: 0,
    education: "Higher education",
    income_type: "Working",
    family: "Married",
    housing: "House / apartment",
    contract: "Cash loans",
    label: "Applicant #100013 (Unseen application_test.csv)"
  },
  100028: {
    id: 100028,
    income: 315000,
    credit: 1575000,
    annuity: 49018.5,
    goods: 1575000,
    age: 38.3,
    employed: 5.1,
    gender: "Female",
    ext1: 0.526,
    ext2: 0.510,
    ext3: 0.613,
    overdue: 0,
    education: "Secondary / secondary special",
    income_type: "Working",
    family: "Married",
    housing: "House / apartment",
    contract: "Cash loans",
    label: "Applicant #100028 (Unseen application_test.csv)"
  }
};

// ============================================================================
// 3. Tab Switching Engine
// ============================================================================
function switchTab(tabId) {
  if (tabId === 'chat-tab') {
    toggleChatPanel(true);
    return;
  }

  // Update button active state
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {
      btn.classList.add('active');
    }
  });

  // Update section active state
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });

  const targetTab = document.getElementById(tabId);
  if (targetTab) {
    targetTab.classList.add('active');
    requestAnimationFrame(() => revealMotionItems(targetTab));
  }

  // Handle Chart.js resizing on tab activation
  if (tabId === 'eda-tab') {
    if (AppState.charts.bureauBar) AppState.charts.bureauBar.resize();
    if (AppState.charts.portfolioDonut) AppState.charts.portfolioDonut.resize();
  } else if (tabId === 'xai-tab') {
    if (AppState.charts.shapDiverging) AppState.charts.shapDiverging.resize();
  }

}

function toggleChatPanel(isOpen) {
  const panel = document.getElementById('chat-tab');
  const launcher = document.querySelector('.chat-launcher');
  if (!panel) return;

  panel.classList.toggle('is-open', isOpen);
  panel.setAttribute('aria-hidden', String(!isOpen));
  if (launcher) launcher.setAttribute('aria-expanded', String(isOpen));

  if (isOpen) {
    requestAnimationFrame(() => document.getElementById('chat-input')?.focus());
  }
}

function revealMotionItems(root) {
  if (!root) return;
  root.querySelectorAll('[data-motion-item]').forEach((item, index) => {
    item.style.setProperty('--motion-delay', `${Math.min(index * 55, 330)}ms`);
    item.classList.add('is-visible');
  });
}

function initializeMotion() {
  const motionItems = document.querySelectorAll(
    '.page-heading, .metric-card, .card, .supporting-card, .insight-panel-simple'
  );
  motionItems.forEach((item) => item.setAttribute('data-motion-item', ''));

  if (!('IntersectionObserver' in window)) {
    motionItems.forEach((item) => item.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        currentObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  motionItems.forEach((item) => observer.observe(item));
  revealMotionItems(document.querySelector('.tab-content.active'));
}

// ============================================================================
// 4. Tab 1: Chart.js Visualizations (Bureau Bar & Portfolio Donut)
// ============================================================================
function initEdaCharts() {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js is unavailable; continuing without portfolio charts.');
    return;
  }
  // Chart 1: Default Rate by External Bureau Score Tier
  const bureauCtx = document.getElementById('bureauTierChart');
  if (bureauCtx && !AppState.charts.bureauBar) {
    AppState.charts.bureauBar = new Chart(bureauCtx, {
      type: 'bar',
      data: {
        labels: [
          'Critical (<0.35)',
          'Subprime (0.35–0.50)',
          'Prime (0.50–0.65)',
          'Super-Prime (>0.65)'
        ],
        datasets: [{
          label: 'Default Rate (%)',
          data: [23.1, 12.2, 5.9, 2.9],
          backgroundColor: [
            '#C94A45', // Critical: muted red
            '#C58A28', // Subprime: warm amber
            '#4779A8', // Prime: muted blue
            '#078A63'  // Super-Prime: emerald
          ],
          borderColor: [
            '#A83E3A',
            '#A8792F',
            '#385F86',
            '#056B4D'
          ],
          borderWidth: 1.5,
          borderRadius: 6,
          barPercentage: 0.65
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#211F1B',
            titleColor: '#FFFCF7',
            bodyColor: '#FFFCF7',
            titleFont: { family: 'Inter', size: 12, weight: '600' },
            bodyFont: { family: 'Inter', size: 12 },
            padding: { top: 8, bottom: 8, left: 12, right: 12 },
            cornerRadius: 6,
            displayColors: false,
            borderWidth: 1,
            borderColor: 'rgba(232, 213, 173, 0.35)',
            callbacks: {
              label: (context) => ` Default Rate: ${context.raw}%`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 26,
            ticks: {
              callback: (val) => val + '%',
              font: { family: 'Inter', size: 11 },
              color: '#64748B'
            },
            grid: {
              color: '#F1F5F9'
            },
            border: {
              color: '#E2E8F0'
            }
          },
          x: {
            ticks: {
              font: { family: 'Inter', size: 11, weight: '600' },
              color: '#334155'
            },
            grid: { display: false },
            border: {
              color: '#E2E8F0'
            }
          }
        }
      }
    });
  }

  // Chart 2: Portfolio Composition Donut Chart
  const donutCtx = document.getElementById('portfolioDonutChart');
  if (donutCtx && !AppState.charts.portfolioDonut) {
    AppState.charts.portfolioDonut = new Chart(donutCtx, {
      type: 'doughnut',
      data: {
        labels: ['Non-Default (91.9%)', 'Default (8.1%)'],
        datasets: [{
          data: [282686, 24825],
          backgroundColor: ['#078A63', '#C94A45'],
          borderColor: ['#FFFFFF', '#FFFFFF'],
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#211F1B',
            titleColor: '#FFFCF7',
            bodyColor: '#FFFCF7',
            titleFont: { family: 'Inter', size: 12, weight: '600' },
            bodyFont: { family: 'Inter', size: 12 },
            padding: { top: 8, bottom: 8, left: 12, right: 12 },
            cornerRadius: 6,
            displayColors: false,
            borderWidth: 1,
            borderColor: 'rgba(232, 213, 173, 0.35)',
            callbacks: {
              label: (context) => {
                const total = 307511;
                const count = context.raw;
                const pct = ((count / total) * 100).toFixed(1);
                return ` ${context.label}: ${count.toLocaleString()} loans (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }
}

// ============================================================================
// 5. Tab 2 & 3: Applicant Loading & Synchronization
// ============================================================================
function switchSimulatorSubtab(subtab) {
  AppState.activeSimulatorSubtab = subtab;
  const manualBtn = document.getElementById('subtab-manual-btn');
  const quickloadBtn = document.getElementById('subtab-quickload-btn');
  const quickDrawer = document.getElementById('quickload-panel');

  if (subtab === 'manual') {
    manualBtn.classList.add('active');
    quickloadBtn.classList.remove('active');
    if (quickDrawer) quickDrawer.style.display = 'none';
  } else {
    manualBtn.classList.remove('active');
    quickloadBtn.classList.add('active');
    if (quickDrawer) quickDrawer.style.display = 'block';
  }
}

function loadTestApplicant(id) {
  const applicant = TEST_APPLICANTS[id];
  if (!applicant) return;
  populateApplicantProfile(applicant);
}

function populateApplicantProfile(p) {
  AppState.currentApplicantId = p.id;
  AppState.currentApplicantLabel = p.label;
  AppState.currentApplicantData = p;
  clearScoringResult(`Loaded · ${p.label} — review values, then predict risk.`);

  // Populate Tab 2 Form Inputs
  setInputValue('inp-income', p.income);
  setInputValue('inp-credit', p.credit);
  setInputValue('inp-annuity', p.annuity);
  setInputValue('inp-goods', p.goods);
  setInputValue('inp-age', p.age);
  setInputValue('inp-employed', p.employed);
  setInputValue('inp-ext1', p.ext1);
  setInputValue('inp-ext2', p.ext2);
  setInputValue('inp-ext3', p.ext3);
  setInputValue('inp-overdue', p.overdue);
  setInputValue('inp-education', p.education);
  setInputValue('inp-income-type', p.income_type);
  if (p.family) setInputValue('inp-family', p.family);
  if (p.contract) setInputValue('inp-contract', p.contract);
  if (p.housing) setInputValue('inp-housing', p.housing);

  // Synchronize Tab 3 Summary Sheet
  updateSummarySheet(p);

}

function setInputValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function updateSummarySheet(p) {
  const extMean = ((p.ext1 + p.ext2 + p.ext3) / 3).toFixed(3);
  setTextContent('xai-sheet-id', `#${p.id}`);
  setTextContent('xai-sheet-age', `${p.age} Years`);
  setTextContent('xai-sheet-gender', p.gender || 'Male');
  setTextContent('xai-sheet-income', `$${Number(p.income).toLocaleString()}`);
  setTextContent('xai-sheet-employed', `${p.employed} Years`);
  setTextContent('xai-sheet-credit', `$${Number(p.credit).toLocaleString()}`);
  setTextContent('xai-sheet-annuity', `$${Number(Math.round(p.annuity)).toLocaleString()}`);
  setTextContent('xai-sheet-contract', p.contract || 'Cash loans');
  setTextContent('xai-sheet-ext', extMean);
}

function resetForm() {
  const form = document.getElementById('scoring-form');
  if (form) form.reset();
  syncManualApplicantProfile();
  clearScoringResult('Form reset. Select Predict Risk when the applicant details are ready.');
}

function syncManualApplicantProfile() {
  const readNumber = (id, fallback = 0) => {
    const value = Number.parseFloat(document.getElementById(id)?.value);
    return Number.isFinite(value) ? value : fallback;
  };
  const preservedGender = AppState.currentApplicantData?.gender;
  const profile = {
    id: 'manual',
    label: 'Manual profile',
    income: readNumber('inp-income'),
    credit: readNumber('inp-credit'),
    annuity: readNumber('inp-annuity'),
    goods: readNumber('inp-goods'),
    age: readNumber('inp-age'),
    employed: readNumber('inp-employed'),
    gender: preservedGender === 'Female' || preservedGender === 'Male' ? preservedGender : '—',
    ext1: readNumber('inp-ext1'),
    ext2: readNumber('inp-ext2'),
    ext3: readNumber('inp-ext3'),
    overdue: readNumber('inp-overdue'),
    contract: document.getElementById('inp-contract')?.value || 'Cash loans'
  };
  AppState.currentApplicantId = null;
  AppState.currentApplicantLabel = profile.label;
  AppState.currentApplicantData = profile;
  updateSummarySheet(profile);
  setTextContent('xai-profile-status', 'Manual profile is ready. Select Predict Risk to generate the explanation.');
}

function clearScoringResult(message) {
  AppState.scoringRequestId += 1;
  AppState.lastScoringResult = null;

  const resultContent = document.getElementById('scoring-result-content');
  if (resultContent) resultContent.hidden = true;

  const placeholder = document.getElementById('scoring-placeholder');
  if (placeholder) {
    placeholder.hidden = false;
    placeholder.classList.add('is-compact');
    placeholder.textContent = message;
  }

  setTextContent('res-applicant-id', `Awaiting scoring: ${AppState.currentApplicantLabel}`);
  const xaiStatus = document.getElementById('xai-profile-status');
  if (xaiStatus) {
    xaiStatus.classList.remove('is-scored');
    xaiStatus.textContent = message;
  }
  if (AppState.currentApplicantData) {
    updateSummarySheet(AppState.currentApplicantData);
  } else {
    resetSummarySheet();
  }

  const factors = document.getElementById('risk-factors-container');
  if (factors) factors.innerHTML = '';

  const policyRules = document.getElementById('policy-rules-tbody');
  if (policyRules) policyRules.innerHTML = '';

  setTextContent('xai-score', '—');
  setTextContent('xai-prob', '—');
  setTextContent('xai-base-val', '—');
  const xaiBand = document.getElementById('xai-band');
  if (xaiBand) {
    xaiBand.textContent = 'Not scored';
    xaiBand.className = 'badge badge-neutral';
  }

  function resetSummarySheet() {
    const emptyFields = {
      'xai-sheet-id': '—',
      'xai-sheet-age': '—',
      'xai-sheet-gender': '—',
      'xai-sheet-income': '—',
      'xai-sheet-employed': '—',
      'xai-sheet-credit': '—',
      'xai-sheet-annuity': '—',
      'xai-sheet-contract': '—',
      'xai-sheet-ext': '—'
    };
    Object.entries(emptyFields).forEach(([id, value]) => setTextContent(id, value));
  }
  setHtmlContent('interp-strength-text', 'Run <strong>Predict Risk</strong> in the Underwriting Simulator to generate this applicant\'s assessment.');
  setHtmlContent('interp-vulnerability-text', 'Run <strong>Predict Risk</strong> in the Underwriting Simulator to generate this applicant\'s assessment.');
  setHtmlContent('interp-recommendation-text', 'A recommendation will appear after the applicant is scored.');

  if (AppState.charts.shapDiverging) {
    AppState.charts.shapDiverging.destroy();
    AppState.charts.shapDiverging = null;
  }
}

// ============================================================================
// 6. Dynamic Underwriting Scoring & API Integration (/api/v1/predict)
// ============================================================================
async function submitScoring(event) {
  if (event) event.preventDefault();
  const requestId = ++AppState.scoringRequestId;

  const income = parseFloat(document.getElementById('inp-income').value);
  const credit = parseFloat(document.getElementById('inp-credit').value);
  const annuity = parseFloat(document.getElementById('inp-annuity').value);
  const goods = parseFloat(document.getElementById('inp-goods').value);
  const age = parseFloat(document.getElementById('inp-age').value);
  const employed = parseFloat(document.getElementById('inp-employed').value);
  const ext1 = parseFloat(document.getElementById('inp-ext1').value);
  const ext2 = parseFloat(document.getElementById('inp-ext2').value);
  const ext3 = parseFloat(document.getElementById('inp-ext3').value);
  const overdue = parseFloat(document.getElementById('inp-overdue').value);
  const education = document.getElementById('inp-education').value;
  const incomeType = document.getElementById('inp-income-type').value;

  const payload = {
    SK_ID_CURR: AppState.currentApplicantId,
    AMT_INCOME_TOTAL: income,
    AMT_CREDIT: credit,
    AMT_ANNUITY: annuity,
    AMT_GOODS_PRICE: goods,
    AGE_YEARS: age,
    EMPLOYED_YEARS: employed,
    EXT_SOURCE_1: ext1,
    EXT_SOURCE_2: ext2,
    EXT_SOURCE_3: ext3,
    BUREAU_TOTAL_OVERDUE: overdue,
    NAME_EDUCATION_TYPE: education,
    NAME_INCOME_TYPE: incomeType,
    CODE_GENDER: (AppState.currentApplicantData && AppState.currentApplicantData.gender === "Female") ? "F" : "M",
    NAME_CONTRACT_TYPE: document.getElementById('inp-contract') ? document.getElementById('inp-contract').value : "Cash loans"
  };
  AppState.currentApplicantData = {
    id: AppState.currentApplicantId || 'manual',
    label: AppState.currentApplicantLabel,
    income,
    credit,
    annuity,
    goods,
    age,
    employed,
    gender: (AppState.currentApplicantData && AppState.currentApplicantData.gender === "Female") ? "Female" : "Male",
    ext1,
    ext2,
    ext3,
    contract: payload.NAME_CONTRACT_TYPE
  };
  updateSummarySheet(AppState.currentApplicantData);

  const predictBtn = document.getElementById('predict-risk-btn');
  if (predictBtn) {
    predictBtn.disabled = true;
    predictBtn.innerHTML = `Computing Risk...`;
  }

  try {
    // Primary endpoint: /api/v1/predict with fallback to /api/underwriting/score
    let resp = await fetch('/api/v1/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      resp = await fetch('/api/underwriting/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }

    const result = await resp.json();
    if (result.error) {
      if (requestId === AppState.scoringRequestId) {
        clearScoringResult(`Unable to score this profile: ${result.error}`);
      }
      return;
    }

    if (requestId !== AppState.scoringRequestId) return;

    AppState.lastScoringResult = result;
    renderScoringResult(result);
  } catch (err) {
    console.error("Scoring request failed:", err);
    if (requestId === AppState.scoringRequestId) {
      clearScoringResult('The scoring service is unavailable. Check the connection and try again.');
    }
  } finally {
    if (predictBtn) {
      predictBtn.disabled = false;
      predictBtn.innerHTML = `Predict Risk &rarr;`;
    }
  }
}

function renderScoringResult(res) {
  const resultContent = document.getElementById('scoring-result-content');
  if (resultContent) resultContent.hidden = false;

  const placeholder = document.getElementById('scoring-placeholder');
  if (placeholder) {
    placeholder.hidden = true;
    placeholder.classList.remove('is-compact');
  }

  // 1. Update Profile Tag
  setTextContent('res-applicant-id', `Evaluated Profile: ${AppState.currentApplicantLabel}`);
  const xaiStatus = document.getElementById('xai-profile-status');
  if (xaiStatus) {
    xaiStatus.classList.add('is-scored');
    xaiStatus.textContent = `Scored · ${AppState.currentApplicantLabel}`;
  }

  // 2. Score & Risk Metrics (Display Credit Health Score e.g. 98 or 93 for low risk)
  const creditHealthScore = Math.max(1, Math.min(99, 100 - res.risk_score));
  setTextContent('res-score', creditHealthScore);
  setTextContent('res-prob', (res.calibrated_default_prob * 100).toFixed(2) + '%');
  setTextContent('res-decision', res.underwriting_decision);
  setTextContent('res-rationale', res.decision_rationale);

  // Badges & Colors
  const badgeColor = res.badge_color || (res.risk_band === 'Low Risk' ? 'success' : (res.risk_band === 'Medium Risk' ? 'warning' : 'danger'));
  
  const bandBadge = document.getElementById('res-band-badge');
  if (bandBadge) {
    bandBadge.textContent = res.risk_band;
    bandBadge.className = 'decision-badge ' + badgeColor;
  }

  const circle = document.getElementById('score-circle-color');
  if (circle) {
    circle.className = 'score-circle-modern ' + badgeColor;
  }

  // Confidence Rating
  const confBadge = document.getElementById('res-confidence-badge');
  if (confBadge) {
    confBadge.textContent = res.risk_band === 'Medium Risk' ? 'Confidence: Medium' : 'Confidence: High';
  }

  // 3. ML Decision-Support Guardrails Flag
  const policyBadge = document.getElementById('res-policy-flag');
  if (policyBadge && res.policy_rules) {
    if (res.policy_rules.all_passed) {
      policyBadge.textContent = 'PASSED (All 5 Guardrails)';
      policyBadge.className = 'badge badge-success';
    } else {
      policyBadge.textContent = `FLAGGED (${res.policy_rules.failed_count} Guardrail Alerts)`;
      policyBadge.className = 'badge badge-danger';
    }
  }

  // 4. Tab 2: Render Key Risk Factors Panel
  renderRiskFactorsList(AppState.activeRiskFactorTab);

  // 5. Tab 3: Update Explainable AI Tab
  renderExplainableAiTab(res, creditHealthScore);

  // 6. Tab 4: Update Active Policy Rules Audit Table
  renderPolicyRulesTable(res.policy_rules);
}

// ============================================================================
// 7. Tab 2: Key Risk Factors Panel Switcher
// ============================================================================
function switchRiskFactorTab(tab) {
  AppState.activeRiskFactorTab = tab;
  const incrBtn = document.getElementById('tab-risk-incr-btn');
  const decrBtn = document.getElementById('tab-risk-decr-btn');

  if (tab === 'increases') {
    if (incrBtn) incrBtn.classList.add('active');
    if (decrBtn) decrBtn.classList.remove('active');
  } else {
    if (incrBtn) incrBtn.classList.remove('active');
    if (decrBtn) decrBtn.classList.add('active');
  }

  renderRiskFactorsList(tab);
}

function renderRiskFactorsList(tab) {
  const container = document.getElementById('risk-factors-container');
  if (!container || !AppState.lastScoringResult) return;

  container.innerHTML = '';
  const isIncreases = (tab === 'increases');
  const factors = isIncreases
    ? (AppState.lastScoringResult.top_risk_escalators || [])
    : (AppState.lastScoringResult.top_risk_reducers || []);

  if (factors.length === 0) {
    container.innerHTML = `<div class="text-muted" style="font-size: 0.78rem; padding: 0.5rem;">No significant ${isIncreases ? 'escalators' : 'reducers'} identified for this profile.</div>`;
    return;
  }

  factors.forEach(f => {
    const item = document.createElement('div');
    item.className = 'factor-card-item';
    const badgeClass = isIncreases ? 'factor-badge-pos' : 'factor-badge-neg';
    const sign = f.shap_value >= 0 ? '+' : '';
    const formattedVal = typeof f.feature_value === 'number' ? f.feature_value.toLocaleString() : f.feature_value;

    item.innerHTML = `
      <div class="factor-item-info">
        <span class="factor-item-name">${escapeHtml(translateFeatureName(f.feature))}</span>
        <span class="factor-item-val">Observed Value: <strong>${formattedVal}</strong></span>
      </div>
      <span class="factor-item-badge ${badgeClass}">${sign}${f.shap_value.toFixed(3)} log-odds</span>
    `;
    container.appendChild(item);
  });
}

// ============================================================================
// 8. Tab 3: Explainable AI & Diverging SHAP Bar Chart
// ============================================================================
function renderExplainableAiTab(res, creditScore) {
  // Top metrics
  setTextContent('xai-score', `${creditScore} / 100`);
  const xaiBand = document.getElementById('xai-band');
  if (xaiBand) {
    xaiBand.textContent = res.risk_band;
    xaiBand.className = 'badge ' + (res.badge_color === 'success' ? 'badge-success' : (res.badge_color === 'warning' ? 'badge-warning' : 'badge-danger'));
  }
  setTextContent('xai-prob', (res.calibrated_default_prob * 100).toFixed(2) + '%');
  
  const baseVal = res.shap_base_value !== undefined ? Number(res.shap_base_value).toFixed(3) : '-2.412';
  setTextContent('xai-base-val', `${baseVal} log-odds`);
  setTextContent('shap-footnote-base', baseVal);

  // Horizontal Diverging SHAP Bar Chart
  renderShapDivergingChart(res);

  // Plain-English Interpretation Cards
  renderInterpretationCards(res);
}

function renderShapDivergingChart(res) {
  const canvas = document.getElementById('shapDivergingChart');
  if (!canvas) return;

  // Prepare combined factors with signed values
  const escalators = (res.top_risk_escalators || []).map(f => ({
    name: translateFeatureName(f.feature),
    value: Math.abs(f.shap_value),
    signedValue: Math.abs(f.shap_value),
    isEscalator: true
  }));

  const reducers = (res.top_risk_reducers || []).map(f => ({
    name: translateFeatureName(f.feature),
    value: Math.abs(f.shap_value),
    signedValue: -Math.abs(f.shap_value),
    isEscalator: false
  }));

  // Combine top 3 reducers and top 3 escalators
  const combined = [...reducers.slice(0, 4), ...escalators.slice(0, 4)];
  if (typeof Chart === 'undefined') {
    const chartNote = canvas.parentElement && canvas.parentElement.nextElementSibling;
    if (chartNote) {
      chartNote.textContent = 'The explanation data is available, but the chart library could not be loaded.';
    }
    return;
  }
  
  const labels = combined.map(c => c.name);
  const data = combined.map(c => c.signedValue);
  const backgroundColors = combined.map(c => c.isEscalator ? '#C94A45' : '#078A63');
  const borderColors = combined.map(c => c.isEscalator ? '#A83E3A' : '#056B4D');

  if (AppState.charts.shapDiverging) {
    AppState.charts.shapDiverging.destroy();
  }

  AppState.charts.shapDiverging = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'SHAP Attribution (Log-Odds Impact)',
        data: data,
        backgroundColor: backgroundColors,
        borderColor: borderColors,
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.65
      }]
    },
    options: {
      indexAxis: 'y', // Horizontal bars
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const val = ctx.raw;
              const dir = val < 0 ? 'Reduces default hazard' : 'Increases default hazard';
              return ` ${val > 0 ? '+' : ''}${val.toFixed(3)} log-odds (${dir})`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Impact on Model Log-Odds (Zero Baseline = Expected Value)',
            font: { family: 'Inter', size: 10, weight: '600' },
            color: '#64748B'
          },
          ticks: {
            font: { family: 'Inter', size: 10 },
            color: '#64748B'
          },
          grid: {
            color: (context) => context.tick.value === 0 ? '#C79A4A' : '#E8E0D4',
            lineWidth: (context) => context.tick.value === 0 ? 2 : 1
          }
        },
        y: {
          ticks: {
            font: { family: 'Inter', size: 11, weight: '600' },
            color: '#1E293B'
          },
          grid: { display: false }
        }
      }
    }
  });
}

function renderInterpretationCards(res) {
  // Strength Card
  const topReducer = (res.top_risk_reducers && res.top_risk_reducers.length > 0) ? res.top_risk_reducers[0] : null;
  const strengthText = topReducer
    ? `Strong external rating across <strong>${translateFeatureName(topReducer.feature)}</strong> significantly lowers expected default hazard (${topReducer.shap_value.toFixed(3)} log-odds impact), indicating solid creditworthiness.`
    : `Overall positive credit history and steady employment mitigate borrower default hazard.`;
  setHtmlContent('interp-strength-text', strengthText);

  // Vulnerability Card
  const topEscalator = (res.top_risk_escalators && res.top_risk_escalators.length > 0) ? res.top_risk_escalators[0] : null;
  const vulnText = topEscalator
    ? `Elevated debt obligations or repayment burden in <strong>${translateFeatureName(topEscalator.feature)}</strong> exerts upward pressure on risk rating (+${topEscalator.shap_value.toFixed(3)} log-odds).`
    : `No severe risk escalators detected. Applicant maintains balanced debt ratios.`;
  setHtmlContent('interp-vulnerability-text', vulnText);

  // Underwriter Recommendation Card
  const band = res.risk_band;
  let recText = '';
  if (band === 'Low Risk') {
    recText = `Applicant qualifies for <strong>Fast-Track Instant Approval (STP)</strong> with straight-through processing. Zero heuristic policy rules were violated.`;
  } else if (band === 'Medium Risk') {
    recText = `Routed to <strong>Manual Underwriting Review</strong>. Recommend verifying secondary income documentation and debt-to-income cushion.`;
  } else {
    recText = `Profile flagged for <strong>Strict Underwriting or Decline</strong>. High default probability requires collateral enhancement or debt restructuring.`;
  }
  setHtmlContent('interp-recommendation-text', recText);
}

// ============================================================================
// 9. Tab 4: Credit Policy Rules Audit Table
// ============================================================================
function renderPolicyRulesTable(policyRules) {
  const tbody = document.getElementById('policy-rules-tbody');
  if (!tbody || !policyRules || !policyRules.rules) return;

  tbody.innerHTML = '';
  policyRules.rules.forEach(r => {
    const tr = document.createElement('tr');
    const statusClass = r.passed ? 'badge-success' : 'badge-danger';
    const statusText = r.passed ? 'PASS' : 'FLAGGED';
    const severityClass = r.severity === 'HIGH' ? 'badge-danger' : (r.severity === 'MEDIUM' ? 'badge-warning' : 'badge-neutral');

    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(r.name)}</strong><br/>
        <code style="font-size: 0.72rem; color: #047857; background: #ECFDF5; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${r.flag_id || r.rule_id}</code>
      </td>
      <td><code>${escapeHtml(r.threshold)}</code></td>
      <td><strong>${escapeHtml(String(r.value))}</strong></td>
      <td><span class="badge ${statusClass}">${statusText}</span></td>
      <td><span class="badge ${severityClass}">${escapeHtml(r.severity)}</span></td>
      <td>${escapeHtml(r.rationale)}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ============================================================================
// 10. Tab 5: Talk-to-Data Assistant
// ============================================================================
function askPreset(question) {
  switchTab('chat-tab');
  const input = document.getElementById('chat-input');
  if (input) {
    input.value = question;
    sendChatMessage();
  }
}

async function sendChatMessage(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('chat-input');
  if (!input) return;
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  appendUserMessage(question);

  const submitBtn = document.getElementById('chat-submit-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Thinking...';
  }

  try {
    // Primary endpoint: /api/v1/query with fallback to /api/talk-to-data/chat
    let resp = await fetch('/api/v1/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    if (!resp.ok) {
      resp = await fetch('/api/talk-to-data/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
    }

    const result = await resp.json();
    if (result.error) {
      appendErrorMessage(result.error);
    } else {
      appendAssistantMessage(result);
    }
  } catch (err) {
    appendErrorMessage("Failed to communicate with Talk-to-Data service.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Send ↵';
    }
  }
}

function appendUserMessage(text) {
  const history = document.getElementById('chat-history');
  if (!history) return;
  const msg = document.createElement('div');
  msg.className = 'chat-message user';
  msg.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-body">
      <div class="msg-text">${escapeHtml(text)}</div>
    </div>
  `;
  history.appendChild(msg);
  history.scrollTop = history.scrollHeight;
}

function appendAssistantMessage(res) {
  const history = document.getElementById('chat-history');
  if (!history) return;

  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';

  let tableHtml = '';
  if (res.data && res.data.length > 0) {
    const cols = res.columns || Object.keys(res.data[0]);
    tableHtml = `
      <div class="table-responsive" style="max-height: 240px; overflow-y: auto; margin-top: 8px; border-radius: 6px; border: 1px solid var(--border-color);">
        <table class="data-table">
          <thead>
            <tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${res.data.slice(0, 10).map(row => `
              <tr>${cols.map(c => `<td>${row[c] !== null ? escapeHtml(String(row[c])) : 'NULL'}</td>`).join('')}</tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  const insightHtml = res.business_insight
    ? `<div class="insight-comment">💡 <strong>Business Insight:</strong> ${escapeHtml(res.business_insight)}</div>`
    : '';

  const sqlHtml = res.sql
    ? `
      <div class="sql-preview-box">
        <span class="sql-badge">Validated SQLite SELECT</span>
        <code>${escapeHtml(res.sql)}</code>
      </div>
    `
    : '';

  const latency = res.execution_time_ms !== undefined ? res.execution_time_ms : (res.total_latency_ms || 15);
  const provider = res.provider || (res.tier_used || 'Deterministic Engine');

  msg.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-body">
      ${insightHtml}
      ${sqlHtml}
      ${tableHtml}
      <div class="chat-meta">
        <span>⚡ Latency: ${latency}ms</span>
        <span>•</span>
        <span>Engine: ${escapeHtml(provider)}</span>
      </div>
    </div>
  `;

  history.appendChild(msg);
  history.scrollTop = history.scrollHeight;
}

function appendErrorMessage(errText) {
  const history = document.getElementById('chat-history');
  if (!history) return;
  const msg = document.createElement('div');
  msg.className = 'chat-message assistant';
  msg.innerHTML = `
    <div class="msg-avatar">⚠️</div>
    <div class="msg-body" style="background: #FEF2F2; color: #991B1B; border-color: #FECACA;">
      <strong>Error:</strong> ${escapeHtml(errText)}
    </div>
  `;
  history.appendChild(msg);
  history.scrollTop = history.scrollHeight;
}

// ============================================================================
// 11. Helper Utilities
// ============================================================================
function translateFeatureName(feat) {
  const map = {
    'EXT_SOURCES_MEAN': 'Composite Bureau Score',
    'EXT_SOURCE_1': 'External Bureau Score 1',
    'EXT_SOURCE_2': 'External Bureau Score 2',
    'EXT_SOURCE_3': 'External Bureau Score 3',
    'AMT_ANNUITY': 'Monthly Annuity Burden',
    'AMT_CREDIT': 'Total Credit Amount',
    'AMT_INCOME_TOTAL': 'Annual Gross Income',
    'AMT_GOODS_PRICE': 'Goods Purchase Price',
    'DEBT_TO_INCOME': 'Debt-to-Income (DTI)',
    'PAYMENT_RATE': 'Payment Rate (Annuity / Credit)',
    'GOODS_PRICE_TO_CREDIT': 'Goods Price to Credit Margin',
    'AGE_YEARS': 'Applicant Age',
    'EMPLOYED_YEARS': 'Employment Tenure',
    'BUREAU_TOTAL_OVERDUE': 'Prior Past Due Debt',
    'NAME_EDUCATION_TYPE': 'Education Attainment Level',
    'NAME_INCOME_TYPE': 'Income Source Category'
  };
  return map[feat] || feat.replace(/_/g, ' ');
}

function setTextContent(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setHtmlContent(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ============================================================================
// 12. Application Initialization on DOMContentLoaded
// ============================================================================
window.addEventListener('DOMContentLoaded', () => {
  initializeMotion();

  // Initialize Chart.js for Tab 1
  initEdaCharts();

  // Keep the simulator unscored until the user explicitly requests a prediction.
  clearScoringResult('Review the applicant details, then select Predict Risk to calculate a credit health score.');

  const scoringForm = document.getElementById('scoring-form');
  if (scoringForm) {
    const invalidateScoring = () => {
      syncManualApplicantProfile();
      clearScoringResult('Inputs changed. Select Predict Risk to refresh the assessment.');
    };
    scoringForm.addEventListener('input', invalidateScoring);
    scoringForm.addEventListener('change', invalidateScoring);
  }
  syncManualApplicantProfile();
  initializeDefaultExplanation();
});

async function initializeDefaultExplanation() {
  // Start with a real test applicant so the XAI tab is useful before manual input.
  loadTestApplicant(100001);
  await submitScoring();
}
