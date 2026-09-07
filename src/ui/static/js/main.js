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
  currentTab: 'eda-tab',
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
    shapDiverging: null,
    underwritingTornado: null
  },
  chatExchanges: []
};

/**
 * Retrieve a computed CSS custom property or return a fallback value.
 */
function getCssColor(varName, fallback) {
  try {
    if (typeof document !== 'undefined' && document.documentElement) {
      const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
      if (val) return val;
    }
  } catch (e) {
    // Ignore and fallback
  }
  return fallback;
}

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

  AppState.currentTab = tabId;
  window.localStorage.setItem('creditRiskActiveTab', tabId);

  // Keep the selected navigation item synchronized with the visible tab.
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tabId === tabId);
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
  } else if (tabId === 'underwriting-tab') {
    if (AppState.charts.underwritingTornado) AppState.charts.underwritingTornado.resize();
    if (AppState.charts.shapDiverging) AppState.charts.shapDiverging.resize();
  }

  // Re-evaluate scroll-aware launcher visibility for the active tab
  requestAnimationFrame(() => {
    updateChatLauncherVisibility();
  });
}

function toggleChatPanel(isOpen) {
  const panel = document.getElementById('chat-tab');
  const launcher = document.querySelector('.chat-launcher');
  if (!panel) return;

  panel.classList.toggle('is-open', isOpen);
  panel.setAttribute('aria-hidden', String(!isOpen));
  if (launcher) {
    launcher.setAttribute('aria-expanded', String(isOpen));
    launcher.classList.toggle('is-hidden', isOpen);
    if (!isOpen) {
      updateChatLauncherVisibility();
    }
  }

  if (isOpen) {
    requestAnimationFrame(() => document.getElementById('chat-input')?.focus());
  }
}

// ============================================================================
// 3b. Scroll-Aware Floating Launcher Manager
// ============================================================================
const SCROLL_TOP_THRESHOLD = 50;
let lastScrollY = typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0;

function isTabContentShort() {
  const launcher = document.querySelector('.chat-launcher');
  if (!launcher) return true;

  // If document height cannot scroll beyond top threshold, content is short
  const maxScroll = Math.max(
    0,
    document.documentElement.scrollHeight - window.innerHeight
  );
  if (maxScroll <= SCROLL_TOP_THRESHOLD) {
    return true;
  }

  // Check if active tab content ends above the launcher resting position
  const activeTab = document.querySelector('.tab-content.active');
  if (activeTab) {
    const tabRect = activeTab.getBoundingClientRect();
    const currentScrollY = Math.max(0, window.scrollY || window.pageYOffset || 0);
    const tabBottomInDoc = tabRect.bottom + currentScrollY;
    const launcherTopInViewport = window.innerHeight - launcher.offsetHeight - 24;
    if (tabBottomInDoc <= launcherTopInViewport) {
      return true;
    }
  }

  return false;
}

function updateChatLauncherVisibility() {
  const launcher = document.querySelector('.chat-launcher');
  if (!launcher) return;

  // Preserve existing open/close behavior of the panel itself
  const chatPanel = document.getElementById('chat-tab');
  if (chatPanel && chatPanel.classList.contains('is-open')) {
    return;
  }

  const currentScrollY = Math.max(0, window.scrollY || window.pageYOffset || 0);

  // 1. Keep it always visible on tabs whose content is short enough not to reach it
  if (isTabContentShort()) {
    launcher.classList.remove('is-scroll-hidden');
    lastScrollY = currentScrollY;
    return;
  }

  // 2. Reappear when within ~50px of the top of the page
  if (currentScrollY <= SCROLL_TOP_THRESHOLD) {
    launcher.classList.remove('is-scroll-hidden');
    lastScrollY = currentScrollY;
    return;
  }

  // 3. Scroll direction handling past threshold
  const deltaY = currentScrollY - lastScrollY;

  // Ignore negligible jitter (< 3px)
  if (Math.abs(deltaY) < 3) {
    return;
  }

  if (deltaY > 0) {
    // Scrolling down more than ~50px -> hide button (fade out)
    launcher.classList.add('is-scroll-hidden');
  } else if (deltaY < 0) {
    // Scrolling up -> reappear
    launcher.classList.remove('is-scroll-hidden');
  }

  lastScrollY = currentScrollY;
}

