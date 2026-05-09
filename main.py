import os
import json
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
import google.generativeai as genai

app = FastAPI()

sessions = {}

# ─── Gemini Setup ────────────────────────────────────────────
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

# ─── Language Selection ──────────────────────────────────────
LANG_SELECT = (
    "Welcome to CropGuard AI / Karibu CropGuard AI\n\n"
    "Choose your language / Chagua lugha yako:\n"
    "1 - English\n"
    "2 - Kiswahili"
)

# ─── All Responses ───────────────────────────────────────────
RESPONSES = {
    "en": {
        "consent": (
            "Hello! CropGuard AI here.\n\n"
            "Before we continue:\n"
            "Your data is used only to improve this service. "
            "It is not stored with your name.\n\n"
            "Would you like to continue?\n"
            "Reply: YES or NO"
        ),
        "q1": (
            "Thank you! Question 1/4:\n\n"
            "What problem does your cow have?\n"
            "1 - Udder problem (mastitis)\n"
            "2 - Foot problem (foot rot)\n"
            "3 - Describe it yourself (AI will analyse)"
        ),
        "q2_mastitis": (
            "Question 2/4:\n\n"
            "How long have you noticed the symptoms?\n"
            "1 - Just today\n"
            "2 - 2 to 3 days\n"
            "3 - More than a week"
        ),
        "q2_footrot": (
            "Question 2/4:\n\n"
            "How does the foot look?\n"
            "1 - Just swollen\n"
            "2 - Has a bad smell\n"
            "3 - Cow refuses to put it down"
        ),
        "q3_mastitis": (
            "Question 3/4:\n\n"
            "How does the udder look?\n"
            "1 - Swollen and hot\n"
            "2 - Milk has dirt or blood\n"
            "3 - Both"
        ),
        "q3_footrot": (
            "Question 3/4:\n\n"
            "Does the cow have a fever?\n"
            "1 - Yes, feels hot\n"
            "2 - Not sure\n"
            "3 - No"
        ),
        "q4": (
            "Question 4/4:\n\n"
            "How many cows have this problem?\n"
            "1 - One only\n"
            "2 - Two\n"
            "3 - More than two"
        ),
        "freetext_prompt": (
            "Please describe your cow's symptoms in your own words.\n\n"
            "What do you see? How long has it been happening?"
        ),
        "thinking": "Analysing your description, please wait...",
        "invalid": "Please reply with 1, 2, or 3.",
        "consent_invalid": "Please reply YES or NO.",
        "no_consent": "OK. Send HI anytime you need help. Thank you!",
        "unknown": (
            "Thank you for the information.\n\n"
            "Your problem needs direct help from a vet.\n\n"
            "Vet helpline: 0800 720 601 (free)\n\n"
            "We will keep improving. Thank you!"
        ),
        "followup": "Send a message in 2 days so we can follow up. Thank you!",
        "ai_failed": (
            "Sorry, our AI is temporarily unavailable.\n\n"
            "Please call the vet directly.\n"
            "Vet helpline: 0800 720 601 (free)"
        ),
    },
    "sw": {
        "consent": (
            "Habari! CropGuard AI hapa.\n\n"
            "Kabla hatujaendelea:\n"
            "Data yako itatumika kuboresha huduma tu. "
            "Huhifadhiwa na jina lako.\n\n"
            "Ungependa kuendelea?\n"
            "Jibu: NDIO au HAPANA"
        ),
        "q1": (
            "Asante! Swali 1/4:\n\n"
            "Ng'ombe wako ana tatizo gani?\n"
            "1 - Kiwele (mastitis)\n"
            "2 - Mguu (foot rot)\n"
            "3 - Elezea mwenyewe (AI itachambua)"
        ),
        "q2_mastitis": (
            "Swali 2/4:\n\n"
            "Dalili zinaonekana kwa muda gani?\n"
            "1 - Leo tu\n"
            "2 - Siku 2 hadi 3\n"
            "3 - Zaidi ya wiki"
        ),
        "q2_footrot": (
            "Swali 2/4:\n\n"
            "Mguu unaonekana vipi?\n"
            "1 - Umevimba tu\n"
            "2 - Una harufu mbaya\n"
            "3 - Ng'ombe hauweki chini"
        ),
        "q3_mastitis": (
            "Swali 3/4:\n\n"
            "Kiwele kinaonekana vipi?\n"
            "1 - Kimevimba, moto\n"
            "2 - Maziwa yana uchafu au damu\n"
            "3 - Vyote viwili"
        ),
        "q3_footrot": (
            "Swali 3/4:\n\n"
            "Ng'ombe ana homa?\n"
            "1 - Ndiyo, ana joto\n"
            "2 - Sijui\n"
            "3 - Hapana"
        ),
        "q4": (
            "Swali 4/4:\n\n"
            "Ng'ombe wangapi wana tatizo hili?\n"
            "1 - Mmoja tu\n"
            "2 - Wawili\n"
            "3 - Zaidi ya wawili"
        ),
        "freetext_prompt": (
            "Tafadhali elezea dalili za ng'ombe wako kwa maneno yako.\n\n"
            "Unaona nini? Imekuwa kwa muda gani?"
        ),
        "thinking": "Inachambua maelezo yako, tafadhali subiri...",
        "invalid": "Tafadhali jibu 1, 2, au 3.",
        "consent_invalid": "Tafadhali jibu NDIO au HAPANA.",
        "no_consent": "Sawa. Tuma HABARI wakati wowote utakapotaka msaada. Asante!",
        "unknown": (
            "Asante kwa maelezo yako.\n\n"
            "Tatizo lako linahitaji msaada wa daktari wa mifugo moja kwa moja.\n\n"
            "Daktari wa mifugo: 0800 720 601 (bure)\n\n"
            "Tutaboresha mfumo wetu. Asante!"
        ),
        "followup": "Tuma ujumbe baada ya siku 2 tufuatilie hali yake. Asante!",
        "ai_failed": (
            "Samahani, AI yetu haifanyi kazi kwa sasa.\n\n"
            "Tafadhali piga simu daktari moja kwa moja.\n"
            "Daktari wa mifugo: 0800 720 601 (bure)"
        ),
    }
}

