import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def build_presentation(output_path="JEE_Performance_Engine_6_Slides.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Clean, modern, minimalist color palette
    BG_COLOR = RGBColor(248, 250, 252)        # #F8FAFC (Soft slate canvas)
    CARD_BG = RGBColor(255, 255, 255)         # Pure White
    CARD_BORDER = RGBColor(226, 232, 240)     # #E2E8F0 (Crisp subtle border)
    TEXT_DARK = RGBColor(15, 23, 42)          # #0F172A (Deep Slate)
    TEXT_MUTED = RGBColor(71, 85, 105)        # #475569 (Slate 600)
    TEXT_SUBTLE = RGBColor(148, 163, 184)     # #94A3B8 (Slate 400)

    # Accent Colors (clean, modern, non-overwhelming)
    BLUE_PRI = RGBColor(37, 99, 235)          # #2563EB (Core Brand)
    BLUE_LIGHT = RGBColor(239, 246, 255)      # #EFF6FF
    BLUE_BORDER = RGBColor(191, 219, 254)

    INDIGO_PRI = RGBColor(79, 70, 229)        # #4F46E5
    INDIGO_LIGHT = RGBColor(238, 242, 255)

    EMERALD_PRI = RGBColor(16, 185, 129)      # #10B981 (Success / Positive)
    EMERALD_LIGHT = RGBColor(236, 253, 245)
    EMERALD_BORDER = RGBColor(167, 243, 208)

    AMBER_PRI = RGBColor(245, 158, 11)        # #F59E0B (Warning / Problem)
    AMBER_LIGHT = RGBColor(254, 243, 199)
    AMBER_BORDER = RGBColor(253, 230, 138)

    ROSE_PRI = RGBColor(244, 63, 94)          # #F43F5E
    ROSE_LIGHT = RGBColor(255, 241, 242)

    # Helper: Slide canvas
    def add_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()
        return bg

    # Helper: Clean, airy header
    def add_header(slide, tag_text, title_text, subtitle_text, tag_color=BLUE_PRI, tag_bg=BLUE_LIGHT):
        # Pill Tag
        tag = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(0.48), Inches(2.5), Inches(0.32))
        tag.fill.solid()
        tag.fill.fore_color.rgb = tag_bg
        tag.line.color.rgb = tag_color
        tag.line.width = Pt(1)
        tf = tag.text_frame
        tf.margin_top = Inches(0.04)
        tf.margin_bottom = Inches(0.04)
        p = tf.paragraphs[0]
        p.text = tag_text.upper()
        p.alignment = PP_ALIGN.CENTER
        p.font.name = "Segoe UI"
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = tag_color

        # Right Slide Tracker
        tracker = slide.shapes.add_textbox(Inches(9.5), Inches(0.48), Inches(2.933), Inches(0.32))
        tf_tr = tracker.text_frame
        p_tr = tf_tr.paragraphs[0]
        p_tr.text = "JEE PERFORMANCE ENGINE"
        p_tr.alignment = PP_ALIGN.RIGHT
        p_tr.font.name = "Segoe UI"
        p_tr.font.size = Pt(9)
        p_tr.font.bold = True
        p_tr.font.color.rgb = TEXT_SUBTLE

        # Title & Subtitle
        tb = slide.shapes.add_textbox(Inches(0.9), Inches(0.88), Inches(11.533), Inches(0.85))
        tf_tb = tb.text_frame
        tf_tb.word_wrap = True
        tf_tb.margin_top = Inches(0)
        tf_tb.margin_left = Inches(0)

        p_t = tf_tb.paragraphs[0]
        p_t.text = title_text
        p_t.font.name = "Segoe UI"
        p_t.font.size = Pt(22)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK

        p_s = tf_tb.add_paragraph()
        p_s.text = subtitle_text
        p_s.font.name = "Segoe UI"
        p_s.font.size = Pt(12)
        p_s.font.color.rgb = TEXT_MUTED
        p_s.space_before = Pt(3)

    # Helper: Modern card
    def add_card(slide, left, top, width, height, bg=CARD_BG, border=CARD_BORDER, border_width=1):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg
        if border:
            card.line.color.rgb = border
            card.line.width = Pt(border_width)
        else:
            card.line.fill.background()
        return card

    # Helper: Top accent bar
    def add_card_accent(slide, left, top, width, color):
        accent = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(0.06))
        accent.fill.solid()
        accent.fill.fore_color.rgb = color
        accent.line.fill.background()
        return accent

    # Helper: Simple bottom callout
    def add_bottom_takeaway(slide, title, message, bg=BLUE_LIGHT, border=BLUE_BORDER, tag_color=BLUE_PRI):
        add_card(slide, Inches(0.9), Inches(5.8), Inches(11.533), Inches(1.15), bg=bg, border=border, border_width=1)
        tb = slide.shapes.add_textbox(Inches(1.15), Inches(5.88), Inches(11.033), Inches(0.98))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0)
        tf.margin_left = Inches(0)

        p1 = tf.paragraphs[0]
        r1 = p1.add_run()
        r1.text = title.upper() + "  —  "
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.name = "Segoe UI"
        r1.font.color.rgb = tag_color

        r2 = p1.add_run()
        r2.text = message
        r2.font.size = Pt(10.5)
        r2.font.name = "Segoe UI"
        r2.font.color.rgb = TEXT_DARK

    # =========================================================================
    # SLIDE 1: Problem Statement
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_background(s1)
    add_header(s1, "01 | The Core Problem", 
               "Personalized JEE Prep Requires More Than Scores", 
               "Current systems track test scores. We need to model how the learner actually learns, forgets, and makes mistakes.")

    # Side by side comparison: Today vs Proposed
    card_w = Inches(5.6)
    card_h = Inches(3.6)
    y_pos = Inches(1.95)

    # Left: The Status Quo
    add_card(s1, Inches(0.9), y_pos, card_w, card_h)
    add_card_accent(s1, Inches(0.9), y_pos, card_w, AMBER_PRI)

    tb1_l = s1.shapes.add_textbox(Inches(1.15), y_pos + Inches(0.2), card_w - Inches(0.5), card_h - Inches(0.4))
    tf1_l = tb1_l.text_frame
    tf1_l.word_wrap = True

    p = tf1_l.paragraphs[0]
    p.text = "TODAY: CRUDE AGGREGATES"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = AMBER_PRI

    points_l = [
        ("Massive Data Wasted", "Thousands of test attempts are flattened into a single score like '140/300'."),
        ("Superficial Diagnosis", "'60% in Mechanics' tells what happened, but hides which concept failed."),
        ("Blind to Cognitive Roots", "Treats a missing prerequisite, a minus-sign slip, and a panic guess identically."),
        ("Static Snapshots", "Treats knowledge as a fixed number; completely ignores retention decay over time.")
    ]
    for h, desc in points_l:
        p_item = tf1_l.add_paragraph()
        p_item.space_before = Pt(8)
        r1 = p_item.add_run()
        r1.text = "•  " + h + ": "
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = TEXT_DARK
        r2 = p_item.add_run()
        r2.text = desc
        r2.font.size = Pt(10)
        r2.font.color.rgb = TEXT_MUTED

    # Right: The Longitudinal Engine
    add_card(s1, Inches(6.833), y_pos, card_w, card_h)
    add_card_accent(s1, Inches(6.833), y_pos, card_w, BLUE_PRI)

    tb1_r = s1.shapes.add_textbox(Inches(7.083), y_pos + Inches(0.2), card_w - Inches(0.5), card_h - Inches(0.4))
    tf1_r = tb1_r.text_frame
    tf1_r.word_wrap = True

    p = tf1_r.paragraphs[0]
    p.text = "THE PROPOSED ENGINE: EVOLVING LEARNER MODEL"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = BLUE_PRI

    points_r = [
        ("Longitudinal Knowledge Tracing", "Estimates dynamic mastery probabilities concept-by-concept over time."),
        ("Cognitive Error Taxonomy", "Separates Concept Gaps, Calculation Slips, Misreading, and Time Pressure."),
        ("Prerequisite Concept Graph", "Finds root blockers (e.g., Vector Cross Product gap breaking Rotational Motion)."),
        ("Outcome Verification", "Measures next-test performance to verify if the recommended intervention worked.")
    ]
    for h, desc in points_r:
        p_item = tf1_r.add_paragraph()
        p_item.space_before = Pt(8)
        r1 = p_item.add_run()
        r1.text = "•  " + h + ": "
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = TEXT_DARK
        r2 = p_item.add_run()
        r2.text = desc
        r2.font.size = Pt(10)
        r2.font.color.rgb = TEXT_MUTED

    # Bottom Callout: The Loop
    add_bottom_takeaway(s1, "Closed-Loop Learning Cycle", 
                        "Observe Attempts  ➔  Model Mastery & Latency  ➔  Diagnose Root Causes  ➔  Intervene with Daily Plan  ➔  Measure Outcome  ➔  Update State",
                        bg=BLUE_LIGHT, border=BLUE_BORDER, tag_color=BLUE_PRI)

    # =========================================================================
    # SLIDE 2: Existing Challenges
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_background(s2)
    add_header(s2, "02 | Core Bottlenecks", 
               "Capturing Performance, Not the Learner", 
               "Five structural flaws in conventional EdTech analytics that prevent personalized preparation.")

    # 5 Clean Cards (3 Top, 2 Bottom Left + 1 Highlight Card)
    c_w = Inches(3.68)
    c_gap = Inches(0.24)
    c_h = Inches(1.72)
    y1 = Inches(1.95)

    challenges = [
        ("1. Coarse Diagnosis", "Shows what happened, not why.", "Stating '45% in Optics' hides whether the flaw is sign conventions, lens formulas, or geometry.", AMBER_PRI),
        ("2. Static Snapshots", "Knowledge evolves constantly.", "Students learn, practice, forget, and revise. Static dashboards ignore forgetting curves completely.", BLUE_PRI),
        ("3. Conflated Errors", "Two wrong answers aren't equal.", "A concept gap, an algebra slip, and a panic guess require completely different remedies.", ROSE_PRI),
        ("4. Generic Volume", "Practice more is not a strategy.", "'Solve 50 more questions' wastes limited hours instead of fixing the exact prerequisite blocker.", INDIGO_PRI),
        ("5. Missing Feedback", "Systems stop at recommendation.", "Portals suggest questions and walk away — never verifying if accuracy improved on the next mock.", BLUE_PRI)
    ]

    for i in range(3):
        x = Inches(0.9) + i * (c_w + c_gap)
        title, sub, body, col = challenges[i]
        add_card(s2, x, y1, c_w, c_h)
        add_card_accent(s2, x, y1, c_w, col)

        tb = s2.shapes.add_textbox(x + Inches(0.2), y1 + Inches(0.18), c_w - Inches(0.4), c_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.name = "Segoe UI"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.name = "Segoe UI"
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = "Segoe UI"
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(3)

    y2 = Inches(3.82)
    for i in range(3, 5):
        x = Inches(0.9) + (i - 3) * (c_w + c_gap)
        title, sub, body, col = challenges[i]
        add_card(s2, x, y2, c_w, c_h)
        add_card_accent(s2, x, y2, c_w, col)

        tb = s2.shapes.add_textbox(x + Inches(0.2), y2 + Inches(0.18), c_w - Inches(0.4), c_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.name = "Segoe UI"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.name = "Segoe UI"
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = "Segoe UI"
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(3)

    # 6th Card: The Highlight
    x6 = Inches(0.9) + 2 * (c_w + c_gap)
    add_card(s2, x6, y2, c_w, c_h, bg=INDIGO_LIGHT, border=INDIGO_PRI, border_width=1.5)
    tb6 = s2.shapes.add_textbox(x6 + Inches(0.2), y2 + Inches(0.18), c_w - Inches(0.4), c_h - Inches(0.3))
    tf6 = tb6.text_frame
    tf6.word_wrap = True

    p = tf6.paragraphs[0]
    p.text = "THE FUNDAMENTAL GAP"
    p.font.name = "Segoe UI"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = INDIGO_PRI

    p2 = tf6.add_paragraph()
    p2.text = "No Persistent Learner Model"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(11)
    p2.font.bold = True
    p2.font.color.rgb = TEXT_DARK
    p2.space_before = Pt(2)

    p3 = tf6.add_paragraph()
    p3.text = "Missing: An evolving student model connecting raw interaction evidence ➔ cognitive root causes ➔ targeted action ➔ verified outcome."
    p3.font.name = "Segoe UI"
    p3.font.size = Pt(9.5)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_before = Pt(3)

    # Bottom Takeaway
    add_bottom_takeaway(s2, "Root Insight", 
                        "Traditional portals treat test scores as endpoints. True personalization treats scores as diagnostic evidence to fix cognitive causes.",
                        bg=AMBER_LIGHT, border=AMBER_BORDER, tag_color=AMBER_PRI)

    # =========================================================================
    # SLIDE 3: Proposed Solution
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_background(s3)
    add_header(s3, "03 | Proposed Solution", 
               "A Longitudinal Student Performance Engine", 
               "Transforming raw question-level interactions into an evolving representation of knowledge and behavior.")

    # 6 Clean Pipeline Steps (2 rows of 3)
    steps = [
        ("01 | Capture", "Raw Question Evidence", "Ingests PYQs, mocks, and practice: correctness, solve time, confidence, and notes.", BLUE_PRI),
        ("02 | Understand", "AI Extraction Layer", "Qwen extracts normalized concepts, error taxonomy, student reasoning, and pacing signals.", INDIGO_PRI),
        ("03 | Model", "Longitudinal Tracing", "Tracks mastery via Bayesian Knowledge Tracing (BKT) and a Prerequisite Concept Graph.", BLUE_PRI),
        ("04 | Diagnose", "Root-Cause Mining", "Pinpoints upstream prerequisite gaps, recurring slips, and speed vs accuracy tradeoffs.", AMBER_PRI),
        ("05 | Intervene", "Targeted Daily Plan", "Prescribes high-yield actions: Prerequisite Review, Worked Example, or Timed Sprint.", INDIGO_PRI),
        ("06 | Measure & Update", "Outcome Verification", "Checks next-test results to prove if the action worked, recalibrating the student state.", EMERALD_PRI)
    ]

    for i in range(3):
        x = Inches(0.9) + i * (c_w + c_gap)
        title, sub, body, col = steps[i]
        add_card(s3, x, y1, c_w, c_h)
        add_card_accent(s3, x, y1, c_w, col)

        tb = s3.shapes.add_textbox(x + Inches(0.2), y1 + Inches(0.18), c_w - Inches(0.4), c_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.name = "Segoe UI"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.name = "Segoe UI"
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = "Segoe UI"
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(3)

    for i in range(3, 6):
        x = Inches(0.9) + (i - 3) * (c_w + c_gap)
        title, sub, body, col = steps[i]
        add_card(s3, x, y2, c_w, c_h)
        add_card_accent(s3, x, y2, c_w, col)

        tb = s3.shapes.add_textbox(x + Inches(0.2), y2 + Inches(0.18), c_w - Inches(0.4), c_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.name = "Segoe UI"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.name = "Segoe UI"
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = "Segoe UI"
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(3)

    add_bottom_takeaway(s3, "Key Differentiator", 
                        "The engine does not just prescribe study tasks — it measures whether its recommendations actually fixed the problem on subsequent tests.",
                        bg=EMERALD_LIGHT, border=EMERALD_BORDER, tag_color=EMERALD_PRI)

    # =========================================================================
    # SLIDE 4: PRISM Integration
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_background(s4)
    add_header(s4, "04 | System Reliability", 
               "Continuous Evaluation via PRISM", 
               "Ensuring deterministic reliability, grounding, and self-healing across every AI component.")

    # 4 Simple Steps in Top Row
    p4_w = Inches(2.7)
    p4_gap = Inches(0.24)
    p4_h = Inches(1.8)

    prism_steps = [
        ("1. Monitor", "Full Observability", "Tracks LLM extraction, RAG retrieval, tool calls, and state transitions.", BLUE_PRI),
        ("2. Evaluate", "Automated Gates", "Tests against strict criteria: syllabus grounding, consistency, and tool choice.", INDIGO_PRI),
        ("3. Detect", "Pinpoint Failures", "Flags hallucinated concepts, overconfident mastery, and edge-case regressions.", ROSE_PRI),
        ("4. Improve", "System Self-Healing", "Drives automated prompt tuning, routing fixes, and regression test suites.", EMERALD_PRI)
    ]

    for i in range(4):
        x = Inches(0.9) + i * (p4_w + p4_gap)
        title, sub, body, col = prism_steps[i]
        add_card(s4, x, y1, p4_w, p4_h)
        add_card_accent(s4, x, y1, p4_w, col)

        tb = s4.shapes.add_textbox(x + Inches(0.18), y1 + Inches(0.18), p4_w - Inches(0.36), p4_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title.upper()
        p.font.name = "Segoe UI"
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.name = "Segoe UI"
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = body
        p3.font.name = "Segoe UI"
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(3)

    # Middle 2 Cards: What's Eliminated vs The Standard
    y_mid = Inches(3.9)
    h_mid = Inches(1.65)
    w_mid = Inches(5.6)

    # Left
    add_card(s4, Inches(0.9), y_mid, w_mid, h_mid)
    add_card_accent(s4, Inches(0.9), y_mid, w_mid, ROSE_PRI)
    tb_l4 = s4.shapes.add_textbox(Inches(1.15), y_mid + Inches(0.18), w_mid - Inches(0.4), h_mid - Inches(0.3))
    tf_l4 = tb_l4.text_frame
    tf_l4.word_wrap = True

    p = tf_l4.paragraphs[0]
    p.text = "FAILURES ELIMINATED BY PRISM"
    p.font.name = "Segoe UI"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = ROSE_PRI

    b_prism = [
        "No Hallucinations: Zero fake formulas or bogus rationales in student advice.",
        "No Concept Drift: Prevents splitting 'Rotational Motion' across different tests.",
        "No Mismatched Plans: Blocks advanced drills when foundational gaps exist."
    ]
    for b in b_prism:
        p_b = tf_l4.add_paragraph()
        p_b.space_before = Pt(3)
        r = p_b.add_run()
        r.text = "•  " + b
        r.font.size = Pt(9.5)
        r.font.color.rgb = TEXT_MUTED

    # Right
    add_card(s4, Inches(6.833), y_mid, w_mid, h_mid, bg=INDIGO_LIGHT, border=INDIGO_PRI, border_width=1.2)
    tb_r4 = s4.shapes.add_textbox(Inches(7.083), y_mid + Inches(0.18), w_mid - Inches(0.4), h_mid - Inches(0.3))
    tf_r4 = tb_r4.text_frame
    tf_r4.word_wrap = True

    p = tf_r4.paragraphs[0]
    p.text = "CONTINUOUS REGRESSION TESTING"
    p.font.name = "Segoe UI"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = INDIGO_PRI

    p2 = tf_r4.add_paragraph()
    p2.text = "Deterministic Confidence for AI"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(11)
    p2.font.bold = True
    p2.font.color.rgb = TEXT_DARK
    p2.space_before = Pt(2)

    p3 = tf_r4.add_paragraph()
    p3.text = "Instead of random spot-checks, PRISM runs continuous test cases. Prompt updates, model switches, or new question banks are verified before student-facing rollout."
    p3.font.name = "Segoe UI"
    p3.font.size = Pt(9.5)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_before = Pt(3)

    # Bottom Takeaway
    add_bottom_takeaway(s4, "Guiding Standard", 
                        "Continuous empirical verification over blind AI trust. Every recommendation is measurable, testable, and provable.",
                        bg=INDIGO_LIGHT, border=INDIGO_PRI, tag_color=INDIGO_PRI)

    # =========================================================================
    # SLIDE 5: System Workflow & Architecture
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_background(s5)
    add_header(s5, "05 | System Architecture", 
               "A Closed-Loop Learning Intelligence System", 
               "Local MCP server coupling deterministic analytics with LLM-assisted extraction for complete privacy & speed.")

    # Top: Cleanly Framed Architecture Diagram
    img_path = r"C:/Users/rikku/.gemini/antigravity/brain/736f3962-e5d7-4e6e-a911-6244bb5df1a4/.user_uploaded/media_1789379021052.png"
    
    diag_w = Inches(11.533)
    diag_h = Inches(3.65)
    add_card(s5, Inches(0.9), Inches(1.95), diag_w, diag_h)
    
    # Diagram inside card (centered)
    # Image aspect ratio is 2:1 (1024x512). Let height = 3.55", width = 7.1"
    img_h = Inches(3.5)
    img_w = Inches(7.0)
    img_x = Inches(0.9) + (diag_w - img_w) / 2
    s5.shapes.add_picture(img_path, Inches(1.05), Inches(2.02), Inches(7.2), Inches(3.5))

    # Right side pillars inside diagram area
    pil_x = Inches(8.45)
    pil_w = Inches(3.75)
    pil_h = Inches(1.05)

    arch_pillars = [
        ("LLM for Extraction Only", "Natural language input converted to structured schema. No hallucinated math or scores.", BLUE_PRI),
        ("100% Deterministic Engine", "All BKT mastery math, prerequisite graphs, and daily ranking run on local code.", INDIGO_PRI),
        ("Local SQLite & Feedback", "Fast, private on-device storage. Subsequent test outcomes feed directly back into history.", EMERALD_PRI)
    ]

    for i in range(3):
        y = Inches(2.05) + i * (pil_h + Inches(0.12))
        p_title, p_desc, p_col = arch_pillars[i]
        add_card(s5, pil_x, y, pil_w, pil_h)
        add_card_accent(s5, pil_x, y, pil_w, p_col)

        tb = s5.shapes.add_textbox(pil_x + Inches(0.18), y + Inches(0.12), pil_w - Inches(0.36), pil_h - Inches(0.2))
        tf = tb.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = p_title.upper()
        p.font.name = "Segoe UI"
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = p_col

        p_b = tf.add_paragraph()
        p_b.text = p_desc
        p_b.font.name = "Segoe UI"
        p_b.font.size = Pt(9)
        p_b.font.color.rgb = TEXT_MUTED
        p_b.space_before = Pt(2)

    # Bottom Takeaway
    add_bottom_takeaway(s5, "Foundational Engineering Rule", 
                        "LLM understands language; deterministic code does the math. Zero guesswork in student knowledge tracing.",
                        bg=BLUE_LIGHT, border=BLUE_BORDER, tag_color=BLUE_PRI)

    # =========================================================================
    # SLIDE 6: Impact & Future Scope
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_background(s6)
    add_header(s6, "06 | Value & Horizon", 
               "From Performance Tracking to Personalized Learning", 
               "Measurable student transformation coupled with a principled 6-stage research roadmap.")

    # 2 Big Clean Columns
    w_col = Inches(5.6)
    h_col = Inches(3.6)

    # Left: Student Transformation
    add_card(s6, Inches(0.9), y1, w_col, h_col)
    add_card_accent(s6, Inches(0.9), y1, w_col, EMERALD_PRI)

    tb_s6 = s6.shapes.add_textbox(Inches(1.15), y1 + Inches(0.2), w_col - Inches(0.5), h_col - Inches(0.4))
    tf_s6 = tb_s6.text_frame
    tf_s6.word_wrap = True

    p = tf_s6.paragraphs[0]
    p.text = "THE TRANSFORMATIVE STUDENT SHIFT"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = EMERALD_PRI

    shifts = [
        ("From Guesswork to Precision", "Replaces 'I scored 42% in Physics, let me do 100 problems' with 'Vector Cross Product gap; a 15-min drill recovers ~16 marks.'"),
        ("Saves 40%+ Study Time", "Eliminates redundant practice in mastered topics; targets high-yield prerequisite blockers."),
        ("Temperament Calibration", "Separates speed-panic slips from true lack of concept understanding."),
        ("Institutional Audit Trail", "Gives coaching institutes granular diagnostic visibility rather than superficial marksheets.")
    ]
    for h, desc in shifts:
        p_item = tf_s6.add_paragraph()
        p_item.space_before = Pt(7)
        r1 = p_item.add_run()
        r1.text = "•  " + h + ": "
        r1.font.bold = True
        r1.font.size = Pt(10)
        r1.font.color.rgb = TEXT_DARK
        r2 = p_item.add_run()
        r2.text = desc
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = TEXT_MUTED

    # Right: 6-Stage Research Roadmap
    add_card(s6, Inches(6.833), y1, w_col, h_col)
    add_card_accent(s6, Inches(6.833), y1, w_col, INDIGO_PRI)

    tb_r6 = s6.shapes.add_textbox(Inches(7.083), y1 + Inches(0.2), w_col - Inches(0.5), h_col - Inches(0.4))
    tf_r6 = tb_r6.text_frame
    tf_r6.word_wrap = True

    p = tf_r6.paragraphs[0]
    p.text = "6-STAGE RESEARCH & DEPLOYMENT ROADMAP"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = INDIGO_PRI

    roadmap = [
        ("Stage 1: Synthetic Learners", "Benchmark KT models against controllable student agents on PYQs."),
        ("Stage 2: Student Modeling", "Empirically evaluate Baseline vs BKT vs PFA vs Deep KT."),
        ("Stage 3: Cohort Validation", "Pilot with real, consented JEE aspirants to calibrate forgetting decay."),
        ("Stage 4: Adaptive Interventions", "Contextual bandits to select the highest-gain action for each student state."),
        ("Stage 5: Student Simulation", "Pre-test interventions against simulated learner twins to forecast outcomes."),
        ("Stage 6: Causal Personalization", "Shift from 'What predicts score?' to 'Which action causes maximal score gain?'")
    ]
    for h, desc in roadmap:
        p_item = tf_r6.add_paragraph()
        p_item.space_before = Pt(4)
        r1 = p_item.add_run()
        r1.text = h + " — "
        r1.font.bold = True
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = TEXT_DARK
        r2 = p_item.add_run()
        r2.text = desc
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = TEXT_MUTED

    # Bottom Takeaway
    add_bottom_takeaway(s6, "Ultimate Vision", 
                        "An AI learning system that doesn't just track scores or explain mistakes, but continuously learns how each student learns, verifies what works, and adapts what's next.",
                        bg=EMERALD_LIGHT, border=EMERALD_BORDER, tag_color=EMERALD_PRI)

    # Save
    prs.save(output_path)
    print(f"Clean & simple presentation successfully saved to: {output_path}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "JEE_Performance_Engine_6_Slides.pptx"
    build_presentation(out_file)