function throttle(fn, wait = 60) {
  let lastTime = 0;
  let timer = null;

  return function (...args) {
    const now = Date.now();
    const remaining = wait - (now - lastTime);

    if (remaining <= 0 || remaining > wait) {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      lastTime = now;
      fn.apply(this, args);
    } else if (!timer) {
      timer = setTimeout(() => {
        lastTime = Date.now();
        timer = null;
        fn.apply(this, args);
      }, remaining);
    }
  };
}

function initScrollAwareChatLauncher() {
  lastScrollY = Math.max(0, window.scrollY || window.pageYOffset || 0);
  const throttledScroll = throttle(updateChatLauncherVisibility, 60);
  const throttledResize = throttle(updateChatLauncherVisibility, 100);

  window.addEventListener('scroll', throttledScroll, { passive: true });
  window.addEventListener('resize', throttledResize, { passive: true });

  updateChatLauncherVisibility();
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
            getCssColor('--risk-critical', '#C94A45'), // Critical: muted red
            getCssColor('--risk-medium', '#C58A28'),   // Subprime: warm amber
            getCssColor('--status-info', '#4779A8'),   // Prime: muted blue
            getCssColor('--risk-low', '#078A63')       // Super-Prime: emerald
          ],
          borderColor: [
            getCssColor('--risk-critical-text', '#A83E3A'),
            getCssColor('--risk-medium-text', '#A8792F'),
            getCssColor('--status-info-text', '#385F86'),
            getCssColor('--risk-low-text', '#056B4D')
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
          backgroundColor: [
            getCssColor('--risk-low', '#078A63'),
            getCssColor('--risk-high', '#C94A45')
          ],
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
  const manualFields = document.getElementById('manual-entry-fields');

  if (subtab === 'manual') {
    if (manualBtn) manualBtn.classList.add('active');
    if (quickloadBtn) quickloadBtn.classList.remove('active');
    if (quickDrawer) {
      quickDrawer.style.display = 'none';
      quickDrawer.hidden = true;
      quickDrawer.classList.add('is-hidden');
    }
    if (manualFields) {
      manualFields.style.display = 'block';
      manualFields.hidden = false;
      manualFields.classList.remove('is-hidden');
    }
  } else {
    if (manualBtn) manualBtn.classList.remove('active');
    if (quickloadBtn) quickloadBtn.classList.add('active');
    if (quickDrawer) {
      quickDrawer.style.display = 'block';
      quickDrawer.hidden = false;
      quickDrawer.classList.remove('is-hidden');
    }
    if (manualFields) {
      manualFields.style.display = 'none';
      manualFields.hidden = true;
      manualFields.classList.add('is-hidden');
    }
  }
}

