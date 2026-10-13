"""
Uzhavar Nalan AI (உழவர் நலன் AI) — Tamil Nadu agriculture schemes assistant.
Run:  streamlit run app.py
"""

import base64
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from chat_store import delete_all_chats, delete_chat, list_chats, load_chat, new_chat_id, save_chat
from rag import SchemeAssistant, send_feedback

st.set_page_config(
    page_title="Uzhavar Nalan AI | உழவர் நலன் AI",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).parent
ASSETS = BASE_DIR / "assets"

LANGUAGE_OPTIONS = {"Auto": None, "தமிழ்": "Tamil", "English": "English"}
FONT_SIZES = {"A-": "0.95rem", "A": "1.05rem", "A+": "1.2rem"}

WELCOME = (
    "வணக்கம்! தமிழ்நாடு அரசு விவசாயத் திட்டங்கள் குறித்து உங்களுக்கு உதவ நான் தயாராக இருக்கிறேன்.\n\n"
    "Hello! I can help you with Tamil Nadu government agriculture schemes — ask in Tamil or English."
)

# (icon, Tamil label, English label, Tamil question, English question)
ASSIST_CARDS = [
    ("💰", "அரசு மானியங்கள்", "Government Subsidies",
     "விவசாயிகளுக்கு கிடைக்கும் அரசு மானியங்கள் என்ன?",
     "What government subsidies are available for farmers?"),
    ("🌱", "விதை மற்றும் உர உதவி", "Seeds & Fertilizer",
     "விதை மற்றும் உரத்திற்கான அரசு உதவித் திட்டங்கள் என்ன?",
     "What schemes support seeds and fertilizer?"),
    ("🛡️", "பயிர்க் காப்பீடு", "Crop Insurance",
     "பயிர்க் காப்பீட்டுத் திட்டம் பற்றி விளக்கவும்.",
     "Explain the crop insurance scheme."),
    ("🏦", "விவசாயக் கடன்", "Agri Loans",
     "விவசாயக் கடன் திட்டங்கள் என்ன?",
     "What agricultural loan schemes are available?"),
    ("🚰", "பாசன உதவிகள்", "Irrigation Assistance",
     "நுண்ணீர் பாசனம் மற்றும் பாசன உதவித் திட்டங்கள் என்ன?",
     "What irrigation and micro-irrigation assistance is available?"),
    ("📘", "விண்ணப்ப வழிகாட்டி", "Application Guide",
     "திட்டங்களுக்கு எப்படி விண்ணப்பிப்பது? படிப்படியாக விளக்கவும்.",
     "How do I apply for these schemes? Explain step by step."),
]

QUICK_QUESTIONS = [
    ("தமிழ்நாடு வேளாண்மைத் துறையின் கீழ் விவசாயிகளுக்கு என்னென்ன திட்டங்கள் உள்ளன?", "What agriculture schemes are available under the Tamil Nadu Agriculture Department?"),
    ("தமிழ்நாட்டில் விவசாயிகளுக்கு நிதியுதவி வழங்கும் திட்டங்கள் எவை?", "Which schemes provide financial assistance to farmers in Tamil Nadu?"),
    ("தமிழ்நாடு அரசின் வேளாண்மைத் திட்டங்களுக்கு விண்ணப்பிக்க என்னென்ன ஆவணங்கள் தேவை?", "What documents are required to apply for Tamil Nadu agriculture schemes?"),
    ("காய்கறி சாகுபடிக்கு உதவும் தமிழ்நாடு அரசுத் திட்டங்கள் உள்ளனவா?", "Are there any schemes that support vegetable cultivation in Tamil Nadu?"),
]


# ------------------------------------------------------------------ helpers
def image_data_uri(path: Path) -> str | None:
    if not path.exists():
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def inject_styles(font_size: str) -> None:
    css = (BASE_DIR / "styles.css").read_text(encoding="utf-8")
    background = image_data_uri(ASSETS / "background.jpg")
    if background:
        bg_css = f"linear-gradient(rgba(255,255,255,.15), rgba(255,255,255,.15)), url('{background}')"
    else:
        bg_css = "linear-gradient(160deg, #cfe8c2 0%, #9fcf87 45%, #5fa463 100%)"
    st.markdown(
        f"<style>{css}\n:root {{ --fs: {font_size}; }}\n.stApp {{ background-image: {bg_css}; }}</style>",
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="அறிவுத் தளம் ஏற்றப்படுகிறது... / Loading knowledge base...")
def get_assistant() -> SchemeAssistant:
    return SchemeAssistant()


def welcome_messages() -> list[dict]:
    return [{"role": "assistant", "content": WELCOME, "welcome": True}]


def init_state() -> None:
    st.session_state.setdefault("chat_id", new_chat_id())
    st.session_state.setdefault("messages", welcome_messages())
    st.session_state.setdefault("answer_language", "Auto")
    st.session_state.setdefault("font_size", "A")


