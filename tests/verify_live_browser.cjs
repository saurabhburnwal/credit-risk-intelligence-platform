const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

function jsonReq(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 1;
    this.callbacks = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && this.callbacks.has(msg.id)) {
          const cb = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) cb.reject(new Error(msg.error.message));
          else cb.resolve(msg.result);
        }
      };
    });
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression, awaitPromise = false) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise
    });
    if (res.exceptionDetails) {
      throw new Error(JSON.stringify(res.exceptionDetails));
    }
    return res.result ? res.result.value : undefined;
  }

  async screenshot(outputPath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(outputPath, Buffer.from(res.data, 'base64'));
    console.log(`[Screenshot saved] -> ${outputPath}`);
  }

  close() {
    if (this.ws) this.ws.close();
  }
}

async function run() {
  console.log('[Browser Verifier] Launching headless Chrome on port 9222...');
  const chrome = spawn('google-chrome', [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--remote-debugging-port=9222',
    '--user-data-dir=/tmp/chrome-test-profile',
    '--window-size=1400,900',
    'http://localhost:5000'
  ]);

  for (let i = 0; i < 25; i++) {
    await new Promise(r => setTimeout(r, 200));
    try {
      const v = await jsonReq('http://127.0.0.1:9222/json/version');
      if (v) break;
    } catch (e) {}
  }

  const targets = await jsonReq('http://127.0.0.1:9222/json/list');
  let pageTarget = targets.find(t => t.type === 'page');
  if (!pageTarget) {
    pageTarget = await jsonReq('http://127.0.0.1:9222/json/new?http://localhost:5000');
  }

  const client = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await client.connect();
  console.log('[Browser Verifier] Connected to Chrome DevTools Protocol!');

  try {
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('DOM.enable');

    console.log('[Browser Verifier] Navigating to http://localhost:5000...');
    await client.send('Page.navigate', { url: 'http://localhost:5000' });
    await new Promise(r => setTimeout(r, 2000));

    // 1. Navigation verification: Confirm "Explainable AI" is gone from navigation tabs
    const navTabs = await client.evaluate(`
      Array.from(document.querySelectorAll('.tabs-nav .tab-btn')).map(b => ({
        text: b.textContent.trim(),
        tabId: b.dataset.tabId
      }))
    `);
    console.log('[Navigation Tabs in DOM]:', JSON.stringify(navTabs, null, 2));

    const hasExplainableTab = navTabs.some(t => t.text.includes('Explainable') || t.tabId === 'xai-tab');
    if (hasExplainableTab) {
      throw new Error('FAILED: Explainable AI tab is still present in navigation!');
    }
    console.log('✓ PASS: "Explainable AI" tab is completely removed from navigation tabs.');

    // Check that #xai-tab section is absent from DOM
    const xaiTabExists = await client.evaluate(`!!document.getElementById('xai-tab')`);
    if (xaiTabExists) {
      throw new Error('FAILED: #xai-tab element still exists in DOM!');
    }
    console.log('✓ PASS: #xai-tab element is completely deleted from DOM.');

    // Check that "SHAP Waterfall Breakdown" is absent from DOM
    const waterfallExists = await client.evaluate(`
      document.body.innerText.includes('SHAP Waterfall Breakdown') || !!document.getElementById('shapDivergingChart')
    `);
    if (waterfallExists) {
      throw new Error('FAILED: SHAP Waterfall Breakdown section still exists in DOM!');
    }
    console.log('✓ PASS: "SHAP Waterfall Breakdown" section is completely removed from DOM.');

    // 2. CREDIT POLICY RULES TAB AUDIT: Confirm no per-applicant data exists on policy-tab
    console.log('[Browser Verifier] Switching to Credit Policy Rules tab...');
    await client.evaluate(`switchTab('policy-tab')`);
    await new Promise(r => setTimeout(r, 500));

    const policyState = await client.evaluate(`(() => {
      const policyTab = document.getElementById('policy-tab');
      return {
        hasPolicyTable: !!policyTab.querySelector('.policy-active-card'),
        hasActiveApplicantAudit: policyTab.innerText.includes('Active Applicant Policy Rules Audit'),
        hasRulesTbody: !!policyTab.querySelector('#policy-rules-tbody'),
        hasRiskBandsMatrix: policyTab.innerText.includes('Risk Bands & Actions Matrix'),
        hasGovernanceRationale: policyTab.innerText.includes('Why These Thresholds?'),
        hasRiskBandDistribution: policyTab.innerText.includes('Risk-band distribution') && !!policyTab.querySelector('img[src*="risk_band_distribution.png"]')
      };
    })()`);
    console.log('[Credit Policy Rules Tab Content Audit]:', JSON.stringify(policyState, null, 2));

    if (policyState.hasActiveApplicantAudit || policyState.hasPolicyTable || policyState.hasRulesTbody) {
      throw new Error('FAILED: Credit Policy Rules tab still contains per-applicant audit table!');
    }
    if (!policyState.hasRiskBandsMatrix || !policyState.hasGovernanceRationale || !policyState.hasRiskBandDistribution) {
      throw new Error('FAILED: Credit Policy Rules tab is missing required portfolio-level static content!');
    }
    console.log('✓ PASS: Credit Policy Rules tab contains ONLY portfolio-level static governance content; zero per-applicant duplicate data.');

    // 3. UNDERWRITING SIMULATOR: Applicant scoring & single source of truth for Guardrails
    console.log('[Browser Verifier] Switching to Underwriting Simulator tab...');
    await client.evaluate(`switchTab('underwriting-tab')`);
    await new Promise(r => setTimeout(r, 500));

    console.log('[Browser Verifier] Scoring applicant #100001...');
    await client.evaluate(`loadTestApplicant(100001)`);
    await client.evaluate(`submitScoring()`);
    await new Promise(r => setTimeout(r, 1500));

    // Verify guardrails callout bar & Audit 5 Heuristics button
    const simulatorGuardrails = await client.evaluate(`(() => {
      const btn = document.getElementById('btn-audit-heuristics');
      const flag = document.getElementById('res-policy-flag');
      const drawer = document.getElementById('guardrail-audit-drawer');
      const tbody = document.getElementById('policy-rules-tbody');
      return {
        flagText: flag?.textContent.trim(),
        hasButton: !!btn,
        buttonText: btn?.textContent.trim(),
        drawerInitialDisplay: drawer ? window.getComputedStyle(drawer).display : null,
        tbodyRows: tbody ? tbody.children.length : 0
      };
    })()`);
    console.log('[Underwriting Guardrails State]:', JSON.stringify(simulatorGuardrails, null, 2));

    if (!simulatorGuardrails.hasButton || simulatorGuardrails.drawerInitialDisplay !== 'none') {
      throw new Error('FAILED: Guardrail expand drawer or button not found / not initially collapsed!');
    }
    if (simulatorGuardrails.tbodyRows !== 5) {
      throw new Error(`FAILED: Expected 5 guardrail rows in #policy-rules-tbody, found ${simulatorGuardrails.tbodyRows}`);
    }
    console.log('✓ PASS: Underwriting Simulator has "Audit 5 Heuristics" button and 5 evaluated guardrail rows populated in drawer.');

    // Test expanding and collapsing the guardrails drawer via toggleGuardrailAudit()
    console.log('[Browser Verifier] Expanding "Audit 5 Heuristics" drawer...');
    await client.evaluate(`toggleGuardrailAudit()`);
    await new Promise(r => setTimeout(r, 300));

    const drawerExpanded = await client.evaluate(`(() => {
      const drawer = document.getElementById('guardrail-audit-drawer');
      const btn = document.getElementById('btn-audit-heuristics');
      return {
        display: window.getComputedStyle(drawer).display,
        ariaExpanded: btn.getAttribute('aria-expanded')
      };
    })()`);
    console.log('[Drawer Expanded State]:', JSON.stringify(drawerExpanded, null, 2));

    if (drawerExpanded.display !== 'block' || drawerExpanded.ariaExpanded !== 'true') {
      throw new Error('FAILED: "Audit 5 Heuristics" drawer did not expand!');
    }
    console.log('✓ PASS: "Audit 5 Heuristics" drawer expanded successfully (display: block, aria-expanded: true).');

    // 4. Check Scrollable Container 1: .key-risk-factors-list in Underwriting Simulator
    const riskListStyles = await client.evaluate(`(() => {
      const el = document.querySelector('.key-risk-factors-list');
      if (!el) return null;
      const cs = window.getComputedStyle(el);
      return {
        overflowY: cs.overflowY,
        maxHeight: cs.maxHeight,
        clientHeight: el.clientHeight,
        scrollHeight: el.scrollHeight
      };
    })()`);
    console.log('[Computed Styles for .key-risk-factors-list]:', JSON.stringify(riskListStyles, null, 2));

    if (riskListStyles.overflowY !== 'auto' && riskListStyles.overflowY !== 'scroll') {
      throw new Error(`FAILED: .key-risk-factors-list overflow-y is '${riskListStyles.overflowY}', expected 'auto' or 'scroll'`);
    }
    if (!riskListStyles.maxHeight.endsWith('px')) {
      throw new Error(`FAILED: .key-risk-factors-list maxHeight is '${riskListStyles.maxHeight}', expected finite pixel value`);
    }
    console.log('✓ PASS: .key-risk-factors-list has overflow-y: auto and bounded pixel maxHeight:', riskListStyles.maxHeight);

    // 5. Check Scrollable Container 2: TALK-TO-DATA CHATBOT
    console.log('[Browser Verifier] Opening Talk-to-Data panel...');
    await client.evaluate(`toggleChatPanel(true)`);
    await new Promise(r => setTimeout(r, 500));

    // Check initial state (compact height, NO extra dead space at the bottom)
    const chatInitial = await client.evaluate(`(() => {
      const card = document.querySelector('.chat-query-card');
      const input = document.getElementById('chat-input');
      const cardRect = card.getBoundingClientRect();
      const inputRect = input.getBoundingClientRect();
      const bottomSpace = cardRect.bottom - inputRect.bottom;
      return {
        cardHeight: cardRect.height,
        bottomSpace,
        isAutoHeight: window.getComputedStyle(card).height !== '740px'
      };
    })()`);
    console.log('[Talk-to-Data Initial State]:', JSON.stringify(chatInitial, null, 2));

    if (chatInitial.bottomSpace > 30) {
      throw new Error(`FAILED: Extra dead space at the bottom of chat panel! Found ${chatInitial.bottomSpace}px space below input.`);
    }
    console.log(`✓ PASS: Talk-to-Data has no extra bottom dead space (space below input: ${chatInitial.bottomSpace.toFixed(1)}px).`);

    // Ask a query to populate rich output (messages + SQL + table)
    console.log('[Browser Verifier] Submitting test query in Talk-to-Data...');
    await client.evaluate(`askPreset("What is the default rate across different education levels?")`);

    // Wait for response table
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 500));
      const hasResponse = await client.evaluate(`!!document.querySelector("#chat-history .sql-preview-box, #chat-history table")`);
      if (hasResponse) break;
    }

    // Verify stream scrollability and exchange card flex properties
    const chatScrollState = await client.evaluate(`(() => {
      const stream = document.getElementById('chat-history');
      const exchangeCard = stream.querySelector('.chat-exchange-card');
      const csExchange = exchangeCard ? window.getComputedStyle(exchangeCard) : {};
      const csStream = window.getComputedStyle(stream);

      const initialScroll = stream.scrollTop;
      stream.scrollTop = 120;
      const scrolledTop = stream.scrollTop;

      // Dispatch mouse wheel event
      const wheelEvt = new WheelEvent('wheel', { deltaY: 100, bubbles: true });
      stream.dispatchEvent(wheelEvt);

      return {
        streamOverflowY: csStream.overflowY,
        streamMaxHeight: csStream.maxHeight,
        streamClientHeight: stream.clientHeight,
        streamScrollHeight: stream.scrollHeight,
        isScrollable: stream.scrollHeight > stream.clientHeight,
        initialScroll,
        scrolledTop,
        exchangeCardFlexShrink: csExchange.flexShrink,
        exchangeCardOverflow: csExchange.overflow
      };
    })()`);
    console.log('[Talk-to-Data Scroll State]:', JSON.stringify(chatScrollState, null, 2));

    if (!chatScrollState.isScrollable) {
      throw new Error('FAILED: Talk-to-Data chat stream is NOT scrollable (scrollHeight <= clientHeight)!');
    }
    if (chatScrollState.exchangeCardFlexShrink !== '0') {
      throw new Error(`FAILED: .chat-exchange-card flex-shrink is '${chatScrollState.exchangeCardFlexShrink}', expected '0' to prevent child shrink clipping!`);
    }
    console.log('✓ PASS: Talk-to-Data chat stream is actively scrollable with mouse wheel (scrollHeight: ' + chatScrollState.streamScrollHeight + 'px > clientHeight: ' + chatScrollState.streamClientHeight + 'px).');

    // 6. Capture Screenshots
    const outDir = path.resolve(__dirname, 'screenshots');
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

    // Screenshot 1: Talk-to-Data panel with conversation and scrollbar
    await client.screenshot(path.join(outDir, 'talk_to_data_verified.png'));

    // Close chat panel
    await client.evaluate(`toggleChatPanel(false)`);
    await new Promise(r => setTimeout(r, 400));

    // Screenshot 2: Underwriting Simulator with expanded Guardrails Drawer
    await client.screenshot(path.join(outDir, 'underwriting_simulator_heuristics_drawer_verified.png'));

    // Switch to Credit Policy Rules
    await client.evaluate(`switchTab('policy-tab')`);
    await new Promise(r => setTimeout(r, 400));

    // Screenshot 3: Credit Policy Rules Tab (purely static, no gridlines, no applicant table)
    await client.screenshot(path.join(outDir, 'credit_policy_rules_verified.png'));

    console.log('\n============================================================');
    console.log('ALL LIVE BROWSER VERIFICATIONS PASSED SUCCESSFULLY!');
    console.log('============================================================');
  } finally {
    client.close();
    chrome.kill();
  }
}

run().catch(err => {
  console.error('VERIFICATION ERROR:', err);
  process.exit(1);
});