function loadTestApplicant(id) {
  const applicant = TEST_APPLICANTS[id];
  if (!applicant) return;
  populateApplicantProfile(applicant);

  if (typeof document !== 'undefined') {
    const chipButtons = document.querySelectorAll('.test-loader-btn');
    chipButtons.forEach(btn => {
      const btnAppId = btn.getAttribute('data-app-id');
      if (btnAppId === String(id) || btn.textContent.includes(String(id))) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }
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
  if (typeof document !== 'undefined') {
    document.querySelectorAll('.test-loader-btn').forEach(btn => btn.classList.remove('active'));
  }
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

  const drawer = document.getElementById('guardrail-audit-drawer');
  if (drawer) drawer.style.display = 'none';
  const icon = document.getElementById('audit-toggle-icon');
  if (icon) icon.innerHTML = '&darr;';
  const btn = document.getElementById('btn-audit-heuristics');
  if (btn) btn.setAttribute('aria-expanded', 'false');

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

  if (AppState.charts.underwritingTornado) {
    AppState.charts.underwritingTornado.destroy();
    AppState.charts.underwritingTornado = null;
  }
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

  // 4. Tab 2: Render Key Risk Factors Combined SHAP Tornado Chart
  renderUnderwritingTornadoChart(res);

  // 5. Tab 3: Update Explainable AI Tab
  renderExplainableAiTab(res, creditHealthScore);

  // 6. Tab 4: Update Active Policy Rules Audit Table
  renderPolicyRulesTable(res.policy_rules);
}

// ============================================================================
// 7. Tab 2: Key Risk Factors Combined SHAP Tornado Chart
// ============================================================================
function switchRiskFactorTab(tab) {
  AppState.activeRiskFactorTab = tab;
  if (AppState.lastScoringResult) {
    renderUnderwritingTornadoChart(AppState.lastScoringResult);
  }
}

function renderRiskFactorsList(tab) {
  if (AppState.lastScoringResult) {
    renderUnderwritingTornadoChart(AppState.lastScoringResult);
  }
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

/**
 * Chart.js plugin to render signed log-odds values outside each bar in the diverging SHAP chart.
 * Labels format to 3 decimal places (e.g. "+0.263", "-0.158") in a small font.
 * Positive bars render outside to the right; negative bars render outside to the left.
 * Label positions are clamped to prevent rendering off-canvas or overlapping feature names on narrow bars.
 */
const shapDivergingLabelsPlugin = {
  id: 'shapDivergingLabels',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    if (!ctx || !scales || !scales.x || !scales.y || !chartArea) return;

    const dataset = chart.data.datasets && chart.data.datasets[0];
    if (!dataset || !dataset.data || dataset.data.length === 0) return;
    const meta = chart.getDatasetMeta(0);
    if (!meta || !meta.data) return;

    ctx.save();
    ctx.font = '600 10px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textBaseline = 'middle';

    const offset = 5;
    // Feature name labels sit to the left of chartArea.left; text must not cross into that area or go off-canvas
    const minAllowedLeft = Math.max(4, chartArea.left + 2);
    const maxAllowedRight = chart.width - 4;

    dataset.data.forEach((rawVal, i) => {
      const val = Number(rawVal);
      if (isNaN(val)) return;

      const element = meta.data[i];
      const barX = (element && typeof element.x === 'number') ? element.x : scales.x.getPixelForValue(val);
      const barY = (element && typeof element.y === 'number') ? element.y : scales.y.getPixelForValue(i);
      const formattedVal = (val >= 0 ? '+' : '') + val.toFixed(3);
      const textWidth = ctx.measureText(formattedVal).width;

      if (val >= 0) {
        // Positive bar: position label outside the bar to the right
        ctx.textAlign = 'left';
        ctx.fillStyle = getCssColor('--risk-increase-text', '#9E3834');
        let x = barX + offset;
        // Clamp so label never renders off-canvas to the right
        if (x + textWidth > maxAllowedRight) {
          x = maxAllowedRight - textWidth;
        }
        ctx.fillText(formattedVal, x, barY);
      } else {
        // Negative bar: position label outside the bar to the left
        ctx.textAlign = 'right';
        ctx.fillStyle = getCssColor('--risk-decrease-text', '#056B4D');
        let x = barX - offset;
        // Clamp so label never renders off-canvas or overlaps feature names on the left
        if (x - textWidth < minAllowedLeft) {
          x = minAllowedLeft + textWidth;
        }
        ctx.fillText(formattedVal, x, barY);
      }
    });

    ctx.restore();
  }
};

if (typeof window !== 'undefined') {
  window.shapDivergingLabelsPlugin = shapDivergingLabelsPlugin;
}

/**
 * Shared Chart.js configuration builder for diverging SHAP / tornado charts across Tab 2 and Tab 3.
 */
function buildTornadoChartConfig(labels, data, backgroundColors, borderColors, scaleLimit) {
  return {
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
      layout: {
        padding: {
          left: 4,
          right: 12
        }
      },
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
          grace: '15%',
          suggestedMin: -scaleLimit,
          suggestedMax: scaleLimit,
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
    },
    plugins: [shapDivergingLabelsPlugin]
  };
}

/**
 * Render single combined SHAP Tornado Chart on Underwriting Simulator (Tab 2).
 * Shows both positive and negative contributors together, sorted by absolute magnitude,
 * capped at top 6 features in one non-scrolling view.
 */
function renderUnderwritingTornadoChart(res) {
  let canvas = document.getElementById('underwritingTornadoChart');
  const container = document.getElementById('risk-factors-container');
  if (!canvas && container) {
    container.innerHTML = '<div class="canvas-wrapper tornado-canvas-wrapper"><canvas id="underwritingTornadoChart" height="230"></canvas></div>';
    canvas = document.getElementById('underwritingTornadoChart');
  }
  if (!canvas) return;

  if (typeof Chart === 'undefined') {
    if (container) {
      container.innerHTML = '<div class="text-muted" style="font-size: 0.78rem; padding: 0.5rem;">The explanation data is available, but the chart library could not be loaded.</div>';
    }
    return;
  }

  // Extract positive (escalators) and negative (reducers) contributors
  const escalators = (res.top_risk_escalators || []).map(f => ({
    name: translateFeatureName(f.feature),
    feature: f.feature,
    feature_value: f.feature_value,
    absMagnitude: Math.abs(f.shap_value),
    signedValue: Math.abs(f.shap_value),
    isEscalator: true
  }));

  const reducers = (res.top_risk_reducers || []).map(f => ({
    name: translateFeatureName(f.feature),
    feature: f.feature,
    feature_value: f.feature_value,
    absMagnitude: Math.abs(f.shap_value),
    signedValue: -Math.abs(f.shap_value),
    isEscalator: false
  }));

  // Combine both positive and negative contributors together, sorted by absolute magnitude descending
  const allFactors = [...escalators, ...reducers];
  allFactors.sort((a, b) => b.absMagnitude - a.absMagnitude);

  // Cap at top 6 features by magnitude for non-scrolling compact presentation
  const topFactors = allFactors.slice(0, 6);

  if (topFactors.length === 0) {
    if (container) {
      container.innerHTML = '<div class="text-muted" style="font-size: 0.78rem; padding: 0.5rem;">No significant risk contributors identified for this profile.</div>';
    }
    return;
  }

  const labels = topFactors.map(c => c.name);
  const data = topFactors.map(c => c.signedValue);

  const riskHighColor = getCssColor('--risk-increase', getCssColor('--risk-high', '#C94A45'));
  const riskLowColor = getCssColor('--risk-decrease', getCssColor('--risk-low', '#078A63'));
  const riskHighBorder = getCssColor('--risk-increase-text', getCssColor('--risk-high-text', '#A83E3A'));
  const riskLowBorder = getCssColor('--risk-decrease-text', getCssColor('--risk-low-text', '#056B4D'));

  const backgroundColors = topFactors.map(c => c.isEscalator ? riskHighColor : riskLowColor);
  const borderColors = topFactors.map(c => c.isEscalator ? riskHighBorder : riskLowBorder);

  // Symmetric scale headroom so labels have ample space outside bars without crowding canvas boundaries
  const minVal = data.length ? Math.min(...data) : 0;
  const maxVal = data.length ? Math.max(...data) : 0;
  const absMax = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.05);
  const pad = Math.max(0.10, absMax * 0.35);
  const scaleLimit = Number((absMax + pad).toFixed(2));

  if (AppState.charts.underwritingTornado) {
    AppState.charts.underwritingTornado.destroy();
  }

  AppState.charts.underwritingTornado = new Chart(
    canvas,
    buildTornadoChartConfig(labels, data, backgroundColors, borderColors, scaleLimit)
  );
}

