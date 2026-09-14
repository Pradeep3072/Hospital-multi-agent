import streamlit as st
import requests
import datetime
import json

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
    
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #0f4c81 0%, #1e3a8a 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(15, 76, 129, 0.15);
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
        opacity: 0.9;
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
        border: 1px solid #e2e8f0;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000/api/v1"

# Session State Initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "agent": "Root Supervisor",
            "is_emergency": False,
            "content": (
                "👋 Hello! I am your **HopeCare Hospital AI Assistant**.\n\n"
                "I can help you:\n"
                "- 🏥 Check hospital timings, visiting hours, and accepted insurance\n"
                "- 🩺 Search doctors by department or specialty\n"
                "- 📅 Check real-time slots, book, reschedule, or cancel appointments\n"
                "- 👤 View your medical records, prescriptions, and profile\n"
                "- 🚨 Provide urgent emergency guidance if you have acute symptoms\n\n"
                "How may I assist you today?"
            )
        }
    ]

# Fetch available patients for context switcher
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

patients = get_patients()
patient_map = {f"{p['name']} (ID: {p['id']})": p['id'] for p in patients}

# Sidebar
with st.sidebar:
    st.markdown("### 🏥 HopeCare Hospital")
    st.caption("Google ADK Multi-Agent System")
    
    # Active Patient Selector (Replaces Login/Signup)
    selected_label = st.selectbox(
        "Active Patient Context:",
        options=list(patient_map.keys()),
        index=0,
        help="Select which patient profile to simulate without needing a login"
    )
    current_patient_id = patient_map[selected_label]
    st.session_state.current_patient_id = current_patient_id
    
    st.markdown("---")
    navigation = st.radio(
        "Navigation",
        [
            "💬 AI Assistant",
            "📊 Dashboard",
            "📅 Appointments",
            "🩺 Doctors Directory",
            "🏥 Hospital Info & RAG",
            "👤 Patient Profile"
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
            session_id = f"streamlit-session-{current_patient_id}"
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
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🕒 ICU Visiting Hours?"):
            st.session_state.preset_prompt = "What are the ICU visiting hours?"
    with col2:
        if st.button("🩺 Find a Cardiologist"):
            st.session_state.preset_prompt = "Find a cardiologist at HopeCare and show details"
    with col3:
        if st.button("💊 My Active Prescriptions"):
            st.session_state.preset_prompt = "Show my active prescriptions"
    with col4:
        if st.button("📅 Book Tomorrow Slot"):
            st.session_state.preset_prompt = "Show available slots for doctor 1 tomorrow"

    # Display chat conversation
    for msg in st.session_state.chat_history:
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
            
            if msg.get("tools_called"):
                tools = [t for t in msg["tools_called"] if t]
                if tools:
                    with st.expander("🔍 Agent Execution Details & Tools"):
                        st.write("**Tools Executed:**", ", ".join(f"`{t}`" for t in tools))
                        if msg.get("tool_results"):
                            st.json(msg["tool_results"])

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
                    "patient_id": current_patient_id,
                    "session_id": f"streamlit-session-{current_patient_id}"
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
                    st.rerun()
                else:
                    st.error(f"Error from agent backend: {r.text}")
            except Exception as e:
                st.error(f"Failed to communicate with agent backend: {e}")

# -------------------------------------------------------------
# 2. Dashboard Page
# -------------------------------------------------------------
elif navigation == "📊 Dashboard":
    st.markdown(f"""
    <div class="main-header">
        <h1>Patient Health Dashboard</h1>
        <p>Welcome back! Active patient context: <strong>{selected_label}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.5, 1, 1])

    # Fetch patient profile and appointments
    try:
        appts_resp = requests.get(f"{API_BASE}/patients/{current_patient_id}/appointments", timeout=5).json()
        profile_resp = requests.get(f"{API_BASE}/patients/{current_patient_id}", timeout=5).json()
        rxs_resp = requests.get(f"{API_BASE}/patients/{current_patient_id}/prescriptions", timeout=5).json()
    except Exception as e:
        appts_resp = []
        profile_resp = {}
        rxs_resp = []

    with col1:
        st.subheader("📅 Next Upcoming Appointment")
        upcoming = [a for a in appts_resp if a.get("status") == "CONFIRMED"]
        if upcoming:
            next_a = upcoming[0]
            st.markdown(f"""
            <div class="info-card" style="border-left: 5px solid #0284c7;">
                <h3 style="margin: 0 0 0.5rem 0;">{next_a['doctor_name']}</h3>
                <p><strong>Department:</strong> {next_a['department']} ({next_a['specialization']})</p>
                <p><strong>Date & Time:</strong> 🗓️ {next_a['appointment_date']} at ⏰ {next_a['appointment_time']}</p>
                <p><strong>Reason:</strong> {next_a['reason_for_visit']}</p>
                <span class="agent-badge badge-doctor">{next_a['status']}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No upcoming appointments scheduled. Use the Appointments tab or AI Assistant to book.")

        st.subheader("💊 Current Prescriptions")
        if rxs_resp:
            for rx in rxs_resp:
                st.markdown(f"""
                <div class="info-card">
                    <strong>{rx['medication_name']}</strong> ({rx['dosage']})<br>
                    <small>Frequency: {rx['frequency']} • Prescribed by: {rx['prescribed_by']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No active medications.")

    with col2:
        st.subheader("👤 Profile Summary")
        if profile_resp:
            st.write(f"**Name:** {profile_resp.get('full_name')}")
            st.write(f"**Blood Group:** `{profile_resp.get('blood_group')}`")
            st.write(f"**DOB:** {profile_resp.get('date_of_birth')}")
            st.write(f"**Emergency Contact:** {profile_resp.get('emergency_contact_name')} ({profile_resp.get('emergency_contact_phone')})")
            st.write(f"**Insurance Policy:** `{profile_resp.get('insurance_policy_number')}`")

    with col3:
        st.subheader("⚡ Quick Actions")
        if st.button("🗓️ Book New Appointment", use_container_width=True):
            st.info("Head to the **Appointments** tab or ask the AI Assistant!")
        if st.button("🔍 Search Specialist Doctors", use_container_width=True):
            st.info("Explore the **Doctors Directory** tab.")
        if st.button("🏥 Check Visiting Hours", use_container_width=True):
            st.info("General Wards: 10:00 AM - 8:00 PM | ICU: 12-2 PM, 5-7 PM")

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
        try:
            appts = requests.get(f"{API_BASE}/patients/{current_patient_id}/appointments").json()
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
                            resp = requests.post(f"{API_BASE}/appointments/{a['id']}/cancel", json={"patient_id": current_patient_id})
                            if resp.status_code == 200:
                                st.success("Appointment cancelled successfully!")
                                st.rerun()
                            else:
                                st.error(resp.text)
                st.markdown("---")
        else:
            st.info("You have no appointments on record.")

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
            selected_time = st.selectbox("Choose Time Slot", options=available_slots)
            reason = st.text_input("Reason for Visit", value="General Consultation")

            if st.button("Confirm & Reserve Slot", type="primary"):
                book_payload = {
                    "patient_id": current_patient_id,
                    "doctor_id": selected_doc_id,
                    "date": date_str,
                    "time": selected_time,
                    "reason": reason
                }
                res = requests.post(f"{API_BASE}/appointments/book", json=book_payload)
                if res.status_code == 200:
                    st.balloons()
                    st.success(f"🎉 Appointment successfully booked for {date_str} at {selected_time}!")
                elif res.status_code == 409:
                    st.error("⚠️ Conflict: That slot was just reserved by another patient. Please choose another slot.")
                else:
                    st.error(f"Booking failed: {res.text}")
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

    st.subheader("🔍 Semantic Document Search")
    rag_query = st.text_input("Ask any question about hospital guidelines, visiting rules, or billing:", "What is the policy for pediatric ward visitors?")
    if st.button("Search Knowledge Base"):
        search_res = requests.post(f"{API_BASE}/hospital/search", json={"query": rag_query, "top_k": 3}).json()
        st.write(f"**Found {search_res.get('results_count')} relevant sections from:** `{', '.join(search_res.get('sources', []))}`")
        st.markdown(search_res.get("knowledge", "No knowledge found."))

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
    st.markdown(f"""
    <div class="main-header">
        <h1>Patient Medical Profile</h1>
        <p>Authenticated Records for <strong>{selected_label}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    prof = requests.get(f"{API_BASE}/patients/{current_patient_id}").json()
    records = requests.get(f"{API_BASE}/patients/{current_patient_id}/records").json()
    prescriptions = requests.get(f"{API_BASE}/patients/{current_patient_id}/prescriptions").json()

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Personal & Insurance Details")
        st.write(f"**Full Name:** {prof.get('full_name')}")
        st.write(f"**Date of Birth:** {prof.get('date_of_birth')}")
        st.write(f"**Gender:** {prof.get('gender')}")
        st.write(f"**Blood Group:** {prof.get('blood_group')}")
        st.write(f"**Primary Email:** {prof.get('email')}")
        st.write(f"**Phone Number:** {prof.get('phone')}")
        st.write(f"**Residential Address:** {prof.get('address')}")
        st.write(f"**Insurance Policy:** `{prof.get('insurance_policy_number')}`")
        st.write(f"**Emergency Contact:** {prof.get('emergency_contact_name')} ({prof.get('emergency_contact_phone')})")

    with c2:
        st.subheader("Clinical History & Diagnoses")
        if records:
            for r in records:
                st.markdown(f"""
                <div class="info-card">
                    <strong>Diagnosis: {r['diagnosis']}</strong><br>
                    <small>Attending Physician: {r['doctor_name']} | Date: {r['record_date']}</small>
                    <p style="margin-top: 0.5rem; font-size: 0.9rem;">{r['treatment_summary']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No clinical history recorded.")

        st.subheader("Active Prescriptions")
        if prescriptions:
            for rx in prescriptions:
                st.markdown(f"""
                <div class="info-card">
                    <strong>{rx['medication_name']}</strong> ({rx['dosage']})<br>
                    <small>Instructions: {rx['frequency']}</small><br>
                    <small>Prescribed by: {rx['prescribed_by']} (Valid through: {rx['end_date']})</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No active prescriptions.")
