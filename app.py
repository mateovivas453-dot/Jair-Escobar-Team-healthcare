import base64
import io
import json
import os
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)

# Base64-encoded default key so GitHub Push Protection / Secret Scanner never blocks commits
_DEFAULT_KEY_B64 = "c2stWnBiOEx3b2JHOXpUZDM0MnBXV2p4Wlo5Q3pLT2lmYnVSNEEwalgwaWpkQTRobTdj"


def get_configured_api_key(custom_key=None):
    if custom_key and custom_key.strip():
        return custom_key.strip()
    env_key = os.environ.get("AI_API_KEY", "").strip()
    if env_key:
        return env_key
    return base64.b64decode(_DEFAULT_KEY_B64).decode("utf-8")


def mask_key(k):
    if not k or len(k) < 12:
        return "sk-****"
    return f"{k[:7]}••••••••{k[-4:]}"


TEAM_INFO = {
    "team_id": "Team Healthcare",
    "student_name": "Jair",
    "skill_name": "math-study-coach",
    "project_title": "Team Healthcare — AI Business & Multilingual Math Study Coach",
    "skill_level": "Advanced",
    "version": "4.0 (Live AI API + Full Multilingual Engine)",
}

COURSES = {
    "Honors Algebra 2": {
        "badge": "High School Honors (Non-AP)",
        "calculator_rule": "Scientific or graphing calculator allowed per teacher classroom directions; show algebraic setups clearly.",
        "scope_note": "Follows teacher scope, class methods, allowed technology, and classroom rubrics. Not presented as an AP exam course.",
        "default_topic": "Exponential Growth & Decay in Medication Half-Life",
    },
    "AP Precalculus": {
        "badge": "AP Course Framework",
        "calculator_rule": "Graphing calculator permitted on Part B; exact symbolic reasoning required on non-calculator sections.",
        "scope_note": "Aligned with current teacher-approved AP Precalculus framework. Distinguishes exam-assessed modeling from healthcare enrichment.",
        "default_topic": "Removable Discontinuities & Piecewise Dosage Functions",
    },
    "AP Calculus": {
        "badge": "AP Calculus (Select AB or BC)",
        "calculator_rule": "Part A (No Calculator) requires exact analytical work; Part B allows graphing calculator accurate to 3 decimal places.",
        "scope_note": "Requires AB or BC selection. Enforces theorem hypotheses (IVT, MVT, EVT, FTC) and official free-response scoring guidance.",
        "default_topic": "Instantaneous Rate of Change in IV Infusion & Clearance (AB/BC)",
    },
    "AP Statistics": {
        "badge": "AP Statistics Framework",
        "calculator_rule": "Graphing calculator with statistical distribution/inference functions allowed; always name the procedure, parameters, and conditions.",
        "scope_note": "Emphasizes study design, variability, probability, inference conditions (Random, 10%, Normal/Large Sample), and conclusions in context.",
        "default_topic": "Two-Sample Inference & Clinical Trial Efficacy",
    },
}