function renderShapDivergingChart(res) {
  const canvas = document.querySelector('#shapDivergingChart');
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

  // Combine top 4 reducers and top 4 escalators
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
  const riskHighColor = getCssColor('--risk-increase', getCssColor('--risk-high', '#C94A45'));
  const riskLowColor = getCssColor('--risk-decrease', getCssColor('--risk-low', '#078A63'));
  const riskHighBorder = getCssColor('--risk-increase-text', getCssColor('--risk-high-text', '#A83E3A'));
  const riskLowBorder = getCssColor('--risk-decrease-text', getCssColor('--risk-low-text', '#056B4D'));

  const backgroundColors = combined.map(c => c.isEscalator ? riskHighColor : riskLowColor);
  const borderColors = combined.map(c => c.isEscalator ? riskHighBorder : riskLowBorder);

  // Symmetric scale headroom so labels have ample space outside bars without crowding canvas boundaries
  const minVal = data.length ? Math.min(...data) : 0;
  const maxVal = data.length ? Math.max(...data) : 0;
  const absMax = Math.max(Math.abs(minVal), Math.abs(maxVal), 0.05);
  const pad = Math.max(0.10, absMax * 0.35);
  const scaleLimit = Number((absMax + pad).toFixed(2));

  if (AppState.charts.shapDiverging) {
    AppState.charts.shapDiverging.destroy();
  }

  AppState.charts.shapDiverging = new Chart(
    canvas,
    buildTornadoChartConfig(labels, data, backgroundColors, borderColors, scaleLimit)
  );
}