# ─── Gemini Diagnosis ────────────────────────────────────────
def gemini_diagnose(symptoms, lang):
    if not model:
        return None

    if lang == "en":
        prompt = f"""You are CropGuard AI, a dairy farming assistant in Kiambu, Kenya.
A farmer described their cow's symptoms as: "{symptoms}"

Respond in English only. Be concise and practical.
Structure your response exactly like this:

CROPGUARD AI DIAGNOSIS
----------------------
Problem: [most likely condition]
Confidence: [High/Medium/Low]

Do this TODAY:
1. [step]
2. [step]
3. [step]

[URGENT - Call vet NOW / Important - Visit agrovet today / Monitor for 2 days]

Call the vet NOW if:
- [warning sign 1]
- [warning sign 2]

Vet helpline: 0800 720 601 (free)

Send a message in 2 days so we can follow up. Thank you!"""
    else:
        prompt = f"""Wewe ni CropGuard AI, msaidizi wa ufugaji wa ng'ombe Kiambu, Kenya.
Mkulima ameelezea dalili za ng'ombe wake hivi: "{symptoms}"

Jibu kwa Kiswahili tu. Kuwa mfupi na wa vitendo.
Panga jibu lako hivi hasa:

UCHAMBUZI WA CROPGUARD AI
-------------------------
Tatizo: [hali inayowezekana zaidi]
Kiwango cha imani: [Juu/Wastani/Chini]

Fanya hivi LEO:
1. [hatua]
2. [hatua]
3. [hatua]

[HARAKA - Piga simu daktari SASA / Muhimu - Tembelea agrovet leo / Angalia kwa siku 2]

Piga simu daktari SASA kama:
- [dalili ya onyo 1]
- [dalili ya onyo 2]

Daktari wa mifugo: 0800 720 601 (bure)

Tuma ujumbe baada ya siku 2 tufuatilie. Asante!"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return None

# ─── Decision Tree Diagnosis ─────────────────────────────────
def diagnose(session):
    lang = session.get("lang", "en")
    issue = session.get("issue")
    duration = session.get("duration")
    severity = session.get("severity")
    R = RESPONSES[lang]

    if issue == "1":
        if severity == "3" or duration == "3":
            urgency = "URGENT - Call a vet NOW" if lang == "en" else "HARAKA - Piga simu daktari WA MIFUGO SASA"
        elif duration == "2":
            urgency = "Important - Visit an agrovet today" if lang == "en" else "Muhimu - Tembelea agrovet leo"
        else:
            urgency = "Monitor closely for 2 days" if lang == "en" else "Angalia kwa makini kwa siku 2"

        if lang == "en":
            return (
                "CROPGUARD AI DIAGNOSIS\n"
                "----------------------\n"
                "Problem: MASTITIS\n"
                "Confidence: High\n\n"
                "Do this TODAY:\n"
                "1. Milk the cow 4 times a day\n"
                "2. Apply a warm cloth on the udder\n"
                "3. Keep her in a clean dry place\n"
                "4. Separate her from other cows\n\n"
                f"{urgency}\n\n"
                "Call the vet NOW if:\n"
                "- She has a high fever\n"
                "- She has not eaten for 2 or more days\n"
                "- Condition is getting worse\n\n"
                "Vet helpline: 0800 720 601 (free)\n\n"
                f"{R['followup']}"
            )
        else:
            return (
                "UCHAMBUZI WA CROPGUARD AI\n"
                "-------------------------\n"
                "Tatizo: MASTITIS\n"
                "Kiwango cha imani: Juu\n\n"
                "Fanya hivi LEO:\n"
                "1. Kama ng'ombe mara 4 kwa siku\n"
                "2. Tumia kitambaa cha moto kwenye kiwele\n"
                "3. Mweke mahali safi na kavu\n"
                "4. Usimwache achanganyike na wengine\n\n"
                f"{urgency}\n\n"
                "Piga simu SASA kama:\n"
                "- Ana joto kali\n"
                "- Hajala siku 2 au zaidi\n"
                "- Hali inazidi kuwa mbaya\n\n"
                "Daktari wa mifugo: 0800 720 601 (bure)\n\n"
                f"{R['followup']}"
            )

    elif issue == "2":
        if severity == "2" or severity == "3":
            urgency = "URGENT - Call a vet NOW" if lang == "en" else "HARAKA - Piga simu daktari WA MIFUGO SASA"
        else:
            urgency = "Important - Visit an agrovet today" if lang == "en" else "Muhimu - Tembelea agrovet leo"

        if lang == "en":
            return (
                "CROPGUARD AI DIAGNOSIS\n"
                "----------------------\n"
                "Problem: FOOT ROT\n"
                "Confidence: High\n\n"
                "Do this TODAY:\n"
                "1. Clean the foot with clean water\n"
                "2. Soak the foot in salt water\n"
                "3. Keep her in a dry clean place\n"
                "4. Avoid mud and dirty areas\n\n"
                f"{urgency}\n\n"
                "Call the vet NOW if:\n"
                "- There is a very strong smell\n"
                "- She cannot stand\n"
                "- Condition is getting worse\n\n"
                "Vet helpline: 0800 720 601 (free)\n\n"
                f"{R['followup']}"
            )
        else:
            return (
                "UCHAMBUZI WA CROPGUARD AI\n"
                "-------------------------\n"
                "Tatizo: FOOT ROT (Ugonjwa wa Mguu)\n"
                "Kiwango cha imani: Juu\n\n"
                "Fanya hivi LEO:\n"
                "1. Safisha mguu na maji safi\n"
                "2. Loweka mguu kwenye maji ya chumvi\n"
                "3. Mweke mahali pakavu na safi\n"
                "4. Epuka matope na uchafu\n\n"
                f"{urgency}\n\n"
                "Piga simu SASA kama:\n"
                "- Ana harufu kali sana\n"
                "- Hawezi kusimama\n"
                "- Hali inazidi kuwa mbaya\n\n"
                "Daktari wa mifugo: 0800 720 601 (bure)\n\n"
                f"{R['followup']}"
            )
    else:
        return R["unknown"]

# ─── Case Logger ─────────────────────────────────────────────
def log_case(phone, session):
    issues = {"1": "Mastitis", "2": "Foot Rot", "3": "Free Text"}
    log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "phone_last4": phone[-4:],
        "lang": session.get("lang"),
        "issue": issues.get(session.get("issue"), "Unknown"),
        "duration": session.get("duration"),
        "severity": session.get("severity"),
        "count": session.get("count"),
        "freetext": session.get("freetext"),
    }
    with open("cases.json", "a") as f:
        f.write(json.dumps(log) + "\n")

# ─── Webhook ─────────────────────────────────────────────────
@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...)
):
    phone = From.strip()
    msg = Body.strip().upper()
    msg_raw = Body.strip()

    reset_words = ["HI", "HELLO", "HABARI", "START", "ANZA", "RESTART"]

    if phone not in sessions or msg in reset_words:
        sessions[phone] = {"step": "lang"}
        return LANG_SELECT

    session = sessions[phone]
    step = session.get("step")

    # Language selection
    if step == "lang":
        if msg == "1":
            session["lang"] = "en"
            session["step"] = "consent"
            return RESPONSES["en"]["consent"]
        elif msg == "2":
            session["lang"] = "sw"
            session["step"] = "consent"
            return RESPONSES["sw"]["consent"]
        else:
            return LANG_SELECT

    lang = session.get("lang", "en")
    R = RESPONSES[lang]

    # Consent
    if step == "consent":
        if msg in ["YES", "NDIO"]:
            session["step"] = "q1"
            return R["q1"]
        elif msg in ["NO", "HAPANA"]:
            del sessions[phone]
            return R["no_consent"]
        else:
            return R["consent_invalid"]

    # Q1
    elif step == "q1":
        if msg == "1":
            session["issue"] = "1"
            session["step"] = "q2"
            return R["q2_mastitis"]
        elif msg == "2":
            session["issue"] = "2"
            session["step"] = "q2"
            return R["q2_footrot"]
        elif msg == "3":
            session["issue"] = "3"
            session["step"] = "freetext"
            return R["freetext_prompt"]
        else:
            return R["invalid"]

    # Free text - Gemini
    elif step == "freetext":
        session["freetext"] = msg_raw
        result = gemini_diagnose(msg_raw, lang)
        if result:
            log_case(phone, session)
            del sessions[phone]
            return result
        else:
            log_case(phone, session)
            del sessions[phone]
            return R["ai_failed"]

    # Q2
    elif step == "q2":
        if msg in ["1", "2", "3"]:
            session["duration"] = msg
            session["step"] = "q3"
            return R["q3_mastitis"] if session["issue"] == "1" else R["q3_footrot"]
        else:
            return R["invalid"]

    # Q3
    elif step == "q3":
        if msg in ["1", "2", "3"]:
            session["severity"] = msg
            session["step"] = "q4"
            return R["q4"]
        else:
            return R["invalid"]

    # Q4
    elif step == "q4":
        if msg in ["1", "2", "3"]:
            session["count"] = msg
            result = diagnose(session)
            log_case(phone, session)
            del sessions[phone]
            return result
        else:
            return R["invalid"]

    else:
        sessions[phone] = {"step": "lang"}
        return LANG_SELECT

@app.get("/")
async def root():
    return {"status": "CropGuard AI is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
