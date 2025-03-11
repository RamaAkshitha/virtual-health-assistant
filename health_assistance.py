import streamlit as st
from typing import Generator
from textblob import TextBlob
from groq import Groq
import datetime
import uuid
import random
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import os
import json

# Calculate duration function
def calculate_duration(start_time_str, end_time_str):
    """Calculate the duration between two time strings"""
    try:
        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        duration = end_time - start_time
        minutes, seconds = divmod(duration.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m {seconds}s"
    except Exception:
        return "Unknown duration"

# Application Setup
st.set_page_config(
    layout="wide",
    page_title="HealthMate",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("styles.css", "r") as f:
    css = f.read()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# API Integration
API_KEY = os.environ.get('GROQ_API_KEY', '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')
api_client = Groq(api_key=API_KEY)

def load_medication_data(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Error: File '{file_path}' not found.")
        return {}
    except json.JSONDecodeError:
        st.error(f"Error: Invalid JSON in '{file_path}'.")
        return {}
medications_file_path = "medications.json"
MEDICATION_DATABASE = load_medication_data(medications_file_path)

# Doctor Database with availability
DOCTORS_DATABASE = {
    "Primary Care": [
        {"id": "dr_smith", "name": "Dr. Emily Smith", "rating": 4.8, "experience": "12 years", "specializations": ["Family Medicine", "Preventive Care"]},
        {"id": "dr_johnson", "name": "Dr. Michael Johnson", "rating": 4.7, "experience": "15 years", "specializations": ["Internal Medicine", "Geriatrics"]}
    ],
    "Cardiology": [
        {"id": "dr_patel", "name": "Dr. Vikram Patel", "rating": 4.9, "experience": "20 years", "specializations": ["Interventional Cardiology", "Heart Failure"]},
        {"id": "dr_rodriguez", "name": "Dr. Maria Rodriguez", "rating": 4.8, "experience": "18 years", "specializations": ["Electrophysiology", "Preventive Cardiology"]}
    ],
    "Dermatology": [
        {"id": "dr_wong", "name": "Dr. Alice Wong", "rating": 4.7, "experience": "14 years", "specializations": ["Cosmetic Dermatology", "Skin Cancer"]},
        {"id": "dr_taylor", "name": "Dr. James Taylor", "rating": 4.6, "experience": "11 years", "specializations": ["Pediatric Dermatology", "Eczema"]}
    ],
    "Neurology": [
        {"id": "dr_chen", "name": "Dr. Lisa Chen", "rating": 4.9, "experience": "22 years", "specializations": ["Movement Disorders", "Epilepsy"]},
        {"id": "dr_brown", "name": "Dr. Robert Brown", "rating": 4.8, "experience": "19 years", "specializations": ["Neuromuscular Disorders", "Headache Medicine"]}
    ],
    "Orthopedics": [
        {"id": "dr_wilson", "name": "Dr. Thomas Wilson", "rating": 4.7, "experience": "17 years", "specializations": ["Sports Medicine", "Joint Replacement"]},
        {"id": "dr_garcia", "name": "Dr. Sofia Garcia", "rating": 4.8, "experience": "13 years", "specializations": ["Spine Surgery", "Trauma"]}
    ],
    "Pediatrics": [
        {"id": "dr_kim", "name": "Dr. Sarah Kim", "rating": 4.9, "experience": "16 years", "specializations": ["Neonatology", "Developmental Pediatrics"]},
        {"id": "dr_davis", "name": "Dr. Jonathan Davis", "rating": 4.8, "experience": "14 years", "specializations": ["Pediatric Allergies", "Respiratory Disorders"]}
    ],
    "Psychiatry": [
        {"id": "dr_miller", "name": "Dr. David Miller", "rating": 4.7, "experience": "19 years", "specializations": ["Mood Disorders", "Anxiety"]},
        {"id": "dr_jones", "name": "Dr. Rachel Jones", "rating": 4.8, "experience": "12 years", "specializations": ["Child Psychiatry", "ADHD"]}
    ],
    "Other": [
        {"id": "dr_martinez", "name": "Dr. Carlos Martinez", "rating": 4.6, "experience": "13 years", "specializations": ["General Medicine", "Holistic Health"]},
        {"id": "dr_lee", "name": "Dr. Jennifer Lee", "rating": 4.7, "experience": "11 years", "specializations": ["Integrative Medicine", "Nutrition"]}
    ]
}

# Session State Initialization
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "scheduled_visits" not in st.session_state:
    st.session_state.scheduled_visits = []
if "video_calls" not in st.session_state:
    st.session_state.video_calls = []
if "show_visit_form" not in st.session_state:
    st.session_state.show_visit_form = False
if "edit_appointment" not in st.session_state:
    st.session_state.edit_appointment = None
if "show_video_call" not in st.session_state:
    st.session_state.show_video_call = False
if "current_doctor" not in st.session_state:
    st.session_state.current_doctor = None
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "",
        "age": None,
        "gender": "",
        "conditions": [],
        "medications": [],
        "allergies": []
    }

# Helper Functions
def gauge_sentiment(text_input: str) -> str:
    """Evaluates the emotional tone of text."""
    sentiment_analysis = TextBlob(text_input)
    if sentiment_analysis.sentiment.polarity > 0:
        return "Optimistic"
    elif sentiment_analysis.sentiment.polarity < 0:
        return "Concerned"
    else:
        return "Neutral"

def stream_response_chunks(api_response) -> Generator[str, None, None]:
    """Processes and yields response segments from the API."""
    for part in api_response:
        if part.choices[0].delta.content:
            yield part.choices[0].delta.content

def check_health_condition(text):
    """Analyze the user input to identify if they're describing a health condition."""
    text = text.lower()
    for condition in MEDICATION_DATABASE.keys():
        if condition in text:
            return condition
    return None

def add_medication_suggestions(identified_condition):
    """Generate medication suggestions HTML for the identified condition."""
    if not identified_condition or identified_condition not in MEDICATION_DATABASE:
        return ""
    condition_info = MEDICATION_DATABASE[identified_condition]
    medications = condition_info["medications"]
    dosage_info = condition_info["dosage_info"]
    suggestion_html = f"""
    <div class="medication-box">
        <h4>💊 Medication Suggestions for {identified_condition.title()}</h4>
<p><strong>Commonly used medications:</strong> {', '.join(medications)}</p>
        <p><strong>Typical usage:</strong> {dosage_info}</p>
        <div class="medication-disclaimer">
            Note: This information is for educational purposes only.
            Consult your doctor or pharmacist before taking any medication.
        </div>
    </div>
    """
    return suggestion_html

def get_available_timeslots(doctor_id, date):
    """Generate dynamically available time slots for a doctor on a specific date."""
    random.seed(f"{doctor_id}_{date}")
    all_slots = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00"]
    available_count = random.randint(4, 6)
    available_slots = random.sample(all_slots, available_count)
    available_slots.sort()
    return available_slots

def get_doctor_by_id(doctor_id):
    """Find a doctor by their ID in the database."""
    for specialty, doctors in DOCTORS_DATABASE.items():
        for doctor in doctors:
            if doctor["id"] == doctor_id:
                return doctor
    return None

def init_video_call(doctor_id):
    """Initialize a video call session with a doctor."""
    doctor = get_doctor_by_id(doctor_id)
    if not doctor:
        return False
    st.session_state.current_doctor = doctor
    st.session_state.show_video_call = True
    call_id = f"call_{uuid.uuid4().hex[:8]}"
    st.session_state.video_calls.append({
        "id": call_id,
        "doctor": doctor,
        "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active"
    })
    return call_id

# Sidebar for additional controls and information
with st.sidebar:
    st.title("AI Health Assistant")

    # User profile section in sidebar
    st.markdown("### My Profile")
    if not st.session_state.user_profile["name"]:
        with st.expander("Complete Your Profile", expanded=True):
            st.session_state.user_profile["name"] = st.text_input("Name", key="profile_name")
            st.session_state.user_profile["age"] = st.number_input("Age", min_value=0, max_value=120, step=1, key="profile_age")
            st.session_state.user_profile["gender"] = st.selectbox("Gender", ["", "Male", "Female", "Non-binary", "Prefer not to say"], key="profile_gender")
            conditions = st.text_area("Existing Medical Conditions (one per line)", key="profile_conditions")
            st.session_state.user_profile["conditions"] = [c.strip() for c in conditions.split("\n") if c.strip()]
            medications = st.text_area("Current Medications (one per line)", key="profile_medications")
            st.session_state.user_profile["medications"] = [m.strip() for m in medications.split("\n") if m.strip()]
            allergies = st.text_area("Allergies (one per line)", key="profile_allergies")
            st.session_state.user_profile["allergies"] = [a.strip() for a in allergies.split("\n") if a.strip()]
    else:
        with st.expander("My Health Profile"):
            st.markdown(f"Name: {st.session_state.user_profile['name']}")
            st.markdown(f"Age: {st.session_state.user_profile['age']}")
            st.markdown(f"Gender: {st.session_state.user_profile['gender']}")

            st.markdown("Medical Conditions:")
            if st.session_state.user_profile["conditions"]:
                for condition in st.session_state.user_profile["conditions"]:
                    st.markdown(f"- {condition}")
            else:
                st.markdown("- None reported")

            st.markdown("Current Medications:")
            if st.session_state.user_profile["medications"]:
                for medication in st.session_state.user_profile["medications"]:
                    st.markdown(f"- {medication}")
            else:
                st.markdown("- None reported")

            st.markdown("Allergies:")
            if st.session_state.user_profile["allergies"]:
                for allergy in st.session_state.user_profile["allergies"]:
                    st.markdown(f"- {allergy}")
            else:
                st.markdown("- None reported")

            if st.button("Edit Profile", key="edit_profile"):
                st.session_state.user_profile = {
                    "name": "",
                    "age": None,
                    "gender": "",
                    "conditions": [],
                    "medications": [], 
                    "allergies": [] 
                }
                st.rerun()

    st.markdown("### About")
    st.markdown("""
    HealthMate provides:
    - 24/7 healthcare assistance
    - Appointment scheduling
    - Health information and advice
    - Medication suggestions
    - Video consultations with doctors
    - Personalized support

    Note: This assistant provides general information only and does not replace professional medical advice.
    """)

# Main Content
st.title("HealthMate")
st.markdown("##### Your AI-Powered Health Assistant")

# Tabs
tab1, tab2, tab3 = st.tabs(["💬 Chat Assistant", "📅 My Appointments", "👨‍⚕ Video Consultation"])

with tab1:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    if st.session_state.user_profile["name"]:
        st.markdown(
            f"""
            <div class="profile-container">
                <h4>👋 Welcome, {st.session_state.user_profile["name"]}</h4>
                <p>How can I assist you with your health needs today?</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Display Conversation
    for message in st.session_state.conversation:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        elif message["role"] == "assistant":
            if "is_html" in message and message["is_html"]:
                st.markdown(message["content"], unsafe_allow_html=True)  # Render HTML for medication suggestions
            else:
                st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)

    if user_query := st.chat_input("How can I help with your health needs today?"):
        st.session_state.conversation.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        condition = check_health_condition(user_query)
        if "video" in user_query.lower() and any(term in user_query.lower() for term in ["call", "consult", "doctor", "talk"]):
            video_response = "I see you're interested in a video consultation. You can schedule one from our 'Video Consultation' tab."
            with st.chat_message("assistant"):
                st.markdown(video_response)
                sentiment = "Optimistic"
                sentiment_class = f"sentiment-{sentiment.lower()}"
                st.markdown(f'<div class="sentiment-indicator {sentiment_class}">Mood: {sentiment}</div>', unsafe_allow_html=True)
            st.session_state.conversation.append({
                "role": "assistant",
                "content": video_response,
                "sentiment": sentiment
            })
        else:
            try:
                with st.spinner("Generating response..."):
                    profile_context = ""
                    if st.session_state.user_profile["name"]:
                        profile_context = f"""
                        User profile information:
                        - Name: {st.session_state.user_profile["name"]}
                        - Age: {st.session_state.user_profile["age"]}
                        - Gender: {st.session_state.user_profile["gender"]}
                        """
                    system_prompt = f"""
                    You are HealthMate, a sophisticated medical assistant. Provide health insights and manage appointments.
                    Be friendly, efficient, and personalized in your responses.
                    {profile_context}
                    """
                    api_stream = api_client.chat.completions.create(
                        model="gemma2-9b-it",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        max_tokens=1028,
                        stream=True
                    )
                    full_reply = "".join(list(stream_response_chunks(api_stream)))

                with st.chat_message("assistant"):
                    st.markdown(full_reply)
                    if condition:
                        medication_html = add_medication_suggestions(condition)
                        st.markdown(medication_html, unsafe_allow_html=True)  
                    sentiment = gauge_sentiment(user_query)
                    sentiment_class = f"sentiment-{sentiment.lower()}"
                    st.markdown(f'<div class="sentiment-indicator {sentiment_class}">Mood: {sentiment}</div>',
                                unsafe_allow_html=True)

                st.session_state.conversation.append({
                    "role": "assistant",
                    "content": full_reply + (add_medication_suggestions(condition) if condition else ""),
                    "sentiment": sentiment,
                    "is_html": condition is not None 
                })

            except Exception as error_info:
                st.error(f"Communication error: {error_info}")
                st.session_state.conversation.append({
                    "role": "assistant",
                    "content": "I'm sorry, I encountered an error trying to process your request. Please try again.",
                    "sentiment": "Concerned"
                })

    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown("### My Scheduled Appointments")
    if not st.session_state.show_visit_form and st.session_state.edit_appointment is None:
        if st.button("➕ New Appointment"):
            st.session_state.show_visit_form = True
            st.rerun()

    if st.session_state.show_visit_form or st.session_state.edit_appointment is not None:
        with st.form(key="appointment_form", clear_on_submit=True):
            st.markdown("#### Schedule a Visit")
            editing = st.session_state.edit_appointment is not None
            current_appt = None
            if editing:
                current_appt = next((a for a in st.session_state.scheduled_visits 
                                  if a["id"] == st.session_state.edit_appointment), None)
            patient_name = st.text_input("Patient Name", 
                                       value=current_appt["patient_name"] if editing else st.session_state.user_profile["name"])
            specialty = st.selectbox("Specialty", 
                                   list(DOCTORS_DATABASE.keys()),
                                   index=list(DOCTORS_DATABASE.keys()).index(current_appt["specialty"]) 
                                   if editing and current_appt["specialty"] in DOCTORS_DATABASE.keys() else 0)
            doctors = DOCTORS_DATABASE[specialty]
            doctor_options = [f"{doc['name']} ({doc['experience']} exp, {doc['rating']}★)" for doc in doctors]
            selected_doctor = st.selectbox("Select Doctor", doctor_options, 
                                         index=doctor_options.index(f"{current_appt['doctor_name']} ({current_appt['doctor_exp']} exp, {current_appt['doctor_rating']}★)") 
                                         if editing else 0)
            min_date = datetime.datetime.now().date()
            appointment_date = st.date_input("Appointment Date", 
                                          value=datetime.datetime.strptime(current_appt["date"], "%Y-%m-%d").date() 
                                          if editing else min_date,
                                          min_value=min_date)
            selected_doctor_idx = doctor_options.index(selected_doctor)
            doctor_id = doctors[selected_doctor_idx]["id"]
            available_slots = get_available_timeslots(doctor_id, appointment_date)
            time_slot = st.selectbox("Available Time Slots", 
                                   available_slots,
                                   index=available_slots.index(current_appt["time"]) 
                                   if editing and current_appt["time"] in available_slots else 0)
            reason = st.text_area("Reason for Visit", 
                                value=current_appt["reason"] if editing else "")
            submit_label = "Update Appointment" if editing else "Schedule Appointment"
            submit_button = st.form_submit_button(submit_label)
            if submit_button:
                appointment = {
                    "id": current_appt["id"] if editing else str(uuid.uuid4()),
                    "patient_name": patient_name,
                    "specialty": specialty,
                    "doctor_id": doctor_id,
                    "doctor_name": doctors[selected_doctor_idx]["name"],
                    "doctor_exp": doctors[selected_doctor_idx]["experience"],
                    "doctor_rating": doctors[selected_doctor_idx]["rating"],
                    "date": appointment_date.strftime("%Y-%m-%d"),
                    "time": time_slot,
                    "reason": reason,
                    "status": "Confirmed"
                }
                if editing:
                    st.session_state.scheduled_visits = [
                        appointment if visit["id"] == st.session_state.edit_appointment else visit 
                        for visit in st.session_state.scheduled_visits
                    ]
                    st.success(f"Appointment with {doctors[selected_doctor_idx]['name']} updated successfully!")
                else:
                    st.session_state.scheduled_visits.append(appointment)
                    st.success(f"Appointment with {doctors[selected_doctor_idx]['name']} scheduled successfully!")
                st.session_state.show_visit_form = False
                st.session_state.edit_appointment = None
                st.rerun()
    
    if not st.session_state.scheduled_visits:
        st.info("You have no upcoming appointments. Schedule a visit to get started.")
    else:
        sorted_visits = sorted(
            st.session_state.scheduled_visits, 
            key=lambda x: (x["date"], x["time"])
        )
        for visit in sorted_visits:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"""
                    <div class="appointment-card">
                        <h4>{visit["date"]} at {visit["time"]} - <span class="pill">{visit["status"]}</span></h4>
                        <p><strong>Doctor:</strong> {visit["doctor_name"]} ({visit["specialty"]})</p>
                        <p><strong>Patient:</strong> {visit["patient_name"]}</p>
                        <p><strong>Reason:</strong> {visit["reason"]}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("Edit", key=f"edit_{visit['id']}"):
                    st.session_state.edit_appointment = visit["id"]
                    st.session_state.show_visit_form = True
                    st.rerun()
                if st.button("Cancel", key=f"cancel_{visit['id']}"):
                    st.session_state.scheduled_visits = [
                        a for a in st.session_state.scheduled_visits if a["id"] != visit["id"]
                    ]
                    st.success("Appointment cancelled successfully.")
                    st.rerun()

with tab3:
    st.markdown("### Connect with a Doctor")
    if st.session_state.show_video_call and st.session_state.current_doctor:
        doctor = st.session_state.current_doctor
        st.markdown(
            f"""
            <div class="video-container">
                <div class="doctor-info">
                    <div class="doctor-avatar">👨‍⚕</div>
                    <div class="doctor-details">
                        <h3>{doctor["name"]}</h3>
                        <p>{", ".join(doctor["specializations"])}</p>
                    </div>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
                    )
        
        # WebRTC Video component for real-time video calls
        rtc_configuration = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
        
        webrtc_ctx = webrtc_streamer(
            key="sample",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=rtc_configuration,
            media_stream_constraints={"video": True, "audio": True},
            video_html_attrs={"style": {"width": "100%", "height": "auto", "margin": "0 auto", "display": "block"}},
        )
        
        if st.button("End Call"):
            # End the current call
            for i, call in enumerate(st.session_state.video_calls):
                if call["status"] == "active":
                    st.session_state.video_calls[i]["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.video_calls[i]["status"] = "completed"
            
            st.session_state.show_video_call = False
            st.session_state.current_doctor = None
            st.success("Call ended successfully.")
            st.rerun()
    
    else:
        # Doctor selection for video consultation
        st.markdown("#### Start a Video Consultation")
        st.markdown("Select a specialty and doctor to begin a video call.")
        
        specialty = st.selectbox("Select Specialty", list(DOCTORS_DATABASE.keys()), key="video_specialty")
        doctors = DOCTORS_DATABASE[specialty]
        
        # Display doctor cards
        for doctor in doctors:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(
                    f"""
                    <div class="doctor-info">
                        <div class="doctor-avatar">👨‍⚕</div>
                        <div class="doctor-details">
                            <h3>{doctor["name"]} ({doctor["rating"]}★)</h3>
                            <p><strong>Experience:</strong> {doctor["experience"]}</p>
                            <p><strong>Specializes in:</strong> {", ".join(doctor["specializations"])}</p>
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            
            with col2:
                if st.button("Connect", key=f"connect_{doctor['id']}"):
                    call_id = init_video_call(doctor["id"])
                    if call_id:
                        st.success(f"Connecting to {doctor['name']}...")
                        st.rerun()
                    else:
                        st.error("Failed to establish connection. Please try again.")
        
        # Previous calls section
        if st.session_state.video_calls:
            st.markdown("### Previous Consultations")
            
            completed_calls = [call for call in st.session_state.video_calls if call["status"] == "completed"]
            
            for call in completed_calls:
                doctor = call["doctor"]
                duration = calculate_duration(call["start_time"], call["end_time"]) if "end_time" in call else "In progress"
                
                st.markdown(
                    f"""
                    <div class="appointment-card">
                        <h4>Call with {doctor["name"]} - {call["start_time"].split()[0]}</h4>
                        <p><strong>Duration:</strong> {duration}</p>
                        <p><strong>Specialty:</strong> {", ".join(doctor["specializations"])}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )