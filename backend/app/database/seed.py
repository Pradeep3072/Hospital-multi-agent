import datetime
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.models import (
    Role, Department, DoctorSpecialization, Doctor,
    DoctorSchedule, DoctorLeave, Patient, Appointment,
    MedicalRecord, Prescription, HospitalService, InsuranceProvider
)


def seed_database():
    init_db()
    db = SessionLocal()

    # Check if already seeded
    if db.query(Role).first():
        db.close()
        return

    print("Seeding database with initial hospital data...")

    # 1. Roles
    roles = {
        "admin": Role(name="admin", description="System administrator"),
        "doctor": Role(name="doctor", description="Medical doctor / physician"),
        "patient": Role(name="patient", description="Registered hospital patient"),
        "staff": Role(name="staff", description="Receptionist and administrative staff"),
    }
    for r in roles.values():
        db.add(r)
    db.commit()

    # 2. Departments
    dept_cardio = Department(name="Cardiology", description="Heart and cardiovascular system care", location_building="Building A", floor=3, contact_phone="555-0101")
    dept_neuro = Department(name="Neurology", description="Brain, spine, and nervous system", location_building="Building A", floor=4, contact_phone="555-0102")
    dept_peds = Department(name="Pediatrics", description="Infant, child, and adolescent healthcare", location_building="Building B", floor=1, contact_phone="555-0103")
    dept_ortho = Department(name="Orthopedics", description="Musculoskeletal system, bones, and joints", location_building="Building B", floor=2, contact_phone="555-0104")
    dept_gen = Department(name="General Medicine", description="Primary adult healthcare and internal medicine", location_building="Building C", floor=1, contact_phone="555-0105")
    dept_er = Department(name="Emergency & Trauma", description="24/7 Acute trauma and life-saving emergency interventions", location_building="Emergency Wing", floor=1, contact_phone="555-0911")

    db.add_all([dept_cardio, dept_neuro, dept_peds, dept_ortho, dept_gen, dept_er])
    db.commit()

    # 3. Doctor Specializations
    spec_cardio = DoctorSpecialization(name="Cardiologist", description="Specialist in cardiovascular diseases and heart surgery")
    spec_neuro = DoctorSpecialization(name="Neurologist", description="Specialist in brain, nerve, and spinal disorders")
    spec_peds = DoctorSpecialization(name="Pediatrician", description="Specialist in infant and child medical care")
    spec_ortho = DoctorSpecialization(name="Orthopedic Surgeon", description="Specialist in bone and joint surgery")
    spec_internist = DoctorSpecialization(name="Internal Medicine Physician", description="Specialist in comprehensive adult healthcare")

    db.add_all([spec_cardio, spec_neuro, spec_peds, spec_ortho, spec_internist])
    db.commit()

    # 4. Doctors
    doctors_info = [
        {
            "name": "Dr. Sarah Mitchell",
            "email": "dr.mitchell@hospital.org",
            "phone": "555-0201",
            "dept": dept_cardio,
            "spec": spec_cardio,
            "license": "MD-CARD-1092",
            "fee": 150.0,
            "exp": 14,
            "bio": "Leading cardiologist specializing in echocardiography and preventive heart care."
        },
        {
            "name": "Dr. Robert Chen",
            "email": "dr.chen@hospital.org",
            "phone": "555-0202",
            "dept": dept_neuro,
            "spec": spec_neuro,
            "license": "MD-NEUR-8841",
            "fee": 180.0,
            "exp": 12,
            "bio": "Neurology specialist focusing on migraine management, stroke recovery, and neuropathy."
        },
        {
            "name": "Dr. Emily Vance",
            "email": "dr.vance@hospital.org",
            "phone": "555-0203",
            "dept": dept_peds,
            "spec": spec_peds,
            "license": "MD-PEDS-3910",
            "fee": 100.0,
            "exp": 9,
            "bio": "Compassionate pediatrician experienced in childhood development, immunizations, and asthma."
        },
        {
            "name": "Dr. James Wilson",
            "email": "dr.wilson@hospital.org",
            "phone": "555-0204",
            "dept": dept_ortho,
            "spec": spec_ortho,
            "license": "MD-ORTH-5521",
            "fee": 160.0,
            "exp": 16,
            "bio": "Orthopedic surgeon specializing in sports injuries, knee arthroscopy, and joint replacement."
        },
        {
            "name": "Dr. Lisa Patel",
            "email": "dr.patel@hospital.org",
            "phone": "555-0205",
            "dept": dept_gen,
            "spec": spec_internist,
            "license": "MD-INTM-7719",
            "fee": 85.0,
            "exp": 8,
            "bio": "Primary care physician focusing on chronic illness management, diabetes, and annual health screenings."
        }
    ]

    created_doctors = []
    for doc in doctors_info:
        doctor = Doctor(
            role_id=roles["doctor"].id,
            department_id=doc["dept"].id,
            specialization_id=doc["spec"].id,
            full_name=doc["name"],
            email=doc["email"],
            phone_number=doc["phone"],
            license_number=doc["license"],
            consultation_fee=doc["fee"],
            experience_years=doc["exp"],
            bio=doc["bio"],
            is_active=True
        )
        db.add(doctor)
        db.flush()
        created_doctors.append(doctor)

        # Schedules (Mon-Fri 09:00 - 17:00, 30 min slots)
        for day in range(0, 5):
            schedule = DoctorSchedule(
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=datetime.time(9, 0),
                end_time=datetime.time(17, 0),
                slot_duration_minutes=30,
                is_available=True
            )
            db.add(schedule)

    db.commit()

    # 5. Patients
    patients_data = [
        {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "555-1001",
            "dob": datetime.date(1985, 4, 12),
            "gender": "Male",
            "blood": "O+",
            "ec_name": "Jane Doe",
            "ec_phone": "555-1002",
            "address": "742 Evergreen Terrace, Springfield",
            "policy": "BCBS-8839201"
        },
        {
            "name": "Sarah Connor",
            "email": "sarah.connor@example.com",
            "phone": "555-2001",
            "dob": datetime.date(1990, 8, 23),
            "gender": "Female",
            "blood": "A-",
            "ec_name": "John Connor",
            "ec_phone": "555-2002",
            "address": "404 SkyNet Way, Los Angeles",
            "policy": "AETNA-992102"
        },
        {
            "name": "Alice Johnson",
            "email": "alice.johnson@example.com",
            "phone": "555-3001",
            "dob": datetime.date(2001, 1, 15),
            "gender": "Female",
            "blood": "B+",
            "ec_name": "Robert Johnson",
            "ec_phone": "555-3002",
            "address": "12 Elm St, Boston",
            "policy": "UHC-448102"
        }
    ]

    created_patients = []
    for p in patients_data:
        patient = Patient(
            role_id=roles["patient"].id,
            full_name=p["name"],
            email=p["email"],
            phone_number=p["phone"],
            date_of_birth=p["dob"],
            gender=p["gender"],
            blood_group=p["blood"],
            emergency_contact_name=p["ec_name"],
            emergency_contact_phone=p["ec_phone"],
            address=p["address"],
            insurance_policy_number=p["policy"]
        )
        db.add(patient)
        db.flush()
        created_patients.append(patient)

    # 6. Medical Records & Prescriptions for John Doe
    mr1 = MedicalRecord(
        patient_id=created_patients[0].id,
        doctor_name="Dr. Sarah Mitchell",
        diagnosis="Mild Hypertension",
        treatment_summary="Prescribed low-sodium diet and daily blood pressure monitoring. Initiated Lisinopril.",
        record_date=datetime.date.today() - datetime.timedelta(days=45)
    )
    db.add(mr1)

    rx1 = Prescription(
        patient_id=created_patients[0].id,
        medication_name="Lisinopril",
        dosage="10mg",
        frequency="Once daily in the morning",
        start_date=datetime.date.today() - datetime.timedelta(days=45),
        end_date=datetime.date.today() + datetime.timedelta(days=45),
        prescribed_by="Dr. Sarah Mitchell"
    )
    db.add(rx1)

    # 7. Initial Appointment for John Doe (tomorrow at 10:00 AM)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    # Ensure tomorrow is weekday
    if tomorrow.weekday() >= 5:
        tomorrow = tomorrow + datetime.timedelta(days=(7 - tomorrow.weekday()))

    appt1 = Appointment(
        patient_id=created_patients[0].id,
        doctor_id=created_doctors[0].id, # Dr. Sarah Mitchell
        appointment_date=tomorrow,
        appointment_time=datetime.time(10, 0),
        status="CONFIRMED",
        reason_for_visit="Routine blood pressure checkup and prescription refill review"
    )
    db.add(appt1)

    # 8. Hospital Services
    services = [
        HospitalService(department_id=dept_cardio.id, name="Echocardiogram", description="Ultrasound test to evaluate heart structure and blood flow", cost=350.0, availability_hours="Mon-Fri 8am-5pm"),
        HospitalService(department_id=dept_neuro.id, name="MRI Brain Scan", description="High-resolution MRI imaging for neurological assessment", cost=650.0, availability_hours="24/7 with on-call radiologist"),
        HospitalService(department_id=dept_ortho.id, name="Digital X-Ray Bone Scan", description="Rapid imaging for fractures, joints, and spine evaluation", cost=120.0, availability_hours="24/7"),
        HospitalService(department_id=dept_gen.id, name="Comprehensive Metabolic Blood Panel", description="Complete blood count, lipid panel, and organ health profile", cost=75.0, availability_hours="Mon-Sat 7am-6pm"),
        HospitalService(department_id=dept_er.id, name="Emergency Trauma Resuscitation", description="Immediate emergency room triage and trauma life support", cost=1200.0, availability_hours="24/7 365 Days")
    ]
    db.add_all(services)

    # 9. Insurance Providers
    insurances = [
        InsuranceProvider(name="Blue Cross Blue Shield", coverage_type="Comprehensive Health", network_tier="Preferred Tier 1", contact_phone="1-800-555-0111", claims_email="claims@bcbs-health.example.com"),
        InsuranceProvider(name="Aetna Healthcare", coverage_type="HMO / PPO Network", network_tier="Tier 1", contact_phone="1-800-555-0222", claims_email="service@aetna.example.com"),
        InsuranceProvider(name="UnitedHealthcare", coverage_type="Standard & Premium PPO", network_tier="Tier 1", contact_phone="1-800-555-0333", claims_email="support@uhc.example.com"),
        InsuranceProvider(name="Cigna Global", coverage_type="Commercial & Expat Coverage", network_tier="Tier 2", contact_phone="1-800-555-0444", claims_email="contact@cigna.example.com"),
        InsuranceProvider(name="Medicare / Medicaid", coverage_type="Government Supported", network_tier="Full In-Network", contact_phone="1-800-555-0555", claims_email="claims@medicare.example.gov")
    ]
    db.add_all(insurances)

    db.commit()
    db.close()
    print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed_database()
