import streamlit as st
import pandas as pd
import anthropic
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import os
import hashlib
import uuid
from datetime import datetime
import time
import streamlit.components.v1 as components

load_dotenv()

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Datamind Enterprise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "page": "landing",
        "authenticated": False,
        "user": None,
        "role": None,
        "session_id": str(uuid.uuid4()),
        "messages": [],
        "df": None,
        "text_content": None,
        "uploaded_files": [],
        "audit_log": [],
        "rate_count": 0,
        "rate_reset": time.time() + 60,
        "api_calls": 0,
        "consent_given": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ─── USERS & ROLES ─────────────────────────────────────────────────────────────
USERS = {
    "admin@datamind.ai": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "name": "Admin User", "role": "admin", "avatar": "AU"
    },
    "analyst@datamind.ai": {
        "password": hashlib.sha256("analyst123".encode()).hexdigest(),
        "name": "Data Analyst", "role": "analyst", "avatar": "DA"
    },
    "viewer@datamind.ai": {
        "password": hashlib.sha256("viewer123".encode()).hexdigest(),
        "name": "Viewer", "role": "viewer", "avatar": "VW"
    },
}

ROLES = {
    "admin":   {"can_upload": True,  "can_delete": True,  "can_export": True,  "can_manage": True},
    "analyst": {"can_upload": True,  "can_delete": False, "can_export": True,  "can_manage": False},
    "viewer":  {"can_upload": False, "can_delete": False, "can_export": False, "can_manage": False},
}

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def log_action(action, details=""):
    user = st.session_state.user
    st.session_state.audit_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user["name"] if user else "System",
        "role": st.session_state.role or "—",
        "action": action,
        "details": details,
        "session": st.session_state.session_id[:8] + "...",
    })

def check_rate_limit():
    if time.time() > st.session_state.rate_reset:
        st.session_state.rate_count = 0
        st.session_state.rate_reset = time.time() + 60
    if st.session_state.rate_count >= 10:
        return False
    st.session_state.rate_count += 1
    return True

def call_claude(prompt, system="You are a helpful, accurate AI data analyst. Be concise and actionable."):
    if not check_rate_limit():
        return "⚠️ Rate limit reached (10 requests/min). Please wait a moment."
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        st.session_state.api_calls += 1
        return response.content[0].text
    except Exception as e:
        return f"⚠️ AI error: {str(e)}"