if (typeof window !== 'undefined') {
  window.shapDivergingLabelsPlugin = shapDivergingLabelsPlugin;
  window.renderUnderwritingTornadoChart = renderUnderwritingTornadoChart;
  window.buildTornadoChartConfig = buildTornadoChartConfig;
  window.switchSimulatorSubtab = switchSimulatorSubtab;
  window.loadTestApplicant = loadTestApplicant;
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
// 9. Guardrails Audit Drawer & Policy Rules Audit Table
// ============================================================================
function toggleGuardrailAudit() {
  const drawer = document.getElementById('guardrail-audit-drawer');
  const btn = document.getElementById('btn-audit-heuristics');
  const icon = document.getElementById('audit-toggle-icon');
  if (!drawer) return;
  const isHidden = drawer.style.display === 'none' || drawer.style.display === '';
  if (isHidden) {
    drawer.style.display = 'block';
    if (btn) btn.setAttribute('aria-expanded', 'true');
    if (icon) icon.innerHTML = '&uarr;';
  } else {
    drawer.style.display = 'none';
    if (btn) btn.setAttribute('aria-expanded', 'false');
    if (icon) icon.innerHTML = '&darr;';
  }
}

function renderPolicyRulesTable(policyRules) {
  const tbody = document.getElementById('policy-rules-tbody');
  if (!tbody || !policyRules || !policyRules.rules) return;

  tbody.innerHTML = '';
  policyRules.rules.forEach(r => {
    const tr = document.createElement('tr');
    if (!r.passed) {
      const sev = (r.severity || '').toUpperCase();
      if (sev === 'CRITICAL') {
        tr.className = 'policy-row-critical';
      } else if (sev === 'HIGH') {
        tr.className = 'policy-row-high';
      }
    }
    const statusClass = r.passed ? 'badge-success' : 'badge-danger';
    const statusText = r.passed ? 'PASS' : 'FLAGGED';
    const severityClass = {
      LOW: 'badge-severity-low',
      MEDIUM: 'badge-severity-medium',
      HIGH: 'badge-severity-high',
      CRITICAL: 'badge-severity-critical'
    }[r.severity] || 'badge-neutral';

    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(r.name)}</strong><br/>
        <code class="policy-flag-code">${escapeHtml(r.flag_id || r.rule_id)}</code>
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
// 10. Tab 5: Talk-to-Data Assistant (Lightweight Session History)
// ============================================================================

const ChatSession = {
  get exchanges() {
    return AppState.chatExchanges;
  },
  set exchanges(val) {
    AppState.chatExchanges = val;
  },
  pendingQuestion: null,

  addExchange(ex) {
    // When adding a new exchange, collapse all prior exchanges so only the new one is expanded
    this.exchanges.forEach(item => { item.expanded = false; });
    ex.expanded = true;
    if (ex.sqlExpanded === undefined) {
      ex.sqlExpanded = false;
    }
    this.exchanges.push(ex);
    this.render();
    this.scrollToBottom();
  },

  toggleExchange(id) {
    const item = this.exchanges.find(ex => ex.id === id);
    if (item) {
      item.expanded = !item.expanded;
      this.render();
    }
  },

  toggleSql(id) {
    const item = this.exchanges.find(ex => ex.id === id);
    if (!item) return;
    item.sqlExpanded = !item.sqlExpanded;

    const box = typeof document !== 'undefined' ? document.getElementById(`sql-box-${id}`) : null;
    const btn = typeof document !== 'undefined' ? document.getElementById(`sql-toggle-btn-${id}`) : null;
    if (box && btn) {
      box.classList.toggle('is-expanded', item.sqlExpanded);
      box.classList.toggle('is-collapsed', !item.sqlExpanded);
      btn.innerHTML = item.sqlExpanded ? 'Show less ▴' : 'Show full query ▾';
      btn.setAttribute('aria-expanded', String(item.sqlExpanded));
      btn.setAttribute('title', item.sqlExpanded ? 'Collapse query to 3 lines' : 'Expand query to full height');
    } else {
      this.render();
    }
  },

  setPending(question) {
    this.pendingQuestion = question;
    this.render();
    this.scrollToBottom();
  },

  clearPending() {
    this.pendingQuestion = null;
    this.render();
  },

  scrollToBottom() {
    requestAnimationFrame(() => {
      const history = document.getElementById('chat-history');
      if (history) {
        history.scrollTop = history.scrollHeight;
      }
    });
  },

  render() {
    const history = document.getElementById('chat-history');
    if (!history) return;

    if (this.exchanges.length === 0 && !this.pendingQuestion) {
      history.innerHTML = `
        <div class="chat-message assistant">
          <div class="msg-avatar">↗</div>
          <div class="msg-body">Ask about portfolio characteristics, bureau signals, or repayment stress.</div>
        </div>
      `;
      return;
    }

    let html = '';

    this.exchanges.forEach((ex) => {
      const isExpanded = !!ex.expanded;
      const isSqlExpanded = !!ex.sqlExpanded;
      const rowText = `${ex.rowCount} ${ex.rowCount === 1 ? 'row' : 'rows'}`;

      html += `
        <div class="chat-exchange-card ${isExpanded ? 'is-expanded' : 'is-collapsed'}" id="exchange-${escapeHtml(ex.id)}" data-exchange-id="${escapeHtml(ex.id)}">
          <div class="exchange-summary-bar ${isExpanded ? 'is-active' : ''}" onclick="ChatSession.toggleExchange('${escapeHtml(ex.id)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();ChatSession.toggleExchange('${escapeHtml(ex.id)}');}" role="button" tabindex="0" aria-expanded="${isExpanded}" title="${isExpanded ? 'Click to collapse details' : 'Click to expand SQL and results'}">
            <div class="exchange-summary-left">
              <span class="exchange-indicator-icon" aria-hidden="true">${isExpanded ? '▾' : '▸'}</span>
              <div class="exchange-summary-texts">
                <span class="exchange-question-summary">${escapeHtml(ex.question)}</span>
                <span class="exchange-result-summary">${escapeHtml(ex.summaryText)}</span>
              </div>
            </div>
            <div class="exchange-summary-right">
              <span class="badge badge-sm badge-neutral">${escapeHtml(rowText)}</span>
              <span class="exchange-expand-hint">${isExpanded ? 'Hide details ▴' : 'View SQL &amp; Data ▾'}</span>
            </div>
          </div>

          <div class="exchange-full-details" style="${isExpanded ? 'display: flex;' : 'display: none;'}">
            <div class="chat-message user">
              <div class="msg-avatar">👤</div>
              <div class="msg-body">
                <div class="msg-text">${escapeHtml(ex.question)}</div>
              </div>
            </div>

            <div class="chat-message assistant">
              <div class="msg-avatar">${ex.error ? '⚠️' : '🤖'}</div>
              <div class="msg-body ${ex.error ? 'msg-body-error' : ''}">
                ${ex.error ? `<strong>Error:</strong> ${escapeHtml(ex.error)}` : `
                  ${ex.businessInsight ? `<div class="insight-comment">💡 <strong>Business Insight:</strong> ${escapeHtml(ex.businessInsight)}</div>` : ''}
                  ${ex.sql ? `
                    <div class="sql-preview-box ${isSqlExpanded ? 'is-expanded' : 'is-collapsed'}" id="sql-box-${escapeHtml(ex.id)}">
                      <div class="sql-preview-header">
                        <span class="sql-badge">Validated SQLite SELECT</span>
                        <button type="button" class="sql-toggle-btn" id="sql-toggle-btn-${escapeHtml(ex.id)}" onclick="ChatSession.toggleSql('${escapeHtml(ex.id)}')" aria-expanded="${isSqlExpanded}" aria-controls="sql-code-${escapeHtml(ex.id)}" title="${isSqlExpanded ? 'Collapse query to 3 lines' : 'Expand query to full height'}">
                          ${isSqlExpanded ? 'Show less ▴' : 'Show full query ▾'}
                        </button>
                      </div>
                      <code id="sql-code-${escapeHtml(ex.id)}" class="sql-code-content ${isSqlExpanded ? 'is-expanded' : 'is-collapsed'}">${escapeHtml(ex.sql)}</code>
                    </div>
                  ` : ''}
                  ${buildTableHtml(ex)}
                  <div class="chat-meta">
                    <span>⚡ Latency: ${ex.latency}ms</span>
                    <span>•</span>
                    <span>Engine: ${escapeHtml(ex.engine)}</span>
                    ${ex.rowCount !== undefined ? `<span>•</span><span>${escapeHtml(rowText)}</span>` : ''}
                  </div>
                `}
              </div>
            </div>
          </div>
        </div>
      `;
    });

    if (this.pendingQuestion) {
      html += `
        <div class="chat-exchange-card is-pending">
          <div class="chat-message user" style="margin-bottom: 8px;">
            <div class="msg-avatar">👤</div>
            <div class="msg-body">
              <div class="msg-text">${escapeHtml(this.pendingQuestion)}</div>
            </div>
          </div>
          <div class="chat-message assistant">
            <div class="msg-avatar">🤖</div>
            <div class="msg-body" style="font-size: 0.8rem; color: var(--text-muted);">
              <span class="spinner-dot" aria-hidden="true">⏳</span> Generating SQL query and analyzing holdout database...
            </div>
          </div>
        </div>
      `;
    }

    history.innerHTML = html;
  }
};

function buildTableHtml(ex) {
  if (!ex.data || ex.data.length === 0) return '';
  const cols = ex.columns || Object.keys(ex.data[0]);
  return `
    <div class="table-responsive" style="overflow-x: auto; margin-top: 8px; border-radius: 6px; border: 1px solid var(--border-color);">
      <table class="data-table">
        <thead>
          <tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${ex.data.slice(0, 10).map(row => `
            <tr>${cols.map(c => `<td>${row[c] !== null ? escapeHtml(String(row[c])) : 'NULL'}</td>`).join('')}</tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function askPreset(question) {
  switchTab('chat-tab');
  toggleChatPanel(true);
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
  ChatSession.setPending(question);

  const submitBtn = document.getElementById('chat-submit-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Thinking...';
  }

  try {
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
    ChatSession.clearPending();

    if (result.error) {
      ChatSession.addExchange({
        id: 'ex-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7),
        question,
        sql: result.sql || '',
        data: [],
        columns: [],
        rowCount: 0,
        latency: result.execution_time_ms || 15,
        engine: result.provider || result.tier_used || 'Deterministic Engine',
        businessInsight: '',
        summaryText: `Error: ${result.error}`,
        error: result.error,
        expanded: true
      });
    } else {
      const rowCount = (result.data && Array.isArray(result.data)) ? result.data.length : 0;
      const latency = result.execution_time_ms !== undefined ? result.execution_time_ms : (result.total_latency_ms || 15);
      const engine = result.provider || (result.tier_used || 'Deterministic Engine');
      const cols = result.columns || (result.data && result.data[0] ? Object.keys(result.data[0]) : []);

      let summaryText = '';
      if (result.business_insight) {
        const insightSummary = result.business_insight.length > 75 ? result.business_insight.slice(0, 72) + '...' : result.business_insight;
        summaryText = `${rowCount} ${rowCount === 1 ? 'row' : 'rows'} · ${insightSummary}`;
      } else {
        summaryText = `${rowCount} ${rowCount === 1 ? 'row' : 'rows'} returned (${latency}ms · ${engine})`;
      }

      ChatSession.addExchange({
        id: 'ex-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7),
        question,
        sql: result.sql || '',
        data: result.data || [],
        columns: cols,
        rowCount,
        latency,
        engine,
        businessInsight: result.business_insight || '',
        summaryText,
        error: null,
        expanded: true
      });
    }
  } catch (err) {
    ChatSession.clearPending();
    ChatSession.addExchange({
      id: 'ex-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7),
      question,
      sql: '',
      data: [],
      columns: [],
      rowCount: 0,
      latency: 0,
      engine: 'System',
      businessInsight: '',
      summaryText: 'Failed to communicate with Talk-to-Data service.',
      error: 'Failed to communicate with Talk-to-Data service.',
      expanded: true
    });
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Ask';
    }
  }
}

function appendUserMessage(text) {
  ChatSession.setPending(text);
}

function appendAssistantMessage(res) {
  ChatSession.clearPending();
  const question = ChatSession.pendingQuestion || 'Question';
  const rowCount = (res.data && Array.isArray(res.data)) ? res.data.length : 0;
  const latency = res.execution_time_ms !== undefined ? res.execution_time_ms : (res.total_latency_ms || 15);
  const engine = res.provider || (res.tier_used || 'Deterministic Engine');
  const cols = res.columns || (res.data && res.data[0] ? Object.keys(res.data[0]) : []);

  let summaryText = '';
  if (res.business_insight) {
    const insightSummary = res.business_insight.length > 75 ? res.business_insight.slice(0, 72) + '...' : res.business_insight;
    summaryText = `${rowCount} ${rowCount === 1 ? 'row' : 'rows'} · ${insightSummary}`;
  } else {
    summaryText = `${rowCount} ${rowCount === 1 ? 'row' : 'rows'} returned (${latency}ms · ${engine})`;
  }

  ChatSession.addExchange({
    id: 'ex-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7),
    question,
    sql: res.sql || '',
    data: res.data || [],
    columns: cols,
    rowCount,
    latency,
    engine,
    businessInsight: res.business_insight || '',
    summaryText,
    error: null,
    expanded: true
  });
}

function appendErrorMessage(errText) {
  ChatSession.clearPending();
  const question = ChatSession.pendingQuestion || 'Query';
  ChatSession.addExchange({
    id: 'ex-' + Date.now() + '-' + Math.random().toString(36).substring(2, 7),
    question,
    sql: '',
    data: [],
    columns: [],
    rowCount: 0,
    latency: 0,
    engine: 'System',
    businessInsight: '',
    summaryText: `Error: ${errText}`,
    error: errText,
    expanded: true
  });
}

if (typeof window !== 'undefined') {
  window.ChatSession = ChatSession;
  window.sendChatMessage = sendChatMessage;
  window.askPreset = askPreset;
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
  initScrollAwareChatLauncher();
  if (typeof ChatSession !== 'undefined') {
    ChatSession.render();
  }

  // Initialize Chart.js for Tab 1
  initEdaCharts();

  // Initialize simulator subtab visibility gating
  switchSimulatorSubtab(AppState.activeSimulatorSubtab || 'manual');

  const savedTab = window.localStorage.getItem('creditRiskActiveTab');
  if (savedTab === 'xai-tab') {
    switchTab('underwriting-tab');
  } else if (['eda-tab', 'underwriting-tab', 'policy-tab'].includes(savedTab)) {
    switchTab(savedTab);
  }

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
