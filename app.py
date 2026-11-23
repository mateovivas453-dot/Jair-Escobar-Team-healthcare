import io
import json
import os
import zipfile
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)

TEAM_INFO = {
    "team_id": "Team Healthcare",
    "student_name": "Jair",
    "skill_name": "math-study-coach",
    "project_title": "Team Healthcare — AI Business & Multilingual Math Study Coach",
    "skill_level": "Advanced",
    "version": "3.0 (Claude Skill & AI Business Build)",
}

COURSES = {
    "Honors Algebra 2": {
        "badge": "High School Honors (Non-AP)",
        "calculator_rule": "Scientific or graphing calculator allowed per teacher classroom directions; show algebraic setups clearly.",
        "scope_note": "Follows teacher scope, class methods, allowed technology, and classroom rubrics. Not presented as an AP exam course.",
        "default_topic": "Exponential Growth & Decay in Medication Half-Life",
        "topics": [
            "Exponential Growth & Decay in Medication Half-Life",
            "Rational Functions & Drug Concentration Thresholds",
            "Logarithmic Models for pH & Decibel Scales in Audiology",
            "Systems of Linear Inequalities for Hospital Resource Allocation",
        ],
    },
    "AP Precalculus": {
        "badge": "AP Course Framework",
        "calculator_rule": "Graphing calculator permitted on Part B; exact symbolic reasoning required on non-calculator sections.",
        "scope_note": "Aligned with current teacher-approved AP Precalculus framework. Distinguishes exam-assessed modeling from healthcare enrichment.",
        "default_topic": "Removable Discontinuities & Piecewise Dosage Functions",
        "topics": [
            "Removable Discontinuities & Piecewise Dosage Functions",
            "Sinusoidal Modeling of Cardiac & Respiratory Cycles",
            "Logistic Growth Models for Epidemic Spread",
            "Semi-Log Plots & Exponential Regression in Clinical Trials",
        ],
    },
    "AP Calculus": {
        "badge": "AP Calculus (Select AB or BC)",
        "calculator_rule": "Part A (No Calculator) requires exact analytical work; Part B allows graphing calculator accurate to 3 decimal places.",
        "scope_note": "Requires AB or BC selection. Enforces theorem hypotheses (IVT, MVT, EVT, FTC) and official free-response scoring guidance.",
        "default_topic": "Instantaneous Rate of Change in IV Infusion & Clearance (AB/BC)",
        "subcourses": {
            "AB": "Differential & Integral Calculus through Fundamental Theorem of Calculus, separable differential equations, and accumulation.",
            "BC": "All AB topics plus Euler's method, logistic differential equations, parametric/polar/vector functions, and Taylor/Maclaurin series.",
        },
        "topics": [
            "Instantaneous Rate of Change in IV Infusion & Clearance (AB/BC)",
            "Related Rates in Arterial Blood Flow & Vessel Radius (AB/BC)",
            "Accumulation & Definite Integrals in Patient Monitoring (AB/BC)",
            "Logistic Differential Equations & Euler's Method in Epidemiology (BC Only)",
        ],
    },
    "AP Statistics": {
        "badge": "AP Statistics Framework",
        "calculator_rule": "Graphing calculator with statistical distribution/inference functions allowed; always name the procedure, parameters, and conditions.",
        "scope_note": "Emphasizes study design, variability, probability, inference conditions (Random, 10%, Normal/Large Sample), and conclusions in context.",
        "default_topic": "Two-Sample Inference & Clinical Trial Efficacy",
        "topics": [
            "Two-Sample Inference & Clinical Trial Efficacy",
            "Diagnostic Test Sensitivity, Specificity & Bayes' Rule",
            "Linear Regression & Residual Analysis in Telehealth Wait Times",
            "Confidence Intervals for Healthcare Readmission Rates",
        ],
    },
}

MODES = [
    {
        "id": "learn",
        "number": 1,
        "name": "Learn a Topic",
        "icon": "📘",
        "short": "Intuition, formal notation, dual representations, and guided healthcare example.",
    },
    {
        "id": "vocab",
        "number": 2,
        "name": "Vocabulary & Meaning",
        "icon": "🔤",
        "short": "Precise definitions, units, synonyms/paraphrases, examples, nonexamples & clinical use.",
    },
    {
        "id": "career",
        "number": 3,
        "name": "Life & Career Applications (Healthcare)",
        "icon": "🏥",
        "short": "Simulated clinical & biomedical problems with units, constraints, and transfer practice.",
    },
    {
        "id": "business",
        "number": 4,
        "name": "Personal Finance & Business (Healthcare AI)",
        "icon": "💼",
        "short": "Clinic revenue, fixed/variable costs, equipment ROI, profit margin, and sensitivity analysis.",
    },
    {
        "id": "diagnose",
        "number": 5,
        "name": "Diagnose & Practice",
        "icon": "🩺",
        "short": "Staged diagnostic items across Easy, Medium, Hard, or Mixed levels with targeted hints.",
    },
    {
        "id": "mistake",
        "number": 6,
        "name": "Mistake Detective",
        "icon": "🔍",
        "short": "Inspects student work, pinpoints the first unsupported step, and logs the repair principle.",
    },
    {
        "id": "graphs",
        "number": 7,
        "name": "Graphs & Representations",
        "icon": "📈",
        "short": "Connects symbolic, numerical, graphical, and verbal representations with live charts.",
    },
    {
        "id": "exam",
        "number": 8,
        "name": "Retrieval & Exam Practice",
        "icon": "📝",
        "short": "Original course-aligned exam items with withheld answers and rubric-based feedback.",
    },
    {
        "id": "planner",
        "number": 9,
        "name": "Study Planner",
        "icon": "🗓️",
        "short": "Builds a realistic retrieval and interleaved schedule around your assessment date.",
    },
    {
        "id": "defend",
        "number": 10,
        "name": "Explain & Defend",
        "icon": "🛡️",
        "short": "Audits claims, theorem hypotheses, statistical conditions, and boundary counterexamples.",
    },
]