def has_questions() -> bool:
    return any(m["role"] == "user" for m in st.session_state.messages)


# ------------------------------------------------------- chat-session actions
def start_new_chat() -> None:
    st.session_state.chat_id = new_chat_id()
    st.session_state.messages = welcome_messages()


def clear_chat() -> None:
    delete_chat(st.session_state.chat_id)
    st.session_state.messages = welcome_messages()
    st.toast("உரையாடல் அழிக்கப்பட்டது · Chat cleared 🧹")


def open_chat(chat_id: str) -> None:
    st.session_state.chat_id = chat_id
    st.session_state.messages = load_chat(chat_id) or welcome_messages()


def clear_all_history() -> None:
    delete_all_chats()
    start_new_chat()
    st.toast("வரலாறு அழிக்கப்பட்டது · History deleted 🗑️")


def day_label(timestamp: str) -> str:
    day = datetime.fromisoformat(timestamp).date()
    if day == date.today():
        return "இன்று · Today"
    if day == date.today() - timedelta(days=1):
        return "நேற்று · Yesterday"
    return day.strftime("%d %b %Y")


def queue_question(tamil: str, english: str) -> None:
    """Called by side-panel buttons: picks the question in the selected language."""
    use_english = st.session_state.answer_language == "English"
    st.session_state.pending_question = english if use_english else tamil


# --------------------------------------------------------------------- UI parts
def render_topbar() -> None:
    logo = image_data_uri(ASSETS / "logo.png")
    logo_html = f"<img src='{logo}' alt='logo'>" if logo else "🌾"
    with st.container(key="topbar"):
        brand, nav, lang, font = st.columns([4.2, 3.4, 1.9, 1.3], vertical_alignment="center")
        brand.markdown(
            f"""<div class="brand">
                  <div class="brand-logo">{logo_html}</div>
                  <div class="brand-title"><div class="ta">உழவர் நலன் AI</div>
                  <div class="en">Uzhavar Nalan AI</div></div>
                </div>""",
            unsafe_allow_html=True,
        )
        nav.markdown(
            """<div class="nav"><a href="#">Home</a><a href="#">அரசுத் திட்டங்கள்</a>
               <a href="#">எங்களைப் பற்றி</a></div>""",
            unsafe_allow_html=True,
        )
        lang.segmented_control(
            "Answer language", list(LANGUAGE_OPTIONS), key="answer_language",
            label_visibility="collapsed", help="பதில் மொழி / Answer language",
        )
        font.segmented_control(
            "Text size", list(FONT_SIZES), key="font_size",
            label_visibility="collapsed", help="எழுத்து அளவு / Text size",
        )