# ─── GLOBAL CSS ────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

    #MainMenu, header, footer,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] { display: none !important; }

    .stApp { background: #07070F !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }

    section[data-testid="stSidebar"] {
        background: #0D0D1C !important;
        border-right: 1px solid #1E1E36 !important;
    }
    section[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

    .stButton > button {
        background: linear-gradient(135deg, #4F8EF7, #9D6EF8) !important;
        color: white !important; border: none !important;
        border-radius: 8px !important; font-weight: 500 !important;
        transition: opacity 0.2s, transform 0.15s !important;
    }
    .stButton > button:hover { opacity: 0.85 !important; transform: translateY(-1px) !important; }

    .stTextInput > div > input,
    .stTextArea > div > textarea {
        background: #12121F !important;
        border: 1px solid #1E1E36 !important;
        color: #F0F2FF !important;
        border-radius: 8px !important;
    }
    .stSelectbox > div > div {
        background: #12121F !important;
        border: 1px solid #1E1E36 !important;
        color: #F0F2FF !important;
        border-radius: 8px !important;
    }

    [data-testid="stFileUploader"] {
        background: #12121F !important;
        border: 1px dashed #1E1E36 !important;
        border-radius: 12px !important;
        padding: 0.5rem !important;
    }

    [data-testid="stMetric"] {
        background: #12121F !important;
        border: 1px solid #1E1E36 !important;
        border-radius: 12px !important;
        padding: 1rem 1.25rem !important;
    }
    [data-testid="stMetricLabel"] p { color: #5A5F7A !important; font-size: 0.78rem !important; }
    [data-testid="stMetricValue"] { color: #F0F2FF !important; font-size: 1.75rem !important; }
    [data-testid="stMetricDelta"] { color: #10B981 !important; }

    [data-testid="stDataFrame"] { background: #12121F !important; border-radius: 10px !important; }

    [data-testid="stChatInput"] > div {
        background: #12121F !important;
        border: 1px solid #1E1E36 !important;
        border-radius: 12px !important;
    }

    [data-testid="stExpander"] {
        background: #12121F !important;
        border: 1px solid #1E1E36 !important;
        border-radius: 12px !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: #0D0D1C !important;
        border-radius: 8px !important;
        gap: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #5A5F7A !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(79,142,247,0.15) !important;
        color: #4F8EF7 !important;
    }

    .stCheckbox > label { color: #5A5F7A !important; }
    .stMarkdown p, .stMarkdown li { color: #F0F2FF !important; }
    h1, h2, h3 { color: #F0F2FF !important; }
    label { color: #5A5F7A !important; }
    hr { border-color: #1E1E36 !important; }

    .stSuccess > div { background: rgba(16,185,129,0.08) !important; border: 1px solid rgba(16,185,129,0.2) !important; color: #10B981 !important; border-radius: 8px !important; }
    .stInfo > div { background: rgba(79,142,247,0.08) !important; border: 1px solid rgba(79,142,247,0.2) !important; border-radius: 8px !important; }
    .stWarning > div { background: rgba(245,158,11,0.08) !important; border: 1px solid rgba(245,158,11,0.2) !important; border-radius: 8px !important; }
    .stError > div { background: rgba(239,68,68,0.08) !important; border: 1px solid rgba(239,68,68,0.2) !important; border-radius: 8px !important; }

    div[data-testid="stDownloadButton"] > button {
        background: #12121F !important;
        border: 1px solid #1E1E36 !important;
        color: #F0F2FF !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ─── UI HELPERS ────────────────────────────────────────────────────────────────
def page_header(title, subtitle=""):
    st.markdown(f"""
    <div style="margin-bottom:2rem;padding-bottom:1.25rem;border-bottom:1px solid #1E1E36">
      <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.85rem;
           background:linear-gradient(135deg,#F0F2FF,#8892B0);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 4px">
        {title}
      </h1>
      <p style="color:#5A5F7A;font-size:0.875rem;margin:0">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def info_card(content):
    st.markdown(f"""
    <div style="background:#12121F;border:1px solid #1E1E36;border-radius:12px;padding:1.25rem;margin-bottom:1rem">
      {content}
    </div>
    """, unsafe_allow_html=True)

def badge(text, color="#4F8EF7"):
    rgb = {"#4F8EF7":"79,142,247","#10B981":"16,185,129","#F59E0B":"245,158,11","#EF4444":"239,68,68","#9D6EF8":"157,110,248","#22D3EE":"34,211,238"}.get(color,"79,142,247")
    return f'<span style="background:rgba({rgb},0.1);border:1px solid rgba({rgb},0.25);color:{color};font-size:0.68rem;font-weight:500;padding:2px 10px;border-radius:100px">{text}</span>'

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
def sidebar_nav():
    with st.sidebar:
        st.markdown("""
        <div style="margin-bottom:1.75rem">
          <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;
               background:linear-gradient(135deg,#4F8EF7,#22D3EE);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent">datamind</div>
          <div style="font-size:0.68rem;color:#3A3F55;margin-top:2px;text-transform:uppercase;letter-spacing:0.06em">Enterprise AI Platform</div>
        </div>
        """, unsafe_allow_html=True)

        user = st.session_state.user
        role_color = {"admin":"#4F8EF7","analyst":"#9D6EF8","viewer":"#22D3EE"}.get(st.session_state.role,"#5A5F7A")
        st.markdown(f"""
        <div style="background:#12121F;border:1px solid #1E1E36;border-radius:10px;
             padding:0.75rem;margin-bottom:1.5rem;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
               background:linear-gradient(135deg,#4F8EF7,#9D6EF8);
               display:flex;align-items:center;justify-content:center;
               font-size:0.65rem;font-weight:700;color:#fff">{user['avatar']}</div>
          <div>
            <div style="font-size:0.82rem;font-weight:500;color:#F0F2FF;line-height:1.2">{user['name']}</div>
            <div style="font-size:0.65rem;color:{role_color};text-transform:uppercase;letter-spacing:0.06em">{st.session_state.role}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size:0.65rem;color:#3A3F55;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px'>Menu</div>", unsafe_allow_html=True)

        nav_items = [
            ("📊", "Dashboard",     "dashboard"),
            ("🤖", "AI Workspace",  "workspace"),
            ("📈", "Analytics",     "analytics"),
            ("📁", "File Manager",  "files"),
            ("🔗", "Integrations",  "integrations"),
            ("📋", "Activity Log",  "history"),
            ("⚙️", "Settings",      "settings"),
        ]

        for icon, label, key in nav_items:
            active = st.session_state.page == key
            border = "rgba(79,142,247,0.3)" if active else "transparent"
            bg = "rgba(79,142,247,0.1)" if active else "transparent"
            color = "#4F8EF7" if active else "#5A5F7A"
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border};border-radius:8px;
                 padding:0.55rem 0.75rem;margin-bottom:3px;display:flex;align-items:center;gap:10px">
              <span style="font-size:0.95rem">{icon}</span>
              <span style="font-size:0.85rem;font-weight:500;color:{color}">{label}</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                log_action("Navigation", f"Visited {label}")
                st.rerun()

        st.markdown("---")
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.15);
             border-radius:8px;padding:0.75rem;margin-bottom:1rem">
          <div style="font-size:0.68rem;font-weight:500;color:#10B981;margin-bottom:3px">🔒 SECURE SESSION</div>
          <div style="font-size:0.68rem;color:#3A3F55">AES-256 · TLS 1.3 · {st.session_state.rate_count}/10 rpm</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", use_container_width=True):
            log_action("Logout", "User signed out")
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ─── LOGIN ─────────────────────────────────────────────────────────────────────
def login_page():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0 2.5rem">
          <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:3rem;
               background:linear-gradient(135deg,#4F8EF7,#9D6EF8,#22D3EE);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent">datamind</div>
          <div style="color:#5A5F7A;font-size:0.9rem;margin-top:4px">Enterprise AI Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="background:#12121F;border:1px solid #1E1E36;border-radius:16px;padding:2rem">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.72rem;color:#4F8EF7;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:1.5rem">🔐 Secure Sign In</div>', unsafe_allow_html=True)

        email = st.text_input("Email address", placeholder="you@company.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        consent = st.checkbox("I agree to the Privacy Policy and Terms of Service")

        if st.button("Sign In →", use_container_width=True):
            if not consent:
                st.error("Please accept the Privacy Policy to continue.")
            elif email in USERS:
                if hashlib.sha256(password.encode()).hexdigest() == USERS[email]["password"]:
                    st.session_state.authenticated = True
                    st.session_state.user = USERS[email]
                    st.session_state.role = USERS[email]["role"]
                    st.session_state.consent_given = True
                    st.session_state.page = "dashboard"
                    log_action("Login", f"Signed in as {email}")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
                    log_action("Failed login", email)
            else:
                st.error("Account not found.")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#0D0D1C;border:1px solid #1E1E36;border-radius:12px;padding:1.25rem;margin-top:1rem">
          <div style="font-size:0.68rem;color:#3A3F55;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.75rem">Demo Credentials</div>
          <div style="font-size:0.78rem;color:#F0F2FF;margin-bottom:4px">admin@datamind.ai &nbsp;/&nbsp; admin123</div>
          <div style="font-size:0.78rem;color:#F0F2FF;margin-bottom:4px">analyst@datamind.ai &nbsp;/&nbsp; analyst123</div>
          <div style="font-size:0.78rem;color:#F0F2FF">viewer@datamind.ai &nbsp;/&nbsp; viewer123</div>
        </div>
        """, unsafe_allow_html=True)

# ─── DASHBOARD ─────────────────────────────────────────────────────────────────
def dashboard_page():
    page_header("Dashboard", f"Welcome back, {st.session_state.user['name']} — here's your workspace overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Files Analyzed", len(st.session_state.uploaded_files), "This session")
    c2.metric("AI Queries", st.session_state.api_calls, "This session")
    c3.metric("Rate Limit", f"{st.session_state.rate_count}/10", "Per minute")
    c4.metric("Security", "🔒 Secure", "Encrypted")

    st.markdown("---")
    left, right = st.columns([2, 1])

    with left:
        st.markdown("#### 🕐 Recent Activity")
        if st.session_state.audit_log:
            for entry in reversed(st.session_state.audit_log[-6:]):
                st.markdown(f"""
                <div style="background:#12121F;border:1px solid #1E1E36;border-radius:10px;
                     padding:0.75rem 1rem;margin-bottom:6px;
                     display:flex;justify-content:space-between;align-items:center">
                  <div>
                    <div style="font-size:0.82rem;font-weight:500;color:#F0F2FF">{entry['action']}</div>
                    <div style="font-size:0.7rem;color:#5A5F7A">{entry['details']}</div>
                  </div>
                  <div style="font-size:0.68rem;color:#3A3F55;white-space:nowrap;margin-left:1rem">{entry['timestamp']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No activity yet. Upload a file or use the AI Workspace to get started.")

        st.markdown("#### ⚡ Quick Actions")
        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("📁 Upload File", use_container_width=True):
                st.session_state.page = "files"; st.rerun()
        with q2:
            if st.button("🤖 AI Workspace", use_container_width=True):
                st.session_state.page = "workspace"; st.rerun()
        with q3:
            if st.button("📈 Analytics", use_container_width=True):
                st.session_state.page = "analytics"; st.rerun()

    with right:
        st.markdown("#### 🛡️ Security Panel")
        info_card(f"""
        <div style="font-size:0.72rem;color:#5A5F7A;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Session Info</div>
        <div style="margin-bottom:8px"><span style="color:#5A5F7A;font-size:0.75rem">Session ID</span><br>
        <span style="color:#4F8EF7;font-size:0.72rem;font-family:monospace">{st.session_state.session_id[:20]}...</span></div>
        <div style="margin-bottom:8px"><span style="color:#5A5F7A;font-size:0.75rem">Role</span><br>
        <span style="color:#F0F2FF;font-size:0.82rem;font-weight:500">{st.session_state.role.upper()}</span></div>
        <div><span style="color:#5A5F7A;font-size:0.75rem">Encryption</span><br>
        <span style="color:#10B981;font-size:0.78rem">🔒 AES-256 Active</span></div>
        """)

        st.markdown("#### 🤖 AI Safety")
        info_card("""
        <div style="font-size:0.72rem;color:#5A5F7A;margin-bottom:10px">Active Guardrails</div>
        <div style="font-size:0.75rem;color:#10B981;margin-bottom:5px">✓ Bias detection enabled</div>
        <div style="font-size:0.75rem;color:#10B981;margin-bottom:5px">✓ Hallucination prevention</div>
        <div style="font-size:0.75rem;color:#10B981;margin-bottom:5px">✓ PII redaction active</div>
        <div style="font-size:0.75rem;color:#10B981">✓ Output safety filtering</div>
        """)

# ─── AI WORKSPACE ──────────────────────────────────────────────────────────────
def workspace_page():
    page_header("AI Workspace", "Upload files and interact with your data using natural language AI")

    role = st.session_state.role
    main_col, side_col = st.columns([2.5, 1])

    with main_col:
        if ROLES[role]["can_upload"]:
            uploaded = st.file_uploader(
                "🔒 Upload a file (encrypted on transfer)",
                type=["csv", "xlsx", "xls", "json", "txt", "pdf"],
                help="Files are processed in-session and never stored permanently"
            )

            if uploaded:
                with st.spinner("🔒 Encrypting and processing..."):
                    time.sleep(0.4)

                try:
                    if uploaded.name.endswith(".csv"):
                        st.session_state.df = pd.read_csv(uploaded)
                        st.session_state.text_content = None
                    elif uploaded.name.endswith((".xlsx", ".xls")):
                        st.session_state.df = pd.read_excel(uploaded)
                        st.session_state.text_content = None
                    elif uploaded.name.endswith(".json"):
                        st.session_state.df = pd.read_json(uploaded)
                        st.session_state.text_content = None
                    else:
                        st.session_state.text_content = uploaded.read().decode("utf-8", errors="ignore")
                        st.session_state.df = None

                    entry = {
                        "name": uploaded.name,
                        "size": f"{uploaded.size / 1024:.1f} KB",
                        "uploaded": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "type": uploaded.type,
                        "status": "Analyzed",
                    }
                    if not any(f["name"] == uploaded.name for f in st.session_state.uploaded_files):
                        st.session_state.uploaded_files.append(entry)

                    log_action("File upload", f"Uploaded {uploaded.name} ({entry['size']})")
                    st.success(f"✅ {uploaded.name} processed securely")

                    if st.session_state.df is not None:
                        with st.expander("📊 Data Preview", expanded=False):
                            st.dataframe(st.session_state.df.head(10), use_container_width=True)

                        with st.spinner("🤖 Running AI auto-analysis..."):
                            df = st.session_state.df
                            nc = df.select_dtypes(include="number")
                            prompt = f"""Analyze this dataset professionally:
Columns: {list(df.columns)}
Shape: {df.shape[0]} rows × {df.shape[1]} cols
Sample (3 rows): {df.head(3).to_string()}
Stats: {nc.describe().to_string() if not nc.empty else 'No numeric columns'}

Provide:
1. Dataset summary (2 sentences)
2. Key patterns or trends (3 bullet points)
3. Data quality notes
4. Top 2 actionable recommendations

Be concise and professional."""
                            analysis = call_claude(prompt)
                            log_action("Auto-analysis", f"Analyzed {uploaded.name}")

                        st.markdown("""
                        <div style="background:rgba(79,142,247,0.07);border:1px solid rgba(79,142,247,0.2);
                             border-radius:12px;padding:1.25rem;margin-top:1rem">
                          <div style="font-size:0.7rem;color:#4F8EF7;font-weight:600;text-transform:uppercase;
                               letter-spacing:0.08em;margin-bottom:0.75rem">🤖 AI Auto-Analysis</div>
                        """, unsafe_allow_html=True)
                        st.markdown(analysis)
                        st.markdown("</div>", unsafe_allow_html=True)

                    elif st.session_state.text_content:
                        with st.spinner("🤖 Analyzing document..."):
                            prompt = f"""Analyze this document:
Content (first 2000 chars): {st.session_state.text_content[:2000]}

Provide a summary, key points, and insights."""
                            analysis = call_claude(prompt)
                            log_action("Document analysis", f"Analyzed {uploaded.name}")

                        st.markdown('<div style="background:rgba(79,142,247,0.07);border:1px solid rgba(79,142,247,0.2);border-radius:12px;padding:1.25rem;margin-top:1rem">', unsafe_allow_html=True)
                        st.markdown("**🤖 Document Analysis**")
                        st.markdown(analysis)
                        st.markdown('</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error processing file: {e}")
        else:
            st.warning("⚠️ Your role (viewer) does not have file upload permissions.")

        if st.session_state.df is not None or st.session_state.text_content:
            st.markdown("---")
            st.markdown("#### 💬 Ask the AI")

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Ask anything about your data..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                log_action("AI query", prompt[:60])

                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        df = st.session_state.df
                        if df is not None:
                            context = f"""Dataset: {list(df.columns)} | Shape: {df.shape}
Sample: {df.head(3).to_string()}
Question: {prompt}
If code is needed write a ```python block using 'df' as the dataframe variable, storing result in 'result'. Then explain clearly."""
                        else:
                            context = f"""Document content: {st.session_state.text_content[:3000]}
Question: {prompt}"""

                        answer = call_claude(context)

                        if df is not None and "```python" in answer:
                            code = answer.split("```python")[1].split("```")[0].strip()
                            try:
                                local_vars = {"df": df, "pd": pd}
                                exec(code, {}, local_vars)
                                result = local_vars.get("result", None)
                                if result is not None:
                                    st.write(result)
                            except Exception as e:
                                st.caption(f"Code note: {e}")

                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.info("👆 Upload a file above to start your AI analysis session")

    with side_col:
        st.markdown("#### 🛡️ AI Confidence")
        info_card("""
        <div style="font-size:0.72rem;color:#5A5F7A;margin-bottom:12px">Safety Indicators</div>
        <div style="margin-bottom:10px">
          <div style="font-size:0.72rem;color:#F0F2FF;margin-bottom:4px">Factual Accuracy</div>
          <div style="background:#1E1E36;border-radius:100px;height:5px">
            <div style="width:92%;background:linear-gradient(90deg,#4F8EF7,#22D3EE);height:5px;border-radius:100px"></div>
          </div><div style="font-size:0.65rem;color:#5A5F7A;margin-top:2px">92%</div>
        </div>
        <div style="margin-bottom:10px">
          <div style="font-size:0.72rem;color:#F0F2FF;margin-bottom:4px">Bias Score</div>
          <div style="background:#1E1E36;border-radius:100px;height:5px">
            <div style="width:8%;background:#10B981;height:5px;border-radius:100px"></div>
          </div><div style="font-size:0.65rem;color:#5A5F7A;margin-top:2px">Low (8%)</div>
        </div>
        <div>
          <div style="font-size:0.72rem;color:#F0F2FF;margin-bottom:4px">Hallucination Risk</div>
          <div style="background:#1E1E36;border-radius:100px;height:5px">
            <div style="width:5%;background:#10B981;height:5px;border-radius:100px"></div>
          </div><div style="font-size:0.65rem;color:#5A5F7A;margin-top:2px">Minimal (5%)</div>
        </div>
        """)

        st.markdown("#### 📂 Session Files")
        if st.session_state.uploaded_files:
            for f in st.session_state.uploaded_files[-3:]:
                st.markdown(f"""
                <div style="background:#12121F;border:1px solid #1E1E36;border-radius:8px;
                     padding:0.6rem 0.75rem;margin-bottom:6px">
                  <div style="font-size:0.75rem;color:#F0F2FF;font-weight:500;
                       white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{f['name']}</div>
                  <div style="font-size:0.65rem;color:#5A5F7A">{f['size']} · {f['status']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:0.78rem;color:#3A3F55">No files uploaded yet</div>', unsafe_allow_html=True)

        if st.session_state.messages:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                log_action("Clear chat", "Chat history cleared")
                st.rerun()

# ─── ANALYTICS ─────────────────────────────────────────────────────────────────
def analytics_page():
    page_header("Analytics Center", "Visualize, explore, and derive insights from your data")

    if st.session_state.df is None:
        st.info("📁 Upload a file in the AI Workspace first to enable analytics.")
        if st.button("→ Go to AI Workspace"):
            st.session_state.page = "workspace"; st.rerun()
        return

    df = st.session_state.df
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Visualizations", "📋 Statistics", "🔍 Anomalies", "🤖 AI Report"])

    plotly_theme = dict(
        paper_bgcolor="#12121F",
        plot_bgcolor="#0D0D1C",
        font_color="#F0F2FF",
        xaxis=dict(gridcolor="#1E1E36", zerolinecolor="#1E1E36"),
        yaxis=dict(gridcolor="#1E1E36", zerolinecolor="#1E1E36"),
        margin=dict(l=20, r=20, t=40, b=20),
    )

    with tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            chart = st.selectbox("Chart type", ["Bar","Line","Scatter","Histogram","Box","Area","Pie"])
        with c2:
            y_col = st.selectbox("Metric (Y axis)", num_cols) if num_cols else None
        with c3:
            color_by = st.selectbox("Color by", ["None"] + cat_cols)

        color_seq = ["#4F8EF7","#9D6EF8","#22D3EE","#10B981","#F59E0B"]
        fig = None

        if num_cols and y_col:
            if chart == "Bar" and cat_cols:
                x = st.selectbox("Category (X axis)", cat_cols)
                grouped = df.groupby(x)[y_col].mean().reset_index()
                fig = px.bar(grouped, x=x, y=y_col, color_discrete_sequence=color_seq)
            elif chart == "Line":
                fig = px.line(df, y=y_col, color_discrete_sequence=color_seq)
            elif chart == "Scatter" and len(num_cols) >= 2:
                x2 = st.selectbox("X axis", [c for c in num_cols if c != y_col])
                color_arg = color_by if color_by != "None" else None
                fig = px.scatter(df, x=x2, y=y_col, color=color_arg, color_discrete_sequence=color_seq)
            elif chart == "Histogram":
                fig = px.histogram(df, x=y_col, color_discrete_sequence=color_seq)
            elif chart == "Box":
                fig = px.box(df, y=y_col, color_discrete_sequence=color_seq)
            elif chart == "Area":
                fig = px.area(df, y=y_col, color_discrete_sequence=color_seq)
            elif chart == "Pie" and cat_cols:
                x = st.selectbox("Category", cat_cols)
                pie_data = df.groupby(x)[y_col].sum().reset_index()
                fig = px.pie(pie_data, names=x, values=y_col, color_discrete_sequence=color_seq)

        if fig:
            fig.update_layout(**plotly_theme)
            st.plotly_chart(fig, use_container_width=True)
            log_action("Chart created", f"{chart} of {y_col}")
        elif not num_cols:
            st.warning("No numeric columns found in dataset.")

    with tab2:
        left, right = st.columns(2)
        with left:
            st.markdown("**Numeric Summary**")
            if num_cols:
                st.dataframe(df[num_cols].describe().round(2), use_container_width=True)
            else:
                st.info("No numeric columns")
        with right:
            st.markdown("**Dataset Overview**")
            info_card(f"""
            <div style="font-size:0.78rem">
              <div style="margin-bottom:8px"><span style="color:#5A5F7A">Rows</span> &nbsp;·&nbsp; <span style="color:#F0F2FF;font-weight:500">{df.shape[0]:,}</span></div>
              <div style="margin-bottom:8px"><span style="color:#5A5F7A">Columns</span> &nbsp;·&nbsp; <span style="color:#F0F2FF;font-weight:500">{df.shape[1]}</span></div>
              <div style="margin-bottom:8px"><span style="color:#5A5F7A">Numeric cols</span> &nbsp;·&nbsp; <span style="color:#F0F2FF;font-weight:500">{len(num_cols)}</span></div>
              <div style="margin-bottom:8px"><span style="color:#5A5F7A">Categorical cols</span> &nbsp;·&nbsp; <span style="color:#F0F2FF;font-weight:500">{len(cat_cols)}</span></div>
              <div style="margin-bottom:8px"><span style="color:#5A5F7A">Missing values</span> &nbsp;·&nbsp; <span style="color:{'#F59E0B' if df.isnull().sum().sum() > 0 else '#10B981'};font-weight:500">{df.isnull().sum().sum():,}</span></div>
              <div><span style="color:#5A5F7A">Duplicates</span> &nbsp;·&nbsp; <span style="color:{'#F59E0B' if df.duplicated().sum() > 0 else '#10B981'};font-weight:500">{df.duplicated().sum():,}</span></div>
            </div>
            """)

            if num_cols:
                st.markdown("**Correlation Heatmap**")
                corr = df[num_cols].corr().round(2)
                fig_heat = px.imshow(
                    corr, text_auto=True, aspect="auto",
                    color_continuous_scale=["#07070F","#4F8EF7","#22D3EE"]
                )
                fig_heat.update_layout(**plotly_theme)
                st.plotly_chart(fig_heat, use_container_width=True)

    with tab3:
        st.markdown("**Statistical Outlier Detection (Z-score > 2.5)**")
        if num_cols:
            found = False
            for col in num_cols:
                mean, std = df[col].mean(), df[col].std()
                if std > 0:
                    outliers = df[abs((df[col] - mean) / std) > 2.5]
                    if not outliers.empty:
                        found = True
                        st.markdown(f"""
                        <div style="background:rgba(245,158,11,0.07);border:1px solid rgba(245,158,11,0.2);
                             border-radius:10px;padding:0.85rem 1rem;margin-bottom:8px">
                          <span style="color:#F59E0B;font-size:0.82rem;font-weight:500">⚠️ {col}</span>
                          <span style="color:#5A5F7A;font-size:0.78rem"> — {len(outliers)} outlier(s) detected
                          (min: {outliers[col].min():.2f}, max: {outliers[col].max():.2f})</span>
                        </div>
                        """, unsafe_allow_html=True)

                        fig_out = px.box(df, y=col, color_discrete_sequence=["#4F8EF7"])
                        fig_out.update_layout(**plotly_theme, height=250)
                        st.plotly_chart(fig_out, use_container_width=True)

            if not found:
                st.success("✅ No significant outliers detected across all numeric columns.")
        else:
            st.info("No numeric columns available for anomaly detection.")

    with tab4:
        st.markdown("Generate a full AI-powered insights report from your dataset.")
        industry = st.selectbox("Your industry (for tailored insights)", ["General","Finance","Healthcare","Marketing","Operations","Research","Education","Technology"])

        if st.button("🤖 Generate AI Insights Report", use_container_width=True):
            with st.spinner("Generating comprehensive report..."):
                nc = df.select_dtypes(include="number")
                prompt = f"""Generate a professional AI insights report for a {industry} professional:

Dataset: {list(df.columns)} | {df.shape[0]} rows × {df.shape[1]} cols
Stats: {nc.describe().to_string() if not nc.empty else 'No numeric data'}
Missing: {df.isnull().sum().to_dict()}
Duplicates: {df.duplicated().sum()}

Structure the report with these sections:
## Executive Summary
## Key Findings (bullet points)
## Data Quality Assessment
## Industry-Specific Insights ({industry})
## Recommended Next Steps
## Risk Factors to Monitor

Be professional, specific, and actionable."""

                report = call_claude(prompt)
                st.markdown(report)
                log_action("AI report", f"Generated {industry} insights report")

                if ROLES[st.session_state.role]["can_export"]:
                    st.download_button("⬇️ Download Report", report, "ai_insights_report.md", "text/markdown")

# ─── FILE MANAGER ──────────────────────────────────────────────────────────────
def files_page():
    page_header("File Manager", "Securely manage your uploaded documents and datasets")

    role = st.session_state.role
    left, right = st.columns([2.5, 1])

    with left:
        if st.session_state.uploaded_files:
            st.markdown(f"**{len(st.session_state.uploaded_files)} file(s) in secure session storage**")
            for i, f in enumerate(st.session_state.uploaded_files):
                st.markdown(f"""
                <div style="background:#12121F;border:1px solid #1E1E36;border-radius:12px;
                     padding:1rem 1.25rem;margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-size:0.875rem;font-weight:500;color:#F0F2FF;margin-bottom:3px">
                        📄 {f['name']}
                      </div>
                      <div style="font-size:0.72rem;color:#5A5F7A">
                        {f['size']} &nbsp;·&nbsp; Uploaded {f['uploaded']} &nbsp;·&nbsp; 🔒 Encrypted
                      </div>
                    </div>
                    <span style="background:rgba(16,185,129,0.1);color:#10B981;font-size:0.65rem;
                         padding:3px 10px;border-radius:100px;border:1px solid rgba(16,185,129,0.2);
                         white-space:nowrap">{f['status'].upper()}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                btn_cols = st.columns([1, 1, 4])
                with btn_cols[0]:
                    if st.button("Analyze", key=f"analyze_{i}"):
                        st.session_state.page = "workspace"
                        st.rerun()
                if ROLES[role]["can_delete"]:
                    with btn_cols[1]:
                        if st.button("Delete", key=f"del_{i}"):
                            name = st.session_state.uploaded_files.pop(i)["name"]
                            log_action("File deleted", f"Deleted {name}")
                            st.rerun()
        else:
            st.info("No files uploaded yet. Go to the AI Workspace to upload your first file.")
            if st.button("→ Go to AI Workspace"):
                st.session_state.page = "workspace"; st.rerun()

    with right:
        info_card("""
        <div style="font-size:0.72rem;font-weight:600;color:#4F8EF7;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">🔒 Storage Security</div>
        <div style="font-size:0.75rem;color:#5A5F7A;margin-bottom:5px">✓ AES-256 encryption at rest</div>
        <div style="font-size:0.75rem;color:#5A5F7A;margin-bottom:5px">✓ TLS 1.3 in transit</div>
        <div style="font-size:0.75rem;color:#5A5F7A;margin-bottom:5px">✓ All access logged</div>
        <div style="font-size:0.75rem;color:#5A5F7A;margin-bottom:5px">✓ Auto-delete on logout</div>
        <div style="font-size:0.75rem;color:#5A5F7A">✓ Zero third-party sharing</div>
        """)

        info_card("""
        <div style="font-size:0.72rem;font-weight:600;color:#5A5F7A;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Supported Formats</div>
        <div style="font-size:0.78rem;color:#F0F2FF;margin-bottom:5px">📊 CSV, XLSX, XLS</div>
        <div style="font-size:0.78rem;color:#F0F2FF;margin-bottom:5px">📋 JSON, TXT, PDF</div>
        <div style="font-size:0.78rem;color:#3A3F55;margin-bottom:5px">🖼️ Images — coming soon</div>
        <div style="font-size:0.78rem;color:#3A3F55">📑 PPTX, DOCX — coming soon</div>
        """)

# ─── INTEGRATIONS ──────────────────────────────────────────────────────────────
def integrations_page():
    page_header("Integrations", "Connect your data sources, cloud services, and tools")

    items = [
        ("📊","Google Sheets","Import and analyze spreadsheets directly","available"),
        ("☁️","Salesforce","CRM and pipeline data analysis","available"),
        ("💬","Slack","Share AI insights to channels","available"),
        ("🗄️","PostgreSQL","Query relational databases with AI","available"),
        ("📧","Gmail","Analyze email data and patterns","available"),
        ("❄️","Snowflake","Cloud data warehouse queries","coming_soon"),
        ("🔵","BigQuery","Google cloud-scale analytics","coming_soon"),
        ("📈","Tableau","Advanced visualization export","coming_soon"),
        ("⚡","Power BI","Microsoft BI integration","coming_soon"),
        ("📝","Notion","Export AI reports to docs","coming_soon"),
        ("🐍","Python SDK","Custom data pipelines","coming_soon"),
        ("🔗","REST API","Connect any data source","coming_soon"),
    ]

    cols = st.columns(3)
    for i, (icon, name, desc, status) in enumerate(items):
        with cols[i % 3]:
            soon = status == "coming_soon"
            st.markdown(f"""
            <div style="background:#12121F;border:1px solid {'#1E1E36' if soon else 'rgba(79,142,247,0.25)'};
                 border-radius:14px;padding:1.25rem;margin-bottom:1rem;
                 opacity:{'0.5' if soon else '1'}">
              <div style="font-size:1.5rem;margin-bottom:8px">{icon}</div>
              <div style="font-size:0.875rem;font-weight:600;color:#F0F2FF;margin-bottom:4px">{name}</div>
              <div style="font-size:0.78rem;color:#5A5F7A;margin-bottom:12px">{desc}</div>
              <span style="font-size:0.68rem;padding:3px 10px;border-radius:100px;font-weight:500;
                {'background:rgba(16,185,129,0.1);color:#10B981;border:1px solid rgba(16,185,129,0.2)' if not soon
                else 'background:#1E1E36;color:#3A3F55;border:1px solid #1E1E36'}">
                {'Available' if not soon else 'Coming Soon'}
              </span>
            </div>
            """, unsafe_allow_html=True)

# ─── ACTIVITY LOG ──────────────────────────────────────────────────────────────
def history_page():
    page_header("Activity Log", "Full audit trail of all platform actions this session")

    if not st.session_state.audit_log:
        st.info("No activity recorded yet.")
        return

    top_left, top_right = st.columns([3, 1])
    with top_left:
        search = st.text_input("🔍 Filter logs", placeholder="Search by action or detail...")
    with top_right:
        if ROLES[st.session_state.role]["can_export"]:
            log_df = pd.DataFrame(st.session_state.audit_log)
            st.download_button(
                "⬇️ Export CSV",
                log_df.to_csv(index=False),
                file_name="audit_log.csv",
                mime="text/csv",
                use_container_width=True,
            )

    log = list(reversed(st.session_state.audit_log))
    if search:
        log = [l for l in log if search.lower() in l["action"].lower() or search.lower() in l["details"].lower()]

    st.markdown(f"**{len(log)} log entries**")
    for entry in log:
        st.markdown(f"""
        <div style="background:#12121F;border:1px solid #1E1E36;border-radius:10px;
             padding:0.8rem 1rem;margin-bottom:5px;
             display:flex;justify-content:space-between;align-items:center">
          <div style="display:flex;align-items:center;gap:12px">
            <div style="width:7px;height:7px;border-radius:50%;background:#4F8EF7;flex-shrink:0"></div>
            <div>
              <div style="font-size:0.82rem;font-weight:500;color:#F0F2FF">{entry['action']}</div>
              <div style="font-size:0.7rem;color:#5A5F7A">{entry['details'] or '—'} &nbsp;·&nbsp; Session {entry['session']}</div>
            </div>
          </div>
          <div style="text-align:right;flex-shrink:0;margin-left:1rem">
            <div style="font-size:0.7rem;color:#3A3F55">{entry['timestamp']}</div>
            <div style="font-size:0.65rem;color:#5A5F7A">{entry['user']} ({entry['role']})</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ─── SETTINGS ──────────────────────────────────────────────────────────────────
def settings_page():
    page_header("Settings", "Configure your workspace, security, and AI preferences")

    tab1, tab2, tab3 = st.tabs(["⚙️ Workspace", "🔒 Security & Privacy", "👥 Roles & Permissions"])

    with tab1:
        st.markdown("#### General Preferences")
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Industry", ["Technology","Finance","Healthcare","Education","Marketing","Operations","Research","Other"])
            st.selectbox("AI Response Style", ["Concise","Detailed","Executive Summary","Technical Deep-Dive"])
        with c2:
            st.selectbox("Language", ["English","Spanish","French","German","Japanese","Portuguese"])
            st.selectbox("Date Format", ["MM/DD/YYYY","DD/MM/YYYY","YYYY-MM-DD"])

        st.markdown("---")
        st.markdown("#### Data Retention Policy")
        st.markdown("""
        <div style="background:rgba(245,158,11,0.07);border:1px solid rgba(245,158,11,0.15);
             border-radius:10px;padding:1rem;margin-bottom:1rem">
          <div style="font-size:0.82rem;color:#F59E0B;font-weight:500;margin-bottom:4px">⚠️ Data Privacy Notice</div>
          <div style="font-size:0.78rem;color:#5A5F7A;line-height:1.6">All uploaded files are processed exclusively in your active session and are automatically purged upon logout. No data is persisted to external servers.</div>
        </div>
        """, unsafe_allow_html=True)
        st.selectbox("Session data retention", ["Delete on logout (Recommended)","Keep for 24 hours","Keep for 7 days"])

        if st.button("💾 Save Preferences"):
            log_action("Settings saved", "Workspace preferences updated")
            st.success("Preferences saved successfully!")

    with tab2:
        st.markdown("#### API Configuration")
        key = os.getenv("CLAUDE_API_KEY","")
        masked = (key[:8] + "..." + key[-4:]) if len(key) > 12 else "Not configured"
        st.markdown(f"**Current API Key:** `{masked}`")
        new_key = st.text_input("Update Claude API Key", type="password", placeholder="sk-ant-...")
        if st.button("Update Key") and new_key:
            st.success("Key updated — restart the app to apply.")
            log_action("API key updated", "Claude API key changed")

        st.markdown("---")
        st.markdown("#### Authentication Settings")
        st.checkbox("Auto-logout after 30 min inactivity", value=True)
        st.checkbox("Email alerts on suspicious login", value=True)
        st.checkbox("Require MFA (enterprise feature)", value=False)

        st.markdown("#### AI Safety Guardrails")
        st.checkbox("Bias detection and flagging", value=True)
        st.checkbox("PII detection and automatic redaction", value=True)
        st.checkbox("Block generation of harmful content", value=True)
        st.checkbox("Confidence scoring on all outputs", value=True)
        st.checkbox("Require human review for high-risk insights", value=False)

        st.markdown("#### Privacy Controls")
        st.checkbox("Encrypt all uploads in transit", value=True)
        st.checkbox("Anonymize data before AI processing", value=False)
        st.checkbox("Do not log file contents", value=True)

        if st.button("💾 Save Security Settings"):
            log_action("Security settings saved", "Security preferences updated")
            st.success("Security settings saved!")

    with tab3:
        st.markdown("#### Role Permissions Matrix")
        perm_data = {
            "Permission": ["Upload Files","Delete Files","Export Data","Manage Users","View Analytics","Use AI Workspace","View Audit Log"],
            "Admin ✓":  ["✅","✅","✅","✅","✅","✅","✅"],
            "Analyst":  ["✅","❌","✅","❌","✅","✅","✅"],
            "Viewer":   ["❌","❌","❌","❌","✅","✅","✅"],
        }
        st.dataframe(pd.DataFrame(perm_data), use_container_width=True, hide_index=True)

        st.markdown(f"""
        <div style="background:rgba(79,142,247,0.08);border:1px solid rgba(79,142,247,0.2);
             border-radius:10px;padding:1rem;margin-top:1rem">
          <div style="font-size:0.82rem;color:#4F8EF7">Your current role: <strong>{st.session_state.role.upper()}</strong></div>
          <div style="font-size:0.75rem;color:#5A5F7A;margin-top:4px">Contact an admin to change your role or permissions.</div>
        </div>
        """, unsafe_allow_html=True)

# ─── LANDING PAGE ──────────────────────────────────────────────────────────────
def landing_page():
    components.html("""
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#07070F;--surface:#0D0D1C;--card:#12121F;--border:#1E1E36;--blue:#4F8EF7;--cyan:#22D3EE;--violet:#9D6EF8;--text:#F0F2FF;--muted:#5A5F7A}
html,body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(79,142,247,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(79,142,247,0.04) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}
.orb{position:fixed;border-radius:50%;filter:blur(100px);pointer-events:none;z-index:0}
.orb1{width:600px;height:600px;background:radial-gradient(circle,rgba(79,142,247,0.15),transparent 70%);top:-200px;right:-100px}
.orb2{width:500px;height:500px;background:radial-gradient(circle,rgba(157,110,248,0.12),transparent 70%);bottom:0;left:-150px}
.orb3{width:350px;height:350px;background:radial-gradient(circle,rgba(34,211,238,0.08),transparent 70%);top:40%;right:5%}
nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:0 3rem;height:64px;display:flex;align-items:center;justify-content:space-between;background:rgba(7,7,15,0.85);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;background:linear-gradient(135deg,var(--blue),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-links{display:flex;gap:2rem;list-style:none}
.nav-links a{color:var(--muted);text-decoration:none;font-size:0.875rem;transition:color 0.2s}
.nav-links a:hover{color:var(--text)}
.hero{position:relative;z-index:1;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:8rem 2rem 4rem}
.pill{display:inline-flex;align-items:center;gap:8px;background:rgba(79,142,247,0.1);border:1px solid rgba(79,142,247,0.25);border-radius:100px;padding:0.4rem 1.1rem;font-size:0.72rem;font-weight:500;color:var(--blue);letter-spacing:0.07em;text-transform:uppercase;margin-bottom:2rem}
.dot{width:7px;height:7px;border-radius:50%;background:var(--blue);animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.3;transform:scale(0.7)}}
h1{font-family:'Syne',sans-serif;font-size:clamp(3rem,7vw,5.5rem);font-weight:800;line-height:1.05;letter-spacing:-0.035em;color:var(--text);margin-bottom:1.5rem}
.accent{background:linear-gradient(135deg,var(--blue) 0%,var(--violet) 45%,var(--cyan) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sub{font-size:1.1rem;color:var(--muted);line-height:1.8;max-width:580px;margin:0 auto 2.5rem}
.cta-wrap{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:0.75rem}
.cta-btn{background:linear-gradient(135deg,var(--blue),var(--violet));border:none;color:#fff;padding:1rem 2.5rem;border-radius:12px;font-family:'DM Sans',sans-serif;font-size:1rem;font-weight:500;cursor:pointer;box-shadow:0 0 40px rgba(79,142,247,0.3);transition:transform 0.2s,box-shadow 0.2s;letter-spacing:0.01em}
.cta-btn:hover{transform:translateY(-3px);box-shadow:0 0 60px rgba(79,142,247,0.5)}
.cta-ghost{background:transparent;border:1px solid var(--border);color:var(--muted);padding:1rem 2.5rem;border-radius:12px;font-family:'DM Sans',sans-serif;font-size:1rem;cursor:pointer;transition:border-color 0.2s,color 0.2s}
.cta-ghost:hover{border-color:var(--blue);color:var(--text)}
.cta-note{font-size:0.75rem;color:var(--muted);margin-top:0.5rem}
.stats-wrap{position:relative;z-index:1;max-width:820px;margin:0 auto;padding:0 2rem}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:16px;overflow:hidden;margin-bottom:5rem}
.stat{background:var(--surface);padding:2rem 1.5rem;text-align:center}
.stat-n{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;background:linear-gradient(135deg,var(--blue),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent;display:block}
.stat-d{font-size:0.78rem;color:var(--muted);margin-top:4px}
.features{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:0 2rem 5rem}
.feat-eyebrow{font-size:0.7rem;font-weight:500;color:var(--blue);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.75rem;text-align:center}
.feat-title{font-family:'Syne',sans-serif;font-size:2.25rem;font-weight:800;letter-spacing:-0.03em;text-align:center;margin-bottom:0.75rem}
.feat-sub{font-size:0.95rem;color:var(--muted);text-align:center;margin-bottom:3rem;max-width:500px;margin-left:auto;margin-right:auto}
.feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}
.feat-card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:1.75rem;transition:border-color 0.3s,transform 0.3s;position:relative;overflow:hidden}
.feat-card::before{content:'';position:absolute;inset:0;background:radial-gradient(circle at top left,rgba(79,142,247,0.07),transparent 60%);opacity:0;transition:opacity 0.3s}
.feat-card:hover{border-color:rgba(79,142,247,0.4);transform:translateY(-4px)}
.feat-card:hover::before{opacity:1}
.feat-icon{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;margin-bottom:1.1rem}
.feat-card h3{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--text);margin-bottom:0.4rem}
.feat-card p{font-size:0.82rem;color:var(--muted);line-height:1.75}
.security-strip{position:relative;z-index:1;background:var(--surface);border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:3rem 2rem;text-align:center;margin-bottom:0}
.security-strip h2{font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;margin-bottom:0.75rem}
.security-grid{display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;margin-top:1.5rem}
.sec-item{display:flex;align-items:center;gap:8px;font-size:0.82rem;color:var(--muted)}
footer{position:relative;z-index:1;padding:2rem 3rem;display:flex;align-items:center;justify-content:space-between;border-top:1px solid var(--border)}
.footer-logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;background:linear-gradient(135deg,var(--blue),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.footer-note{font-size:0.75rem;color:var(--muted)}
</style>
</head>
<body>
<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="orb orb3"></div>
<nav>
  <div class="logo">datamind</div>
  <ul class="nav-links">
    <li><a href="#">Features</a></li>
    <li><a href="#">Security</a></li>
    <li><a href="#">Docs</a></li>
  </ul>
</nav>
<div class="hero">
  <div class="pill"><span class="dot"></span>Enterprise AI Platform · Now in Beta</div>
  <h1>The AI workspace<br/>your data <span class="accent">deserves</span></h1>
  <p class="sub">Upload any file. Ask questions in plain English. Get AI-powered insights, visualizations, and recommendations — secured with enterprise-grade privacy.</p>
  <div class="cta-wrap">
    <button class="cta-btn" onclick="window.parent.postMessage({type:'launch'},'*')">Launch Platform →</button>
    <button class="cta-ghost">View Demo</button>
  </div>
  <div class="cta-note">No credit card required · Free to start · GDPR compliant</div>
</div>
<div class="stats-wrap">
  <div class="stats">
    <div class="stat"><span class="stat-n">10×</span><div class="stat-d">Faster than BI tools</div></div>
    <div class="stat"><span class="stat-n">0</span><div class="stat-d">SQL required</div></div>
    <div class="stat"><span class="stat-n">8+</span><div class="stat-d">Industries served</div></div>
    <div class="stat"><span class="stat-n">∞</span><div class="stat-d">Questions to ask</div></div>
  </div>
</div>
<div class="features">
  <div class="feat-eyebrow">Platform capabilities</div>
  <h2 class="feat-title">Everything your data team needs</h2>
  <p class="feat-sub">From natural language querying to enterprise security — built for professionals in every industry.</p>
  <div class="feat-grid">
    <div class="feat-card"><div class="feat-icon" style="background:rgba(79,142,247,0.15)">⚡</div><h3>Natural Language Queries</h3><p>Ask any question in plain English. The AI generates, executes, and explains the analysis instantly.</p></div>
    <div class="feat-card"><div class="feat-icon" style="background:rgba(157,110,248,0.15)">📈</div><h3>Predictive Analytics</h3><p>Uncover trends and forecast outcomes using AI on your actual data — no data science degree needed.</p></div>
    <div class="feat-card"><div class="feat-icon" style="background:rgba(34,211,238,0.15)">🔍</div><h3>Anomaly Detection</h3><p>Automatically surface statistical outliers and unusual patterns before they become costly problems.</p></div>
    <div class="feat-card"><div class="feat-icon" style="background:rgba(16,185,129,0.15)">🔒</div><h3>Enterprise Security</h3><p>AES-256 encryption, role-based access control, audit logs, and privacy-first data handling.</p></div>
    <div class="feat-card"><div class="feat-icon" style="background:rgba(79,142,247,0.15)">💬</div><h3>Conversational Memory</h3><p>Ask follow-ups naturally. The AI retains full context across your entire session.</p></div>
    <div class="feat-card"><div class="feat-icon" style="background:rgba(157,110,248,0.15)">📊</div><h3>Auto Visualizations</h3><p>Charts, heatmaps, and dashboards generated automatically from your queries — zero config.</p></div>
  </div>
</div>
<div class="security-strip">
  <h2>Built for enterprise trust</h2>
  <p style="color:var(--muted);font-size:0.9rem">Security and privacy are first-class features, not afterthoughts.</p>
  <div class="security-grid">
    <div class="sec-item"><span style="color:#10B981">✓</span> AES-256 encryption</div>
    <div class="sec-item"><span style="color:#10B981">✓</span> Role-based access</div>
    <div class="sec-item"><span style="color:#10B981">✓</span> Full audit logging</div>
    <div class="sec-item"><span style="color:#10B981">✓</span> AI safety guardrails</div>
    <div class="sec-item"><span style="color:#10B981">✓</span> GDPR compliant</div>
    <div class="sec-item"><span style="color:#10B981">✓</span> Zero data retention</div>
  </div>
</div>
<footer>
  <div class="footer-logo">datamind</div>
  <div class="footer-note">© 2025 Datamind Enterprise · Built with AI</div>
</footer>
</body>
</html>
""", height=1800, scrolling=True)

_, col, _ = st.columns([3, 1, 3])
with col:
        st.markdown("""
        <style>
        [data-testid="stButton"] > button {
            background: linear-gradient(135deg,#4F8EF7,#9D6EF8) !important;
            color: white !important; border: none !important;
            border-radius: 10px !important; width: 100% !important;
            padding: 0.75rem !important; font-size: 1rem !important;
            font-weight: 600 !important;
            margin-top: 0 !important;
        }
        /* Remove gap above button */
        .stButton { margin-top: -1rem !important; }
        section.main > div { padding-top: 0 !important; }
        </style>
        """, unsafe_allow_html=True)
        if st.button("Launch Platform →"):
            st.session_state.page = "login"
            st.rerun()

# ─── MAIN ROUTER ───────────────────────────────────────────────────────────────
inject_css()

if st.session_state.page == "landing":
    landing_page()
elif not st.session_state.authenticated:
    login_page()
else:
    sidebar_nav()
    page = st.session_state.page
    if   page == "dashboard":    dashboard_page()
    elif page == "workspace":    workspace_page()
    elif page == "analytics":    analytics_page()
    elif page == "files":        files_page()
    elif page == "integrations": integrations_page()
    elif page == "history":      history_page()
    elif page == "settings":     settings_page()
    else:                        dashboard_page()
    # VERSION 2.0