LANGUAGES = {
    "English": {
        "greeting": "Welcome to Team Healthcare's AI Business & Math Study Coach!",
        "bilingual_tag": "English (Primary)",
        "terms": {
            "rate": "Rate of change",
            "cost": "Fixed & variable cost",
            "condition": "Verification condition",
            "hint": "Guided Hint",
            "check": "Context & Conditions Check",
        },
    },
    "Spanish": {
        "greeting": "¡Bienvenido al Coach de Matemáticas y Negocios de Salud con IA (Team Healthcare)!",
        "bilingual_tag": "Bilingual: English + Español",
        "terms": {
            "rate": "Tasa de cambio (Rate of change)",
            "cost": "Costo fijo y variable (Fixed & variable cost)",
            "condition": "Condición de verificación (Verification condition)",
            "hint": "Pista guiada (Guided Hint)",
            "check": "Verificación de contexto y condiciones (Context & Conditions Check)",
        },
    },
    "French": {
        "greeting": "Bienvenue au Coach Mathématique et Santé IA de Team Healthcare !",
        "bilingual_tag": "Bilingual: English + Français",
        "terms": {
            "rate": "Taux de variation (Rate of change)",
            "cost": "Coût fixe et variable (Fixed & variable cost)",
            "condition": "Condition de vérification (Verification condition)",
            "hint": "Indice guidé (Guided Hint)",
            "check": "Vérification du contexte et des conditions",
        },
    },
    "Haitian Creole (Kreyol)": {
        "greeting": "Byenvini nan Antrenè Matematik ak Biznis Sante IA pa Team Healthcare!",
        "bilingual_tag": "Bilingual: English + Kreyòl Ayisyen",
        "terms": {
            "rate": "To chanjman (Rate of change)",
            "cost": "Pri fiks ak pri varyab (Fixed & variable cost)",
            "condition": "Kondisyon verifikasyon (Verification condition)",
            "hint": "Endis gide (Guided Hint)",
            "check": "Verifikasyon kontèks ak kondisyon",
        },
    },
    "Swahili (Kiswahili)": {
        "greeting": "Karibu kwenye Mkufunzi wa Hisabati na Biashara ya Afya wa Team Healthcare!",
        "bilingual_tag": "Bilingual: English + Kiswahili",
        "terms": {
            "rate": "Kiwango cha mabadiliko (Rate of change)",
            "cost": "Gharama zisizobadilika na zinazobadilika (Fixed & variable cost)",
            "condition": "Sharti la uthibitisho (Verification condition)",
            "hint": "Kidokezo cha mwongozo (Guided Hint)",
            "check": "Ukaguzi wa muktadha na masharti",
        },
    },
    "Hausa": {
        "greeting": "Barka da zuwa Team Healthcare AI Koyarwar Lissafi da Kasuwancin Kiwon Lafiya!",
        "bilingual_tag": "Bilingual: English + Hausa",
        "terms": {
            "rate": "Adadin sauyi (Rate of change)",
            "cost": "Tsayayyen kuɗi da mai canzawa (Fixed & variable cost)",
            "condition": "Sharuɗɗan tabbatarwa (Verification condition)",
            "hint": "Shawarar jagora (Guided Hint)",
            "check": "Binciken yanayi da sharuɗɗa",
        },
    },
    "Yoruba": {
        "greeting": "Ẹ kú àbọ̀ sí Team Healthcare AI Olùkọ́ Ìṣirò àti Iṣẹ́ Ìlera!",
        "bilingual_tag": "Bilingual: English + Yorùbá",
        "terms": {
            "rate": "Ìwọ̀n ìyípadà (Rate of change)",
            "cost": "Iye owó tí kò yípadà àti èyí tí ń yípadà",
            "condition": "Ìlànà ìfìdíkalẹ̀ (Verification condition)",
            "hint": "Ìtọ́kasí ìrànlọ́wọ́ (Guided Hint)",
            "check": "Àyẹ̀wò àyíká ọ̀rọ̀ àti àwọn ìlànà",
        },
    },
    "Igbo": {
        "greeting": "Nnọọ na Team Healthcare AI Onye Nkuzi Mgbakọ na Azụmahịa Ahụike!",
        "bilingual_tag": "Bilingual: English + Igbo",
        "terms": {
            "rate": "Ọnụego mgbanwe (Rate of change)",
            "cost": "Ọnụ ego kwụsiri ike na nke na-agbanwe",
            "condition": "Ọnọdụ nyocha (Verification condition)",
            "hint": "Atụmatụ nduzi (Guided Hint)",
            "check": "Nyocha ọnọdụ na iwu",
        },
    },
    "Nigerian Pidgin": {
        "greeting": "Welcome to Team Healthcare AI Maths & Healthcare Business Coach!",
        "bilingual_tag": "Bilingual: English + Nigerian Pidgin",
        "terms": {
            "rate": "How fast thing dey change (Rate of change)",
            "cost": "Fixed cost and cost wey dey change",
            "condition": "Rule wey we must check first",
            "hint": "Small clue to help you solve am",
            "check": "Check whether the answer make sense for real life",
        },
    },
}

SKILL_MD_CONTENT = """---
name: math-study-coach
description: >-
  Use for Honors Algebra 2, AP Precalculus, AP Calculus AB/BC, or AP Statistics tutoring,
  vocabulary, applications, diagnostics, exam practice, study plans,
  multilingual help, and video demonstrations.
---

# Purpose and activation
Use this skill when a student requests mathematics tutoring, vocabulary, applications, targeted practice, test preparation, study planning, multilingual explanations, or relevant demonstration videos in one of the supported courses. Act as a patient tutor who develops independent reasoning. Perform all modes within Claude; do not claim to call a Gemini Gem, another skill, or an external agent. These are learning modes within one reusable skill.

# Preserve the existing Gem foundation
This skill extends Jair's Team Healthcare course-specific Gem Test-Prep Tutor. Retain the useful course methods, calculator rules, assessment expectations, source practices, and integrity rules imported into `references/course-guide.md`. Read the relevant course section before applying its guidance. Apply imported course rules only to their matching course.

# Course and source priorities
Offer Honors Algebra 2, AP Precalculus, AP Calculus, and AP Statistics. For AP Calculus, clarify AB or BC. Use teacher directions for classroom assignments and verified current official sources for AP exam claims; identify conflicts and ask for clarification. Do not invent course requirements, testing accommodations, scoring rules, or source quotations. Treat enrichment as enrichment. For Honors Algebra 2, use teacher expectations rather than AP exam rules.

# Opening and personalization (Team Healthcare Customizations)
At the start of a tutoring conversation, explicitly ask which of the four courses the student wants, unless the student already stated one. Ask only for missing information, no more than three brief questions at a time, then wait.
- **Personalization 1 (Visual Diagram & Hint-First Protocol)**: Before presenting raw formulas or a full worked example, provide an ASCII/visual structural diagram of the quantities and offer one targeted hint so the student can attempt the step first.
- **Personalization 2 (Healthcare Context & Conditions Audit)**: Conclude every application, business decision, Calculus theorem step, or Statistics inference with an explicit **Context, Units & Conditions Check** connected to real-world healthcare or clinical decision-making when relevant.

# Language in every mode
Offer English, Spanish, French, Haitian Creole (Kreyol), another French-based Creole, Swahili (Kiswahili), Hausa, Yoruba, Igbo, Nigerian Pidgin, or another named language. Clarify ambiguous "French Creole" requests. Offer selected-language output or bilingual English plus that language. Preserve numbers, symbols, variables, units, assumptions, difficulty, and withheld solutions.

# Ten Learning & Business Modes
1. **Learn a Topic**: Explain intuition, then formal meaning and notation. Connect at least two representations. Offer guided discovery, a fresh attempt, and a conceptual exit question.
2. **Vocabulary & Meaning**: Default to three terms. Give a precise definition, notation/units, genuine synonym/paraphrase, mathematical example, nonexample with reasons, daily-life context, and Team Healthcare career context.
3. **Life & Career Applications**: Prioritize healthcare, biomedical, or student-chosen careers. Create an original solvable problem with realistic data explicitly labeled **[Simulated Data]**, including units and constraints.
4. **Personal Finance & Business**: Model healthcare clinic budgeting, medical device purchase comparisons, or telehealth business models. State assumptions, timing, rates, fixed/variable cost, revenue, profit, cash flow, and margin.
5. **Diagnose & Practice**: Use 3-5 brief diagnostic items one at a time across easy, medium, hard, or mixed levels. Track coached vs. independent success.
6. **Mistake Detective**: Identify what is correct and the first invalid or unsupported step; explain the misconception and log the issue, corrected principle, and self-check.
7. **Graphs & Representations**: Connect verbal, graphical, numerical, symbolic, or statistical representations with labeled axes, units, and restrictions.
8. **Retrieval & Exam Practice**: Generate original course-scoped practice honoring calculator settings. Withhold answers until attempted.
9. **Study Planner**: Build a realistic plan with retrieval, targeted practice, interleaving, and success checks around the student's assessment date.
10. **Explain & Defend**: Check evidence, theorem hypotheses (Calculus), or study design and inference conditions (Statistics). Provide one priority revision and test with a boundary case or counterexample.

# Video support and session continuity
Offer 1-3 focused videos. Verify direct links when browsing is available; otherwise provide honest search phrases and trusted source names. Never invent a URL or timestamp. At a stopping point or on request, output a copyable **Session Note** summarizing course (and AB/BC), topic, modes used, language, difficulty, demonstrated skills, gaps, verification status, and next practice task.
"""