def render_side_panels() -> None:
    with st.container(key="assist_panel"):
        st.markdown(
            "<div class='panel-title'>விவசாயிகளுக்கான உதவிகள் | Farmer Assistance</div>",
            unsafe_allow_html=True,
        )
        for row in (ASSIST_CARDS[:3], ASSIST_CARDS[3:]):
            for col, (icon, ta, en, q_ta, q_en) in zip(st.columns(3), row):
                col.button(
                    f"{icon}  {ta}\n{en}", key=f"card_{en}", use_container_width=True,
                    on_click=queue_question, args=(q_ta, q_en),
                )

    with st.container(key="quick_panel"):
        st.markdown(
            "<div class='panel-title'>விரைவான கேள்விகள் | Quick Questions</div>",
            unsafe_allow_html=True,
        )
        english = st.session_state.answer_language == "English"
        for q_ta, q_en in QUICK_QUESTIONS:
            st.button(q_en if english else q_ta, key=f"quick_{q_en}",
                      on_click=queue_question, args=(q_ta, q_en))

    with st.container(key="heritage_panel"):
        st.markdown(
            """<div class='panel-title'>உழவின் பெருமை, தமிழின் பெருமை | Celebrating Tamil Farming Heritage</div>
            <div class="heritage-grid">
              <div class="verse"><h4>திருக்குறள்</h4><div class="ref">குறள் 1031 | திருவள்ளுவர்</div>
                <div class="lines">சுழன்றும்ஏர்ப் பின்னது உலகம் அதனால்<br>உழந்தும் உழவே தலை.</div></div>
              <div class="verse"><h4>புறநானூறு</h4><div class="ref">புறநானூறு 35 | வெள்ளைக்குடி நாகனார்</div>
                <div class="lines">பொருபடை தரூஉம் கொற்றமும் உழுபடை<br>ஊன்றுசால் மருங்கின் ஈன்றதன் பயனே.</div></div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_messages() -> None:
    for i, msg in enumerate(st.session_state.messages):
        role = "bot" if msg["role"] == "assistant" else "user"
        with st.container(key=f"msg-{role}-{i}"):
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.caption("📄 ஆதாரம் / Sources: " + " · ".join(msg["sources"]))
            if msg.get("run_id"):
                rating = st.feedback("thumbs", key=f"feedback_{st.session_state.chat_id}_{i}")
                if rating is not None and not msg.get("feedback_sent"):
                    send_feedback(msg["run_id"], rating)
                    msg["feedback_sent"] = True
                    save_chat(st.session_state.chat_id, st.session_state.messages)
                    st.toast("நன்றி! Thanks for your feedback 🙏")


def render_history() -> None:
    """Contents of the History popover: search + list of saved chats."""
    chats = list_chats()
    query = st.text_input("Search chats", placeholder="🔍 தேடு · Search chats",
                          label_visibility="collapsed", key="history_search")
    if query:
        chats = [c for c in chats if query.casefold() in c["title"].casefold()]
    if not chats:
        st.caption("சேமித்த உரையாடல்கள் இல்லை · No saved chats yet")
        return

    group = None
    for chat in chats:
        if day_label(chat["updated"]) != group:
            group = day_label(chat["updated"])
            st.caption(group)
        active = chat["id"] == st.session_state.chat_id
        st.button(
            f"{'🟢' if active else '💬'}  {chat['title']}",
            key=f"open_{chat['id']}", use_container_width=True,
            on_click=open_chat, args=(chat["id"],),
            help=f"{chat['count']} கேள்வி(கள்) · question(s) — {chat['updated'][11:16]}",
        )
    st.divider()
    st.button("🗑️ அனைத்தையும் நீக்கு · Delete all history", key="delete_all",
              use_container_width=True, on_click=clear_all_history)


def render_chat_actions() -> None:
    with st.container(key="chat_actions"):
        new, clear, history = st.columns(3)
        new.button("➕ புதிய உரையாடல் · New chat", key="btn_new_chat",
                   use_container_width=True, on_click=start_new_chat)
        clear.button("🧹 அழி · Clear chat", key="btn_clear_chat", use_container_width=True,
                     on_click=clear_chat, disabled=not has_questions())
        with history.popover("🕘 வரலாறு · History", use_container_width=True):
            render_history()


def render_chat_panel() -> None:
    with st.container(key="chat_panel"):
        st.markdown(
            """<div class="chat-head"><div class="mascot">🌱</div><div>
                 <h2>உங்கள் விவசாயக் கேள்விகளைக் கேளுங்கள்</h2>
                 <h3>Ask Your Agriculture Questions</h3>
                 <p>பசுமையான நாளைக்காக உங்களுடன் AI உதவியாளர்</p>
               </div></div>""",
            unsafe_allow_html=True,
        )
        render_chat_actions()
        history_box = st.container(height=470, key="chat_history")
        st.markdown("<div class='lang-hint'>தமிழ் / English</div>", unsafe_allow_html=True)
        typed = st.chat_input(
            "உங்கள் கேள்வியை இங்கே தமிழில் அல்லது ஆங்கிலத்தில் எழுதுங்கள்... / "
            "Ask about agriculture schemes, subsidies, eligibility..."
        )

    question = typed or st.session_state.pop("pending_question", None)

    with history_box:
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
        render_messages()

        if not question:
            return
        try:
            assistant = get_assistant()
            with st.spinner("பதில் தயாராகிறது... / Preparing your answer..."):
                result = assistant.ask(
                    question,
                    history=st.session_state.messages[:-1],
                    language=LANGUAGE_OPTIONS[st.session_state.answer_language or "Auto"],
                )
            st.session_state.messages.append({"role": "assistant", "content": result["answer"],
                                              "sources": result["sources"], "run_id": result["run_id"]})
        except (FileNotFoundError, EnvironmentError) as exc:
            st.session_state.messages.pop()
            st.error(f"⚙️ Setup needed: {exc}")
            return
        except Exception as exc:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "மன்னிக்கவும், ஒரு பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.\n\n"
                           f"Sorry, something went wrong. Please try again. ({type(exc).__name__})",
            })
        save_chat(st.session_state.chat_id, st.session_state.messages)
        st.rerun()


# ---------------------------------------------------------------------- page
def main() -> None:
    init_state()
    inject_styles(FONT_SIZES[st.session_state.font_size or "A"])
    render_topbar()

    with st.container(key="main"):
        chat_col, side_col = st.columns([1.15, 1], gap="large")
        with side_col:            # side panel first, so its buttons can queue a question
            render_side_panels()
        with chat_col:
            render_chat_panel()

    st.markdown(
        "<div class='footer-note'>குறிப்பு: திட்டங்கள், தகுதி மற்றும் ஆவணங்களை அரசுத் துறை அதிகாரப்பூர்வ "
        "வலைதளங்களில் சரிபார்க்கவும். / Note: Please verify schemes, eligibility, and document "
        "requirements from current official government sources.</div>",
        unsafe_allow_html=True,
    )


main()
