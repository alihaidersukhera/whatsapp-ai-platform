"""
WhatsApp AI Platform - Bot Brain
Rule-based demo brain with optional Gemini AI fallback.
All user-facing replies are in Roman Urdu (mixed with light English).
"""
import os
import re

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except Exception:
    _GENAI_AVAILABLE = False


class BotBrain:
    """Handles one conversational turn per user, incl. a COD order flow."""

    def __init__(self, business_name="MuvMod Shoes", owner_whatsapp="03278369194"):
        self.business_name = business_name
        self.owner_whatsapp = owner_whatsapp
        self.sessions = {}
        self.conversation_log = []
        self.products = [
            {"id": "1", "name": "Nike Football Shoes (Original Preloved)", "price": 9000},
            {"id": "2", "name": "Ballet Shoes", "price": 1299},
            {"id": "3", "name": "Fancy Slides", "price": 999},
            {"id": "4", "name": "Posh Pumps", "price": 1199},
        ]
        self._gemini_model = None
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key and _GENAI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
            except Exception:
                self._gemini_model = None

    def _session(self, user_id):
        return self.sessions.setdefault(user_id, {"state": "idle", "order": {}})

    def _product_list(self):
        lines = ["\U0001F6CD\uFE0F *Hamari Products:*\n"]
        for p in self.products:
            lines.append(f"{p['id']}. {p['name']} \u2014 Rs. {p['price']:,}")
        lines.append("\nOrder karne ke liye likhein: *order*")
        return "\n".join(lines)

    def handle_message(self, text, user_id="demo-user"):
        text = (text or "").strip()
        low = text.lower()
        sess = self._session(user_id)
        if sess["state"] != "idle":
            reply = self._advance_order(sess, text)
        elif re.search(r"\b(assalam|salam|aoa|hello|hi|hey)\b", low):
            reply = (f"Walaikum Assalam! \U0001F44B *{self.business_name}* me khush aamdeed!\n\n"
                     "Me aapki kese madad kar sakta hun?\n"
                     "\u2022 Products dekhne ke liye: *products*\n"
                     "\u2022 Order karne ke liye: *order*\n"
                     "\u2022 Kisi insan se baat karni ho to: *human*")
        elif "order" in low or "kharid" in low or "buy" in low or "mangwana" in low:
            reply = self._start_order(sess)
        elif "product" in low or "cheez" in low or "shoes" in low or "catalog" in low:
            reply = self._product_list()
        elif any(w in low for w in ["price", "qeemat", "rate", "kimat", "paisay", "paisy"]):
            reply = self._product_list()
        elif any(w in low for w in ["timing", "time", "open", "khula", "band", "hours"]):
            reply = "\U0001F558 Hamari shop timings: *Subah 10 \u2013 Raat 9* (haftay ke 7 din khula!)"
        elif any(w in low for w in ["location", "address", "kahan", "pata", "dukkan", "shop kahan"]):
            reply = "\U0001F4CD Hum online hain \u2014 *poore Pakistan me free delivery!* Order WhatsApp par hi ho jayega."
        elif any(w in low for w in ["delivery", "bhijwana", "parsal", "courier", "kitne din"]):
            reply = "\U0001F69A *Free delivery* poore Pakistan me! Order ke 2\u20134 din me aapke paas. Payment Cash on Delivery (COD) \u2014 pehle cheez dekhein, phir paise dein!"
        elif any(w in low for w in ["return", "wapis", "exchange", "badalna"]):
            reply = "\U0001F504 Easy return policy hai! Koi masla ho to 7 din me *exchange* ho jayega. Bas humein WhatsApp par batayein."
        elif any(w in low for w in ["human", "insan", "banda", "owner", "malik", "call", "phone"]):
            reply = (f"\U0001F9D1\u200D\U0001F4BC Bilkul! Hamari team ka banda aapse khud baat karega.\n"
                     f"Aap direct WhatsApp bhi kar sakte hain: *{self.owner_whatsapp}*")
        elif any(w in low for w in ["shukriya", "thanks", "thank"]):
            reply = "Khush aamdeed! \U0001F60A Koi aur madad chahiye to bas likhein."
        elif low in ["bye", "allah hafiz", "khuda hafiz"]:
            reply = f"Allah Hafiz! \U0001F44B *{self.business_name}* ko yaad rakhiye ga!"
        else:
            reply = self._ai_fallback(text)
        self.conversation_log.append({"user_id": user_id, "incoming": text, "reply": reply})
        return reply

    def _start_order(self, sess):
        sess["state"] = "awaiting_product"
        sess["order"] = {}
        return ("\U0001F6D2 *Order shuru karte hain!*\n\n" + self._product_list() +
                "\n\nProduct ka *number* likhein (jaise: 2)")

    def _advance_order(self, sess, text):
        low = text.lower()
        state = sess["state"]
        order = sess["order"]
        if any(w in low for w in ["cancel", "khatam", "rehne", "nahi chahiye"]):
            sess["state"] = "idle"; sess["order"] = {}
            return "Koi baat nahi! Order cancel kar diya. \U0001F44D Dobara order ke liye *order* likhein."
        if state == "awaiting_product":
            prod = next((p for p in self.products if p["id"] == text.strip()), None)
            if not prod:
                return "\u26A0\uFE0F Sahi number likhein (1\u20134). Ya *cancel* likh kar order rok dein."
            order["product"] = prod
            sess["state"] = "awaiting_name"
        if state == "awaiting_address":
            if len(text) < 5:
                return "\u26A0\uFE0F Mukamal address likhein (gali/mohallah + sheher):"
            order["address"] = text.strip()
            sess["state"] = "awaiting_confirm"
            p = order["product"]
            return (f"\U0001F4DD *Order confirm karein:*\n\nProduct: {p['name']}\nQeemat: Rs. {p['price']:,} (COD)\n"
                    f"Naam: {order['name']}\nAddress: {order['address']}\n\nConfirm ke liye *haan* likhein, cancel ke liye *cancel*:")
        if state == "awaiting_confirm":
            if low in ["haan", "han", "yes", "confirm", "ok", "theek"]:
                p = order["product"]
                sess["state"] = "idle"; sess["order"] = {}
                return (f"\U0001F389 *Order confirm ho gaya!*\n\n{p['name']} \u2014 Rs. {p['price']:,}\n"
                        "2\u20134 din me aapke paas pohnch jayega. Payment delivery par (COD).\n\n"
                        f"Shukriya {order['name']}! *{self.business_name}* par bharosa karne ka! \u2764\uFE0F")
            sess["state"] = "idle"; sess["order"] = {}
            return "Order cancel kar diya. Koi baat nahi! \U0001F44D"
        sess["state"] = "idle"
        return self._ai_fallback(text)

    def _ai_fallback(self, text):
        if self._gemini_model:
            try:
                prompt = (f"You are a friendly WhatsApp shop assistant for '{self.business_name}' "
                          f"(shoes store, Pakistan, COD, free delivery). Reply in Roman Urdu, "
                          f"short (under 40 words), warm. Customer asked: {text}")
                resp = self._gemini_model.generate_content(prompt)
                return resp.text.strip()[:400]
            except Exception:
                pass
        return ("Samajh nahi aaya! \U0001F605 Aap ye try karein:\n\u2022 *products* \u2014 cheezen dekhein\n"
                "\u2022 *order* \u2014 order karein\n\u2022 *human* \u2014 kisi insan se baat karein")