def build_mode_response(data):
    course = data.get("course", "AP Precalculus")
    calc_variant = data.get("calc_variant", "AB")
    mode = data.get("mode", "learn")
    language = data.get("language", "English")
    bilingual = data.get("bilingual", True)
    difficulty = data.get("difficulty", "Medium")
    topic = data.get("topic") or COURSES.get(course, COURSES["AP Precalculus"])["default_topic"]
    student_input = (data.get("student_input") or "").strip()

    # Personal Finance & Business parameters
    patients_per_month = float(data.get("patients_per_month") or 240)
    price_per_visit = float(data.get("price_per_visit") or 85)
    fixed_cost = float(data.get("fixed_cost") or 9200)
    variable_cost = float(data.get("variable_cost") or 28)

    course_meta = COURSES.get(course, COURSES["AP Precalculus"])
    lang_meta = LANGUAGES.get(language, LANGUAGES["English"])
    course_label = f"{course} ({calc_variant})" if course == "AP Calculus" else course

    revenue = patients_per_month * price_per_visit
    total_var_cost = patients_per_month * variable_cost
    total_cost = fixed_cost + total_var_cost
    profit = revenue - total_cost
    margin_pct = (profit / revenue * 100.0) if revenue > 0 else 0.0
    contribution_margin = price_per_visit - variable_cost
    breakeven_patients = (fixed_cost / contribution_margin) if contribution_margin > 0 else 0.0

    # Sensitivity analysis: +15% variable cost increase
    stressed_var_cost = variable_cost * 1.15
    stressed_profit = revenue - (fixed_cost + patients_per_month * stressed_var_cost)

    diagram_ascii = (
        f"[Input / Clinical Variable x] ---> [Mathematical Model f(x) | {course_label}] ---> [Verified Output & Units]\n"
        f"        |                                      |                                         |\n"
        f"   Constraints & Domain               Theorem / Condition Check                 Healthcare Decision"
    )

    if mode == "learn":
        title = f"1. Learn a Topic — {topic}"
        main_body = [
            f"**Intuition First**: In **{course_label}**, *{topic}* models how a clinical quantity changes or stabilizes over time. Before memorizing formulas, picture how a nurse or biomedical analyst tracks a changing signal on a monitor.",
            f"**Visual Concept Map (Personalization #1)**:\n```\n{diagram_ascii}\n```",
            f"**Formal Meaning & Notation**: Let $C(t)$ represent the measured clinical quantity at time $t$ (in hours). We connect two representations:\n"
            f"1. **Symbolic Form**: $C(t) = C_0 \\cdot e^{{-kt}}$ (or piecewise rate model depending on {course_label} scope).\n"
            f"2. **Numerical Table**: At $t=0$, $C(0)=120\\text{{ mg/L}}$; at $t=4$, $C(4)=60\\text{{ mg/L}}$; at $t=8$, $C(8)=30\\text{{ mg/L}}$.",
            f"**Hint Before Worked Example (Personalization #1)**: Notice how the concentration halves every 4 hours. Before looking at a full solution, what is the ratio $\\frac{{C(4)}}{{C(0)}}$?",
            f"**Fresh Student Attempt ({difficulty} Difficulty)**: Using the table above, predict $C(12)$ with proper units, and state one reason why $C(t)$ cannot be negative in a real patient.",
        ]
    elif mode == "vocab":
        title = f"2. Vocabulary & Meaning — {course_label} Healthcare Lexicon"
        main_body = [
            "**Term 1: Asymptote / Limiting Threshold**\n"
            "- *Definition*: A value that a function approaches arbitrarily closely as the input grows without bound.\n"
            "- *Notation & Units*: $\\lim_{t \\to \\infty} C(t) = L\\text{ (mg/L)}$.\n"
            "- *Synonym / Paraphrase*: Long-run steady-state ceiling or baseline.\n"
            "- *Mathematical Example*: $C(t) = 50(1 - e^{-0.4t})$ approaches $50\\text{ mg/L}$ during a continuous IV drip.\n"
            "- *Nonexample*: $f(t) = 12t + 5$ grows linearly forever without approaching a finite ceiling.\n"
            "- *Team Healthcare Context*: Prevents overdose by ensuring steady-state bloodstream medication stays below toxic limits.",
            "**Term 2: Instantaneous / Marginal Rate of Change**\n"
            "- *Definition*: The exact rate at which one quantity changes with respect to another at a specific instant or unit.\n"
            "- *Notation & Units*: $f'(t)$ or $\\frac{\\Delta y}{\\Delta x}$ in units of $\\text{mg/(L}\\cdot\\text{hr)}$ or $\\text{USD/patient}$.\n"
            "- *Mathematical Example*: At $t=2\\text{ hr}$, drug clearance is $-8.4\\text{ mg/hr}$.\n"
            "- *Nonexample*: Reporting only the total dose $200\\text{ mg}$ without any time interval.",
            "**Term 3: Parameter vs. Statistic (or Domain Constraint)**\n"
            "- *Definition*: A parameter describes an entire patient population ($p, \\mu$), whereas a statistic describes the observed clinical sample ($\\hat{p}, \\bar{x}$).\n"
            "- *Your Turn*: Write one sentence using **Steady-State Threshold** or **Marginal Rate** in your preferred language.",
        ]
    elif mode == "career":
        title = f"3. Life & Career Applications — Team Healthcare Clinical Modeling"
        main_body = [
            f"**Scenario [Simulated Data — Team Healthcare Telemetry Lab]**: A regional clinic monitors an oral medication for hypertension. After an initial dose of $160\\text{{ mg}}$, the active amount in the bloodstream is modeled by $A(t) = 160(0.82)^t$, where $t$ is measured in hours ($0 \\le t \\le 24$) and $A(t)$ is in milligrams ($\\text{{mg}}$).",
            f"**Guided Step 1 (Variables & Units)**: Identify the independent variable ($t$ in hours), dependent variable ($A(t)$ in $\\text{{mg}}$), and hourly retention factor ($0.82$, meaning $18\\%$ is metabolized per hour).",
            f"**Guided Step 2 ({difficulty} Challenge)**: A therapeutic window requires at least $45\\text{{ mg}}$ in the bloodstream. Set up the inequality $160(0.82)^t \\ge 45$ and determine when the patient needs a booster dose.",
            f"**Transfer Practice (Changed Condition)**: Suppose a patient with slower hepatic metabolism clears only $12\\%$ per hour instead of $18\\%$. How does the decay factor change, and does the time between doses increase or decrease?",
        ]
    elif mode == "business":
        title = "4. Personal Finance & Business — Team Healthcare AI Clinic Model"
        main_body = [
            f"**Healthcare Business Decision Model [Simulated Data]**: Evaluating monthly operations for **Team Healthcare AI Diagnostics Clinic** applying **{course_label}** quantitative modeling.",
            f"- **Assumptions & Inputs**:\n"
            f"  - Patient Volume ($q$): `{int(patients_per_month)} patients/month`\n"
            f"  - Fee per Telehealth/AI Screening ($p$): `${price_per_visit:,.2f} / visit`\n"
            f"  - Fixed Monthly Overhead ($FC$ — rent, EHR software, compliance): `${fixed_cost:,.2f} / month`\n"
            f"  - Variable Cost per Visit ($VC$ — lab consumables, cloud inference): `${variable_cost:,.2f} / visit`",
            f"- **Financial Model Equations**:\n"
            f"  - Revenue Function: $R(q) = {price_per_visit:.2f}q = \\${revenue:,.2f}$\n"
            f"  - Total Cost Function: $C(q) = {fixed_cost:.2f} + {variable_cost:.2f}q = \\${total_cost:,.2f}$\n"
            f"  - Operating Profit: $\\Pi(q) = R(q) - C(q) = \\${profit:,.2f}$ (Operating Margin: `{margin_pct:.1f}%`)\n"
            f"  - Break-Even Volume ($R(q) = C(q)$): $q^* = \\frac{{FC}}{{p - VC}} = \\mathbf{{{breakeven_patients:.1f}\\text{{ patients/month}}}}$",
            f"- **Sensitivity Test (Changed Assumption)**: If reagent/cloud variable costs rise by $+15\\%$ to `${stressed_var_cost:,.2f}/visit`, monthly profit shifts from `${profit:,.2f}` to `${stressed_profit:,.2f}`. *Note: Educational business modeling only; not financial or investment advice.*",
        ]
    elif mode == "diagnose":
        title = f"5. Diagnose & Practice — {course_label} ({difficulty} Level)"
        main_body = [
            f"**Diagnostic Item 1 of 3 ({difficulty} Level)**: A clinic records patient wait times or dosage decay for *{topic}*. Before computing the final numerical value, identify which prerequisite rule applies first:",
            "- **Easy check**: Identify the initial value and units at $t = 0$.\n"
            "- **Medium check**: Link the rate of change to the slope or ratio between two consecutive measurements.\n"
            "- **Hard check**: Justify whether an extrapolation to $t = 72\\text{ hours}$ is valid under the model's domain assumptions.",
            "**Targeted Hint (1 at a time)**: Check whether the rate of change is constant (linear) or proportional to the current amount (exponential/differential).",
            "**Session Tracker**: `Coached items completed: 1` | `Independent items ready: 2`. Submit your reasoning in the box to unlock the next adaptive item!",
        ]
    elif mode == "mistake":
        title = f"6. Mistake Detective — Error Analysis in {course_label}"
        sample_work = student_input if student_input else "Step 1: 160(0.5)^(t/4) = 40  --> Step 2: 80^(t/4) = 40  --> Step 3: t/4 = 40/80 = 0.5"
        main_body = [
            f"**Submitted Student Work Inspected**:\n```\n{sample_work}\n```",
            "**What is Correct**: Step 1 properly sets the initial quantity ($160\\text{ mg}$), half-life decay factor ($0.5^{t/4}$), and target threshold ($40\\text{ mg}$).",
            "**First Unsupported / Invalid Step**: In **Step 2**, multiplying the coefficient $160$ by the base $0.5$ to get $80^{t/4}$ violates the order of operations ($a \\cdot b^x \\ne (ab)^x$). Also, in **Step 3**, solving for an exponent requires logarithms or common bases, not dividing by the base.",
            "**Conversation Error Log & Repair Principle**:\n"
            "- *Issue*: Combined coefficient and exponential base before isolating $b^x$.\n"
            "- *Corrected Principle*: First divide both sides by $160$ to get $(0.5)^{t/4} = \\frac{40}{160} = 0.25 = (0.5)^2$.\n"
            "- *Your Repair Task*: From $(0.5)^{t/4} = (0.5)^2$, solve for $t$ and verify by substituting back into Step 1.",
        ]
    elif mode == "graphs":
        title = f"7. Graphs & Representations — {course_label}"
        main_body = [
            f"**Connecting Four Representations for {topic}**:\n"
            "1. **Verbal**: A healthcare metric starts at an initial peak and decays (or accumulates toward capacity) across 6 time intervals.\n"
            "2. **Symbolic**: $y(t) = 120 \\cdot e^{-0.25t}$ (or clinic profit $\\Pi(q) = (p - VC)q - FC$).\n"
            "3. **Numerical Table**: Shown below with explicit units and domain $0 \\le t \\le 10\\text{ hours}$.\n"
            "4. **Graphical Plot**: Interactive chart rendered below with labeled axes and units.",
            "**Prediction Prompt**: Before reading $t = 8\\text{ hr}$ on the graph, predict whether the curve is concave up or concave down, and state what that concavity means for the rate of medication clearance.",
        ]
    elif mode == "exam":
        title = f"8. Retrieval & Exam Practice — {course_label}"
        main_body = [
            f"**Course & Calculator Policy**: {course_meta['calculator_rule']}",
            f"**Original Practice Free-Response Item ({difficulty})**:\n"
            f"A biomedical sensor measures the rate at which a saline solution enters a recovery tank as $R(t) = 18 + 6\\cos\\left(\\frac{{\\pi t}}{{6}}\\right)$ milliliters per minute for $0 \\le t \\le 12$ minutes.\n"
            f"- **(a)** Find the rate at $t = 3$ minutes with proper units.\n"
            f"- **(b)** Explain the meaning of the accumulation (or average rate of change) over the interval $0 \\le t \\le 6$ in the context of patient hydration monitoring.\n"
            f"- **(c)** State any theorem hypothesis or modeling assumption required to guarantee an instant where the rate equals the average rate.",
            "**Answer Status**: *Withheld until you submit your attempt!* Type your setup for part (a) or (b) to receive staged rubric feedback.",
        ]
    elif mode == "planner":
        title = f"9. Study Planner — {course_label} Review Schedule"
        main_body = [
            f"**Customized 5-Day Interleaved Study Plan ({course_label})**:\n"
            "- **Day 1 (25 min — Concept & Vocabulary Retrieval)**: Self-quiz on 3 core terms without notes + 2 representation matches.\n"
            "- **Day 2 (30 min — Diagnostic & Mistake Repair)**: Complete 4 mixed-difficulty items; log any algebraic or condition errors.\n"
            "- **Day 3 (30 min — Healthcare & Business Modeling)**: Solve 1 clinical career problem and 1 clinic cost/revenue sensitivity problem.\n"
            "- **Day 4 (35 min — Timed Exam Simulation)**: Run 2 no-calculator items + 1 calculator-active item under official course rules.\n"
            "- **Day 5 (20 min — Explain & Defend + Session Note)**: Practice justifying theorem hypotheses / inference conditions aloud.",
            "**Honest Continuity Note**: Save your copyable Session Note below; this tutor does not send automatic push reminders across separate chats.",
        ]
    else:  # defend
        title = f"10. Explain & Defend — {course_label} Reasoning Audit"
        claim = student_input if student_input else "Because the sample mean blood pressure dropped by 6 mmHg, the new treatment is proven effective for all patients."
        main_body = [
            f"**Student Claim Under Review**: *\"{claim}\"*",
            f"**Logical & Mathematical Audit ({course_label})**:\n"
            "- **Evidence Checked**: Identifies a directional change ($-6\\text{ mmHg}$) with proper units.\n"
            "- **Missing Hypothesis / Condition**: In **AP Statistics**, a sample difference alone does not prove causation or statistical significance without checking **Random assignment**, **Normal/Large sample conditions**, and a **$p$-value / confidence interval**. In **AP Calculus**, guarantees require checking **continuity and differentiability** on the closed/open interval.",
            "**Priority Revision Task**: Rewrite your conclusion in 2 sentences so that it (1) explicitly states the required condition/hypothesis and (2) scopes the conclusion to the population or interval supported by the study design.",
            "**Boundary Counterexample Test**: What happens to your claim if the sample size was only $n = 4$ non-randomly selected volunteers?",
        ]

    bilingual_block = (
        f"**{lang_meta['bilingual_tag']} Support**:\n"
        f"- *{lang_meta['greeting']}*\n"
        f"- Key Terms: `{lang_meta['terms']['rate']}` | `{lang_meta['terms']['cost']}` | `{lang_meta['terms']['condition']}`\n"
        f"- *{lang_meta['terms']['hint']}*: Mathematical numbers, units, and symbolic expressions remain invariant across translations."
    )

    context_check = (
        f"**{lang_meta['terms']['check']} (Personalization #2)**:\n"
        f"1. **Course Scope**: Verified for **{course_label}** ({course_meta['scope_note']}).\n"
        f"2. **Units & Constraints**: All quantities carry explicit clinical or financial units (`mg/L`, `hours`, `USD/visit`, `patients/month`).\n"
        f"3. **Healthcare Plausibility**: Checked non-negativity and domain bounds before interpreting model outputs."
    )

    videos = [
        {
            "title": f"{course_label}: {topic} — Conceptual & Worked Demonstration",
            "provider": "Khan Academy / College Board AP Daily (Verified Search Query)",
            "search_query": f"{course} {calc_variant if course == 'AP Calculus' else ''} {topic} worked example",
            "why_it_fits": f"Matches {difficulty} difficulty and reinforces {course_label} notation and representations.",
            "caption_note": f"English captions generally available; verify {language} auto-translate track on the video page before assuming fluency.",
            "follow_up": "Before watching, predict how doubling the initial parameter changes the vertical intercept.",
        },
        {
            "title": "Quantitative Healthcare & Biostatistical Modeling in Practice",
            "provider": "3Blue1Brown / StatQuest / MIT OpenCourseWare (Verified Search Query)",
            "search_query": f"healthcare mathematical modeling {topic} intuition",
            "why_it_fits": "Connects classroom mathematics to clinical dosage, epidemiology, and healthcare operations.",
            "caption_note": "Check transcript and caption availability directly on the provider page.",
            "follow_up": "After watching, explain one limitation of applying a smooth mathematical curve to real patient data.",
        },
    ]

    session_note = (
        f"=== MATH-STUDY-COACH SESSION NOTE (TEAM HEALTHCARE) ===\n"
        f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Team / Student: {TEAM_INFO['team_id']} / {TEAM_INFO['student_name']}\n"
        f"Course: {course_label}\n"
        f"Active Topic: {topic}\n"
        f"Mode Used: {title}\n"
        f"Language Preference: {language} ({'Bilingual English + ' + language if bilingual else 'Single Language'})\n"
        f"Difficulty: {difficulty}\n"
        f"Demonstrated Skills: Model setup, unit tracking, healthcare context interpretation.\n"
        f"Identified Gaps to Review: Explicit statement of theorem hypotheses / inference conditions before final conclusions.\n"
        f"Verification Status: Financial & decay calculations verified analytically; external video caption tracks labeled unconfirmed until opened.\n"
        f"Next Practice Task: Complete the transfer problem with a +15% parameter shift and defend the conclusion in 2 sentences.\n"
        f"======================================================="
    )

    chart_labels = ["t=0h", "t=2h", "t=4h", "t=6h", "t=8h", "t=10h"]
    chart_series_a = [160, 108, 72, 49, 33, 22]
    chart_series_b = [45, 45, 45, 45, 45, 45]

    return {
        "title": title,
        "course_label": course_label,
        "badge": course_meta["badge"],
        "calculator_rule": course_meta["calculator_rule"],
        "scope_note": course_meta["scope_note"],
        "main_body": main_body,
        "bilingual_block": bilingual_block,
        "context_check": context_check,
        "videos": videos,
        "session_note": session_note,
        "business_metrics": {
            "revenue": round(revenue, 2),
            "total_cost": round(total_cost, 2),
            "profit": round(profit, 2),
            "margin_pct": round(margin_pct, 1),
            "breakeven_patients": round(breakeven_patients, 1),
            "stressed_profit": round(stressed_profit, 2),
        },
        "chart": {
            "labels": chart_labels,
            "series_a": chart_series_a,
            "series_b": chart_series_b,
        },
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ team.project_title }}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #0b1120;
      --panel: #111827;
      --panel-2: #1e293b;
      --accent: #06b6d4;
      --accent-2: #10b981;
      --text: #f8fafc;
      --muted: #94a3b8;
      --border: #334155;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: radial-gradient(circle at top right, #0f172a, #0b1120 70%);
      color: var(--text);
      line-height: 1.6;
      padding-bottom: 48px;
    }
    header {
      background: linear-gradient(135deg, rgba(6,182,212,0.18), rgba(16,185,129,0.12));
      border-bottom: 1px solid var(--border);
      padding: 22px 28px;
    }
    .header-inner {
      max-width: 1320px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    .brand-title {
      font-size: 1.45rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #fff;
    }
    .brand-sub {
      color: var(--muted);
      font-size: 0.92rem;
      margin-top: 4px;
    }
    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .pill {
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--accent);
      color: #67e8f9;
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    .pill.green {
      border-color: var(--accent-2);
      color: #6ee7b7;
    }
    .container {
      max-width: 1320px;
      margin: 24px auto;
      padding: 0 20px;
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 24px;
    }
    @media (max-width: 980px) {
      .container { grid-template-columns: 1fr; }
    }
    .card {
      background: rgba(17, 24, 39, 0.92);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.35);
    }
    .card h2 {
      font-size: 1.08rem;
      margin-bottom: 14px;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    label {
      display: block;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--muted);
      margin-top: 12px;
      margin-bottom: 5px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    select, input, textarea {
      width: 100%;
      background: var(--panel-2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 0.92rem;
    }
    textarea { min-height: 76px; resize: vertical; }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      margin-top: 16px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #04131a;
      font-weight: 700;
      border: none;
      padding: 12px 16px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 0.95rem;
      text-decoration: none;
      transition: transform 0.12s ease, opacity 0.12s ease;
    }
    .btn:hover { opacity: 0.94; transform: translateY(-1px); }
    .btn-secondary {
      background: var(--panel-2);
      color: #e2e8f0;
      border: 1px solid var(--border);
      margin-top: 10px;
    }
    .modes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }
    .mode-tile {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 11px 13px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .mode-tile:hover, .mode-tile.active {
      border-color: var(--accent);
      background: rgba(6, 182, 212, 0.13);
    }
    .mode-tile .m-title {
      font-weight: 700;
      font-size: 0.88rem;
      color: #fff;
    }
    .mode-tile .m-desc {
      font-size: 0.76rem;
      color: var(--muted);
      margin-top: 4px;
    }
    .output-section {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .banner-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      background: rgba(30, 41, 59, 0.7);
      border-left: 4px solid var(--accent);
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 0.86rem;
    }
    .step-block {
      background: rgba(30, 41, 59, 0.55);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 10px;
      white-space: pre-line;
      font-size: 0.93rem;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
      gap: 12px;
      margin-top: 10px;
    }
    .kpi {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      text-align: center;
    }
    .kpi .val {
      font-size: 1.25rem;
      font-weight: 800;
      color: #38bdf8;
    }
    .kpi .lbl {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 3px;
    }
    pre.session-box {
      background: #020617;
      border: 1px solid var(--border);
      color: #a7f3d0;
      padding: 14px;
      border-radius: 10px;
      font-size: 0.8rem;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    table.migration-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      margin-top: 10px;
    }
    table.migration-table th, table.migration-table td {
      border: 1px solid var(--border);
      padding: 9px 11px;
      text-align: left;
    }
    table.migration-table th {
      background: var(--panel-2);
      color: #67e8f9;
    }
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    @media (max-width: 780px) {
      .two-col { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div>
        <div class="brand-title">🏥 {{ team.project_title }}</div>
        <div class="brand-sub">Reusable Claude Skill (<code>{{ team.skill_name }}</code>) &amp; AI Business Helper Web Service • Built for Render.com</div>
      </div>
      <div class="pill-row">
        <span class="pill">Team ID: {{ team.team_id }}</span>
        <span class="pill">Student: {{ team.student_name }}</span>
        <span class="pill green">Skill Level: {{ team.skill_level }}</span>
        <span class="pill green">10 Modes • 4 Courses • 9+ Languages</span>
      </div>
    </div>
  </header>

  <div class="container">
    <!-- Left Control Panel -->
    <aside class="card">
      <h2>⚙️ Course &amp; Skill Intake</h2>

      <label for="course">1. Required Course Selection</label>
      <select id="course" onchange="onCourseChange()">
        <option value="Honors Algebra 2">Honors Algebra 2 (Non-AP)</option>
        <option value="AP Precalculus" selected>AP Precalculus</option>
        <option value="AP Calculus">AP Calculus (Prompts AB / BC)</option>
        <option value="AP Statistics">AP Statistics</option>
      </select>

      <div id="calcVariantWrap" style="display:none;">
        <label for="calc_variant">AP Calculus Track (Required AB or BC)</label>
        <select id="calc_variant" onchange="runTutor()">
          <option value="AB">AP Calculus AB</option>
          <option value="BC">AP Calculus BC</option>
        </select>
      </div>

      <label for="topic">2. Course Anchor Topic</label>
      <input type="text" id="topic" value="Removable Discontinuities & Piecewise Dosage Functions" />

      <label for="language">3. Multilingual Support</label>
      <select id="language" onchange="runTutor()">
        {% for lang in languages %}
        <option value="{{ lang }}" {% if lang == 'Spanish' %}selected{% endif %}>{{ lang }}</option>
        {% endfor %}
      </select>

      <label for="bilingual">Language Mode</label>
      <select id="bilingual" onchange="runTutor()">
        <option value="true" selected>Bilingual (English + Selected Language)</option>
        <option value="false">Selected Language Primary</option>
      </select>

      <label for="difficulty">4. Difficulty &amp; Diagnostic Demand</label>
      <select id="difficulty" onchange="runTutor()">
        <option value="Easy">Easy (Prerequisites &amp; 1 Core Step)</option>
        <option value="Medium" selected>Medium (Linked Steps &amp; Interpretation)</option>
        <option value="Hard">Hard (Unfamiliar Transfer &amp; Justification)</option>
        <option value="Mixed">Mixed (Adaptive Progression)</option>
      </select>

      <label for="student_input">5. Student Work / Claim (for Mistake Detective or Explain &amp; Defend)</label>
      <textarea id="student_input" placeholder="Paste your math steps, healthcare scenario question, or statistical claim here..."></textarea>

      <h2 style="margin-top:20px;">💼 Team Healthcare Business Inputs</h2>
      <div class="two-col">
        <div>
          <label for="patients_per_month">Patients / Mo</label>
          <input type="number" id="patients_per_month" value="240" />
        </div>
        <div>
          <label for="price_per_visit">Fee / Visit ($)</label>
          <input type="number" id="price_per_visit" value="85" />
        </div>
        <div>
          <label for="fixed_cost">Fixed Cost ($)</label>
          <input type="number" id="fixed_cost" value="9200" />
        </div>
        <div>
          <label for="variable_cost">Var Cost ($)</label>
          <input type="number" id="variable_cost" value="28" />
        </div>
      </div>

      <button class="btn" onclick="runTutor()">🚀 Run AI Business &amp; Math Coach</button>
      <a class="btn btn-secondary" href="/download-skill-zip">📦 Download math-study-coach.zip (Claude Skill)</a>
      <a class="btn btn-secondary" href="/skill-md" target="_blank">📄 View Raw SKILL.md</a>
    </aside>

    <!-- Main Interactive Workspace -->
    <main class="output-section">
      <div class="card">
        <h2>🧭 Select Any of the 10 Required Tutoring &amp; Business Modes</h2>
        <div class="modes-grid" id="modesGrid">
          {% for m in modes %}
          <div class="mode-tile {% if m.id == 'learn' %}active{% endif %}" data-mode="{{ m.id }}" onclick="selectMode('{{ m.id }}')">
            <div class="m-title">{{ m.icon }} {{ m.number }}. {{ m.name }}</div>
            <div class="m-desc">{{ m.short }}</div>
          </div>
          {% endfor %}
        </div>

        <div class="banner-meta" id="courseBanner">
          <div><strong>Active Course:</strong> <span id="outCourse">AP Precalculus</span></div>
          <div><strong>Calculator Policy:</strong> <span id="outCalcRule">Loading...</span></div>
          <div><strong>Scope Priority:</strong> <span id="outScopeNote">Loading...</span></div>
        </div>
      </div>

      <div class="card">
        <h2 id="outTitle">1. Learn a Topic</h2>
        <div id="outSteps"></div>
        <div class="step-block" id="outBilingual" style="border-color:#06b6d4;"></div>
        <div class="step-block" id="outContextCheck" style="border-color:#10b981;"></div>
      </div>

      <!-- Healthcare Business KPIs & Interactive Representation Chart -->
      <div class="two-col">
        <div class="card">
          <h2>🏥 Team Healthcare Clinic Financial Model</h2>
          <p style="font-size:0.83rem; color:var(--muted);">Live quantitative business model connecting course functions to clinic operations:</p>
          <div class="kpi-grid">
            <div class="kpi"><div class="val" id="kpiRev">$20,400</div><div class="lbl">Monthly Revenue</div></div>
            <div class="kpi"><div class="val" id="kpiCost">$15,920</div><div class="lbl">Total Cost (FC+VC)</div></div>
            <div class="kpi"><div class="val" id="kpiProfit">$4,480</div><div class="lbl">Operating Profit</div></div>
            <div class="kpi"><div class="val" id="kpiMargin">22.0%</div><div class="lbl">Operating Margin</div></div>
            <div class="kpi"><div class="val" id="kpiBE">161.4</div><div class="lbl">Break-Even Patients</div></div>
            <div class="kpi"><div class="val" id="kpiStress">$3,472</div><div class="lbl">Profit (+15% VC Shock)</div></div>
          </div>
        </div>

        <div class="card">
          <h2>📈 Mode 7: Dual Graphical Representation</h2>
          <canvas id="mathChart" height="175"></canvas>
        </div>
      </div>

      <!-- Video Demonstrations & Session Note -->
      <div class="two-col">
        <div class="card">
          <h2>🎥 Verified Video Search &amp; Viewing-to-Learning</h2>
          <div id="outVideos"></div>
        </div>

        <div class="card">
          <h2>📋 Copyable Session Note (Honest Continuity)</h2>
          <pre class="session-box" id="outSessionNote"></pre>
          <button class="btn btn-secondary" onclick="copySessionNote()">📋 Copy Session Note for Next Chat</button>
        </div>
      </div>

      <!-- Migration Map & Verification Record -->
      <div class="card">
        <h2>🗺️ Gem-to-Claude Migration Map &amp; 13-Test Verification Summary</h2>
        <table class="migration-table">
          <thead>
            <tr>
              <th>Original Gem Feature / Instruction</th>
              <th>Action</th>
              <th>Claude Skill / Web App Location</th>
              <th>Verification Test (from 13-Test Log)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Course-specific AP / Honors math rules &amp; calculator policy</td>
              <td><strong>Keep &amp; Scope</strong></td>
              <td><code>SKILL.md</code> + <code>references/course-guide.md</code></td>
              <td>Test #1 &amp; #8: 4-course intake + AB/BC prompt + calculator rule check</td>
            </tr>
            <tr>
              <td>10 Learning Modes including Healthcare Career &amp; Business modeling</td>
              <td><strong>Extend</strong></td>
              <td><code>SKILL.md</code> Modes 1–10 + Team Healthcare Business Engine</td>
              <td>Test #2, #3, #4, #5: Vocabulary, Simulated Healthcare data, Clinic ROI</td>
            </tr>
            <tr>
              <td>Multilingual &amp; Bilingual tutoring (9+ languages &amp; Creoles)</td>
              <td><strong>Add</strong></td>
              <td><code>SKILL.md</code> Language Layer + Bilingual Toggle</td>
              <td>Test #6 &amp; #7: Switch to Bilingual Spanish / Haitian Creole preserving math</td>
            </tr>
            <tr>
              <td>Personalization #1: Visual concept diagram &amp; hint before worked example</td>
              <td><strong>Add</strong></td>
              <td><code>SKILL.md</code> Opening &amp; Mode 1/5/6</td>
              <td>Retest #12: Confirmed diagram + single hint prior to full solution</td>
            </tr>
            <tr>
              <td>Personalization #2: Healthcare Context, Units &amp; Conditions Check</td>
              <td><strong>Add</strong></td>
              <td><code>SKILL.md</code> Shared Rules &amp; Mode 3/4/10</td>
              <td>Retest #13: Verified theorem hypotheses &amp; statistical conditions in context</td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  </div>

  <script>
    let currentMode = 'learn';
    let chartInstance = null;

    const courseTopics = {
      "Honors Algebra 2": "Exponential Growth & Decay in Medication Half-Life",
      "AP Precalculus": "Removable Discontinuities & Piecewise Dosage Functions",
      "AP Calculus": "Instantaneous Rate of Change in IV Infusion & Clearance (AB/BC)",
      "AP Statistics": "Two-Sample Inference & Clinical Trial Efficacy"
    };

    function onCourseChange() {
      const course = document.getElementById('course').value;
      const calcWrap = document.getElementById('calcVariantWrap');
      calcWrap.style.display = (course === 'AP Calculus') ? 'block' : 'none';
      document.getElementById('topic').value = courseTopics[course] || "";
      runTutor();
    }

    function selectMode(modeId) {
      currentMode = modeId;
      document.querySelectorAll('.mode-tile').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-mode') === modeId);
      });
      runTutor();
    }

    async function runTutor() {
      const payload = {
        course: document.getElementById('course').value,
        calc_variant: document.getElementById('calc_variant').value,
        mode: currentMode,
        topic: document.getElementById('topic').value,
        language: document.getElementById('language').value,
        bilingual: document.getElementById('bilingual').value === 'true',
        difficulty: document.getElementById('difficulty').value,
        student_input: document.getElementById('student_input').value,
        patients_per_month: document.getElementById('patients_per_month').value,
        price_per_visit: document.getElementById('price_per_visit').value,
        fixed_cost: document.getElementById('fixed_cost').value,
        variable_cost: document.getElementById('variable_cost').value
      };

      const res = await fetch('/api/tutor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      document.getElementById('outCourse').textContent = data.course_label + " — " + data.badge;
      document.getElementById('outCalcRule').textContent = data.calculator_rule;
      document.getElementById('outScopeNote').textContent = data.scope_note;
      document.getElementById('outTitle').textContent = data.title;

      const stepsContainer = document.getElementById('outSteps');
      stepsContainer.innerHTML = '';
      data.main_body.forEach(step => {
        const div = document.createElement('div');
        div.className = 'step-block';
        div.innerHTML = step.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
        stepsContainer.appendChild(div);
      });

      document.getElementById('outBilingual').innerHTML = data.bilingual_block.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      document.getElementById('outContextCheck').innerHTML = data.context_check.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');

      const bm = data.business_metrics;
      document.getElementById('kpiRev').textContent = '$' + bm.revenue.toLocaleString();
      document.getElementById('kpiCost').textContent = '$' + bm.total_cost.toLocaleString();
      document.getElementById('kpiProfit').textContent = '$' + bm.profit.toLocaleString();
      document.getElementById('kpiMargin').textContent = bm.margin_pct + '%';
      document.getElementById('kpiBE').textContent = bm.breakeven_patients;
      document.getElementById('kpiStress').textContent = '$' + bm.stressed_profit.toLocaleString();

      const vidContainer = document.getElementById('outVideos');
      vidContainer.innerHTML = '';
      data.videos.forEach(v => {
        const d = document.createElement('div');
        d.className = 'step-block';
        const ytUrl = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(v.search_query);
        d.innerHTML = `<strong>🎬 ${v.title}</strong><br/>
          <span style="color:#94a3b8;font-size:0.82rem;">Source: ${v.provider}</span><br/>
          <strong>Why it fits:</strong> ${v.why_it_fits}<br/>
          <strong>Captions &amp; Access:</strong> ${v.caption_note}<br/>
          <strong>Pre-Viewing Prompt:</strong> ${v.follow_up}<br/>
          <a href="${ytUrl}" target="_blank" style="color:#38bdf8;font-weight:600;display:inline-block;margin-top:6px;">🔎 Open Verified Video Search &rarr;</a>`;
        vidContainer.appendChild(d);
      });

      document.getElementById('outSessionNote').textContent = data.session_note;
      renderChart(data.chart);
    }

    function renderChart(chartData) {
      const ctx = document.getElementById('mathChart').getContext('2d');
      if (chartInstance) chartInstance.destroy();
      chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: chartData.labels,
          datasets: [
            {
              label: 'Active Bloodstream Concentration A(t) [mg]',
              data: chartData.series_a,
              borderColor: '#06b6d4',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              fill: true,
              tension: 0.3
            },
            {
              label: 'Minimum Therapeutic Threshold [45 mg]',
              data: chartData.series_b,
              borderColor: '#f59e0b',
              borderDash: [6, 6],
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { labels: { color: '#e2e8f0' } }
          },
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } }
          }
        }
      });
    }

    function copySessionNote() {
      const text = document.getElementById('outSessionNote').textContent;
      navigator.clipboard.writeText(text);
      alert('Session Note copied! Paste it into a fresh chat for honest continuity.');
    }

    window.addEventListener('DOMContentLoaded', runTutor);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        team=TEAM_INFO,
        modes=MODES,
        languages=list(LANGUAGES.keys()),
    )


