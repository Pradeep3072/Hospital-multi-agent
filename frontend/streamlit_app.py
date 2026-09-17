import streamlit as st
import requests
import datetime
import json
import pandas as pd

# Page Config
st.set_page_config(
    page_title="HopeCare — Multi-Agent Hospital AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Light Green App Background */
    .stApp {
        background-color: #f0fdf4 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #e6f4ea !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(240, 253, 244, 0.85) !important;
    }
    
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #065f46 0%, #047857 50%, #059669 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 14px rgba(6, 95, 70, 0.18);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: white;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        font-size: 1.05rem;
        opacity: 0.95;
    }
    
    /* Emergency alert banner */
    .emergency-banner {
        background-color: #fee2e2;
        border-left: 6px solid #dc2626;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        color: #991b1b;
        margin-bottom: 1.5rem;
        font-weight: 500;
    }
    
    /* Agent Badges */
    .agent-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .badge-emergency { background-color: #fee2e2; color: #dc2626; border: 1px solid #f87171; }
    .badge-doctor { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
    .badge-appointment { background-color: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }
    .badge-patient { background-color: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
    .badge-hospital { background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .badge-medical { background-color: #ffedd5; color: #c2410c; border: 1px solid #fdba74; }

    /* Cards */
    .info-card {
        background: #ffffff;
        border: 1px solid #bbf7d0;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(5, 150, 105, 0.07);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000/api/v1"

DEFAULT_WELCOME_MESSAGE = {
    "role": "assistant",
    "agent": "Root Supervisor",
    "is_emergency": False,
    "content": (
        "👋 Hello! I am your **HopeCare Hospital AI Assistant**.\n\n"
        "I can help you:\n"
        "- 🏥 Check hospital timings, visiting hours, and accepted insurance\n"
        "- 🩺 Search doctors by department or specialty\n"
        "- 📅 Check real-time slots, book, reschedule, or cancel appointments\n"
        "- 👤 View your medical records and profile\n"
        "- 🚨 Provide urgent emergency guidance if you have acute symptoms\n\n"
        "How may I assist you today?"
    )
}

def load_persisted_chat_history(session_id: str = "streamlit-session") -> list:
    """
    Restores the active conversation from the backend memory/database.
    Allows continuing the conversation seamlessly across browser refreshes.
    """
    history = [DEFAULT_WELCOME_MESSAGE]
    try:
        r = requests.get(f"{API_BASE}/chat/history/{session_id}?limit=100", timeout=3)
        if r.status_code == 200:
            data = r.json()
            raw_turns = data.get("history", [])
            if raw_turns:
                for turn in raw_turns:
                    role = "user" if turn.get("role") == "user" else "assistant"
                    agent_name = turn.get("agent_name") or "Root Supervisor"
                    is_emerg = "emergency" in str(agent_name).lower()
                    history.append({
                        "role": role,
                        "agent": agent_name if role == "assistant" else None,
                        "is_emergency": is_emerg,
                        "content": turn.get("content", "")
                    })
    except Exception:
        pass
    return history

# Session State Initialization (Auto-restores on page refresh)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_persisted_chat_history("streamlit-session")

# Helper to fetch patients
def get_patients():
    try:
        r = requests.get(f"{API_BASE}/patients", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return [
        {"id": 1, "name": "John Doe", "policy": "BCBS-8839201"},
        {"id": 2, "name": "Sarah Connor", "policy": "AETNA-992102"},
        {"id": 3, "name": "Alice Johnson", "policy": "UHC-448102"}
    ]

# Default patient ID
current_patient_id = 1

# Sidebar
with st.sidebar:
    st.markdown("### 🏥 HopeCare Hospital")
    st.caption("Google ADK Multi-Agent AI System")
    st.markdown("---")
    navigation = st.radio(
        "Navigation",
        [
            "💬 AI Assistant",
            "📊 Dashboard",
            "📅 Appointments",
            "🩺 Doctors Directory",
            "🏥 Hospital Info & RAG",
            "👤 Patient Profile",
            "⚡ NeMo Profiler & Profiles"
        ]
    )

    # Memory Status Indicator
    try:
        mem_r = requests.get(f"{API_BASE}/chat/status", timeout=2)
        if mem_r.status_code == 200:
            mem_data = mem_r.json()
            if mem_data.get("redis_connected"):
                st.success("⚡ **Memory:** Redis Active")
            else:
                st.info("💾 **Memory:** Local Fast Store")
    except Exception:
        pass

    st.markdown("---")
    st.markdown(
        """
        <div class="emergency-banner" style="margin-top: 1rem; padding: 0.8rem;">
            <strong>🚨 Urgent Medical Emergency?</strong><br>
            Direct 911 / Emergency Line:<br>
            📞 <strong>(555) 0911</strong><br>
            Emergency Wing (24/7 Ground Floor)
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------------------------------------------
# 1. AI Assistant Page
# -------------------------------------------------------------
if navigation == "💬 AI Assistant":
    hcol1, hcol2 = st.columns([4, 1])
    with hcol1:
        st.markdown("""
        <div class="main-header">
            <h1>HopeCare Multi-Agent AI Assistant</h1>
            <p>Grounded orchestration across specialized sub-agents: Hospital Info, Doctor Discovery, Patient Records, and Appointments.</p>
        </div>
        """, unsafe_allow_html=True)
    with hcol2:
        st.write("")
        st.write("")
        if st.button("🗑️ Clear Chat", help="Clear conversation history from active memory"):
            session_id = "streamlit-session"
            try:
                requests.delete(f"{API_BASE}/chat/history/{session_id}", timeout=3)
            except Exception:
                pass
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "agent": "Root Supervisor",
                    "is_emergency": False,
                    "content": "Conversation cleared! How may I assist you today?"
                }
            ]
            st.rerun()

    # Quick prompts chips
    st.write("💡 **Suggested Inquiries:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🕒 ICU Visiting Hours?"):
            st.session_state.preset_prompt = "What are the ICU visiting hours?"
    with col2:
        if st.button("🩺 Find a Cardiologist"):
            st.session_state.preset_prompt = "Find a cardiologist at HopeCare and show details"
    with col3:
        if st.button("📅 Book Tomorrow Slot"):
            st.session_state.preset_prompt = "Show available slots for doctor 1 tomorrow"

    # Initialize interactive booking flow state
    if "booking_flow" not in st.session_state:
        st.session_state.booking_flow = None

    # Display chat conversation
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        with st.chat_message(msg["role"]):
            if msg.get("agent") and msg["role"] == "assistant":
                badge_class = "badge-hospital"
                ag = msg["agent"].lower()
                if "emergency" in ag:
                    badge_class = "badge-emergency"
                elif "doctor" in ag:
                    badge_class = "badge-doctor"
                elif "appointment" in ag:
                    badge_class = "badge-appointment"
                elif "patient" in ag:
                    badge_class = "badge-patient"
                elif "medical" in ag:
                    badge_class = "badge-medical"

                st.markdown(f'<span class="agent-badge {badge_class}">⚡ {msg["agent"]}</span>', unsafe_allow_html=True)
                
            st.markdown(msg["content"])

            # Interactive doctor selection cards if doctors were retrieved in this turn
            doctors_list = []
            has_auto_select = False
            if msg.get("tool_results"):
                tr = msg["tool_results"]
                if "auto_select_doctor" in tr and tr["auto_select_doctor"]:
                    has_auto_select = True
                if "doctors" in tr and isinstance(tr["doctors"], list) and tr["doctors"]:
                    doctors_list = tr["doctors"]
                elif "search" in tr and isinstance(tr["search"], dict) and "doctors" in tr["search"] and tr["search"]["doctors"]:
                    doctors_list = tr["search"]["doctors"]

            # Only show doctor cards list when not auto-selected to a specific doctor
            if doctors_list and not has_auto_select and msg["role"] == "assistant":
                st.markdown("---")
                st.markdown("##### 🩺 Available Physicians & Specialties — Select to View Calendar Slots:")
                for d in doctors_list:
                    with st.container(border=True):
                        d_col1, d_col2 = st.columns([3, 1])
                        with d_col1:
                            st.markdown(
                                f"**{d['name']}** — *{d.get('specialization', d.get('department', 'General'))}*  \n"
                                f"Experience: {d.get('experience_years', 5)} yrs | Consultation Fee: `${d.get('consultation_fee', 100):.0f}`"
                            )
                        with d_col2:
                            if st.button("📅 Select & Book", key=f"book_btn_{msg_idx}_{d['id']}"):
                                st.session_state.booking_flow = {
                                    "doctor_id": d["id"],
                                    "doctor_name": d["name"],
                                    "specialty": d.get("specialization", d.get("department", "General")),
                                    "fee": d.get("consultation_fee", 100)
                                }
                                st.rerun()
            
            if msg.get("tools_called"):
                tools = [t for t in msg["tools_called"] if t]
                if tools:
                    with st.expander("🔍 Agent Execution Details & Tools"):
                        st.write("**Tools Executed:**", ", ".join(f"`{t}`" for t in tools))
                        if msg.get("tool_results"):
                            st.json(msg["tool_results"])

    # Interactive Calendar & Slot Booking Widget
    if st.session_state.get("booking_flow"):
        bf = st.session_state.booking_flow
        with st.container(border=True):
            b_head1, b_head2 = st.columns([4, 1])
            with b_head1:
                st.markdown(f"### 🗓️ Book Consultation with **{bf['doctor_name']}** ({bf['specialty']})")
                st.caption(f"Consultation Fee: ${bf['fee']:.0f} | HopeCare In-Person Clinic")
            with b_head2:
                if st.button("✖ Close", key="close_booking_drawer"):
                    st.session_state.booking_flow = None
                    st.rerun()

            c_date, c_pt = st.columns(2)
            with c_date:
                min_date = datetime.date.today()
                selected_date = st.date_input(
                    "📅 Choose Date (Calendar):",
                    min_value=min_date,
                    value=min_date + datetime.timedelta(days=1),
                    key="chat_booking_date_picker"
                )
            with c_pt:
                patient_name_input = st.text_input(
                    "👤 Patient Full Name:",
                    value="",
                    placeholder="Type patient's full name (e.g. John Doe)",
                    key="chat_booking_patient_name_input"
                )

            # Fetch slots dynamically for chosen doctor & date
            date_str = selected_date.strftime("%Y-%m-%d")
            try:
                slots_res = requests.get(f"{API_BASE}/doctors/{bf['doctor_id']}/slots?date={date_str}", timeout=3).json()
                open_slots = slots_res.get("slots", [])
            except Exception:
                open_slots = []

            if open_slots:
                st.success(f"Found {len(open_slots)} open slots for {selected_date.strftime('%A, %B %d, %Y')}:")
                col_s, col_r = st.columns([2, 2])
                with col_s:
                    selected_slot = st.selectbox("⏰ Choose Available Time Slot:", options=open_slots, key="chat_slot_select")
                with col_r:
                    reason_text = st.text_input("📝 Reason for Visit:", value="Consultation", key="chat_reason_input")

                if st.button("✅ Confirm & Book Appointment", type="primary", key="chat_confirm_book_btn"):
                    clean_pname = patient_name_input.strip()
                    if not clean_pname:
                        st.error("⚠️ Please type the patient's full name before confirming.")
                    else:
                        book_payload = {
                            "patient_name": clean_pname,
                            "doctor_id": bf["doctor_id"],
                            "date": date_str,
                            "time": selected_slot,
                            "reason": reason_text
                        }
                        try:
                            b_resp = requests.post(f"{API_BASE}/appointments/book", json=book_payload, timeout=5)
                            if b_resp.status_code == 200:
                                b_data = b_resp.json()
                                st.balloons()
                                
                                # Add confirmed booking to chat history
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "agent": "Appointment Agent",
                                    "is_emergency": False,
                                    "tools_called": ["book_appointment"],
                                    "tool_results": {"booking": b_data},
                                    "content": (
                                        f"🎉 **Appointment Successfully Confirmed!**\n\n"
                                        f"- **Appointment ID**: `#{b_data.get('appointment_id')}`\n"
                                        f"- **Patient**: {clean_pname}\n"
                                        f"- **Doctor**: {bf['doctor_name']} ({bf['specialty']})\n"
                                        f"- **Date**: {date_str} ({selected_date.strftime('%A')})\n"
                                        f"- **Time**: {selected_slot}\n"
                                        f"- **Reason**: {reason_text}\n\n"
                                        f"✉️ A confirmation notice has been dispatched. You can view or manage it in the **Appointments** tab."
                                    )
                                })
                                st.session_state.booking_flow = None
                                st.rerun()
                            elif b_resp.status_code == 409:
                                st.error("⚠️ Conflict: That slot was just reserved by another patient. Please choose another time.")
                            else:
                                st.error(f"Booking error: {b_resp.text}")
                        except Exception as e:
                            st.error(f"Failed to submit booking: {e}")
            else:
                st.warning(f"No available consultation slots for {bf['doctor_name']} on {selected_date.strftime('%A, %b %d')}. Please select another weekday.")


    # Input handling
    user_input = st.chat_input("Ask a question, find a doctor, or manage your appointments...")
    if "preset_prompt" in st.session_state and st.session_state.preset_prompt:
        user_input = st.session_state.preset_prompt
        st.session_state.preset_prompt = None

    if user_input:
        # Display user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Call Backend Multi-Agent API
        with st.spinner("Root Supervisor routing to domain specialist..."):
            try:
                payload = {
                    "message": user_input,
                    "session_id": "streamlit-session"
                }
                r = requests.post(f"{API_BASE}/chat", json=payload, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "agent": data["delegated_agent"],
                        "is_emergency": data["is_emergency"],
                        "tools_called": data["tools_called"],
                        "tool_results": data["tool_results"],
                        "content": data["response"]
                    })

                    # If a specific doctor or specialty was requested, auto-open the booking table for that selection
                    auto_doc = data.get("tool_results", {}).get("auto_select_doctor")
                    if auto_doc:
                        st.session_state.booking_flow = {
                            "doctor_id": auto_doc["id"],
                            "doctor_name": auto_doc["name"],
                            "specialty": auto_doc.get("specialization", auto_doc.get("department", "General")),
                            "fee": auto_doc.get("consultation_fee", 100)
                        }
                    st.rerun()
                else:
                    st.error(f"Error from agent backend: {r.text}")
            except Exception as e:
                st.error(f"Failed to communicate with agent backend: {e}")

# -------------------------------------------------------------
# 2. Dashboard Page
# -------------------------------------------------------------
elif navigation == "📊 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>Hospital Healthcare Dashboard</h1>
        <p>Real-time overview of medical departments, active physicians, patient care, and appointments.</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch hospital statistics
    try:
        docs = requests.get(f"{API_BASE}/doctors", timeout=3).json()
        depts = requests.get(f"{API_BASE}/hospital/departments", timeout=3).json()
        services = requests.get(f"{API_BASE}/hospital/services", timeout=3).json()
        insurances = requests.get(f"{API_BASE}/hospital/insurances", timeout=3).json()
        appts = requests.get(f"{API_BASE}/patients/1/appointments", timeout=3).json()
    except Exception:
        docs, depts, services, insurances, appts = [], [], [], [], []

    # KPI Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Doctors On Duty", len(docs))
    with m2:
        st.metric("Clinical Departments", len(depts))
    with m3:
        st.metric("Diagnostic Services", len(services))
    with m4:
        st.metric("Insurance Networks", len(insurances))

    st.markdown("---")
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.subheader("📅 Recent & Upcoming Consultations")
        if appts:
            for a in appts[:3]:
                st.markdown(f"""
                <div class="info-card" style="border-left: 5px solid #0284c7;">
                    <h4 style="margin: 0 0 0.3rem 0;">{a['doctor_name']} — {a['specialization']}</h4>
                    <p style="margin: 0.2rem 0; font-size: 0.95rem;">🗓️ <strong>{a['appointment_date']}</strong> at ⏰ <strong>{a['appointment_time']}</strong></p>
                    <p style="margin: 0.2rem 0; color: #64748b; font-size: 0.9rem;">Reason: {a['reason_for_visit']}</p>
                    <span class="agent-badge badge-doctor">{a['status']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent appointments found. You can book an appointment anytime via the Appointments tab or AI Assistant.")

    with col2:
        st.subheader("⚡ Quick Hospital Guide")
        st.markdown("""
        <div class="info-card">
            <strong>🕒 Visiting Hours</strong>
            <p style="margin: 0.3rem 0; font-size: 0.9rem;">
            • General Wards: 10:00 AM – 8:00 PM Daily<br>
            • Intensive Care Unit (ICU): 12:00 PM – 2:00 PM, 5:00 PM – 7:00 PM
            </p>
        </div>
        <div class="info-card">
            <strong>🚨 Emergency & Trauma Center</strong>
            <p style="margin: 0.3rem 0; font-size: 0.9rem;">
            Open 24/7 Ground Floor, Emergency Wing.<br>
            Direct Emergency Line: <strong>(555) 0911</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# 3. Appointments Page
# -------------------------------------------------------------
elif navigation == "📅 Appointments":
    st.markdown("""
    <div class="main-header">
        <h1>Appointment Management</h1>
        <p>View your scheduled visits, check live slot availability, book with instant concurrency locks, or cancel.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_my, tab_book = st.tabs(["📋 My Appointments", "➕ Book New Appointment"])

    with tab_my:
        pts = get_patients()
        pt_options = {f"{p['name']} (ID: {p['id']})": p['id'] for p in pts}
        selected_pt_label = st.selectbox("View Appointments For Patient:", options=list(pt_options.keys()), key="appts_filter_pt")
        view_pid = pt_options[selected_pt_label]

        try:
            r_appts = requests.get(f"{API_BASE}/patients/{view_pid}/appointments", timeout=3)
            appts = r_appts.json() if r_appts.status_code == 200 and isinstance(r_appts.json(), list) else []
        except Exception:
            appts = []

        if appts:
            for a in appts:
                c1, c2, c3 = st.columns([3, 1, 1])
                status_color = "green" if a['status'] == "CONFIRMED" else ("red" if a['status'] == "CANCELLED" else "orange")
                with c1:
                    st.markdown(f"""
                    **Appointment #{a['id']}** with **{a['doctor_name']}** ({a['specialization']})  
                    🗓️ Date: `{a['appointment_date']}` | ⏰ Time: `{a['appointment_time']}`  
                    Status: <span style="color:{status_color}; font-weight:bold;">{a['status']}</span> | Reason: *{a['reason_for_visit']}*
                    """, unsafe_allow_html=True)
                with c2:
                    if a['status'] == "CONFIRMED":
                        if st.button(f"Cancel #{a['id']}", key=f"cancel_{a['id']}"):
                            resp = requests.post(f"{API_BASE}/appointments/{a['id']}/cancel", json={"patient_id": view_pid})
                            if resp.status_code == 200:
                                st.success("Appointment cancelled successfully!")
                                st.rerun()
                            else:
                                st.error(resp.text)
                st.markdown("---")
        else:
            st.info("No appointments found for this patient.")

    with tab_book:
        st.subheader("Book an In-Person Consultation")
        doctors = requests.get(f"{API_BASE}/doctors").json()
        doc_options = {f"{d['name']} — {d['specialization']} (${d['consultation_fee']:.0f})": d['id'] for d in doctors}
        
        col_d, col_date = st.columns(2)
        with col_d:
            selected_doc_label = st.selectbox("Select Doctor", options=list(doc_options.keys()))
            selected_doc_id = doc_options[selected_doc_label]
        
        with col_date:
            min_date = datetime.date.today()
            chosen_date = st.date_input("Consultation Date", min_value=min_date, value=min_date + datetime.timedelta(days=1))

        # Query live available slots
        date_str = chosen_date.strftime("%Y-%m-%d")
        slots_resp = requests.get(f"{API_BASE}/doctors/{selected_doc_id}/slots?date={date_str}").json()
        available_slots = slots_resp.get("slots", [])

        if available_slots:
            st.success(f"Found {len(available_slots)} available slots for {chosen_date.strftime('%A, %b %d')}:")
            c_time, c_patient = st.columns(2)
            with c_time:
                selected_time = st.selectbox("Choose Time Slot", options=available_slots)
            with c_patient:
                tab_patient_name = st.text_input("Patient Full Name", value="", placeholder="Type patient's full name", key="book_pt_name_input")

            reason = st.text_input("Reason for Visit", value="General Consultation")

            if st.button("Confirm & Reserve Slot", type="primary"):
                clean_name = tab_patient_name.strip()
                if not clean_name:
                    st.error("⚠️ Please type the patient's full name.")
                else:
                    book_payload = {
                        "patient_name": clean_name,
                        "doctor_id": selected_doc_id,
                        "date": date_str,
                        "time": selected_time,
                        "reason": reason
                    }
                    try:
                        res = requests.post(f"{API_BASE}/appointments/book", json=book_payload, timeout=5)
                        if res.status_code == 200:
                            st.balloons()
                            st.success(f"🎉 Appointment successfully booked for {date_str} at {selected_time}!")
                        elif res.status_code == 409:
                            st.error("⚠️ Conflict: That slot was just reserved by another patient. Please choose another slot.")
                        else:
                            st.error(f"Booking failed: {res.text}")
                    except Exception as e:
                        st.error(f"Error booking appointment: {str(e)}")
        else:
            st.warning("No available consultation slots for this doctor on the selected date (Doctor may be off or booked).")

# -------------------------------------------------------------
# 4. Doctors Directory Page
# -------------------------------------------------------------
elif navigation == "🩺 Doctors Directory":
    st.markdown("""
    <div class="main-header">
        <h1>Doctor Directory & Specialties</h1>
        <p>Explore board-certified physicians, clinical departments, and fees at HopeCare.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_dir, tab_add = st.tabs(["🩺 Browse Directory", "➕ Add New Doctor"])

    with tab_dir:
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_kw = st.text_input("Search by doctor name or condition", "")
        with col_filter:
            specialty_filter = st.selectbox("Filter Specialty", ["All Specialties", "Cardiologist", "Neurologist", "Pediatrician", "Orthopedic Surgeon", "Internal Medicine Physician"])

        spec_param = specialty_filter if specialty_filter != "All Specialties" else None
        params = {}
        if search_kw:
            params["query"] = search_kw
        if spec_param:
            params["specialty"] = spec_param

        docs = requests.get(f"{API_BASE}/doctors", params=params).json()

        st.write(f"Showing **{len(docs)}** doctors:")
        for d in docs:
            st.markdown(f"""
            <div class="info-card">
                <h3 style="margin: 0; color: #1e3a8a;">{d['name']}</h3>
                <p style="margin: 0.2rem 0; color: #0284c7; font-weight: 600;">{d['specialization']} • {d['department']}</p>
                <p style="margin: 0.5rem 0;">{d['bio']}</p>
                <p style="margin: 0; font-size: 0.9rem; color: #475569;">
                    🎓 Experience: <strong>{d['experience_years']} years</strong> | 💰 Consultation Fee: <strong>${d['consultation_fee']:.2f}</strong> | 📞 {d['phone']}
                </p>
            </div>
            """, unsafe_allow_html=True)

    with tab_add:
        st.subheader("➕ Register a New Doctor")
        st.caption("Provide the doctor's name and clinical department. The Doctor ID, license, and weekly consultation schedules are generated automatically.")

        # Fetch departments dynamically
        try:
            depts_resp = requests.get(f"{API_BASE}/hospital/departments", timeout=3).json()
            dept_names = [dept["name"] for dept in depts_resp if "name" in dept]
        except Exception:
            dept_names = ["Cardiology", "Neurology", "Pediatrics", "Orthopedics", "General Medicine", "Emergency Medicine"]

        if not dept_names:
            dept_names = ["Cardiology", "Neurology", "Pediatrics", "Orthopedics", "General Medicine", "Emergency Medicine"]

        with st.form("add_doctor_form", clear_on_submit=True):
            col_doc_name, col_doc_dept = st.columns(2)
            with col_doc_name:
                doc_name_input = st.text_input("Doctor Name *", placeholder="e.g. Dr. Marcus Vance")
            with col_doc_dept:
                doc_dept_input = st.selectbox("Department *", options=dept_names)

            submitted = st.form_submit_button("➕ Add Doctor", type="primary")

            if submitted:
                clean_name = doc_name_input.strip()
                if not clean_name:
                    st.error("⚠️ Please provide the doctor's name.")
                else:
                    payload = {
                        "name": clean_name,
                        "department_name": doc_dept_input
                    }
                    try:
                        resp = requests.post(f"{API_BASE}/doctors", json=payload, timeout=5)
                        if resp.status_code in [200, 201]:
                            created_doc = resp.json()
                            st.balloons()
                            st.success(f"🎉 Successfully registered **{created_doc['name']}** with auto-generated ID **#{created_doc['id']}** in **{created_doc['department']}**!")
                            st.info(f"📋 License Number: `{created_doc.get('license_number')}` | Auto-assigned weekly schedule: Mon–Fri, 09:00–17:00")
                        else:
                            st.error(f"Failed to add doctor: {resp.text}")
                    except Exception as e:
                        st.error(f"Error connecting to server: {str(e)}")

# -------------------------------------------------------------
# 5. Hospital Info & RAG Page
# -------------------------------------------------------------
elif navigation == "🏥 Hospital Info & RAG":
    st.markdown("""
    <div class="main-header">
        <h1>Hospital Information & Semantic Knowledge Base</h1>
        <p>Search hospital guidelines, policies, visiting hours, and accepted insurance networks via hybrid RAG.</p>
    </div>
    """, unsafe_allow_html=True)

    col_search_head, col_reindex = st.columns([3, 1])
    with col_search_head:
        st.subheader("🔍 Semantic Document Search")
    with col_reindex:
        st.write("")
        if st.button("🔄 Re-index Documents", help="Re-scan data/documents folder (including PDFs & Markdown)"):
            try:
                reindex_res = requests.post(f"{API_BASE}/hospital/reindex", timeout=10).json()
                st.success(f"Indexed **{reindex_res.get('total_chunks', 0)} chunks** across **{reindex_res.get('total_documents', 0)} documents**!")
            except Exception as e:
                st.error(f"Re-indexing failed: {e}")

    rag_query = st.text_input(
        "Ask any question about hospital guidelines, visiting rules, pricing, or locations:",
        "What is the price of basic MRI or CT scan?"
    )
    if st.button("Search Knowledge Base", type="primary"):
        try:
            search_res = requests.post(f"{API_BASE}/hospital/search", json={"query": rag_query, "top_k": 3}, timeout=5).json()
            if search_res and search_res.get("results_count", 0) > 0:
                sources_str = ", ".join(f"`{s}`" for s in search_res.get("sources", []))
                st.markdown(f"**Found {search_res.get('results_count')} relevant sections from:** {sources_str}")
                st.markdown(search_res.get("knowledge", "No knowledge found."))
            else:
                st.warning("No matching documentation found for this query.")
        except Exception as e:
            st.error(f"Search request failed: {e}")

    st.markdown("---")
    st.subheader("📋 Hospital Services & Diagnostics")
    services = requests.get(f"{API_BASE}/hospital/services").json()
    cols = st.columns(3)
    for i, s in enumerate(services):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="info-card">
                <h4 style="margin: 0;">{s['name']}</h4>
                <p style="color: #64748b; font-size: 0.85rem; margin: 0.2rem 0;">{s['department']}</p>
                <p style="font-size: 0.9rem;">{s['description']}</p>
                <strong>${s['cost']:.2f}</strong> • <small>{s['availability']}</small>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("🛡️ Accepted Insurance Networks")
    insurances = requests.get(f"{API_BASE}/hospital/insurances").json()
    for ins in insurances:
        st.write(f"- **{ins['name']}** ({ins['coverage_type']}) — Tier: `{ins['network_tier']}` | 📞 {ins['contact_phone']}")

# -------------------------------------------------------------
# 6. Patient Profile Page
# -------------------------------------------------------------
elif navigation == "👤 Patient Profile":
    st.markdown("""
    <div class="main-header">
        <h1>Patient Medical Records</h1>
        <p>Access confidential patient health profiles and clinical histories.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_records, tab_add = st.tabs(["📋 Patient Medical Records", "➕ Register New Patient"])

    with tab_records:
        patients_list = get_patients()
        if not isinstance(patients_list, list) or not patients_list:
            patients_list = []
        patient_opts = {f"{p['name']} (ID: {p['id']})": p['id'] for p in patients_list if isinstance(p, dict) and 'name' in p and 'id' in p}
        
        if patient_opts:
            sel_patient_label = st.selectbox("Select Patient to View Records:", list(patient_opts.keys()))
            prof_patient_id = patient_opts[sel_patient_label]

            try:
                prof_resp = requests.get(f"{API_BASE}/patients/{prof_patient_id}", timeout=3)
                prof = prof_resp.json() if prof_resp.status_code == 200 and isinstance(prof_resp.json(), dict) else {}
            except Exception:
                prof = {}

            try:
                records_resp = requests.get(f"{API_BASE}/patients/{prof_patient_id}/records", timeout=3)
                records = records_resp.json() if records_resp.status_code == 200 and isinstance(records_resp.json(), list) else []
            except Exception:
                records = []

            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader("Personal & Insurance Details")
                st.write(f"**Full Name:** {prof.get('full_name', 'N/A')}")
                st.write(f"**Date of Birth:** {prof.get('date_of_birth', 'N/A')}")
                st.write(f"**Gender:** {prof.get('gender', 'N/A')}")
                st.write(f"**Blood Group:** {prof.get('blood_group', 'N/A')}")
                st.write(f"**Primary Email:** {prof.get('email', 'N/A')}")
                st.write(f"**Phone Number:** {prof.get('phone', 'N/A')}")
                st.write(f"**Residential Address:** {prof.get('address', 'N/A')}")
                st.write(f"**Insurance Policy:** `{prof.get('insurance_policy_number', 'N/A')}`")
                st.write(f"**Emergency Contact:** {prof.get('emergency_contact_name', 'N/A')} ({prof.get('emergency_contact_phone', 'N/A')})")

            with c2:
                st.subheader("Clinical History & Diagnoses")
                if records:
                    for r in records:
                        st.markdown(f"""
                        <div class="info-card">
                            <strong>Diagnosis: {r.get('diagnosis', 'General')}</strong><br>
                            <small>Attending Physician: {r.get('doctor_name', 'Physician')} | Date: {r.get('record_date', 'N/A')}</small>
                            <p style="margin-top: 0.5rem; font-size: 0.9rem;">{r.get('treatment_summary', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No clinical history recorded for this patient.")
        else:
            st.info("No registered patients found. Please use the '➕ Register New Patient' tab to add your first patient profile.")

    with tab_add:
        st.subheader("➕ Register a New Patient")
        st.caption("Provide patient details. The Patient ID and unique insurance policy number are generated automatically.")

        with st.form("add_patient_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                p_name = st.text_input("Patient Full Name *", placeholder="e.g. Emma Watson")
            with f_col2:
                p_gender = st.selectbox("Gender *", ["Female", "Male", "Other"])

            f_col3, f_col4 = st.columns(2)
            with f_col3:
                p_dob = st.date_input(
                    "Date of Birth",
                    value=datetime.date(1995, 5, 15),
                    min_value=datetime.date(1920, 1, 1),
                    max_value=datetime.date.today()
                )
            with f_col4:
                p_blood = st.selectbox("Blood Group", ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-", "Unknown"])

            f_col5, f_col6 = st.columns(2)
            with f_col5:
                p_phone = st.text_input("Contact Phone", placeholder="e.g. +1-555-0188")
            with f_col6:
                p_email = st.text_input("Email Address (optional)", placeholder="Leave blank to auto-generate")

            p_address = st.text_input("Residential Address (optional)", placeholder="e.g. 742 Evergreen Terrace")

            f_col7, f_col8 = st.columns(2)
            with f_col7:
                p_em_name = st.text_input("Emergency Contact Name", placeholder="e.g. Robert Watson")
            with f_col8:
                p_em_phone = st.text_input("Emergency Contact Phone", placeholder="e.g. +1-555-0911")

            p_policy = st.text_input("Insurance Policy Number (optional)", placeholder="Leave blank to auto-generate")

            p_submitted = st.form_submit_button("➕ Register Patient", type="primary")

            if p_submitted:
                clean_pname = p_name.strip()
                if not clean_pname:
                    st.error("⚠️ Please provide the patient's full name.")
                else:
                    patient_payload = {
                        "name": clean_pname,
                        "gender": p_gender,
                        "date_of_birth": p_dob.strftime("%Y-%m-%d"),
                        "blood_group": p_blood,
                        "phone_number": p_phone.strip() if p_phone else None,
                        "email": p_email.strip() if p_email else None,
                        "address": p_address.strip() if p_address else None,
                        "emergency_contact_name": p_em_name.strip() if p_em_name else None,
                        "emergency_contact_phone": p_em_phone.strip() if p_em_phone else None,
                        "insurance_policy_number": p_policy.strip() if p_policy else None
                    }
                    try:
                        p_resp = requests.post(f"{API_BASE}/patients", json=patient_payload, timeout=5)
                        if p_resp.status_code in [200, 201]:
                            created_pt = p_resp.json()
                            st.balloons()
                            st.success(f"🎉 Successfully registered **{created_pt['name']}** with auto-generated Patient ID **#{created_pt['id']}**!")
                            st.info(f"🛡️ Insurance Policy: `{created_pt.get('policy')}` | 🩸 Blood Group: `{created_pt.get('blood_group')}` | 📅 DOB: `{created_pt.get('date_of_birth')}`")
                        else:
                            st.error(f"Registration failed: {p_resp.text}")
                    except Exception as e:
                        st.error(f"Error connecting to server: {str(e)}")

# -------------------------------------------------------------
# 7. NeMo Profiler & Agent Profiles Page
# -------------------------------------------------------------
elif navigation == "⚡ NeMo Profiler & Profiles":
    st.markdown("""
    <div class="main-header">
        <h1>NVIDIA NeMo Agent Profile & Performance Toolkit</h1>
        <p>Enterprise multi-agent governance: Declarative YAML contracts, clinical ethos, and real-time execution telemetry.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_telemetry, tab_nat, tab_profiles, tab_ethos = st.tabs([
        "📊 Real-Time Profiler Telemetry",
        "⚡ NVIDIA NAT Engine & Benchmark",
        "🛡️ Declarative Agent Profiles",
        "📜 Clinical AI Ethos Contract"
    ])

    with tab_telemetry:

        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.subheader("⚡ Live Multi-Agent Execution Telemetry")
        with col_t2:
            st.write("")
            if st.button("🔄 Refresh Telemetry"):
                st.rerun()

        try:
            metrics_resp = requests.get(f"{API_BASE}/profiler/metrics", timeout=3)
            metrics = metrics_resp.json() if metrics_resp.status_code == 200 else {}
        except Exception:
            metrics = {}

        # KPI Metrics Cards
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("Total Profiler Traces", metrics.get("total_requests", 0))
        with kpi2:
            st.metric("Average Latency", f"{metrics.get('avg_latency_ms', 0.0)} ms")
        with kpi3:
            st.metric("P95 Latency", f"{metrics.get('p95_latency_ms', 0.0)} ms")
        with kpi4:
            st.metric("Clinical Safety Pass Rate", f"{metrics.get('compliance_rate', 100.0)}%")

        st.markdown("---")

        # Visual Breakdown Columns
        col_graph1, col_graph2 = st.columns(2)
        with col_graph1:
            st.markdown("### 🤖 Invocations by Sub-Agent")
            agent_dist = metrics.get("agent_distribution", {})
            if agent_dist:
                dist_df = pd.DataFrame(list(agent_dist.items()), columns=["Agent", "Requests"])
                st.bar_chart(dist_df.set_index("Agent"))
            else:
                st.info("No workflow traces recorded yet. Chat with the AI Assistant to generate telemetry!")

        with col_graph2:
            st.markdown("### ⏱️ Average Latency by Agent (ms)")
            agent_lats = metrics.get("agent_avg_latencies", {})
            if agent_lats:
                lat_df = pd.DataFrame(list(agent_lats.items()), columns=["Agent", "Avg Latency (ms)"])
                st.bar_chart(lat_df.set_index("Agent"))
            else:
                st.info("No agent latency data available yet.")

        # Tool Performance Table
        st.markdown("### 🛠️ Tool Execution Metrics & Invocations")
        tool_metrics = metrics.get("tool_metrics", {})
        if tool_metrics:
            tool_rows = []
            for tname, tdata in tool_metrics.items():
                tool_rows.append({
                    "Tool Name": tname,
                    "Invocations": tdata.get("invocations", 0),
                    "Avg Duration (ms)": f"{tdata.get('avg_duration_ms', 0.0)} ms",
                    "Error Rate": f"{tdata.get('error_rate', 0.0) * 100:.1f}%"
                })
            st.dataframe(pd.DataFrame(tool_rows), use_container_width=True)
        else:
            st.info("No tool invocations recorded yet.")

        # Recent Traces Waterfall
        st.markdown("---")
        st.markdown("### 🌊 Recent Workflow Waterfall Traces")
        try:
            traces_resp = requests.get(f"{API_BASE}/profiler/traces?limit=10", timeout=3)
            traces = traces_resp.json().get("traces", []) if traces_resp.status_code == 200 else []
        except Exception:
            traces = []

        if traces:
            for tr in traces:
                with st.expander(f"📍 Trace `{tr['trace_id']}` — {tr['delegated_agent']} ({tr['total_latency_ms']} ms) — \"{tr['user_query'][:50]}...\""):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Route:** `{tr['route']}`")
                    c2.write(f"**Delegated Agent:** `{tr['delegated_agent']}`")
                    c3.write(f"**Total Duration:** `{tr['total_latency_ms']} ms`")

                    c4, c5, c6 = st.columns(3)
                    c4.write(f"**Routing Latency:** `{tr.get('routing_latency_ms', 0.0)} ms`")
                    c5.write(f"**Agent Exec Latency:** `{tr.get('agent_latency_ms', 0.0)} ms`")
                    c6.write(f"**Tools Latency:** `{tr.get('tools_latency_ms', 0.0)} ms`")

                    st.markdown("**Execution Step Events (Waterfall):**")
                    events = tr.get("events", [])
                    if events:
                        for ev in events:
                            st.caption(f"⏱️ **{ev['duration_ms']} ms** — `{ev['name']}` ({ev['category']}) — status: `{ev['status']}`")
                    else:
                        st.caption("No sub-events recorded.")
        else:
            st.info("No traces logged yet. Send a message in the 💬 AI Assistant view to populate traces!")

    with tab_nat:
        st.subheader("⚡ NVIDIA NeMo Agent Toolkit (nvidia-nat) Engine")
        st.caption("Official NVIDIA NAT integration: ProfilerConfig instrumentation, prediction trie lookups, and latency bottleneck decomposition.")

        try:
            nat_resp = requests.get(f"{API_BASE}/profiler/nat/summary", timeout=3)
            nat_data = nat_resp.json() if nat_resp.status_code == 200 else {}
        except Exception:
            nat_data = {}

        # 1. Official Package Status
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            st.metric("NVIDIA NAT Package", "Active (v1.9.0)" if nat_data.get("is_available") else "Inactive")
        with col_n2:
            st.metric("Prediction Trie", f"{nat_data.get('prediction_trie', {}).get('total_traces_indexed', 0)} Traces")
        with col_n3:
            b_info = nat_data.get("bottleneck_analysis", {})
            st.metric("Primary Bottleneck", b_info.get("primary_bottleneck", "None").upper())

        st.markdown("---")

        # 2. Interactive On-Demand Profiling Benchmark
        st.markdown("### 🧪 On-Demand Workflow Benchmark")
        st.caption("Execute any clinical or operational workflow with real-time NVIDIA NAT trace hooks and bottleneck attribution.")

        col_bench_in, col_bench_btn = st.columns([4, 1])
        with col_bench_in:
            bench_query = st.text_input(
                "Benchmark Query:",
                value="I need to see a cardiologist for heart palpitations",
                key="bench_query_input"
            )
        with col_bench_btn:
            st.write("")
            run_bench = st.button("⚡ Profile Workflow", type="primary", key="btn_run_bench")

        if run_bench and bench_query:
            with st.spinner("Profiling multi-agent execution with NVIDIA NAT..."):
                try:
                    bench_res = requests.post(
                        f"{API_BASE}/profiler/nat/benchmark",
                        json={"query": bench_query, "patient_id": 1},
                        timeout=15
                    ).json()

                    if bench_res.get("status") == "success":
                        st.success("✅ Workflow Profiled Successfully!")
                        b_trace = bench_res.get("trace", {})
                        
                        # Benchmark Results Cards
                        bc1, bc2, bc3, bc4 = st.columns(4)
                        with bc1:
                            st.metric("Total Latency", f"{b_trace.get('total_latency_ms', 0)} ms")
                        with bc2:
                            st.metric("Route", b_trace.get("route", "N/A"))
                        with bc3:
                            st.metric("Delegated Agent", b_trace.get("delegated_agent", "N/A"))
                        with bc4:
                            st.metric("Est. Tokens", b_trace.get("tokens", {}).get("total", 0))

                        # Response Preview
                        with st.expander("💬 Agent Response Preview", expanded=True):
                            st.markdown(bench_res.get("response", ""))

                        # Waterfall Table
                        st.markdown("#### ⏱️ Trace Waterfall Timeline")
                        b_events = b_trace.get("events", [])
                        if b_events:
                            ev_rows = []
                            for ev in b_events:
                                ev_rows.append({
                                    "Step": ev.get("name"),
                                    "Category": ev.get("category"),
                                    "Duration (ms)": f"{ev.get('duration_ms')} ms",
                                    "Status": ev.get("status")
                                })
                            st.dataframe(pd.DataFrame(ev_rows), use_container_width=True)
                    else:
                        st.error(f"Benchmark failed: {bench_res}")
                except Exception as e:
                    st.error(f"Benchmark request error: {e}")

        st.markdown("---")

        # 3. NVIDIA NAT Bottleneck Stack
        col_bot1, col_bot2 = st.columns(2)
        with col_bot1:
            st.markdown("### 🔬 Latency Stack Breakdown")
            breakdown = b_info.get("breakdown", {})
            if breakdown:
                b_df_rows = []
                for cat, dat in breakdown.items():
                    b_df_rows.append({
                        "Category": cat.replace("_", " ").title(),
                        "Latency (ms)": dat.get("total_ms", 0.0),
                        "Share (%)": f"{dat.get('percentage', 0.0)}%"
                    })
                st.dataframe(pd.DataFrame(b_df_rows), use_container_width=True)
            else:
                st.info("Run a benchmark to populate bottleneck breakdown.")

        with col_bot2:
            st.markdown("### 🌲 Prediction Trie & Config")
            trie_res = nat_data.get("prediction_trie", {})
            st.write(f"**Total Workflow Paths:** `{trie_res.get('total_traces_indexed', 0)}`")
            st.write(f"**Branch Children Nodes:** `{trie_res.get('total_children', 0)}`")
            
            with st.expander("🛠️ Active NVIDIA ProfilerConfig (JSON)"):
                st.json(nat_data.get("config", {}))

            with st.expander("🌲 Serialized Prediction Trie (Root)"):
                st.json(trie_res.get("root", {}))

    with tab_profiles:
        st.subheader("🛡️ Declarative NeMo Agent Profiles")
        st.caption("Inspect behavioral contracts, permitted tool bindings, and RBAC permissions for each autonomous agent.")

        try:
            prof_list_resp = requests.get(f"{API_BASE}/profiles", timeout=3)
            all_profiles = prof_list_resp.json().get("profiles", []) if prof_list_resp.status_code == 200 else []
        except Exception:
            all_profiles = []

        if all_profiles:
            prof_dict = {p["display_name"]: p for p in all_profiles}
            selected_prof_name = st.selectbox("Select Agent Profile to Inspect:", list(prof_dict.keys()))
            p_data = prof_dict[selected_prof_name]

            p_col1, p_col2 = st.columns([2, 1])
            with p_col1:
                st.markdown(f"### {p_data['display_name']} (`{p_data['name']}`)")
                st.markdown(f"**Role:** {p_data['role']}")
                st.markdown(f"**Description:** {p_data['description']}")
                st.markdown(f"**Ethos Anchor:** `{p_data['ethos_reference']}` | **Max Timeout:** `{p_data['max_execution_timeout_ms']} ms`")
            with p_col2:
                st.markdown(f"**Version:** `{p_data['version']}`")
                st.markdown(f"**Priority:** `{p_data.get('metadata', {}).get('priority', 'Default')}`")

            st.markdown("#### 🛠️ Allowed Tools")
            tools_list = p_data.get("allowed_tools", [])
            st.write(", ".join(f"`{t}`" for t in tools_list) if tools_list else "None (Pure Orchestration)")

            st.markdown("#### 📜 Behavioral Contract & Principles")
            contract = p_data.get("behavioral_contract", {})
            for pr in contract.get("principles", []):
                st.markdown(f"- ✅ {pr}")
            for pa in contract.get("prohibited_actions", []):
                st.markdown(f"- 🚫 **Prohibited:** {pa}")

            st.markdown("#### 📄 Raw NeMo Profile Specification (YAML)")
            st.code(p_data.get("raw_yaml", "# No YAML available"), language="yaml")
        else:
            st.warning("Could not connect to profiles API endpoint.")

    with tab_ethos:
        st.subheader("📜 HopeCare Clinical AI Ethos")
        try:
            ethos_resp = requests.get(f"{API_BASE}/profiles/ethos", timeout=3)
            ethos_text = ethos_resp.json().get("content", "") if ethos_resp.status_code == 200 else ""
        except Exception:
            ethos_text = ""
        st.markdown(ethos_text if ethos_text else "Failed to load clinical ethos contract.")