import streamlit as st

st.set_page_config(page_title="WhatsApp AI Platform", page_icon="\U0001F4F1", layout="wide")

if "brain" not in st.session_state:
    st.session_state.brain = BotBrain()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "settings" not in st.session_state:
    st.session_state.settings = {"business_name": "MuvMod Shoes", "owner_whatsapp": "03278369194", "gemini_key": ""}

brain = st.session_state.brain
brain.business_name = st.session_state.settings["business_name"]
brain.owner_whatsapp = st.session_state.settings["owner_whatsapp"]

st.sidebar.title("\U0001F4F1 WhatsApp AI Platform")
page = st.sidebar.radio("Menu", ["\U0001F4AC Demo Chat", "\U0001F4CB Conversations", "\U0001F4E2 Broadcast", "\u2699\uFE0F Settings"])
st.sidebar.caption("JONNY PRODUCTIONS \u2022 Demo (zero cost)")

if page == "\U0001F4AC Demo Chat":
    st.header("\U0001F4AC Demo Chat \u2014 Bot se baat karein")
    st.caption("Yehi bot aapke client ki WhatsApp par chalega. Try karein: *salam*, *products*, *order*")
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)
    if prompt := st.chat_input("Message likhein..."):
        st.session_state.chat_history.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        reply = brain.handle_message(prompt, user_id="demo-user")
        st.session_state.chat_history.append(("assistant", reply))
        with st.chat_message("assistant"):
            st.markdown(reply)
elif page == "\U0001F4CB Conversations":
    st.header("\U0001F4CB Conversations Log")
    log = brain.conversation_log
    st.metric("Total messages handled", len(log))
    if log:
        for item in reversed(log[-20:]):
            with st.expander(f"\U0001F464 {item['user_id']}: {item['incoming'][:50]}"):
                st.markdown(f"**Customer:** {item['incoming']}")
                st.markdown(f"**Bot:** {item['reply']}")
    else:
        st.info("Abhi koi conversation nahi \u2014 pehle Demo Chat me bot se baat karein!")
elif page == "\U0001F4E2 Broadcast":
    st.header("\U0001F4E2 Broadcast Campaign (Demo)")
    st.caption("Real mode me ye Meta WhatsApp API se sab customers ko jayega.")
    audience = st.number_input("Kitne customers ko bhejna hai?", 1, 100000, 150)
    message = st.text_area("Broadcast message", "\U0001F389 *EID SALE!* MuvMod Shoes par 60% tak OFF! Aaj hi order karein \u2014 free delivery! \U0001F6CD\uFE0F")
    if st.button("\U0001F680 Broadcast Bhejein"):
        st.success(f"\u2705 Demo: {audience} customers ko broadcast queue ho gaya!")
        st.balloons()
else:
    st.header("\u2699\uFE0F Settings")
    s = st.session_state.settings
    s["business_name"] = st.text_input("Business ka naam", s["business_name"])
    s["owner_whatsapp"] = st.text_input("Owner ka WhatsApp number", s["owner_whatsapp"])
    key = st.text_input("Gemini API Key (optional \u2014 smart jawabon ke liye)", s["gemini_key"], type="password")
    if key != s["gemini_key"]:
        s["gemini_key"] = key
        os.environ["GEMINI_API_KEY"] = key
        st.session_state.brain = BotBrain(business_name=s["business_name"], owner_whatsapp=s["owner_whatsapp"])
        st.success("\u2705 Settings save ho gayin! Bot restart ho gaya.")
    st.info("\U0001F4A1 Gemini key ke baghair bot rule-based demo mode me chalega \u2014 phir bhi poori tarah kaam karega!")