@app.route("/api/tutor", methods=["POST"])
def api_tutor():
    payload = request.get_json(silent=True) or {}
    return jsonify(build_mode_response(payload))


@app.route("/skill-md")
def view_skill_md():
    return app.response_class(SKILL_MD_CONTENT, mimetype="text/plain; charset=utf-8")


@app.route("/download-skill-zip")
def download_skill_zip():
    course_guide_md = (
        "# Team Healthcare Course Guide (references/course-guide.md)\n\n"
        "- **Team ID**: Team Healthcare\n"
        "- **Student**: Jair\n"
        "- **Skill Level**: Advanced\n\n"
        "## Course Foundations\n"
        "1. **Honors Algebra 2**: Teacher classroom scope, non-AP expectations, algebraic setups required.\n"
        "2. **AP Precalculus**: Modeling with functions, rate of change, exam-assessed vs. healthcare enrichment.\n"
        "3. **AP Calculus (AB / BC)**: Always confirm AB or BC; check theorem hypotheses (IVT, MVT, EVT, FTC).\n"
        "4. **AP Statistics**: Study design, randomness, 10% condition, Normal/Large sample, conclusions in clinical context.\n"
    )
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("math-study-coach/SKILL.md", SKILL_MD_CONTENT)
        zf.writestr("math-study-coach/references/course-guide.md", course_guide_md)
    mem_zip.seek(0)
    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name="math-study-coach.zip",
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "team": TEAM_INFO["team_id"], "student": TEAM_INFO["student_name"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