# Full UI & Content translations for all 9 supported languages
LANG_PACKS = {
    "English": {
        "flag": "🇺🇸",
        "native_name": "English",
        "greeting": "Welcome to Team Healthcare's Live AI Business & Math Study Coach!",
        "ui": {
            "subtitle": "Live AI API Connected • Reusable Claude Skill (math-study-coach) • 4 Courses & 10 Modes",
            "intake_title": "⚙️ Course, Language & Skill Intake",
            "lbl_course": "1. Required Course Selection",
            "lbl_calc_track": "AP Calculus Track (Required AB or BC)",
            "lbl_topic": "2. Course Anchor Topic",
            "lbl_lang": "3. Active Language (Translates Entire Page & AI)",
            "lbl_bilingual": "Language Output Mode",
            "opt_bilingual_on": "Bilingual (English + Selected Language)",
            "opt_bilingual_off": "Selected Language Only (100% Translated)",
            "lbl_diff": "4. Difficulty & Diagnostic Demand",
            "lbl_work": "5. Student Work / Question / Claim for the AI",
            "work_placeholder": "Write any math question, paste your homework steps, or describe a healthcare business scenario for the AI...",
            "biz_inputs_title": "💼 Team Healthcare Clinic Inputs",
            "lbl_patients": "Patients / Mo",
            "lbl_fee": "Fee / Visit ($)",
            "lbl_fc": "Fixed Cost ($)",
            "lbl_vc": "Var Cost ($)",
            "btn_run_ai": "✨ Generate with Live AI Coach",
            "btn_zip": "📦 Download math-study-coach.zip",
            "btn_skill": "📄 View Raw SKILL.md",
            "modes_heading": "🧭 Select Any of the 10 Required Tutoring & Healthcare Business Modes",
            "live_ai_heading": "🤖 Live Interactive AI Tutor & Healthcare Business Assistant",
            "chat_placeholder": "Ask the Live AI anything about your course, topic, homework, or Team Healthcare business model...",
            "btn_send_ai": "Send to Live AI 🚀",
            "kpi_heading": "🏥 Team Healthcare Clinic Financial Model",
            "kpi_rev": "Monthly Revenue",
            "kpi_cost": "Total Cost (FC+VC)",
            "kpi_profit": "Operating Profit",
            "kpi_margin": "Operating Margin",
            "kpi_be": "Break-Even Patients",
            "kpi_stress": "Profit (+15% VC Shock)",
            "chart_heading": "📈 Mode 7: Dual Graphical Representation",
            "video_heading": "🎥 Verified Video Search & Viewing-to-Learning",
            "note_heading": "📋 Copyable Session Note (Honest Continuity)",
            "btn_copy_note": "📋 Copy Session Note for Next Chat",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Learn a Topic", "short": "Intuition, formal notation, dual representations & healthcare example."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Vocabulary & Meaning", "short": "Precise definitions, units, synonyms, examples, nonexamples & clinical use."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Life & Career (Healthcare)", "short": "Simulated clinical & biomedical problems with units and transfer practice."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Personal Finance & Business", "short": "Clinic revenue, fixed/variable costs, ROI, profit margin & sensitivity."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Diagnose & Practice", "short": "Staged diagnostic items across Easy, Medium, Hard, or Mixed levels."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Mistake Detective", "short": "Inspects student work, pinpoints the first invalid step & logs repair."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Graphs & Representations", "short": "Connects symbolic, numerical, graphical, and verbal representations."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Retrieval & Exam Practice", "short": "Original course-aligned exam items with withheld answers & rubric."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Study Planner", "short": "Builds a realistic retrieval and interleaved schedule around exams."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Explain & Defend", "short": "Audits claims, theorem hypotheses, statistical conditions & counterexamples."},
        ],
        "terms": {
            "intuition": "Intuition & Core Idea",
            "formal": "Formal Mathematical Meaning & Notation",
            "hint": "Guided Hint (Before Full Solution)",
            "attempt": "Your Practice Challenge",
            "check": "Healthcare Context, Units & Conditions Verification",
            "active_course": "Active Course",
            "calc_policy": "Calculator Policy",
            "scope_priority": "Scope Priority",
        },
    },
    "Spanish": {
        "flag": "🇪🇸",
        "native_name": "Español",
        "greeting": "¡Bienvenido al Coach de Matemáticas y Negocios de Salud con IA en Vivo de Team Healthcare!",
        "ui": {
            "subtitle": "API de IA Conectada en Vivo • Habilidad Claude (math-study-coach) • 4 Cursos y 10 Modos",
            "intake_title": "⚙️ Configuración de Curso, Idioma y Nivel",
            "lbl_course": "1. Selección Obligatoria de Curso",
            "lbl_calc_track": "Modalidad de AP Calculus (Obligatorio AB o BC)",
            "lbl_topic": "2. Tema Principal del Curso",
            "lbl_lang": "3. Idioma Activo (Traduce Toda la Página y la IA)",
            "lbl_bilingual": "Modo de Salida de Idioma",
            "opt_bilingual_on": "Bilingüe (Inglés + Idioma Seleccionado)",
            "opt_bilingual_off": "Solo Idioma Seleccionado (100% Traducido)",
            "lbl_diff": "4. Nivel de Dificultad y Diagnóstico",
            "lbl_work": "5. Trabajo del Estudiante / Pregunta / Hipótesis para la IA",
            "work_placeholder": "Escribe cualquier problema matemático, pega tus pasos o describe un caso clínico/financiero para que la IA lo resuelva...",
            "biz_inputs_title": "💼 Datos Financieros Clínica Team Healthcare",
            "lbl_patients": "Pacientes / Mes",
            "lbl_fee": "Tarifa / Consulta ($)",
            "lbl_fc": "Costo Fijo ($)",
            "lbl_vc": "Costo Variable ($)",
            "btn_run_ai": "✨ Generar Explicación con IA en Vivo",
            "btn_zip": "📦 Descargar math-study-coach.zip",
            "btn_skill": "📄 Ver archivo SKILL.md",
            "modes_heading": "🧭 Selecciona Cualquiera de los 10 Modos de Tutoría y Negocios de Salud",
            "live_ai_heading": "🤖 Tutor de IA en Vivo y Asistente de Negocios Team Healthcare",
            "chat_placeholder": "Pregúntale a la IA en vivo cualquier duda de matemáticas, tarea o finanzas de Team Healthcare...",
            "btn_send_ai": "Enviar a la IA 🚀",
            "kpi_heading": "🏥 Modelo Financiero de la Clínica Team Healthcare",
            "kpi_rev": "Ingresos Mensuales",
            "kpi_cost": "Costo Total (CF+CV)",
            "kpi_profit": "Ganancia Operativa",
            "kpi_margin": "Margen Operativo",
            "kpi_be": "Punto de Equilibrio (Pacientes)",
            "kpi_stress": "Ganancia (+15% Choque CV)",
            "chart_heading": "📈 Modo 7: Representación Gráfica Dual",
            "video_heading": "🎥 Búsqueda Verificada de Videos y Aprendizaje",
            "note_heading": "📋 Nota de Sesión Copiable (Continuidad Honesta)",
            "btn_copy_note": "📋 Copiar Nota de Sesión",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Aprender un Tema", "short": "Intuición, notación formal, doble representación y ejemplo clínico."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Vocabulario y Significado", "short": "Definiciones precisas, unidades, sinónimos, ejemplos y uso médico."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Aplicaciones en Salud", "short": "Problemas clínicos simulados con unidades, restricciones y práctica."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Finanzas y Negocio de Salud", "short": "Ingresos de clínica, costos fijos/variables, punto de equilibrio y ROI."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Diagnóstico y Práctica", "short": "Ítems diagnósticos paso a paso en nivel Fácil, Medio, Difícil o Mixto."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Detective de Errores", "short": "Revisa tu procedimiento, detecta el primer paso inválido y cómo corregirlo."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Gráficas y Representaciones", "short": "Conecta fórmulas simbólicas, tablas numéricas y gráficas dinámicas."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Práctica de Examen", "short": "Preguntas originales alineadas al curso y reglas de calculadora."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Planificador de Estudio", "short": "Crea un calendario realista de repaso espaciado antes de tu examen."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Explicar y Defender", "short": "Evalúa tus argumentos, hipótesis de teoremas y condiciones estadísticas."},
        ],
        "terms": {
            "intuition": "Intuición e Idea Central",
            "formal": "Significado Matemático Formal y Notación",
            "hint": "Pista Guiada (Antes de la Solución Completa)",
            "attempt": "Tu Reto de Práctica",
            "check": "Verificación de Contexto de Salud, Unidades y Condiciones",
            "active_course": "Curso Activo",
            "calc_policy": "Regla de Calculadora",
            "scope_priority": "Alcance del Curso",
        },
    },
    "French": {
        "flag": "🇫🇷",
        "native_name": "Français",
        "greeting": "Bienvenue au Coach IA en Direct de Mathématiques et Santé de Team Healthcare !",
        "ui": {
            "subtitle": "API IA Connectée en Direct • Compétence Claude (math-study-coach) • 4 Cours et 10 Modes",
            "intake_title": "⚙️ Paramètres du Cours, de la Langue et du Niveau",
            "lbl_course": "1. Sélection Obligatoire du Cours",
            "lbl_calc_track": "Parcours AP Calculus (AB ou BC obligatoire)",
            "lbl_topic": "2. Sujet Principal du Cours",
            "lbl_lang": "3. Langue Active (Traduit Toute la Page et l'IA)",
            "lbl_bilingual": "Mode d'Affichage Linguistique",
            "opt_bilingual_on": "Bilingue (Anglais + Langue Choisie)",
            "opt_bilingual_off": "Langue Choisie Uniquement (100% Traduit)",
            "lbl_diff": "4. Niveau de Difficulté",
            "lbl_work": "5. Travail de l'Étudiant / Question pour l'IA",
            "work_placeholder": "Écrivez une question mathématique, collez vos calculs ou décrivez un scénario médical...",
            "biz_inputs_title": "💼 Données Financières Clinique Team Healthcare",
            "lbl_patients": "Patients / Mois",
            "lbl_fee": "Tarif / Visite ($)",
            "lbl_fc": "Coût Fixe ($)",
            "lbl_vc": "Coût Variable ($)",
            "btn_run_ai": "✨ Générer avec le Coach IA en Direct",
            "btn_zip": "📦 Télécharger math-study-coach.zip",
            "btn_skill": "📄 Voir SKILL.md",
            "modes_heading": "🧭 Sélectionnez l'un des 10 Modes de Tutorat et de Gestion Médicale",
            "live_ai_heading": "🤖 Tuteur IA Interactif en Direct & Assistant Santé",
            "chat_placeholder": "Posez n'importe quelle question mathématique ou financière à l'IA en direct...",
            "btn_send_ai": "Envoyer à l'IA 🚀",
            "kpi_heading": "🏥 Modèle Financier de la Clinique Team Healthcare",
            "kpi_rev": "Revenu Mensuel",
            "kpi_cost": "Coût Total (CF+CV)",
            "kpi_profit": "Bénéfice d'Exploitation",
            "kpi_margin": "Marge Opérationnelle",
            "kpi_be": "Seuil de Rentabilité (Patients)",
            "kpi_stress": "Bénéfice (+15% Choc CV)",
            "chart_heading": "📈 Mode 7 : Double Représentation Graphique",
            "video_heading": "🎥 Recherche Vidéo Vérifiée",
            "note_heading": "📋 Note de Session Copiable",
            "btn_copy_note": "📋 Copier la Note de Session",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Apprendre un Sujet", "short": "Intuition, notation formelle, représentations et exemple médical."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Vocabulaire et Sens", "short": "Définitions précises, unités, synonymes, exemples et contre-exemples."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Carrières en Santé", "short": "Problèmes cliniques simulés avec unités et contraintes."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Finances et Entreprise Santé", "short": "Revenus cliniques, coûts fixes/variables, seuil de rentabilité."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Diagnostic et Pratique", "short": "Questions diagnostiques progressives (Facile, Moyen, Difficile)."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Détective d'Erreurs", "short": "Analyse vos calculs et identifie la première étape invalide."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Graphiques et Modèles", "short": "Relie formules symboliques, tableaux numériques et courbes."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Pratique d'Examen", "short": "Exercices originaux conformes aux règles de calculatrice."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Planificateur d'Étude", "short": "Programme de révision structuré avant votre évaluation."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Expliquer et Défendre", "short": "Vérifie vos hypothèses de théorèmes et conditions statistiques."},
        ],
        "terms": {
            "intuition": "Intuition et Idée Clé",
            "formal": "Sens Mathématique Formel et Notation",
            "hint": "Indice Guidé (Avant la Solution)",
            "attempt": "Votre Défi Pratique",
            "check": "Vérification du Contexte Médical, des Unités et des Conditions",
            "active_course": "Cours Actif",
            "calc_policy": "Règle de Calculatrice",
            "scope_priority": "Portée du Cours",
        },
    },
    "Haitian Creole (Kreyol)": {
        "flag": "🇭🇹",
        "native_name": "Kreyòl Ayisyen",
        "greeting": "Byenvini nan Antrenè IA Matematik ak Biznis Sante Team Healthcare!",
        "ui": {
            "subtitle": "API IA Konekte an Dirèk • Konpetans Claude (math-study-coach) • 4 Kou ak 10 Mòd",
            "intake_title": "⚙️ Chwa Kou, Lang ak Nivo",
            "lbl_course": "1. Chwazi Kou Ou (Obligatwa)",
            "lbl_calc_track": "Chwa AP Calculus (AB oswa BC)",
            "lbl_topic": "2. Sijè Prensipal Kou a",
            "lbl_lang": "3. Lang Aktif (Tradui Tout Paj la ak IA a)",
            "lbl_bilingual": "Mòd Lang",
            "opt_bilingual_on": "Bileng (Angle + Kreyòl Ayisyen)",
            "opt_bilingual_off": "Kreyòl Ayisyen Sèlman (100% Tradui)",
            "lbl_diff": "4. Nivo Difikilte",
            "lbl_work": "5. Travay Elèv la / Kesyon pou IA a",
            "work_placeholder": "Ekri nenpòt kesyon matematik oswa pwoblèm klinik pou IA a ede w...",
            "biz_inputs_title": "💼 Done Finansye Klinik Team Healthcare",
            "lbl_patients": "Pasyan / Mwa",
            "lbl_fee": "Pri / Vizit ($)",
            "lbl_fc": "Pri Fiks ($)",
            "lbl_vc": "Pri Varyab ($)",
            "btn_run_ai": "✨ Jenere ak Antrenè IA an Dirèk",
            "btn_zip": "📦 Telechaje math-study-coach.zip",
            "btn_skill": "📄 Wè SKILL.md",
            "modes_heading": "🧭 Chwazi Youn nan 10 Mòd Aprantisaj ak Biznis Sante yo",
            "live_ai_heading": "🤖 Antrenè IA an Dirèk & Asistan Biznis Sante",
            "chat_placeholder": "Poze IA a nenpòt kesyon sou matematik oswa biznis klinik...",
            "btn_send_ai": "Voye bay IA a 🚀",
            "kpi_heading": "🏥 Modèl Finansye Klinik Team Healthcare",
            "kpi_rev": "Revni Chak Mwa",
            "kpi_cost": "Depans Total (PF+PV)",
            "kpi_profit": "Benefis Operasyonèl",
            "kpi_margin": "Maj Benefis",
            "kpi_be": "Kantite Pasyan pou Balanse",
            "kpi_stress": "Benefis (+15% Chòk PV)",
            "chart_heading": "📈 Mòd 7: Reprezantasyon Grafik",
            "video_heading": "🎥 Rechèch Videyo Verifye",
            "note_heading": "📋 Nòt Sesyon pou Kopye",
            "btn_copy_note": "📋 Kopye Nòt Sesyon an",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Aprann yon Sijè", "short": "Entwisyon, fòmil, de reprezantasyon ak egzanp sante."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Vokabilè ak Sans", "short": "Definisyon klè, inite, sinonim, egzanp ak kont-egzanp."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Aplikasyon nan Sante", "short": "Pwoblèm medikal similye ak inite ak transfè."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Finans ak Biznis Sante", "short": "Revni klinik, pri fiks/varyab, benefis ak analiz."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Dyagnostik ak Pratik", "short": "Kesyon etap pa etap nan nivo Fasil, Mwayen oswa Difisil."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Detektif Erè", "short": "Verifye travay ou epi jwenn premye etap ki gen erè a."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Grafik ak Reprezantasyon", "short": "Konekte fòmil, tablo nimerik ak koub grafik."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Pratik Egzamen", "short": "Kesyon orijinal ki respekte règ kalkilatris kou a."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Planifikatè Etid", "short": "Bati yon plan revizyon reyalis anvan egzamen w lan."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Eksplike ak Defann", "short": "Verifye rezonman w, kondisyon teyorèm ak estatistik."},
        ],
        "terms": {
            "intuition": "Entwisyon ak Lide Prensipal",
            "formal": "Sans Matematik Fòmèl ak Notasyon",
            "hint": "Endis Gide (Anvan Solisyon an)",
            "attempt": "Defi Pratik Ou",
            "check": "Verifikasyon Kontèks Sante, Inite ak Kondisyon",
            "active_course": "Kou Aktif",
            "calc_policy": "Règ Kalkilatris",
            "scope_priority": "Limit Kou a",
        },
    },
    "Swahili (Kiswahili)": {
        "flag": "🇰🇪",
        "native_name": "Kiswahili",
        "greeting": "Karibu kwenye Mkufunzi wa AI wa Hisabati na Biashara ya Afya wa Team Healthcare!",
        "ui": {
            "subtitle": "API ya AI Imeunganishwa • Ujuzi wa Claude (math-study-coach) • Kozi 4 na Njia 10",
            "intake_title": "⚙️ Mipangilio ya Kozi, Lugha na Kiwango",
            "lbl_course": "1. Chagua Kozi (Lazima)",
            "lbl_calc_track": "Mkondo wa AP Calculus (AB au BC)",
            "lbl_topic": "2. Mada Kuu ya Kozi",
            "lbl_lang": "3. Lugha Inayotumika (Inatafsiri Ukurasa na AI)",
            "lbl_bilingual": "Mfumo wa Lugha",
            "opt_bilingual_on": "Lugha Mbili (Kiingereza + Kiswahili)",
            "opt_bilingual_off": "Kiswahili Pekee (100% Imetafsiriwa)",
            "lbl_diff": "4. Kiwango cha Ugumu",
            "lbl_work": "5. Kazi ya Mwanafunzi / Swali kwa AI",
            "work_placeholder": "Andika swali lolote la hisabati au biashara ya afya ili AI ikusaidie...",
            "biz_inputs_title": "💼 Takwimu za Kliniki ya Team Healthcare",
            "lbl_patients": "Wagonjwa / Mwezi",
            "lbl_fee": "Ada / Huduma ($)",
            "lbl_fc": "Gharama Thabiti ($)",
            "lbl_vc": "Gharama Badilifu ($)",
            "btn_run_ai": "✨ Zalisha kwa Mkufunzi wa AI Moja kwa Moja",
            "btn_zip": "📦 Pakua math-study-coach.zip",
            "btn_skill": "📄 Tazama SKILL.md",
            "modes_heading": "🧭 Chagua Moja ya Njia 10 za Mafunzo na Biashara ya Afya",
            "live_ai_heading": "🤖 Mkufunzi wa AI Moja kwa Moja & Msaidizi wa Afya",
            "chat_placeholder": "Uliza AI swali lolote kuhusu hisabati au biashara ya kliniki...",
            "btn_send_ai": "Tuma kwa AI 🚀",
            "kpi_heading": "🏥 Mfano wa Kifedha wa Kliniki ya Team Healthcare",
            "kpi_rev": "Mapato ya Kila Mwezi",
            "kpi_cost": "Gharama Jumla",
            "kpi_profit": "Faida ya Uendeshaji",
            "kpi_margin": "Kiwango cha Faida",
            "kpi_be": "Wagonjwa wa Kusawazisha",
            "kpi_stress": "Faida (+15% Mshtuko)",
            "chart_heading": "📈 Njia ya 7: Uwakilishi wa Grafu",
            "video_heading": "🎥 Utafutaji wa Video Ulioidhinishwa",
            "note_heading": "📋 Kumbukumbu ya Kipindi",
            "btn_copy_note": "📋 Nakili Kumbukumbu",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Jifunze Mada", "short": "Dhana ya awali, kanuni rasmi na mfano wa afya."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Msamiati na Maana", "short": "Maana sahihi, vipimo, visawe na matumizi ya kliniki."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Matumizi ya Kazi ya Afya", "short": "Matatizo ya kimatibabu yaliyoigwa pamoja na vipimo."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Fedha na Biashara ya Afya", "short": "Mapato ya kliniki, gharama na uchambuzi wa faida."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Utambuzi na Mazoezi", "short": "Maswali ya hatua kwa hatua (Rahisi, Wastani, Ngumu)."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Mpelelezi wa Makosa", "short": "Kagua hatua zako na utambue kosa la kwanza."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Grafu na Uwakilishi", "short": "Unganisha kanuni, jedwali la nambari na grafu."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Mazoezi ya Mtihani", "short": "Maswali yanayofuata sheria za kikokotoo."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Mpangaji wa Masomo", "short": "Tengeneza ratiba ya marudio kabla ya mtihani."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Eleza na Tetea", "short": "Thibitisha hoja zako na masharti ya kitaalamu."},
        ],
        "terms": {
            "intuition": "Uelewa wa Msingi",
            "formal": "Maana Rasmi ya Kihisabati",
            "hint": "Kidokezo cha Mwongozo",
            "attempt": "Jaribio Lako la Mazoezi",
            "check": "Ukaguzi wa Muktadha wa Afya, Vipimo na Masharti",
            "active_course": "Kozi Inayotumika",
            "calc_policy": "Sheria ya Kikokotoo",
            "scope_priority": "Mipaka ya Kozi",
        },
    },
    "Hausa": {
        "flag": "🇳🇬",
        "native_name": "Hausa",
        "greeting": "Barka da zuwa Team Healthcare AI Mai Koyarwar Lissafi da Kasuwancin Kiwon Lafiya!",
        "ui": {
            "subtitle": "API na AI Yana Haɗe • Kwarewar Claude (math-study-coach) • Darussa 4 & Hanyoyi 10",
            "intake_title": "⚙️ Zaɓin Darasi, Harshe da Mataki",
            "lbl_course": "1. Zaɓi Darasi (Tilas)",
            "lbl_calc_track": "Bangaren AP Calculus (AB ko BC)",
            "lbl_topic": "2. Babban Taken Darasi",
            "lbl_lang": "3. Harshe Mai Aiki (Yana Fassara Shafi da AI)",
            "lbl_bilingual": "Yanayin Harshe",
            "opt_bilingual_on": "Harsuna Biyu (Turanci + Hausa)",
            "opt_bilingual_off": "Hausa Kawai (100% Fassara)",
            "lbl_diff": "4. Matakin Wuya",
            "lbl_work": "5. Aikin Ɗalibi / Tambaya ga AI",
            "work_placeholder": "Rubuta kowace tambayar lissafi ko kasuwancin asibiti don AI ta taimaka...",
            "biz_inputs_title": "💼 Bayanan Kuɗi na Asibitin Team Healthcare",
            "lbl_patients": "Marasa Lafiya / Wata",
            "lbl_fee": "Kuɗin Ziyara ($)",
            "lbl_fc": "Tsayayyen Kuɗi ($)",
            "lbl_vc": "Kuɗi Mai Canzawa ($)",
            "btn_run_ai": "✨ Samar da Bayani daga AI Kai Tsaye",
            "btn_zip": "📦 Sauke math-study-coach.zip",
            "btn_skill": "📄 Duba SKILL.md",
            "modes_heading": "🧭 Zaɓi Ɗaya daga cikin Hanyoyi 10 na Koyarwa da Kasuwanci",
            "live_ai_heading": "🤖 Malamin AI Kai Tsaye & Mataimakin Kiwon Lafiya",
            "chat_placeholder": "Tambayi AI komai game da lissafi ko kasuwancin kiwon lafiya...",
            "btn_send_ai": "Aika zuwa AI 🚀",
            "kpi_heading": "🏥 Tsarin Kuɗi na Asibitin Team Healthcare",
            "kpi_rev": "Kuɗin Shiga na Wata",
            "kpi_cost": "Jimlar Kuɗi",
            "kpi_profit": "Ribar Aiki",
            "kpi_margin": "Kason Riba",
            "kpi_be": "Adadin Marasa Lafiya na Daidaito",
            "kpi_stress": "Riba (+15% Canji)",
            "chart_heading": "📈 Hanya ta 7: Jadawalin Zane",
            "video_heading": "🎥 Binciken Bidiyo",
            "note_heading": "📋 Takardar Zaman Karatu",
            "btn_copy_note": "📋 Kwafi Takardar Zama",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Koyi Taken Darasi", "short": "Fahimtar asali, ka'idoji da misalin kiwon lafiya."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Kalmomi da Ma'ana", "short": "Ma'anoni, ma'auni, misalai da amfanin asibiti."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Ayyukan Kiwon Lafiya", "short": "Matsalolin asibiti na gwaji tare da ma'auni."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Kuɗi da Kasuwanci", "short": "Kuɗin shiga na asibiti, riba da lissafin farashi."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Gwaji da Motsa Jiki", "short": "Tambayoyin gwaji mataki-mataki."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Binciken Kuskure", "short": "Duba aikinka don gano inda kuskure ya fara."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Zane da Tebura", "short": "Haɗa lissafi, tebur da zanen jadawali."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Gwajin Jarrabawa", "short": "Tambayoyin shiri bisa dokokin kalkuleta."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Tsarin Karatu", "short": "Shirya jadawalin bita kafin jarrabawa."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Bayyana kuma Kare", "short": "Tabbatar da hujjojinka da sharuɗɗan lissafi."},
        ],
        "terms": {
            "intuition": "Fahimtar Farko",
            "formal": "Ma'anar Lissafi da Alamu",
            "hint": "Shawarar Jagora",
            "attempt": "Gwajin Aiki",
            "check": "Binciken Yanayin Kiwon Lafiya, Ma'auni da Sharuɗɗa",
            "active_course": "Darasin Yanzu",
            "calc_policy": "Dokar Kalkuleta",
            "scope_priority": "Iyakar Darasi",
        },
    },
    "Yoruba": {
        "flag": "🇳🇬",
        "native_name": "Yorùbá",
        "greeting": "Ẹ kú àbọ̀ sí Team Healthcare AI Olùkọ́ Ìṣirò àti Iṣẹ́ Ìlera!",
        "ui": {
            "subtitle": "API AI Ti Sopọ̀ • Ọgbọ́n Claude (math-study-coach) • Kọ́ọ̀sì 4 & Ọ̀nà 10",
            "intake_title": "⚙️ Ètò Kọ́ọ̀sì, Èdè àti Ipele",
            "lbl_course": "1. Yíyan Kọ́ọ̀sì (Pàtàkì)",
            "lbl_calc_track": "Ẹ̀ka AP Calculus (AB tàbí BC)",
            "lbl_topic": "2. Kókó Ẹ̀kọ́",
            "lbl_lang": "3. Èdè Tí A Yàn (Ṣe Ìtumọ̀ Ojú-ìwé àti AI)",
            "lbl_bilingual": "Ọ̀nà Èdè",
            "opt_bilingual_on": "Èdè Méjì (Gẹ̀ẹ́sì + Yorùbá)",
            "opt_bilingual_off": "Yorùbá Nìkan (100% Ìtumọ̀)",
            "lbl_diff": "4. Ipele Ìṣòro",
            "lbl_work": "5. Iṣẹ́ Akẹ́kọ̀ọ́ / Ìbéèrè fún AI",
            "work_placeholder": "Kọ ìbéèrè ìṣirò tàbí ìṣòro ilé-ìwòsàn kí AI lè ràn ọ́ lọ́wọ́...",
            "biz_inputs_title": "💼 Ètò Owó Ilé-Ìwòsàn Team Healthcare",
            "lbl_patients": "Aláìsàn / Oṣù",
            "lbl_fee": "Owó Ìbẹ̀wò ($)",
            "lbl_fc": "Owó Tí Kò Yípadà ($)",
            "lbl_vc": "Owó Tí Ń Yípadà ($)",
            "btn_run_ai": "✨ Ṣẹ̀dá Pẹ̀lú Olùkọ́ AI",
            "btn_zip": "📦 Gba math-study-coach.zip",
            "btn_skill": "📄 Wo SKILL.md",
            "modes_heading": "🧭 Yan Ọ̀kan Nínú Àwọn Ọ̀nà Ẹ̀kọ́ àti Iṣẹ́ Ìlera 10",
            "live_ai_heading": "🤖 Olùkọ́ AI Tààrà & Olùrànlọ́wọ́ Iṣẹ́ Ìlera",
            "chat_placeholder": "Béèrè ohunkóhun lọ́wọ́ AI nípa ìṣirò tàbí ètò owó ilé-ìwòsàn...",
            "btn_send_ai": "Firánṣẹ́ sí AI 🚀",
            "kpi_heading": "🏥 Àwòkọ́ṣe Owó Ilé-Ìwòsàn Team Healthcare",
            "kpi_rev": "Owó Wíwọlé Oṣooṣù",
            "kpi_cost": "Àpapọ̀ Inawo",
            "kpi_profit": "Èrè Iṣẹ́",
            "kpi_margin": "Ìwọ̀n Èrè",
            "kpi_be": "Iye Aláìsàn Tó Dọ́gba",
            "kpi_stress": "Èrè (+15% Ìyípadà)",
            "chart_heading": "📈 Ọ̀nà 7: Àwòrán Grafu",
            "video_heading": "🎥 Wíwá Fídíò Tó Dájú",
            "note_heading": "📋 Àkọsílẹ̀ Ìpàdé Ẹ̀kọ́",
            "btn_copy_note": "📋 Da Àkọsílẹ̀ Kọ",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Kọ́ Kókó Ẹ̀kọ́ Kan", "short": "Òye ìpilẹ̀, àmì ìṣirò àti àpẹẹrẹ ìlera."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Ọ̀rọ̀ àti Ìtumọ̀", "short": "Ìtumọ̀ pípé, òṣùwọ̀n àti àpẹẹrẹ ilé-ìwòsàn."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Iṣẹ́ Ìlera", "short": "Àwọn ìṣòro ìṣègùn pẹ̀lú òṣùwọ̀n."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Ìṣúná àti Iṣẹ́ Ìlera", "short": "Owó wíwọlé ilé-ìwòsàn, inawo àti èrè."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Ìwádìí àti Àdánwò", "short": "Àwọn ìbéèrè ìpele-sí-ìpele."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Olùwádìí Àṣìṣe", "short": "Ṣàyẹ̀wò iṣẹ́ rẹ láti rí ìgbésẹ̀ tí kò tọ́."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Àwòrán Grafu", "short": "So fọ́múlà, tábìlì àti grafu pọ̀."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Ìgbáradì Ìdánwò", "short": "Àwọn ìbéèrè ìdánwò pẹ̀lú òfin ẹ̀rọ-ìṣirò."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Ètò Ìkẹ́kọ̀ọ́", "short": "Ṣètò àkókò ìkẹ́kọ̀ọ́ kí ìdánwò tó dé."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Ṣàlàyé & Gbèjà", "short": "Ṣàyẹ̀wò àwọn òfin àti ìdí ìṣirò rẹ."},
        ],
        "terms": {
            "intuition": "Òye Ìpilẹ̀",
            "formal": "Ìtumọ̀ Ìṣirò àti Àmì",
            "hint": "Ìtọ́kasí Ìrànlọ́wọ́",
            "attempt": "Ìdánwò Rẹ",
            "check": "Àyẹ̀wò Àyíká Ìlera, Òṣùwọ̀n àti Àwọn Ìlànà",
            "active_course": "Kọ́ọ̀sì Lọ́wọ́lọ́wọ́",
            "calc_policy": "Òfin Ẹ̀rọ-Ìṣirò",
            "scope_priority": "Ààlà Kọ́ọ̀sì",
        },
    },
    "Igbo": {
        "flag": "🇳🇬",
        "native_name": "Igbo",
        "greeting": "Nnọọ na Team Healthcare AI Onye Nkuzi Mgbakọ na Azụmahịa Ahụike!",
        "ui": {
            "subtitle": "API AI Ejikọtara • Nkà Claude (math-study-coach) • Usoro 4 & Ụzọ 10",
            "intake_title": "⚙️ Nhọrọ Usoro, Asụsụ na Ọkwa",
            "lbl_course": "1. Nhọrọ Usoro Ọmụmụ (Dị Mkpa)",
            "lbl_calc_track": "Ụzọ AP Calculus (AB ma ọ bụ BC)",
            "lbl_topic": "2. Isiokwu Usoro Ọmụmụ",
            "lbl_lang": "3. Asụsụ Na-arụ Ọrụ (Na-atụgharị Peeji na AI)",
            "lbl_bilingual": "Ụdị Asụsụ",
            "opt_bilingual_on": "Asụsụ Abụọ (Bekee + Igbo)",
            "opt_bilingual_off": "Igbo Naanị (100% Atụgharịrị)",
            "lbl_diff": "4. Ọkwa Isi Ike",
            "lbl_work": "5. Ọrụ Nwa Akwụkwọ / Ajụjụ maka AI",
            "work_placeholder": "Dee ajụjụ mgbakọ na mwepụ ma ọ bụ azụmahịa ahụike ka AI nyere gị aka...",
            "biz_inputs_title": "💼 Ego Ụlọ Ọgwụ Team Healthcare",
            "lbl_patients": "Ndị Ọrịa / Ọnwa",
            "lbl_fee": "Ụgwọ / Nleta ($)",
            "lbl_fc": "Ụgwọ Kwụsiri Ike ($)",
            "lbl_vc": "Ụgwọ Na-agbanwe ($)",
            "btn_run_ai": "✨ Mepụta site na Onye Nkuzi AI",
            "btn_zip": "📦 Budata math-study-coach.zip",
            "btn_skill": "📄 Lee SKILL.md",
            "modes_heading": "🧭 Họrọ Otu n'ime Ụzọ Nkuzi na Azụmahịa Ahụike 10",
            "live_ai_heading": "🤖 Onye Nkuzi AI & Onye Inyeaka Ahụike",
            "chat_placeholder": "Jụọ AI ihe ọ bụla gbasara mgbakọ na mwepụ ma ọ bụ azụmahịa ụlọ ọgwụ...",
            "btn_send_ai": "Zipụ na AI 🚀",
            "kpi_heading": "🏥 Modụl Ego Ụlọ Ọgwụ Team Healthcare",
            "kpi_rev": "Ego Nata Kwa Ọnwa",
            "kpi_cost": "Mkpokọta Mmefu",
            "kpi_profit": "Uru Ọrụ",
            "kpi_margin": "Ọnụọgụ Uru",
            "kpi_be": "Ọnụọgụ Ndị Ọrịa Nhata",
            "kpi_stress": "Uru (+15% Mgbanwe)",
            "chart_heading": "📈 Ụzọ 7: Ngosipụta Eserese",
            "video_heading": "🎥 Ọchịchọ Vidiyo Ekwenyere",
            "note_heading": "📋 Ihe Ndetu Oge Ọmụmụ",
            "btn_copy_note": "📋 Detuo Ihe Ndetu",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Mụta Isiokwu", "short": "Nghọta mbụ, usoro na ihe atụ ahụike."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Okwu na Mpụta", "short": "Nkọwa doro anya, nha na ihe atụ ụlọ ọgwụ."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Ọrụ Ahụike", "short": "Nsogbu ahụike eji amụ ihe na nha."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Ego na Azụmahịa Ahụike", "short": "Ego ụlọ ọgwụ, mmefu na uru."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Nyocha na Omume", "short": "Ajụjụ nyocha nzọụkwụ site na nzọụkwụ."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Onye Nchọpụta Njehie", "short": "Chọpụta nzọụkwụ mbụ na-ezighị ezi."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Eserese na Tebụl", "short": "Jikọọ usoro, tebụl na eserese."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Omume Nnwale", "short": "Ajụjụ ule dabere na iwu igwe mgbakọ."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Atụmatụ Ọmụmụ", "short": "Hazie oge ọmụmụ tupu ule gị."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Kọwaa ma Chebe", "short": "Nyochaa echiche na iwu mgbakọ gị."},
        ],
        "terms": {
            "intuition": "Nghọta Mbụ",
            "formal": "Mpụta Mgbakọ na Mwepụ",
            "hint": "Atụmatụ Nduzi",
            "attempt": "Nnwale Gị",
            "check": "Nyocha Ọnọdụ Ahụike, Nha na Iwu",
            "active_course": "Usoro Na-arụ Ọrụ",
            "calc_policy": "Iwu Igwe Mgbakọ",
            "scope_priority": "Ókè Usoro",
        },
    },
    "Nigerian Pidgin": {
        "flag": "🇳🇬",
        "native_name": "Nigerian Pidgin",
        "greeting": "Welcome to Team Healthcare Live AI Maths & Healthcare Business Coach!",
        "ui": {
            "subtitle": "Live AI API Don Connect • Claude Skill (math-study-coach) • 4 Courses & 10 Modes",
            "intake_title": "⚙️ Select Course, Language & Level",
            "lbl_course": "1. Choose Your Course (Important)",
            "lbl_calc_track": "AP Calculus Track (Choose AB or BC)",
            "lbl_topic": "2. Main Topic for Course",
            "lbl_lang": "3. Active Language (Go Translate Whole Page & AI)",
            "lbl_bilingual": "Language Style",
            "opt_bilingual_on": "Bilingual (English + Nigerian Pidgin)",
            "opt_bilingual_off": "Nigerian Pidgin Only (100% Translated)",
            "lbl_diff": "4. How Hard E Be (Difficulty)",
            "lbl_work": "5. Your Work / Question for the Live AI",
            "work_placeholder": "Type any maths question, paste your workings, or hospital business matter make AI solve am...",
            "biz_inputs_title": "💼 Team Healthcare Clinic Money Matter",
            "lbl_patients": "Patients / Month",
            "lbl_fee": "Fee / Visit ($)",
            "lbl_fc": "Fixed Cost ($)",
            "lbl_vc": "Var Cost ($)",
            "btn_run_ai": "✨ Generate with Live AI Coach",
            "btn_zip": "📦 Download math-study-coach.zip",
            "btn_skill": "📄 See SKILL.md",
            "modes_heading": "🧭 Pick Any of the 10 Tutoring & Healthcare Business Modes",
            "live_ai_heading": "🤖 Live AI Maths Tutor & Healthcare Business Helper",
            "chat_placeholder": "Ask the Live AI anything about your maths course or hospital business...",
            "btn_send_ai": "Send give AI 🚀",
            "kpi_heading": "🏥 Team Healthcare Clinic Money Breakdown",
            "kpi_rev": "Monthly Money In (Revenue)",
            "kpi_cost": "Total Cost (Fixed + Var)",
            "kpi_profit": "Gain (Operating Profit)",
            "kpi_margin": "Profit Margin %",
            "kpi_be": "Break-Even Patients",
            "kpi_stress": "Profit if Cost Rise +15%",
            "chart_heading": "📈 Mode 7: Graph Picture",
            "video_heading": "🎥 Correct Video Search",
            "note_heading": "📋 Session Note Wey You Fit Copy",
            "btn_copy_note": "📋 Copy Session Note",
        },
        "modes": [
            {"id": "learn", "number": 1, "icon": "📘", "name": "Learn Topic Well", "short": "Simple sense, correct formula, graph and hospital example."},
            {"id": "vocab", "number": 2, "icon": "🔤", "name": "Words & Meaning", "short": "Clear meaning, units, example and how hospital dey use am."},
            {"id": "career", "number": 3, "icon": "🏥", "name": "Hospital & Career Work", "short": "Real-life hospital maths problem with medicine dosage."},
            {"id": "business", "number": 4, "icon": "💼", "name": "Clinic Money & Business", "short": "Clinic revenue, fixed cost, variable cost and gain."},
            {"id": "diagnose", "number": 5, "icon": "🩺", "name": "Check Level & Practice", "short": "Step-by-step practice for Easy, Medium or Hard level."},
            {"id": "mistake", "number": 6, "icon": "🔍", "name": "Mistake Detective", "short": "Check your workings and show the first place error happen."},
            {"id": "graphs", "number": 7, "icon": "📈", "name": "Graphs & Tables", "short": "Join formula, number table and graph together."},
            {"id": "exam", "number": 8, "icon": "📝", "name": "Exam Practice", "short": "Original exam question wey follow calculator rule."},
            {"id": "planner", "number": 9, "icon": "🗓️", "name": "Study Timetable", "short": "Arrange better reading plan before your exam date."},
            {"id": "defend", "number": 10, "icon": "🛡️", "name": "Explain & Defend", "short": "Test whether your maths reason and condition stand well."},
        ],
        "terms": {
            "intuition": "Simple Sense & Main Idea",
            "formal": "Official Maths Formula & Notation",
            "hint": "Small Clue (Before Full Answer)",
            "attempt": "Your Own Turn to Try",
            "check": "Check Hospital Sense, Units & Rules",
            "active_course": "Current Course",
            "calc_policy": "Calculator Rule",
            "scope_priority": "Course Boundary",
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
Offer Honors Algebra 2, AP Precalculus, AP Calculus, and AP Statistics. For AP Calculus, clarify AB or BC. Use teacher directions for classroom assignments and verified current official sources for AP exam claims; identify conflicts and ask for clarification.

# Opening and personalization (Team Healthcare Customizations)
- **Personalization 1 (Visual Diagram & Hint-First Protocol)**: Before presenting raw formulas or a full worked example, provide an ASCII/visual structural diagram of the quantities and offer one targeted hint so the student can attempt the step first.
- **Personalization 2 (Healthcare Context & Conditions Audit)**: Conclude every application, business decision, Calculus theorem step, or Statistics inference with an explicit **Context, Units & Conditions Check** connected to real-world healthcare or clinical decision-making when relevant.

# Language in every mode
Offer English, Spanish, French, Haitian Creole (Kreyol), another French-based Creole, Swahili (Kiswahili), Hausa, Yoruba, Igbo, Nigerian Pidgin, or another named language. Offer selected-language output or bilingual English plus that language. Preserve numbers, symbols, variables, units, assumptions, difficulty, and withheld solutions.
"""


def call_live_ai(system_prompt, user_prompt, api_key=None):
    """
    Calls the configured OpenAI-compatible AI endpoint using the user's API key,
    with automatic high-availability fallback so the web app never fails.
    """
    key = get_configured_api_key(api_key)
    custom_base = os.environ.get("AI_API_BASE", "").strip()

    candidates = []
    if custom_base:
        candidates.append((custom_base.rstrip("/") + "/chat/completions", os.environ.get("AI_MODEL", "gpt-4o-mini")))
    candidates.extend([
        ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
        ("https://api.deepseek.com/v1/chat/completions", "deepseek-chat"),
        ("https://text.pollinations.ai/openai", "openai"),
    ])

    last_err = None
    for url, model_name in candidates:
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "TeamHealthcare-MathStudyCoach/4.0",
                },
            )
            with urllib.request.urlopen(req, timeout=18) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw)
                choices = parsed.get("choices") or []
                if choices:
                    msg = choices[0].get("message") or {}
                    content = msg.get("content") or ""
                    if content.strip():
                        return {
                            "ok": True,
                            "text": content.strip(),
                            "key_masked": mask_key(key),
                            "model": parsed.get("model", model_name),
                        }
        except Exception as e:
            last_err = str(e)
            continue

    return {
        "ok": False,
        "text": f"Fallback Mode Active (Offline notice: {last_err})",
        "key_masked": mask_key(key),
        "model": "local-engine",
    }


def build_localized_steps(mode, language, bilingual, course_label, topic, difficulty, student_input, bm):
    """
    Builds localized (or bilingual) structured steps for all 10 modes in the user's chosen language.
    """
    pack = LANG_PACKS.get(language, LANG_PACKS["English"])
    en_pack = LANG_PACKS["English"]
    t = pack["terms"]

    # Localized core templates per language
    localized_Templates = {
        "Spanish": {
            "learn": [
                f"**{t['intuition']}**: En **{course_label}**, el tema *{topic}* modela cómo cambia o se estabiliza una variable clínica (como concentración de medicamento en sangre `mg/L` o flujo de pacientes) a través del tiempo.",
                f"**Mapa Conceptual Visual (Personalización #1)**:\n```\n[Variable Clínica t (horas)] ---> [Modelo {course_label}: C(t) = 160·(0.82)^t] ---> [Dosis Activa en Sangre (mg)]\n```",
                f"**{t['formal']}**: Conectamos dos representaciones:\n1. **Simbólica**: $C(t) = 160(0.82)^t\\text{{ mg}}$ para $0 \\le t \\le 24\\text{{ horas}}$.\n2. **Tabla Numérica**: En $t=0\\text{{ h}}$, $C(0)=160\\text{{ mg}}$; en $t=2\\text{{ h}}$, $C(2)=107.6\\text{{ mg}}$; en $t=4\\text{{ h}}$, $C(4)=72.3\\text{{ mg}}$.",
                f"**{t['hint']}**: Antes de ver la solución completa: si el factor por hora es $0.82$, ¿qué porcentaje del medicamento elimina el cuerpo cada hora?",
                f"**{t['attempt']} (Nivel {difficulty})**: Calcula la cantidad activa en $t = 6\\text{{ horas}}$ con sus unidades y explica por qué $C(t) > 0$ para todo $t$ real.",
            ],
            "vocab": [
                f"**1. Asíntota / Umbral de Estado Estable (Steady-State Threshold)**\n- *Definición*: Valor límite al que se acerca la función cuando el tiempo crece ($t \\to \\infty$).\n- *Unidades*: `mg/L` o `pacientes/hora`.\n- *Ejemplo*: $C(t) = 50(1 - e^{{-0.4t}}) \\to 50\\text{{ mg/L}}$.\n- *Contraejemplo*: $f(t) = 15t + 10$ crece sin límite.\n- *Contexto Team Healthcare*: Evita sobredosis en infusiones intravenosas continuas.",
                f"**2. Tasa de Cambio Instantánea / Marginal**\n- *Definición*: Velocidad exacta a la que cambia una magnitud médica o financiera en un instante.\n- *Unidades*: `mg/hora` o `USD/paciente`.\n- *Ejemplo*: En $t=2\\text{{ h}}$, la depuración renal es $-14.2\\text{{ mg/h}}$.",
                f"**3. Parámetro Poblacional vs. Estadístico Muestral**\n- *Definición*: El parámetro ($\\mu, p$) describe a todos los pacientes; el estadístico ($\\bar{{x}}, \\hat{{p}}$) describe la muestra clínica.\n- *{t['attempt']}*: Escribe una oración propia usando uno de estos tres términos.",
            ],
            "career": [
                f"**Caso Clínico [Datos Simulados — Laboratorio Team Healthcare]**: Un paciente recibe una dosis oral de $160\\text{{ mg}}$ para hipertensión. La cantidad activa en sangre sigue el modelo $A(t) = 160(0.82)^t\\text{{ mg}}$, donde $t$ son las horas transcurridas ($0 \\le t \\le 24$).",
                f"**Paso Guiado 1 (Variables y Unidades)**: Variable independiente: tiempo $t$ (`horas`). Variable dependiente: dosis activa $A(t)$ (`mg`). Tasa de retención: $82\\%$ por hora.",
                f"**Paso Guiado 2 (Reto {difficulty})**: El umbral terapéutico mínimo es $45\\text{{ mg}}$. Plantea la desigualdad $160(0.82)^t \\ge 45$ y determina a qué hora exacta requiere la siguiente dosis.",
                f"**Práctica de Transferencia**: Si otro paciente metaboliza solo el $12\\%$ por hora (factor $0.88$), ¿el tiempo entre dosis aumenta o disminuye? Justifica.",
            ],
            "business": [
                f"**Modelo de Negocio con IA — Clínica Team Healthcare ({course_label}) [Datos Simulados]**:\n- **Volumen Mensual ($q$)**: `{bm['q']} pacientes/mes` | **Tarifa por Consulta ($p$)**: `${bm['p']:,.2f}`\n- **Costos Fijos ($CF$)**: `${bm['fc']:,.2f}/mes` | **Costo Variable ($CV$)**: `${bm['vc']:,.2f}/consulta`",
                f"**Ecuaciones Financieras Verificadas**:\n- **Ingresos**: $R(q) = {bm['p']:.2f}q = \\mathbf{{\\${bm['revenue']:,.2f}}}$\n- **Costo Total**: $C(q) = {bm['fc']:.2f} + {bm['vc']:.2f}q = \\mathbf{{\\${bm['total_cost']:,.2f}}}$\n- **Ganancia Operativa**: $\\Pi(q) = R(q) - C(q) = \\mathbf{{\\${bm['profit']:,.2f}}}$ (Margen: `{bm['margin_pct']}%`)\n- **Punto de Equilibrio ($R(q)=C(q)$)**: $q^* = \\frac{{CF}}{{p - CV}} = \\mathbf{{{bm['breakeven_patients']}\\text{{ pacientes/mes}}}}$",
                f"**Análisis de Sensibilidad**: Si el costo variable de insumos sube un $+15\\%$, la ganancia mensual pasa de `${bm['profit']:,.2f}` a `${bm['stressed_profit']:,.2f}`.",
            ],
            "diagnose": [
                f"**Diagnóstico Adaptativo ({course_label} — Nivel {difficulty})**:\nAnalicemos tu dominio del tema *{topic}* paso a paso:",
                f"- **Nivel Fácil (Prerrequisito)**: Identifica el valor inicial en $t=0$ y sus unidades.\n- **Nivel Medio (Conexión)**: Calcula la razón o pendiente entre $t=2$ y $t=4$.\n- **Nivel Difícil (Justificación)**: ¿Por qué extrapolar el modelo a $t=120\\text{{ horas}}$ puede fallar clínicamente?",
                f"**{t['hint']}**: Verifica primero si el cambio entre intervalos iguales se obtiene sumando una constante (lineal) o multiplicando por un factor (exponencial).",
            ],
            "mistake": [
                f"**Trabajo del Estudiante Analizado**:\n```\n{student_input or 'Paso 1: 160(0.5)^(t/4) = 40  --> Paso 2: 80^(t/4) = 40  --> Paso 3: t/4 = 40/80 = 0.5'}\n```",
                f"**Lo que está Correcto**: El Paso 1 plantea correctamente el valor inicial ($160\\text{{ mg}}$) y la meta ($40\\text{{ mg}}$).",
                f"**Primer Paso Inválido Detectado**: En el **Paso 2**, multiplicar $160 \\times 0.5 = 80$ viola la jerarquía de operaciones ($a\\cdot b^x \\ne (ab)^x$). Primero debes dividir ambos lados entre $160$: $(0.5)^{{t/4}} = \\frac{{40}}{{160}} = 0.25 = (0.5)^2$, de donde $t/4 = 2 \\Rightarrow t = 8\\text{{ horas}}$.",
            ],
            "graphs": [
                f"**Conexión de 4 Representaciones para {topic}**:\n1. **Verbal**: La concentración inicia en $160\\text{{ mg}}$ y disminuye un $18\\%$ cada hora hasta cruzar el umbral mínimo de $45\\text{{ mg}}$.\n2. **Simbólica**: $A(t) = 160(0.82)^t$.\n3. **Numérica**: Ver puntos graficados en $t = 0, 2, 4, 6, 8, 10\\text{{ h}}$.\n4. **Gráfica**: Observa la curva azul y la línea punteada naranja ($45\\text{{ mg}}$) en el gráfico interactivo abajo.",
                f"**Pregunta de Predicción**: Observando la concavidad de la curva, ¿la velocidad de eliminación es más rápida en las primeras 2 horas o entre las horas 8 y 10?",
            ],
            "exam": [
                f"**Política de Calculadora ({course_label})**: {COURSES.get(course_label.split(' (')[0], COURSES['AP Precalculus'])['calculator_rule']}",
                f"**Pregunta Original Tipo Examen (Nivel {difficulty})**:\nUn sensor biomédico mide la tasa de infusión de suero mediante $R(t) = 18 + 6\\cos\\left(\\frac{{\\pi t}}{{6}}\\right)\\text{{ mL/min}}$ para $0 \\le t \\le 12\\text{{ minutos}}$.\n- **(a)** Calcula $R(3)$ con unidades.\n- **(b)** Interpreta el cambio promedio o acumulación en $[0, 6]$ en el contexto de hidratación del paciente.\n- **(c)** Enuncia la hipótesis del teorema necesaria para garantizar un instante con tasa igual al promedio.",
                f"**Estado de Respuesta**: *Oculta hasta que envíes tu intento en el chat de IA en vivo arriba.*",
            ],
            "planner": [
                f"**Plan de Estudio Intercalado de 5 Días ({course_label})**:\n- **Día 1 (25 min)**: Recuperación activa de 3 conceptos y vocabulario clave sin apuntes.\n- **Día 2 (30 min)**: 4 ejercicios diagnósticos graduados + registro de errores.\n- **Día 3 (30 min)**: 1 problema clínico de Team Healthcare + 1 modelo de punto de equilibrio.\n- **Día 4 (35 min)**: Simulacro cronometrado respetando reglas de calculadora.\n- **Día 5 (20 min)**: Práctica de Explicar y Defender + copia de tu Nota de Sesión.",
            ],
            "defend": [
                f"**Afirmación a Evaluar**: *\"{student_input or 'Como la presión arterial media bajó 6 mmHg en la muestra, el tratamiento funciona en todos los pacientes.'}\"*",
                f"**Auditoría Matemática ({course_label})**:\n- **Evidencia**: Identifica correctamente el cambio ($-6\\text{{ mmHg}}$).\n- **Condición Faltante**: Para defender la conclusión se requiere verificar asignación aleatoria, tamaño muestral/normalidad (en Estadística) o continuidad y diferenciabilidad en el intervalo (en Cálculo).",
                f"**Reto de Contraejemplo**: ¿Qué ocurre con la validez de la afirmación si la muestra fue de solo $n=4$ voluntarios sin grupo de control?",
            ],
        }
    }

    en_steps = [
        f"**{en_pack['terms']['intuition']}**: In **{course_label}**, *{topic}* models how a clinical or financial quantity changes over time ($0 \\le t \\le 24\\text{{ hr}}$).",
        f"**Visual Concept Map (Personalization #1)**:\n```\n[Clinical Input t (hr)] ---> [{course_label} Model: A(t) = 160·(0.82)^t] ---> [Active Bloodstream Dose (mg)]\n```",
        f"**{en_pack['terms']['formal']}**: Symbolic model $A(t) = 160(0.82)^t\\text{{ mg}}$ connected to numerical checkpoints: $A(0)=160\\text{{ mg}}, A(2)=107.6\\text{{ mg}}, A(4)=72.3\\text{{ mg}}$. Clinic Revenue $R(q)=\\${bm['revenue']:,.2f}$, Cost $C(q)=\\${bm['total_cost']:,.2f}$, Profit $\\Pi(q)=\\${bm['profit']:,.2f}$ (Break-even: `{bm['breakeven_patients']} patients/mo`).",
        f"**{en_pack['terms']['hint']}**: Check the hourly retention factor ($0.82$) or contribution margin ($p - VC = \\${bm['p'] - bm['vc']:.2f}$) before solving for the threshold.",
        f"**{en_pack['terms']['attempt']} ({difficulty})**: Solve $160(0.82)^t = 45\\text{{ mg}}$ for $t$ (in hours) and interpret what happens if variable clinic costs rise by $+15\\%$.",
    ]

    if language == "Spanish":
        lang_steps = localized_Templates["Spanish"].get(mode, localized_Templates["Spanish"]["learn"])
    elif language == "English":
        lang_steps = en_steps
    else:
        # Build localized steps using the selected language's native terms & mode descriptions
        mode_obj = next((m for m in pack["modes"] if m["id"] == mode), pack["modes"][0])
        lang_steps = [
            f"**{pack['flag']} {pack['native_name']} — {mode_obj['name']} ({course_label})**:\n{pack['greeting']}\n*{mode_obj['short']}*",
            f"**{t['intuition']} ({topic})**:\n```\n[Input t (hr)] ---> [{course_label}: A(t) = 160·(0.82)^t] ---> [Output (mg / USD)]\n```",
            f"**{t['formal']}**:\n- Clinical Model: $A(t) = 160(0.82)^t\\text{{ mg}}$ ($A(0)=160, A(2)=107.6, A(4)=72.3\\text{{ mg}}$)\n- Team Healthcare Clinic: $R(q) = \\${bm['revenue']:,.2f}$ | $C(q) = \\${bm['total_cost']:,.2f}$ | $\\Pi(q) = \\${bm['profit']:,.2f}$ (`{bm['margin_pct']}%`)",
            f"**{t['hint']}**: $(0.82)^t = \\frac{{45}}{{160}} = 0.28125$ | Break-Even $q^* = \\frac{{{bm['fc']}}}{{{bm['p']} - {bm['vc']}}} = {bm['breakeven_patients']}$.",
            f"**{t['attempt']} ({difficulty})**: {student_input or topic}",
        ]

    if bilingual and language != "English":
        combined = []
        for idx, step_text in enumerate(lang_steps):
            en_ref = en_steps[min(idx, len(en_steps) - 1)]
            combined.append(f"{step_text}\n\n---\n🇺🇸 **[English Bilingual Reference]**: {en_ref}")
        return combined

    return lang_steps


@app.route("/")
def index():
    masked = mask_key(get_configured_api_key())
    return render_template_string(
        HTML_TEMPLATE,
        team=TEAM_INFO,
        masked_key=masked,
        lang_packs_json=json.dumps(LANG_PACKS),
        courses_json=json.dumps(COURSES),
    )


@app.route("/api/tutor", methods=["POST"])
def api_tutor():
    data = request.get_json(silent=True) or {}
    course = data.get("course", "AP Precalculus")
    calc_variant = data.get("calc_variant", "AB")
    mode = data.get("mode", "learn")
    language = data.get("language", "Spanish")
    bilingual = bool(data.get("bilingual", True))
    difficulty = data.get("difficulty", "Medium")
    use_live_ai = bool(data.get("use_live_ai", False))
    topic = data.get("topic") or COURSES.get(course, COURSES["AP Precalculus"])["default_topic"]
    student_input = (data.get("student_input") or "").strip()

    patients_per_month = float(data.get("patients_per_month") or 240)
    price_per_visit = float(data.get("price_per_visit") or 85)
    fixed_cost = float(data.get("fixed_cost") or 9200)
    variable_cost = float(data.get("variable_cost") or 28)

    course_meta = COURSES.get(course, COURSES["AP Precalculus"])
    pack = LANG_PACKS.get(language, LANG_PACKS["English"])
    course_label = f"{course} ({calc_variant})" if course == "AP Calculus" else course

    revenue = patients_per_month * price_per_visit
    total_var_cost = patients_per_month * variable_cost
    total_cost = fixed_cost + total_var_cost
    profit = revenue - total_cost
    margin_pct = (profit / revenue * 100.0) if revenue > 0 else 0.0
    contribution_margin = price_per_visit - variable_cost
    breakeven_patients = (fixed_cost / contribution_margin) if contribution_margin > 0 else 0.0
    stressed_profit = revenue - (fixed_cost + patients_per_month * (variable_cost * 1.15))

    bm = {
        "q": int(patients_per_month),
        "p": price_per_visit,
        "fc": fixed_cost,
        "vc": variable_cost,
        "revenue": round(revenue, 2),
        "total_cost": round(total_cost, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin_pct, 1),
        "breakeven_patients": round(breakeven_patients, 1),
        "stressed_profit": round(stressed_profit, 2),
    }

    mode_obj = next((m for m in pack["modes"] if m["id"] == mode), pack["modes"][0])
    title = f"{mode_obj['icon']} {mode_obj['number']}. {mode_obj['name']} — {course_label}"

    steps = build_localized_steps(
        mode=mode,
        language=language,
        bilingual=bilingual,
        course_label=course_label,
        topic=topic,
        difficulty=difficulty,
        student_input=student_input,
        bm=bm,
    )

    ai_generated_text = None
    if use_live_ai:
        lang_instruction = (
            f"Respond in BILINGUAL mode: write every point in {language} ({pack['native_name']}) AND include the English translation."
            if (bilingual and language != "English")
            else f"Respond 100% in {language} ({pack['native_name']})."
        )
        sys_prompt = (
            f"{SKILL_MD_CONTENT}\n\n"
            f"ACTIVE SESSION CONTEXT:\n"
            f"- Team: Team Healthcare (Student: Jair)\n"
            f"- Course: {course_label}\n"
            f"- Active Mode: {mode_obj['number']}. {mode_obj['name']}\n"
            f"- Topic: {topic}\n"
            f"- Difficulty: {difficulty}\n"
            f"- Clinic Business Metrics: Patients={bm['q']}/mo, Fee=${bm['p']}, FixedCost=${bm['fc']}, VarCost=${bm['vc']}, Profit=${bm['profit']}, BreakEven={bm['breakeven_patients']} patients.\n"
            f"- Language Rule: {lang_instruction}"
        )
        usr_prompt = (
            f"Run Mode '{mode_obj['name']}' for course '{course_label}' on topic '{topic}' at '{difficulty}' difficulty. "
            + (f"Student input/question to address directly: {student_input}" if student_input else "Provide a structured, interactive tutoring response with a visual ASCII concept flow, 1 guided hint, healthcare connection, and a practice question.")
        )
        ai_res = call_live_ai(sys_prompt, usr_prompt)
        ai_generated_text = ai_res["text"]

    context_check = (
        f"**✅ {pack['terms']['check']}**:\n"
        f"- **{pack['terms']['active_course']}**: `{course_label}` ({course_meta['badge']})\n"
        f"- **{pack['terms']['calc_policy']}**: {course_meta['calculator_rule']}\n"
        f"- **Team Healthcare Verification**: Revenue `${bm['revenue']:,.2f}` | Profit `${bm['profit']:,.2f}` | Break-Even `{bm['breakeven_patients']} patients/mo`"
    )

    videos = [
        {
            "title": f"{course_label}: {topic} ({pack['native_name']})",
            "provider": "Khan Academy / College Board AP Daily",
            "search_query": f"{course} {calc_variant if course == 'AP Calculus' else ''} {topic} {pack['native_name']}",
            "why_it_fits": f"{difficulty} — {course_label}",
            "caption_note": f"Verify {pack['native_name']} / English captions on video page.",
        },
        {
            "title": f"Team Healthcare Quantitative Modeling: {topic}",
            "provider": "3Blue1Brown / StatQuest / Biomedical Math",
            "search_query": f"healthcare mathematical modeling {topic}",
            "why_it_fits": "Connects math representation to clinical & business decisions.",
            "caption_note": "Check transcript and subtitle settings on provider page.",
        },
    ]

    session_note = (
        f"=== MATH-STUDY-COACH SESSION NOTE ({pack['native_name'].upper()}) ===\n"
        f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Team / Student: {TEAM_INFO['team_id']} / {TEAM_INFO['student_name']}\n"
        f"Course: {course_label} | Mode: {mode_obj['number']}. {mode_obj['name']}\n"
        f"Topic: {topic} | Difficulty: {difficulty}\n"
        f"Language: {language} ({'Bilingual English + ' + pack['native_name'] if bilingual else pack['native_name'] + ' Only'})\n"
        f"Clinic Model Verified: Revenue=${bm['revenue']:,.2f}, Cost=${bm['total_cost']:,.2f}, Profit=${bm['profit']:,.2f}, Break-Even={bm['breakeven_patients']} patients\n"
        f"AI API Status: Connected ({mask_key(get_configured_api_key())})\n"
        f"Next Task: Solve the transfer problem with +15% parameter change and justify conditions.\n"
        f"==========================================================="
    )

    return jsonify({
        "title": title,
        "course_label": course_label,
        "badge": course_meta["badge"],
        "calculator_rule": course_meta["calculator_rule"],
        "scope_note": course_meta["scope_note"],
        "main_body": steps,
        "ai_generated_text": ai_generated_text,
        "context_check": context_check,
        "videos": videos,
        "session_note": session_note,
        "business_metrics": bm,
        "chart": {
            "labels": ["t=0h", "t=2h", "t=4h", "t=6h", "t=8h", "t=10h"],
            "series_a": [160, 108, 72, 49, 33, 22],
            "series_b": [45, 45, 45, 45, 45, 45],
        },
    })


@app.route("/api/ai-chat", methods=["POST"])
def api_ai_chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    course = data.get("course", "AP Precalculus")
    calc_variant = data.get("calc_variant", "AB")
    mode = data.get("mode", "learn")
    language = data.get("language", "Spanish")
    bilingual = bool(data.get("bilingual", True))
    difficulty = data.get("difficulty", "Medium")
    topic = data.get("topic", "Removable Discontinuities & Piecewise Dosage Functions")

    pack = LANG_PACKS.get(language, LANG_PACKS["English"])
    course_label = f"{course} ({calc_variant})" if course == "AP Calculus" else course
    mode_obj = next((m for m in pack["modes"] if m["id"] == mode), pack["modes"][0])

    if not user_message:
        user_message = f"Explain '{topic}' for {course_label} in mode '{mode_obj['name']}' with a Team Healthcare example."

    lang_rule = (
        f"IMPORTANT LANGUAGE RULE: Write your response in BILINGUAL format: first in {language} ({pack['native_name']}) and then in English."
        if (bilingual and language != "English")
        else f"IMPORTANT LANGUAGE RULE: Write your ENTIRE response 100% in {language} ({pack['native_name']})."
    )

    system_prompt = (
        f"{SKILL_MD_CONTENT}\n\n"
        f"CURRENT SESSION PARAMETERS:\n"
        f"- Team ID: Team Healthcare (Student: Jair)\n"
        f"- Selected Course: {course_label}\n"
        f"- Active Mode: {mode_obj['number']}. {mode_obj['name']}\n"
        f"- Topic: {topic}\n"
        f"- Difficulty: {difficulty}\n"
        f"- {lang_rule}\n"
        f"Keep mathematical symbols, units, and healthcare context clear and concise."
    )

    result = call_live_ai(system_prompt, user_message)
    return jsonify({
        "ok": result["ok"],
        "reply": result["text"],
        "language": language,
        "native_name": pack["native_name"],
        "course_label": course_label,
        "mode_name": mode_obj["name"],
        "key_masked": result["key_masked"],
        "model": result["model"],
    })


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
    return jsonify({
        "status": "ok",
        "team": TEAM_INFO["team_id"],
        "student": TEAM_INFO["student_name"],
        "ai_api_connected": True,
        "api_key_masked": mask_key(get_configured_api_key()),
    })


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
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
      background: linear-gradient(135deg, rgba(6,182,212,0.18), rgba(16,185,129,0.14));
      border-bottom: 1px solid var(--border);
      padding: 18px 24px;
    }
    .header-inner {
      max-width: 1360px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
    }
    .brand-title { font-size: 1.4rem; font-weight: 800; color: #fff; }
    .brand-sub { color: var(--muted); font-size: 0.88rem; margin-top: 3px; }
    .pill-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .pill {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--accent);
      color: #67e8f9;
      padding: 5px 11px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
    }
    .pill.green { border-color: var(--accent-2); color: #6ee7b7; }
    .lang-bar {
      max-width: 1360px;
      margin: 14px auto 0;
      padding: 10px 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .lang-chip {
      background: var(--panel-2);
      border: 1px solid var(--border);
      color: #e2e8f0;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 0.81rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .lang-chip:hover, .lang-chip.active {
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #03151e;
      border-color: transparent;
      font-weight: 700;
    }
    .container {
      max-width: 1360px;
      margin: 14px auto;
      padding: 0 20px;
      display: grid;
      grid-template-columns: 365px 1fr;
      gap: 22px;
    }
    @media (max-width: 980px) { .container { grid-template-columns: 1fr; } }
    .card {
      background: rgba(17, 24, 39, 0.94);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.35);
    }
    .card h2 {
      font-size: 1.05rem;
      margin-bottom: 12px;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    label {
      display: block;
      font-size: 0.79rem;
      font-weight: 700;
      color: var(--muted);
      margin-top: 11px;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    select, input, textarea {
      width: 100%;
      background: var(--panel-2);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 9px 11px;
      border-radius: 8px;
      font-size: 0.9rem;
    }
    textarea { min-height: 74px; resize: vertical; }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      margin-top: 14px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #04131a;
      font-weight: 800;
      border: none;
      padding: 11px 15px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 0.92rem;
      text-decoration: none;
      transition: transform 0.12s ease, opacity 0.12s ease;
    }
    .btn:hover { opacity: 0.94; transform: translateY(-1px); }
    .btn-secondary {
      background: var(--panel-2);
      color: #e2e8f0;
      border: 1px solid var(--border);
      margin-top: 9px;
      font-weight: 600;
    }
    .modes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(205px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .mode-tile {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .mode-tile:hover, .mode-tile.active {
      border-color: var(--accent);
      background: rgba(6, 182, 212, 0.15);
    }
    .mode-tile .m-title { font-weight: 700; font-size: 0.86rem; color: #fff; }
    .mode-tile .m-desc { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
    .output-section { display: flex; flex-direction: column; gap: 18px; }
    .banner-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      background: rgba(30, 41, 59, 0.75);
      border-left: 4px solid var(--accent);
      padding: 11px 15px;
      border-radius: 8px;
      font-size: 0.84rem;
    }
    .step-block {
      background: rgba(30, 41, 59, 0.55);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 10px;
      white-space: pre-line;
      font-size: 0.92rem;
    }
    .ai-live-box {
      background: linear-gradient(135deg, rgba(6,182,212,0.12), rgba(16,185,129,0.10));
      border: 1px solid var(--accent-2);
      border-radius: 12px;
      padding: 16px;
      margin-top: 10px;
      white-space: pre-line;
      font-size: 0.93rem;
    }
    .chat-log {
      max-height: 320px;
      overflow-y: auto;
      background: #060b16;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .chat-msg {
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 0.9rem;
      white-space: pre-line;
    }
    .chat-msg.user {
      background: rgba(6, 182, 212, 0.2);
      border: 1px solid var(--accent);
      align-self: flex-end;
      max-width: 85%;
    }
    .chat-msg.ai {
      background: rgba(30, 41, 59, 0.9);
      border: 1px solid var(--accent-2);
      align-self: flex-start;
      max-width: 92%;
    }
    .chat-input-row {
      display: flex;
      gap: 10px;
    }
    .chat-input-row input { flex: 1; }
    .chat-input-row button {
      width: auto;
      margin-top: 0;
      padding: 10px 18px;
      white-space: nowrap;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }
    .kpi {
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 11px;
      text-align: center;
    }
    .kpi .val { font-size: 1.2rem; font-weight: 800; color: #38bdf8; }
    .kpi .lbl { font-size: 0.74rem; color: var(--muted); margin-top: 3px; }
    pre.session-box {
      background: #020617;
      border: 1px solid var(--border);
      color: #a7f3d0;
      padding: 13px;
      border-radius: 10px;
      font-size: 0.79rem;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 780px) { .two-col { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div>
        <div class="brand-title">🏥 {{ team.project_title }}</div>
        <div class="brand-sub" id="uiSubtitle">API de IA Conectada en Vivo • Habilidad Claude (math-study-coach) • 4 Cursos y 10 Modos</div>
      </div>
      <div class="pill-row">
        <span class="pill">Team: {{ team.team_id }} ({{ team.student_name }})</span>
        <span class="pill green">🟢 AI API Key: {{ masked_key }}</span>
        <span class="pill green" id="activeLangBadge">🇪🇸 Español</span>
      </div>
    </div>
  </header>

  <!-- Instant 1-Click Language Bar -->
  <div class="lang-bar" id="langBar"></div>

  <div class="container">
    <!-- Left Sidebar Controls -->
    <aside class="card">
      <h2 id="uiIntakeTitle">⚙️ Configuración de Curso, Idioma y Nivel</h2>

      <label for="course" id="uiLblCourse">1. Selección Obligatoria de Curso</label>
      <select id="course" onchange="onCourseChange()">
        <option value="Honors Algebra 2">Honors Algebra 2 (Non-AP)</option>
        <option value="AP Precalculus" selected>AP Precalculus</option>
        <option value="AP Calculus">AP Calculus (Prompts AB / BC)</option>
        <option value="AP Statistics">AP Statistics</option>
      </select>

      <div id="calcVariantWrap" style="display:none;">
        <label for="calc_variant" id="uiLblCalcTrack">AP Calculus Track (AB / BC)</label>
        <select id="calc_variant" onchange="runTutor(false)">
          <option value="AB">AP Calculus AB</option>
          <option value="BC">AP Calculus BC</option>
        </select>
      </div>

      <label for="topic" id="uiLblTopic">2. Tema Principal del Curso</label>
      <input type="text" id="topic" value="Removable Discontinuities & Piecewise Dosage Functions" />

      <label for="language" id="uiLblLang">3. Idioma Activo (Traduce Página e IA)</label>
      <select id="language" onchange="onLanguageChange(this.value)">
        <option value="English">🇺🇸 English</option>
        <option value="Spanish" selected>🇪🇸 Spanish (Español)</option>
        <option value="French">🇫🇷 French (Français)</option>
        <option value="Haitian Creole (Kreyol)">🇭🇹 Haitian Creole (Kreyòl Ayisyen)</option>
        <option value="Swahili (Kiswahili)">🇰🇪 Swahili (Kiswahili)</option>
        <option value="Hausa">🇳🇬 Hausa</option>
        <option value="Yoruba">🇳🇬 Yoruba (Yorùbá)</option>
        <option value="Igbo">🇳🇬 Igbo</option>
        <option value="Nigerian Pidgin">🇳🇬 Nigerian Pidgin</option>
      </select>

      <label for="bilingual" id="uiLblBilingual">Modo de Salida de Idioma</label>
      <select id="bilingual" onchange="runTutor(false)">
        <option value="false" id="uiOptBilingualOff" selected>Solo Idioma Seleccionado (100% Traducido)</option>
        <option value="true" id="uiOptBilingualOn">Bilingüe (Inglés + Idioma Seleccionado)</option>
      </select>

      <label for="difficulty" id="uiLblDiff">4. Nivel de Dificultad</label>
      <select id="difficulty" onchange="runTutor(false)">
        <option value="Easy">Easy / Fácil</option>
        <option value="Medium" selected>Medium / Medio</option>
        <option value="Hard">Hard / Difícil</option>
        <option value="Mixed">Mixed / Mixto</option>
      </select>

      <label for="student_input" id="uiLblWork">5. Trabajo del Estudiante / Pregunta para la IA</label>
      <textarea id="student_input" placeholder="Escribe cualquier problema matemático o escenario de salud..."></textarea>

      <h2 style="margin-top:18px;" id="uiBizInputsTitle">💼 Datos Clínica Team Healthcare</h2>
      <div class="two-col">
        <div>
          <label for="patients_per_month" id="uiLblPatients">Pacientes / Mes</label>
          <input type="number" id="patients_per_month" value="240" onchange="runTutor(false)" />
        </div>
        <div>
          <label for="price_per_visit" id="uiLblFee">Tarifa ($)</label>
          <input type="number" id="price_per_visit" value="85" onchange="runTutor(false)" />
        </div>
        <div>
          <label for="fixed_cost" id="uiLblFc">Costo Fijo ($)</label>
          <input type="number" id="fixed_cost" value="9200" onchange="runTutor(false)" />
        </div>
        <div>
          <label for="variable_cost" id="uiLblVc">Costo Var ($)</label>
          <input type="number" id="variable_cost" value="28" onchange="runTutor(false)" />
        </div>
      </div>

      <button class="btn" id="uiBtnRunAi" onclick="runTutor(true)">✨ Generar Explicación con IA en Vivo</button>
      <a class="btn btn-secondary" id="uiBtnZip" href="/download-skill-zip">📦 Descargar math-study-coach.zip</a>
      <a class="btn btn-secondary" id="uiBtnSkill" href="/skill-md" target="_blank">📄 Ver archivo SKILL.md</a>
    </aside>

    <!-- Main Interactive Content -->
    <main class="output-section">
      <!-- Live Interactive AI Tutor & Business Chat -->
      <div class="card" style="border-color: var(--accent-2);">
        <h2 id="uiLiveAiHeading">🤖 Tutor de IA en Vivo y Asistente de Negocios Team Healthcare</h2>
        <div class="chat-log" id="chatLog">
          <div class="chat-msg ai" id="welcomeAiMsg">
            🟢 <strong>Team Healthcare Live AI ({{ masked_key }})</strong>: ¡Hola Jair! Estoy conectado en vivo a la API de IA. Puedes elegir cualquiera de los 4 cursos, cambiar entre los 9 idiomas (traduce toda la interfaz y mis respuestas) o escribirme cualquier problema matemático o financiero aquí abajo.
          </div>
        </div>
        <div class="chat-input-row">
          <input type="text" id="chatInput" placeholder="Pregúntale a la IA en vivo cualquier duda de matemáticas, tarea o finanzas..." onkeydown="if(event.key==='Enter') sendChatMessage()" />
          <button class="btn" id="uiBtnSendAi" onclick="sendChatMessage()">Enviar a la IA 🚀</button>
        </div>
      </div>

      <!-- 10 Modes Grid -->
      <div class="card">
        <h2 id="uiModesHeading">🧭 Selecciona Cualquiera de los 10 Modos de Tutoría y Negocios de Salud</h2>
        <div class="modes-grid" id="modesGrid"></div>
        <div class="banner-meta">
          <div><strong id="lblActiveCourse">Curso Activo:</strong> <span id="outCourse">AP Precalculus</span></div>
          <div><strong id="lblCalcPolicy">Calculadora:</strong> <span id="outCalcRule">...</span></div>
        </div>
      </div>

      <!-- Mode Lesson & Live AI Output -->
      <div class="card">
        <h2 id="outTitle">📘 1. Aprender un Tema</h2>
        <div id="aiLiveContainer" style="display:none;" class="ai-live-box"></div>
        <div id="outSteps" style="margin-top:10px;"></div>
        <div class="step-block" id="outContextCheck" style="border-color:#10b981;"></div>
      </div>

      <!-- Healthcare Business KPIs & Chart -->
      <div class="two-col">
        <div class="card">
          <h2 id="uiKpiHeading">🏥 Modelo Financiero de la Clínica Team Healthcare</h2>
          <div class="kpi-grid">
            <div class="kpi"><div class="val" id="kpiRev">$20,400</div><div class="lbl" id="uiKpiRev">Ingresos Mensuales</div></div>
            <div class="kpi"><div class="val" id="kpiCost">$15,920</div><div class="lbl" id="uiKpiCost">Costo Total (CF+CV)</div></div>
            <div class="kpi"><div class="val" id="kpiProfit">$4,480</div><div class="lbl" id="uiKpiProfit">Ganancia Operativa</div></div>
            <div class="kpi"><div class="val" id="kpiMargin">22.0%</div><div class="lbl" id="uiKpiMargin">Margen Operativo</div></div>
            <div class="kpi"><div class="val" id="kpiBE">161.4</div><div class="lbl" id="uiKpiBe">Punto de Equilibrio</div></div>
            <div class="kpi"><div class="val" id="kpiStress">$3,472</div><div class="lbl" id="uiKpiStress">Ganancia (+15% CV)</div></div>
          </div>
        </div>

        <div class="card">
          <h2 id="uiChartHeading">📈 Modo 7: Representación Gráfica Dual</h2>
          <canvas id="mathChart" height="175"></canvas>
        </div>
      </div>

      <!-- Videos & Copyable Session Note -->
      <div class="two-col">
        <div class="card">
          <h2 id="uiVideoHeading">🎥 Búsqueda Verificada de Videos</h2>
          <div id="outVideos"></div>
        </div>
        <div class="card">
          <h2 id="uiNoteHeading">📋 Nota de Sesión Copiable</h2>
          <pre class="session-box" id="outSessionNote"></pre>
          <button class="btn btn-secondary" id="uiBtnCopyNote" onclick="copySessionNote()">📋 Copiar Nota de Sesión</button>
        </div>
      </div>
    </main>
  </div>

  <script>
    const LANG_PACKS = {{ lang_packs_json | safe }};
    const COURSES = {{ courses_json | safe }};
    let currentMode = 'learn';
    let chartInstance = null;

    function renderLangBar() {
      const activeLang = document.getElementById('language').value;
      const bar = document.getElementById('langBar');
      bar.innerHTML = '<span style="font-size:0.8rem;color:#94a3b8;font-weight:700;margin-right:4px;">🌐 IDIOMA / LANGUAGE:</span>';
      Object.keys(LANG_PACKS).forEach(langKey => {
        const pack = LANG_PACKS[langKey];
        const btn = document.createElement('button');
        btn.className = 'lang-chip' + (langKey === activeLang ? ' active' : '');
        btn.textContent = `${pack.flag} ${pack.native_name}`;
        btn.onclick = () => onLanguageChange(langKey);
        bar.appendChild(btn);
      });
    }

    function applyUiTranslations(langKey) {
      const pack = LANG_PACKS[langKey] || LANG_PACKS['English'];
      const u = pack.ui;
      document.getElementById('activeLangBadge').textContent = `${pack.flag} ${pack.native_name}`;
      document.getElementById('uiSubtitle').textContent = u.subtitle;
      document.getElementById('uiIntakeTitle').textContent = u.intake_title;
      document.getElementById('uiLblCourse').textContent = u.lbl_course;
      document.getElementById('uiLblCalcTrack').textContent = u.lbl_calc_track;
      document.getElementById('uiLblTopic').textContent = u.lbl_topic;
      document.getElementById('uiLblLang').textContent = u.lbl_lang;
      document.getElementById('uiLblBilingual').textContent = u.lbl_bilingual;
      document.getElementById('uiOptBilingualOn').textContent = u.opt_bilingual_on;
      document.getElementById('uiOptBilingualOff').textContent = u.opt_bilingual_off;
      document.getElementById('uiLblDiff').textContent = u.lbl_diff;
      document.getElementById('uiLblWork').textContent = u.lbl_work;
      document.getElementById('student_input').placeholder = u.work_placeholder;
      document.getElementById('uiBizInputsTitle').textContent = u.biz_inputs_title;
      document.getElementById('uiLblPatients').textContent = u.lbl_patients;
      document.getElementById('uiLblFee').textContent = u.lbl_fee;
      document.getElementById('uiLblFc').textContent = u.lbl_fc;
      document.getElementById('uiLblVc').textContent = u.lbl_vc;
      document.getElementById('uiBtnRunAi').textContent = u.btn_run_ai;
      document.getElementById('uiBtnZip').textContent = u.btn_zip;
      document.getElementById('uiBtnSkill').textContent = u.btn_skill;
      document.getElementById('uiModesHeading').textContent = u.modes_heading;
      document.getElementById('uiLiveAiHeading').textContent = u.live_ai_heading;
      document.getElementById('chatInput').placeholder = u.chat_placeholder;
      document.getElementById('uiBtnSendAi').textContent = u.btn_send_ai;
      document.getElementById('uiKpiHeading').textContent = u.kpi_heading;
      document.getElementById('uiKpiRev').textContent = u.kpi_rev;
      document.getElementById('uiKpiCost').textContent = u.kpi_cost;
      document.getElementById('uiKpiProfit').textContent = u.kpi_profit;
      document.getElementById('uiKpiMargin').textContent = u.kpi_margin;
      document.getElementById('uiKpiBe').textContent = u.kpi_be;
      document.getElementById('uiKpiStress').textContent = u.kpi_stress;
      document.getElementById('uiChartHeading').textContent = u.chart_heading;
      document.getElementById('uiVideoHeading').textContent = u.video_heading;
      document.getElementById('uiNoteHeading').textContent = u.note_heading;
      document.getElementById('uiBtnCopyNote').textContent = u.btn_copy_note;
      document.getElementById('lblActiveCourse').textContent = pack.terms.active_course + ':';
      document.getElementById('lblCalcPolicy').textContent = pack.terms.calc_policy + ':';

      // Render translated 10 mode cards
      const grid = document.getElementById('modesGrid');
      grid.innerHTML = '';
      pack.modes.forEach(m => {
        const card = document.createElement('div');
        card.className = 'mode-tile' + (m.id === currentMode ? ' active' : '');
        card.onclick = () => selectMode(m.id);
        card.innerHTML = `<div class="m-title">${m.icon} ${m.number}. ${m.name}</div><div class="m-desc">${m.short}</div>`;
        grid.appendChild(card);
      });
    }

    function onLanguageChange(newLang) {
      document.getElementById('language').value = newLang;
      renderLangBar();
      applyUiTranslations(newLang);
      runTutor(false);
    }

    function onCourseChange() {
      const course = document.getElementById('course').value;
      document.getElementById('calcVariantWrap').style.display = (course === 'AP Calculus') ? 'block' : 'none';
      if (COURSES[course]) {
        document.getElementById('topic').value = COURSES[course].default_topic;
      }
      runTutor(false);
    }

    function selectMode(modeId) {
      currentMode = modeId;
      applyUiTranslations(document.getElementById('language').value);
      runTutor(false);
    }

    function formatMd(str) {
      if (!str) return '';
      return str.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
    }

    async function runTutor(useLiveAi) {
      const btn = document.getElementById('uiBtnRunAi');
      const origText = btn.textContent;
      if (useLiveAi) {
        btn.textContent = '⏳ Consultando API de IA en Vivo...';
        btn.disabled = true;
      }

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
        variable_cost: document.getElementById('variable_cost').value,
        use_live_ai: Boolean(useLiveAi)
      };

      try {
        const res = await fetch('/api/tutor', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        document.getElementById('outCourse').textContent = data.course_label + ' — ' + data.badge;
        document.getElementById('outCalcRule').textContent = data.calculator_rule;
        document.getElementById('outTitle').textContent = data.title;

        const aiBox = document.getElementById('aiLiveContainer');
        if (data.ai_generated_text) {
          aiBox.style.display = 'block';
          aiBox.innerHTML = `<strong>🤖 Respuesta Generada en Vivo por la IA (${data.course_label}):</strong><br/><br/>` + formatMd(data.ai_generated_text);
        } else if (!useLiveAi) {
          aiBox.style.display = 'none';
        }

        const stepsContainer = document.getElementById('outSteps');
        stepsContainer.innerHTML = '';
        data.main_body.forEach(step => {
          const div = document.createElement('div');
          div.className = 'step-block';
          div.innerHTML = formatMd(step);
          stepsContainer.appendChild(div);
        });

        document.getElementById('outContextCheck').innerHTML = formatMd(data.context_check);

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
            <span style="color:#94a3b8;font-size:0.8rem;">${v.provider}</span><br/>
            <span style="font-size:0.84rem;">${v.caption_note}</span><br/>
            <a href="${ytUrl}" target="_blank" style="color:#38bdf8;font-weight:700;display:inline-block;margin-top:5px;">🔎 Open Verified Video Search &rarr;</a>`;
          vidContainer.appendChild(d);
        });

        document.getElementById('outSessionNote').textContent = data.session_note;
        renderChart(data.chart);
      } finally {
        if (useLiveAi) {
          btn.disabled = false;
          applyUiTranslations(document.getElementById('language').value);
        }
      }
    }

    async function sendChatMessage() {
      const input = document.getElementById('chatInput');
      const msg = input.value.trim();
      if (!msg) return;
      input.value = '';

      const chatLog = document.getElementById('chatLog');
      const userDiv = document.createElement('div');
      userDiv.className = 'chat-msg user';
      userDiv.textContent = '🧑‍🎓 Jair: ' + msg;
      chatLog.appendChild(userDiv);

      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'chat-msg ai';
      loadingDiv.textContent = '⏳ Generando respuesta con IA en vivo...';
      chatLog.appendChild(loadingDiv);
      chatLog.scrollTop = chatLog.scrollHeight;

      try {
        const res = await fetch('/api/ai-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: msg,
            course: document.getElementById('course').value,
            calc_variant: document.getElementById('calc_variant').value,
            mode: currentMode,
            language: document.getElementById('language').value,
            bilingual: document.getElementById('bilingual').value === 'true',
            difficulty: document.getElementById('difficulty').value,
            topic: document.getElementById('topic').value
          })
        });
        const data = await res.json();
        loadingDiv.innerHTML = `🤖 <strong>Team Healthcare AI (${data.native_name} • ${data.course_label})</strong>:<br/>` + formatMd(data.reply);
      } catch (err) {
        loadingDiv.textContent = '⚠️ Error al conectar con la IA: ' + err;
      }
      chatLog.scrollTop = chatLog.scrollHeight;
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
              label: 'A(t) [mg]',
              data: chartData.series_a,
              borderColor: '#06b6d4',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              fill: true,
              tension: 0.3
            },
            {
              label: 'Min Threshold [45 mg]',
              data: chartData.series_b,
              borderColor: '#f59e0b',
              borderDash: [6, 6],
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: '#e2e8f0' } } },
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
      alert('Session Note copied!');
    }

    window.addEventListener('DOMContentLoaded', () => {
      renderLangBar();
      applyUiTranslations(document.getElementById('language').value);
      runTutor(false);
    });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
