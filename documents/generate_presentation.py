"""
Generate a professional 10-slide executive presentation PDF for NeoStats.
Uses ReportLab with custom canvas drawing, sleek styling, and embedded high-res plots.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so script executes cleanly standalone without PYTHONPATH=.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas
from src.utils.config import BASE_DIR, MODELS_DIR

# Paths
OUTPUT_PDF = BASE_DIR / "documents/project_presentation.pdf"
PLOTS_DIR = BASE_DIR / "notebooks/plots"
OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)

# Slide Dimensions (Landscape Letter: 11 x 8.5 in -> 792 x 612 pt)
PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)

# Color Palette
NAVY_DARK = colors.HexColor("#0B192C")
NAVY_PRIMARY = colors.HexColor("#1E3E62")
TEAL_ACCENT = colors.HexColor("#00ADB5")
SLATE_DARK = colors.HexColor("#111827")
SLATE_GRAY = colors.HexColor("#4B5563")
SLATE_LIGHT = colors.HexColor("#F3F4F6")
BG_CARD = colors.HexColor("#F8FAFC")
WHITE = colors.HexColor("#FFFFFF")
RED_ALERT = colors.HexColor("#EF4444")
GREEN_SAFE = colors.HexColor("#10B981")
AMBER_WARN = colors.HexColor("#F59E0B")
BORDER_COLOR = colors.HexColor("#E2E8F0")


def draw_cover_background(canvas_obj, doc_obj):
    """Draw dark background on slide 1 before flowables are rendered."""
    canvas_obj.saveState()
    canvas_obj.setFillColor(NAVY_DARK)
    canvas_obj.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
    # Teal and navy accent strips
    canvas_obj.setFillColor(TEAL_ACCENT)
    canvas_obj.rect(0, PAGE_HEIGHT - 8, PAGE_WIDTH, 8, fill=True, stroke=False)
    canvas_obj.rect(40, PAGE_HEIGHT - 210, 6, 95, fill=True, stroke=False)
    canvas_obj.setFillColor(NAVY_PRIMARY)
    canvas_obj.rect(0, 0, PAGE_WIDTH, 14, fill=True, stroke=False)
    canvas_obj.restoreState()


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that adds slide header and footer on each page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_slide_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_slide_decorations(self, total_pages):
        page_num = self._pageNumber
        if page_num == 1:
            # Cover decorations already drawn in draw_cover_background
            return

        # Regular slides 2 to 10
        self.saveState()

        # Header bar
        self.setFillColor(NAVY_PRIMARY)
        self.rect(0, PAGE_HEIGHT - 40, PAGE_WIDTH, 40, fill=True, stroke=False)
        self.setFillColor(TEAL_ACCENT)
        self.rect(0, PAGE_HEIGHT - 43, PAGE_WIDTH, 3, fill=True, stroke=False)

        # Header Title text
        self.setFillColor(WHITE)
        self.setFont("Helvetica-Bold", 10.5)
        self.drawString(40, PAGE_HEIGHT - 25, "NEOSTATS")
        self.setFillColor(TEAL_ACCENT)
        self.setFont("Helvetica", 10.5)
        self.drawString(106, PAGE_HEIGHT - 25, "|   AI-Powered Credit Risk Intelligence Platform")

        # Footer bar
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.8)
        self.line(40, 28, PAGE_WIDTH - 40, 28)

        # Footer text
        self.setFillColor(SLATE_GRAY)
        self.setFont("Helvetica", 8)
        self.drawString(40, 16, "Candidate: Saurabh Burnwal  |  Role: AI/ML Engineer Intern  |  Confidential & Proprietary")
        page_str = f"Slide {page_num} of {total_pages}"
        self.drawRightString(PAGE_WIDTH - 40, 16, page_str)

        self.restoreState()


def build_presentation():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=landscape(letter),
        leftMargin=40,
        rightMargin=40,
        topMargin=54,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_cover = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=WHITE,
    )

    subtitle_cover = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#CBD5E1"),
    )

    slide_title = ParagraphStyle(
        "SlideTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=NAVY_DARK,
        spaceAfter=4,
    )

    slide_subtitle = ParagraphStyle(
        "SlideSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=SLATE_GRAY,
        spaceAfter=10,
    )

    heading_box = ParagraphStyle(
        "HeadingBox",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=NAVY_PRIMARY,
        spaceAfter=4,
    )

    body_text = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=SLATE_DARK,
    )

    body_bold = ParagraphStyle(
        "BodyBoldCustom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12.5,
        textColor=SLATE_DARK,
    )

    bullet_text = ParagraphStyle(
        "BulletTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=SLATE_DARK,
    )

    metric_val = ParagraphStyle(
        "MetricValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=NAVY_PRIMARY,
        alignment=1,
    )

    metric_lbl = ParagraphStyle(
        "MetricLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=SLATE_GRAY,
        alignment=1,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=SLATE_DARK,
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=NAVY_PRIMARY,
    )

    story = []

    # =========================================================================
    # SLIDE 1: COVER SLIDE
    # =========================================================================
    story.append(Spacer(1, 100))
    story.append(Paragraph("AI-Powered Credit Risk<br/>Intelligence Platform", title_cover))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "End-to-End Predictive Modeling, Explainable AI (SHAP), Rule-Based Policy Engine,<br/>"
        "and Conversational NL-to-SQL Analytics on Home Credit Default Risk Dataset",
        subtitle_cover
    ))
    story.append(Spacer(1, 60))

    meta_data = [
        [
            Paragraph("<b>Candidate Name:</b> Saurabh Burnwal", ParagraphStyle("C1", parent=body_text, textColor=WHITE, fontSize=10, leading=14)),
            Paragraph("<b>Position:</b> AI/ML Engineer Intern", ParagraphStyle("C2", parent=body_text, textColor=WHITE, fontSize=10, leading=14)),
        ],
        [
            Paragraph("<b>Company:</b> NeoStats Solutions", ParagraphStyle("C3", parent=body_text, textColor=WHITE, fontSize=10, leading=14)),
            Paragraph("<b>Submission Date:</b> September 2026", ParagraphStyle("C4", parent=body_text, textColor=WHITE, fontSize=10, leading=14)),
        ],
        [
            Paragraph("<b>Dataset Scale:</b> 307,511 Loans (Full Dataset)", ParagraphStyle("C5", parent=body_text, textColor=WHITE, fontSize=10, leading=14)),
            Paragraph("<b>Core Stack:</b> LightGBM • SHAP • Flask • SQLite • Groq/Ollama • uv", ParagraphStyle("C6", parent=body_text, textColor=TEAL_ACCENT, fontSize=10, leading=14)),
        ]
    ]
    t_meta = Table(meta_data, colWidths=[330, 370])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#132743")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E3E62")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#1E3E62")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 16),
        ('RIGHTPADDING', (0,0), (-1,-1), 16),
    ]))
    story.append(t_meta)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: BUSINESS CONTEXT & PROBLEM STATEMENT
    # =========================================================================
    story.append(Paragraph("01. Business Context & Problem Statement", slide_title))
    story.append(Paragraph("Navigating the Underwriting Trade-off: Mitigating Asymmetric Default Losses while Expanding Credit Inclusion", slide_subtitle))

    # Metric Cards Top Row
    m1 = [
        [Paragraph("8.07%", metric_val)],
        [Paragraph("BASELINE DEFAULT RATE<br/>(11.39:1 Imbalance)", metric_lbl)]
    ]
    m2 = [
        [Paragraph("307,511", metric_val)],
        [Paragraph("HISTORICAL APPLICANTS<br/>Trained Without Sampling", metric_lbl)]
    ]
    m3 = [
        [Paragraph("5x – 8x", metric_val)],
        [Paragraph("ASYMMETRIC LOSS COST<br/>False Negatives vs False Positives", metric_lbl)]
    ]
    m4 = [
        [Paragraph("100% Audit", metric_val)],
        [Paragraph("REGULATORY COMPLIANCE<br/>FCRA / ECOA SHAP Mandate", metric_lbl)]
    ]

    metric_row = Table([[Table(m1, colWidths=[165]), Table(m2, colWidths=[165]), Table(m3, colWidths=[165]), Table(m4, colWidths=[165])]], colWidths=[175, 175, 175, 175])
    metric_row.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(metric_row)
    story.append(Spacer(1, 14))

    # 2 Column Body
    col1_content = [
        Paragraph("<b>The Lending Dilemma in Thin-File Populations</b>", heading_box),
        Paragraph(
            "Traditional credit bureaus systematically exclude thin-file, unbanked individuals due to lack of standard credit bureau histories. "
            "Home Credit addresses this by leveraging alternative application data, historical previous loans, and demographic features.",
            bullet_text
        ),
        Spacer(1, 6),
        Paragraph("<b>The Asymmetry of Credit Risk Errors</b>", heading_box),
        Paragraph(
            "• <b>Type II Error (False Negative):</b> Approving an applicant who defaults causes catastrophic capital loss (typically 80%–100% of loan principal loss).<br/>"
            "• <b>Type I Error (False Positive):</b> Rejecting a creditworthy applicant incurs opportunity cost (forgone 10%–15% net interest margin).<br/>"
            "• <i>Imperative:</i> The model must optimize for high recall on defaulters (KS statistic & PR-AUC) without paralyzing loan origination volume.",
            bullet_text
        ),
    ]

    col2_content = [
        Paragraph("<b>Enterprise Requirements & Objectives</b>", heading_box),
        Paragraph(
            "<b>1. Calibrated Predictive Modeling:</b> Produce genuine default probabilities, resolving the distortion created by class imbalance reweighting.",
            bullet_text
        ),
        Paragraph(
            "<b>2. Explainability & Fair Lending:</b> Every automated credit score must produce local SHAP force explanations, providing clear adverse action factors for declined borrowers.",
            bullet_text
        ),
        Paragraph(
            "<b>3. Actionable Underwriting Policy Rules:</b> Convert raw probabilities into 3 discrete risk bands (Low, Medium, High) with ML decision-support guardrails.",
            bullet_text
        ),
        Paragraph(
            "<b>4. Conversational Executive Access:</b> Empower non-technical risk executives to query portfolio data through safe, read-only Natural Language to SQL.",
            bullet_text
        ),
    ]

    story.append(Table([[col1_content, col2_content]], colWidths=[350, 350], style=[
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: END-TO-END SYSTEM ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("02. End-to-End System Architecture", slide_title))
    story.append(Paragraph("Modular, Production-Ready Architecture: From Multi-Table Data Aggregations to Explainable Scoring and NL-to-SQL", slide_subtitle))

    arch_layers = [
        [
            Paragraph("<b>Layer 1: Data Pipeline & Relational Store</b>", heading_box),
            Paragraph(
                "• Ingests 307,511 primary applications joined with aggregated Bureau loans and Previous Applications.<br/>"
                "• Resolves the 365,243-day anomaly (`DAYS_EMPLOYED_ANOM=1`, NaN imputation).<br/>"
                "• Persists engineered analytics tables into SQLite (indexed on `SK_ID_CURR`, `TARGET`, `OCCUPATION_TYPE`).",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Layer 2: ML Engine & Bayes Odds Calibrator</b>", heading_box),
            Paragraph(
                "• Champion LightGBM classifier trained with <code>scale_pos_weight = 11.39</code>.<br/>"
                "• Bayesian Odds Calibration: Rescales shifted boosting scores to unbiased real-world default probabilities (P &lt; 5%, 5% &le; P &lt; 15%, P &ge; 15%).<br/>"
                "• Pre-computes SHAP TreeExplainer explainer models for real-time attribution.",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Layer 3: Credit Policy Engine (Rules + Scoring)</b>", heading_box),
            Paragraph(
                "• 5 Operational Decision-Support Guardrails: High DTI (&gt;40%), Weak Bureau Score (&lt;0.35), Active Overdue Debt (&gt;$0), Unstable Young Tenure (&lt;25y, &lt;1y emp), and Payment Rate Stress (&gt;8%).<br/>"
                "• Decision Hierarchy Synthesis: P &lt; 5% with 0 alerts triggers Fast-Track STP Approval; any alert routes to Manual Underwriter Review; P &ge; 15% with alerts triggers Strict Decline.",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Layer 4: Conversational Talk-to-Data (NL-to-SQL)</b>", heading_box),
            Paragraph(
                "• 3-Tier Cascading Architecture: Tier 1 (Groq Cloud openai/gpt-oss-120b) &rarr; Tier 2 (Local Ollama Ministral-3:3B) &rarr; Tier 3 (Deterministic AST Compiler).<br/>"
                "• Security AST Single-SELECT Whitelist Validator: Blocks comments, semicolons, and modifications with read-only SQLite execution.",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Layer 5: Modern UI Redesign & REST API</b>", heading_box),
            Paragraph(
                "• Modern Decision-Support Workspace: Warm-ivory & champagne-gold design system with progressive motion and 4 guided tabs (Executive EDA, Underwriting Simulator, Explainable AI, Policy Rules).<br/>"
                "• Global Floating Talk-to-Data Launcher (<code>chat-launcher</code>) opening interactive sliding conversational NL-to-SQL panel with formatted SQL, data tables, and latency badges.<br/>"
                "• Versioned Flask REST API (<code>/api/v1/predict</code>, <code>/api/v1/query</code>, <code>/health</code>).",
                bullet_text
            )
        ],
    ]

    t_arch = Table(arch_layers, colWidths=[200, 500])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), BG_CARD),
        ('BACKGROUND', (1,0), (1,-1), WHITE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_arch)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: EXPLORATORY DATA ANALYSIS & 5 KEY FINDINGS
    # =========================================================================
    story.append(Paragraph("03. Exploratory Data Analysis & Key Domain Insights", slide_title))
    story.append(Paragraph("Empirical Verification of Credit Risk Drivers Across 307,511 Historical Borrowers", slide_subtitle))

    # We will display 2 images side by side or 1 image + detailed insight table
    img1_path = str(PLOTS_DIR / "insight1_ext_scores.png")
    img2_path = str(PLOTS_DIR / "insight2_debt_stress.png")

    img_table = Table([[
        Image(img1_path, width=340, height=185),
        Image(img2_path, width=340, height=185)
    ]], colWidths=[350, 350])
    img_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(img_table)
    story.append(Spacer(1, 10))

    eda_insights_data = [
        [
            Paragraph("<b>Finding 1: External Credit Bureau Scores</b>", table_cell_bold),
            Paragraph("EXT_SOURCE_1, 2, 3 show the highest rank correlation with default. Borrowers in the bottom decile default at >22.4%, compared to <2.1% in the top decile.", table_cell),
        ],
        [
            Paragraph("<b>Finding 2: Payment Rate & Debt Stress</b>", table_cell_bold),
            Paragraph("Payment Rate (Annuity / Credit) above 8% indicates extreme cash flow compression. Default rates double from 5.2% to 11.8% as payment obligations mount.", table_cell),
        ],
        [
            Paragraph("<b>Finding 3: The 365,243-Day Anomaly</b>", table_cell_bold),
            Paragraph("55,374 applicants had DAYS_EMPLOYED = 365,243 (exactly 1,000 years). This is a legacy code for pensioners/unemployed. Replacing with NaN + `DAYS_EMPLOYED_ANOM=1` restored true signal.", table_cell),
        ],
        [
            Paragraph("<b>Finding 4: Bureau Overdue Contagion</b>", table_cell_bold),
            Paragraph("Applicants with prior overdue debt in external credit bureaus default at 18.2%, compared to 7.8% for clean bureau histories. Maximum overdue days is a critical guardrail feature.", table_cell),
        ],
        [
            Paragraph("<b>Finding 5: Education & Income Tiers</b>", table_cell_bold),
            Paragraph("Academic degree holders exhibit the lowest default rate (1.8%), whereas lower secondary applicants default at 10.9%. Education acts as a resilient buffer across economic cycles.", table_cell),
        ]
    ]
    t_eda = Table(eda_insights_data, colWidths=[200, 500])
    t_eda.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), BG_CARD),
        ('BACKGROUND', (1,0), (1,-1), WHITE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_eda)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5: ML MODEL DESIGN & CLASS IMBALANCE STRATEGY
    # =========================================================================
    story.append(Paragraph("04. Machine Learning Model Design & Imbalance Strategy", slide_title))
    story.append(Paragraph("Resolving Severe Class Imbalance (11.4:1) with LightGBM and Prior-Odds Probability Calibration", slide_subtitle))

    img_feat_path = str(PLOTS_DIR / "feature_importance.png")

    col_ml_text = [
        Paragraph("<b>Addressing Class Imbalance (8.07% Defaulters)</b>", heading_box),
        Paragraph(
            "• <b>Problem with Naive Resampling:</b> Synthetic oversampling (SMOTE) on 307k rows induces artificial variance and extreme computational overhead. Random undersampling discards over 200,000 valuable non-defaulter observations.<br/>"
            "• <b>Cost-Sensitive Gradient Boosting:</b> We configured LightGBM with <code>scale_pos_weight = 11.39</code>, penalizing false negatives by exactly the inverse class ratio. This pushes the tree split gains toward separating rare defaulters.",
            bullet_text
        ),
        Spacer(1, 8),
        Paragraph("<b>Bayesian Odds Probability Calibration</b>", heading_box),
        Paragraph(
            "Because <code>scale_pos_weight</code> artificially inflates raw predicted probabilities (shifting mean probability from ~0.08 to ~0.50), raw outputs cannot be directly used for credit limits.<br/>"
            "We apply exact prior odds rescaling:<br/>"
            "<b>P_calibrated = 1 / (1 + ((1 - P_raw) / P_raw) × (w_pos / w_neg))</b><br/>"
            "This preserves monotonic ROC-AUC ranking while restoring statistically sound probabilities that align with portfolio default rates.",
            bullet_text
        ),
        Spacer(1, 8),
        Paragraph("<b>Reconciled Feature Matrix (142 Total Features)</b>", heading_box),
        Paragraph(
            "• <b>Explicit Feature Arithmetic:</b> 119 raw + 13 engineered domain + 5 bureau + 5 previous loans = <b>142 features total</b> (127 numerical, 15 categorical).<br/>"
            "• <b>Native NaN Handling:</b> LightGBM histogram binning routes missing values natively during tree splits, retaining all 41 columns with &gt;50% missingness without synthetic distortion.<br/>"
            "• <b>Key Predictive Drivers:</b> <code>PAYMENT_RATE</code> (Annuity / Credit), <code>EXT_SOURCES_MEAN</code>, <code>DAYS_BIRTH</code>, and <code>GOODS_PRICE_TO_CREDIT</code>.",
            bullet_text
        ),
    ]

    t_slide5 = Table([[col_ml_text, Image(img_feat_path, width=340, height=260)]], colWidths=[355, 345])
    t_slide5.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_slide5)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6: MODEL PERFORMANCE & BENCHMARKS
    # =========================================================================
    story.append(Paragraph("05. Model Benchmarks & Risk Band Validation", slide_title))
    story.append(Paragraph("Rigorous Out-of-Sample Evaluation on 61,503 Test Applicants", slide_subtitle))

    # Comparison Table
    bench_table_data = [
        [
            Paragraph("<b>Evaluation Metric</b>", table_cell_bold),
            Paragraph("<b>Logistic Regression (Baseline)</b>", table_cell_bold),
            Paragraph("<b>LightGBM (Champion)</b>", table_cell_bold),
            Paragraph("<b>Relative Gain / Business Impact</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>ROC-AUC</b>", table_cell),
            Paragraph("0.7564", table_cell),
            Paragraph("<b>0.7717</b>", table_cell_bold),
            Paragraph("+1.53 pts (Superior non-linear ranking)", table_cell),
        ],
        [
            Paragraph("<b>PR-AUC (Average Precision)</b>", table_cell),
            Paragraph("0.2410", table_cell),
            Paragraph("<b>0.2667</b>", table_cell_bold),
            Paragraph("+10.7% relative gain on minority defaulters", table_cell),
        ],
        [
            Paragraph("<b>KS Statistic (%)</b>", table_cell),
            Paragraph("38.08%", table_cell),
            Paragraph("<b>40.67%</b>", table_cell_bold),
            Paragraph("Observed empirical test separation (maximum CDF divergence)", table_cell),
        ],
        [
            Paragraph("<b>Brier Score (Calibration)</b>", table_cell),
            Paragraph("0.1982", table_cell),
            Paragraph("<b>0.1867</b>", table_cell_bold),
            Paragraph("High probability calibration accuracy", table_cell),
        ],
        [
            Paragraph("<b>Training Time (307k rows)</b>", table_cell),
            Paragraph("48.2s", table_cell),
            Paragraph("<b>33.9s</b>", table_cell_bold),
            Paragraph("Histogram binning yields 30% faster convergence", table_cell),
        ],
    ]
    t_bench = Table(bench_table_data, colWidths=[150, 160, 160, 230])
    t_bench.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_bench)
    story.append(Spacer(1, 10))

    # Bottom Visuals: Risk Band Chart & Confusion Matrix
    img_risk_path = str(PLOTS_DIR / "risk_band_distribution.png")
    img_cm_path = str(PLOTS_DIR / "confusion_matrix.png")

    bottom_visuals = Table([[
        Image(img_risk_path, width=390, height=200),
        Image(img_cm_path, width=290, height=200)
    ]], colWidths=[400, 300])
    bottom_visuals.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(bottom_visuals)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7: EXPLAINABLE AI & MODEL GOVERNANCE (SHAP)
    # =========================================================================
    story.append(Paragraph("06. Explainable AI & Governance (SHAP TreeExplainer)", slide_title))
    story.append(Paragraph("Meeting Regulatory Mandates: Adverse Action Transparency via Game-Theoretic Attributions", slide_subtitle))

    shap_cards = [
        [
            Paragraph("<b>Regulatory Imperative (FCRA & ECOA)</b>", heading_box),
            Paragraph(
                "• The Fair Credit Reporting Act (FCRA) and Equal Credit Opportunity Act (ECOA) require lenders to issue <b>Adverse Action Notices</b> detailing the top key factors causing a credit denial.<br/>"
                "• Black-box machine learning models cannot be deployed in regulated banking without auditable, mathematically consistent local feature explanations.",
                bullet_text
            )
        ],
        [
            Paragraph("<b>TreeSHAP Implementation & Performance</b>", heading_box),
            Paragraph(
                "• Implemented <code>shap.TreeExplainer</code> optimized for tree-based ensemble models.<br/>"
                "• Sub-second local explanation latency (~120ms per borrower) enables real-time waterfall rendering during online underwriting.<br/>"
                "• Explains the log-odds margin divergence from expected value E[f(x)] to individual prediction f(x).",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Natural Language Translation Engine</b>", heading_box),
            Paragraph(
                "• Raw SHAP coefficients (e.g. <code>PAYMENT_RATE = +0.42</code>) are incomprehensible to consumers.<br/>"
                "• The platform automatically parses positive/negative Shapley values into human-readable business narratives:<br/>"
                "  – <i>'High annual annuity relative to loan principal signals repayment debt stress.'</i><br/>"
                "  – <i>'Low external credit score ratings from credit bureaus significantly elevate default probability.'</i><br/>"
                "  – <i>'Longer employment stability and mature age buffer against default risk.'</i>",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Global Feature Attributions (Key Risk Drivers)</b>", heading_box),
            Paragraph(
                "1. <b>PAYMENT_RATE (853 splits):</b> Monthly repayment burden.<br/>"
                "2. <b>EXT_SOURCES_MEAN (382 splits):</b> Cross-bureau composite score.<br/>"
                "3. <b>EXT_SOURCE_3 & EXT_SOURCE_1:</b> External bureau credit quality.<br/>"
                "4. <b>GOODS_PRICE_TO_CREDIT:</b> Down-payment buffer on goods purchased.<br/>"
                "5. <b>DAYS_BIRTH (Age):</b> Younger borrowers exhibit higher relative default tendency.",
                bullet_text
            )
        ]
    ]
    t_shap = Table(shap_cards, colWidths=[210, 490])
    t_shap.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), BG_CARD),
        ('BACKGROUND', (1,0), (1,-1), WHITE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_shap)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 8: CREDIT POLICY & UNDERWRITING DECISION RULES
    # =========================================================================
    story.append(Paragraph("07. ML Decision-Support Guardrails & Risk Bands", slide_title))
    story.append(Paragraph("Hybrid Decision Architecture: 5 Operational Guardrails Synthesized with 3 Calibrated Risk Tiers", slide_subtitle))

    guardrails_table_data = [
        [
            Paragraph("<b>Guardrail ID</b>", table_cell_bold),
            Paragraph("<b>Rule & Threshold</b>", table_cell_bold),
            Paragraph("<b>Severity</b>", table_cell_bold),
            Paragraph("<b>Empirical & Banking Rationale</b>", table_cell_bold),
            Paragraph("<b>Operational Mandate</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>FLAG_HIGH_DTI</b>", table_cell_bold),
            Paragraph("DTI (Annuity / Income) &gt; 40%", table_cell),
            Paragraph("<font color='#EF4444'><b>HIGH</b></font>", table_cell),
            Paragraph("DTI &gt; 40% elevates default rate to 12.4% vs 6.1% baseline.", table_cell),
            Paragraph("Manual Underwriter Review", table_cell),
        ],
        [
            Paragraph("<b>FLAG_LOW_EXT_SOURCE</b>", table_cell_bold),
            Paragraph("EXT_SOURCES_MEAN &lt; 0.35", table_cell),
            Paragraph("<font color='#EF4444'><b>HIGH</b></font>", table_cell),
            Paragraph("Bureau composite &lt; 0.35 represents &gt;10x default spread (22.4% vs 1.8%).", table_cell),
            Paragraph("Committee Review Required", table_cell),
        ],
        [
            Paragraph("<b>FLAG_PAST_DUE</b>", table_cell_bold),
            Paragraph("BUREAU_TOTAL_OVERDUE &gt; $0", table_cell),
            Paragraph("<font color='#DC2626'><b>CRITICAL</b></font>", table_cell),
            Paragraph("Active external overdue debt doubles default risk (18.2% vs 7.8%).", table_cell),
            Paragraph("Mandatory Review / Stricter Terms", table_cell),
        ],
        [
            Paragraph("<b>FLAG_UNSTABLE_TENURE</b>", table_cell_bold),
            Paragraph("Age &lt; 25 &amp; Employed &lt; 1 yr", table_cell),
            Paragraph("<font color='#F59E0B'><b>MEDIUM</b></font>", table_cell),
            Paragraph("Young thin-file applicants carry elevated income & repayment volatility.", table_cell),
            Paragraph("Guarantor / Diligence Check", table_cell),
        ],
        [
            Paragraph("<b>FLAG_PAYMENT_RATE_STRESS</b>", table_cell_bold),
            Paragraph("Payment Rate (Annuity/Credit) &gt; 8%", table_cell),
            Paragraph("<font color='#F59E0B'><b>MEDIUM</b></font>", table_cell),
            Paragraph("Accelerated amortization schedule doubles default hazard (11.8% vs 5.2%).", table_cell),
            Paragraph("Debt Capacity Re-evaluation", table_cell),
        ],
    ]
    t_guardrails = Table(guardrails_table_data, colWidths=[142, 126, 58, 235, 146])
    t_guardrails.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_guardrails)
    story.append(Spacer(1, 8))

    bands_table_data = [
        [
            Paragraph("<b>Calibrated Risk Band</b>", table_cell_bold),
            Paragraph("<b>Calibrated Prob</b>", table_cell_bold),
            Paragraph("<b>Pop. Share</b>", table_cell_bold),
            Paragraph("<b>Realized Default</b>", table_cell_bold),
            Paragraph("<b>Defaulter Capture</b>", table_cell_bold),
            Paragraph("<b>Integrated Underwriting Decision</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>Low Risk</b>", table_cell_bold),
            Paragraph("P &lt; 5.0%", table_cell),
            Paragraph("50.9%", table_cell),
            Paragraph("2.67%", table_cell),
            Paragraph("16.9%", table_cell),
            Paragraph("<font color='#10B981'><b>Fast-Track STP Approval</b></font> (if 0 guardrail alerts)", table_cell),
        ],
        [
            Paragraph("<b>Medium Risk</b>", table_cell_bold),
            Paragraph("5.0% &le; P &lt; 15.0%", table_cell),
            Paragraph("35.7%", table_cell),
            Paragraph("9.08%", table_cell),
            Paragraph("40.1%", table_cell),
            Paragraph("<font color='#F59E0B'><b>Conditional Review / Standard Underwriting</b></font>", table_cell),
        ],
        [
            Paragraph("<b>High Risk</b>", table_cell_bold),
            Paragraph("P &ge; 15.0%", table_cell),
            Paragraph("13.4%", table_cell),
            Paragraph("25.90%", table_cell),
            Paragraph("<b>43.1%</b>", table_cell_bold),
            Paragraph("<font color='#EF4444'><b>Strict Underwrite / Decline / Adverse Action Notice</b></font>", table_cell),
        ],
    ]
    t_bands = Table(bands_table_data, colWidths=[105, 95, 75, 90, 95, 247])
    t_bands.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_CARD),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_bands)
    story.append(Spacer(1, 8))

    exec_summary_box = [
        [
            Paragraph(
                "<b>Decision Synthesis Hierarchy (src/ml/predict.py):</b> "
                "P &lt; 5% with 0 guardrail alerts triggers <b>Fast-Track STP Approval</b> (50.9% share, 2.67% realized default). "
                "Any triggered guardrail alert elevates the applicant to <b>Manual Underwriter Review</b>. "
                "P &ge; 15% combined with guardrail alerts triggers <b>Strict Decline</b>, isolating <b>43.1% of all defaulters</b> in just 13.4% of applicant volume.",
                body_text
            )
        ]
    ]
    t_box = Table(exec_summary_box, colWidths=[707])
    t_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#3B82F6")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_box)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 9: CONVERSATIONAL TALK-TO-DATA (NL-TO-SQL)
    # =========================================================================
    story.append(Paragraph("08. Conversational Analytics (Talk-to-Data NL-to-SQL)", slide_title))
    story.append(Paragraph("Safe, Multi-Tier AI Query Assistant with Strict AST Whitelist Guardrails", slide_subtitle))

    col_talk_left = [
        Paragraph("<b>3-Tier Cascading Fallback Architecture</b>", heading_box),
        Paragraph(
            "• <b>Tier 1: Cloud LLM (Groq Cloud openai/gpt-oss-120b):</b> High-speed Groq LPU inference (~1.2s latency) for complex multi-group analytical queries.<br/>"
            "• <b>Tier 2: Local LLM (Ollama Ministral-3:3B):</b> Privacy-preserving, fully offline fallback running on local host with zero data leakage.<br/>"
            "• <b>Tier 3: Deterministic AST Compiler:</b> Keyword regex & semantic parser that guarantees 100% SLA uptime even during total LLM outages.",
            bullet_text
        ),
        Spacer(1, 8),
        Paragraph("<b>AST Single-SELECT Whitelist Security</b>", heading_box),
        Paragraph(
            "• <b>sqlparse AST Analysis:</b> Inspects parsed syntax tree to enforce exactly one root <code>SELECT</code> statement.<br/>"
            "• <b>SQL Injection Hardening:</b> Rejects semicolons (<code>;</code>), comment tokens (<code>--</code>, <code>/* */</code>), and administrative/mutation commands (<code>DROP</code>, <code>DELETE</code>, <code>INSERT</code>, <code>UPDATE</code>, <code>ATTACH</code>).<br/>"
            "• <b>Read-Only Execution:</b> SQLite URI opened with <code>mode=ro</code>, preventing write hazards at the operating system driver level.",
            bullet_text
        ),
    ]

    col_talk_right = [
        Paragraph("<b>Validated Analytical Query Patterns</b>", heading_box),
        Paragraph("<b>1. Education Level Default Analysis:</b><br/><code>SELECT NAME_EDUCATION_TYPE, COUNT(*), ROUND(AVG(TARGET)*100, 2) FROM applications GROUP BY 1</code>", bullet_text),
        Spacer(1, 4),
        Paragraph("<b>2. Debt Burden by Income Segment:</b><br/><code>SELECT NAME_INCOME_TYPE, ROUND(AVG(AMT_CREDIT), 2), ROUND(AVG(TARGET)*100, 2) FROM applications GROUP BY 1</code>", bullet_text),
        Spacer(1, 4),
        Paragraph("<b>3. Bureau Overdue Risk Divergence:</b><br/><code>SELECT CASE WHEN BUREAU_TOTAL_OVERDUE &gt; 0 THEN 'Has Overdue' ELSE 'Clean' END, ROUND(AVG(TARGET)*100, 2) FROM applications GROUP BY 1</code>", bullet_text),
        Spacer(1, 6),
        Paragraph("<b>Automated Business Narrative Synthesis</b>", heading_box),
        Paragraph("The agent does not merely dump tabular numbers; it computes statistical comparisons and synthesizes an executive summary highlighting actionable takeaways for credit officers.", bullet_text),
    ]

    t_talk = Table([[col_talk_left, col_talk_right]], colWidths=[350, 350])
    t_talk.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_talk)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 10: PRODUCTION DEPLOYMENT & FUTURE ROADMAP
    # =========================================================================
    story.append(Paragraph("09. Modern UI Redesign, Deployment & Limitations", slide_title))
    story.append(Paragraph("Warm-Ivory Decision Workspace, uv Reproducibility, and Candid Engineering Trade-offs", slide_subtitle))

    dep_cards = [
        [
            Paragraph("<b>Modern UI Redesign & Workspace Architecture</b>", heading_box),
            Paragraph(
                "• <b>Warm-Ivory & Champagne-Gold Theme:</b> Modern design system (<code>#F5F0E8</code>, gold <code>#C79A4A</code>, green <code>#078A63</code>) with progressive motion and Inter typography.<br/>"
                "• <b>4 Primary Workspace Tabs:</b> Executive EDA, Underwriting Simulator, Explainable AI, and Credit Policy Rules with guided hierarchy hooks.<br/>"
                "• <b>Global Floating Assistant:</b> Talk-to-Data launcher (<code>chat-launcher</code>) opening sliding NL-to-SQL conversational drawer.<br/>"
                "• <b>Evaluator Usability:</b> Quick-Load benchmark applicants (#100001, #100005, #100013, #100028), unconstrained decimal inputs, modular Jinja2 partials.",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Modern Packaging with uv & Lockfile</b>", heading_box),
            Paragraph(
                "• <b>Reproducibility:</b> Entire dependency tree locked via <code>uv.lock</code>, preventing transitive dependency drift across environments.<br/>"
                "• <b>Multi-Stage Docker Image:</b> Binary copy from <code>ghcr.io/astral-sh/uv:latest</code>. <code>uv sync --frozen</code> reduces build times from minutes to &lt;25 seconds.<br/>"
                "• <b>Dynamic Database Compilation:</b> Automatically builds and indexes SQLite store from raw CSVs on boot (zero binary DBs in git).",
                bullet_text
            )
        ],
        [
            Paragraph("<b>3-Tier Conversational Provider Extensibility</b>", heading_box),
            Paragraph(
                "• <b>Multi-Tier Cascade:</b> Operational Groq Cloud (<code>openai/gpt-oss-120b</code>) and local Ollama (<code>ministral-3:3b</code>) connectors with self-healing feedback loop.<br/>"
                "• <b>AST Single-SELECT Whitelist:</b> Rejects semicolons, comments, and mutation keywords; read-only SQLite execution (<code>mode=ro</code>).<br/>"
                "• <b>Deterministic AST Fallback:</b> Certified regex and AST compiler guaranteeing 100% SLA uptime even during total LLM outages.",
                bullet_text
            )
        ],
        [
            Paragraph("<b>Candid Technical Limitations & Trade-offs</b>", heading_box),
            Paragraph(
                "1. <b>Secondary Table Aggregations:</b> Engineered 5 key summary metrics from bureau and previous applications; omitted temporal sequence modeling over monthly installments to preserve sub-second scoring.<br/>"
                "2. <b>Single-Table Analytics Denormalization:</b> Pre-joined SQLite store ensures sub-second queries and eliminates multi-table join injection risks.<br/>"
                "3. <b>Static Bayesian Prior Odds:</b> Assumes steady ~8.07% portfolio default rate; macroeconomic regime shifts require periodic rolling recalibration.<br/>"
                "4. <b>Tabular-Only Local SHAP:</b> Explains observable gradient contributions, but cannot detect unmeasured latent socioeconomic factors.",
                bullet_text
            )
        ]
    ]
    t_dep = Table(dep_cards, colWidths=[220, 480])
    t_dep.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), BG_CARD),
        ('BACKGROUND', (1,0), (1,-1), WHITE),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_dep)

    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=draw_cover_background)
    print(f"Successfully generated presentation PDF: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_presentation()
