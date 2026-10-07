import json
import uuid
from server import app

def test_strict_curriculum_availability_gate():
    """
    Comprehensive Verification for Curriculum Availability Gate:
    1. NOT_UPLOADED: Fresh student has status='NOT_UPLOADED', is_valid=False, subjects=[], topics=[]
    2. Trainer chat, Reality Lab, Knowledge Transfer, Challenge Quiz ALL reject requests when no valid syllabus
    3. NEEDS_REVIEW: Uploading mismatched semester syllabus flags status='NEEDS_REVIEW' with subjects=[], topics=[]
    4. VALID: Authentic validated syllabus activates status='VALID' with extracted subjects and topics
    5. Anti-invention: Trainer chat rejects subjects not present in validated curriculum
    6. Post-deletion: Reverts to NOT_UPLOADED with subjects=[]
    """
    client = app.test_client()
    
    # ── 1. Register brand new student (NOT_UPLOADED state) ─────────────────────
    email = f"gate_test_student_{uuid.uuid4().hex[:8]}@example.com"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Gate Test Student",
        "email": email,
        "password": "Password123!",
        "role": "student",
        "level": "college",
        "degree": "B.Tech",
        "department": "Information Technology",
        "current_semester": 4
    })
    assert reg_resp.status_code in [200, 201]
    
    # Check Active Curriculum Gate
    cur_resp = client.get("/api/curriculum/active")
    assert cur_resp.status_code == 200
    cur_data = cur_resp.get_json()
    
    print("\n[State 1 - NOT_UPLOADED] Active curriculum response:", cur_data)
    assert cur_data.get("status") in ["NOT_UPLOADED", "NOT_AVAILABLE"], f"Expected NOT_UPLOADED, got {cur_data.get('status')}"
    assert cur_data.get("is_valid") is False
    assert cur_data.get("is_active") is False
    assert cur_data.get("subjects") == []
    assert cur_data.get("extracted_subjects") == []
    assert cur_data.get("topics") == []
    assert cur_data.get("units") == {}
    
    # ── 2. Backend Gating: All learning agent endpoints must reject requests ──
    # A. Reality Lab Generate
    rl_resp = client.post("/api/reality-lab/generate", json={
        "subject": "Operating Systems",
        "module": "Process Scheduling"
    })
    print("\n[Gate Check] Reality Lab without syllabus:", rl_resp.status_code, rl_resp.get_json())
    assert rl_resp.status_code == 400
    assert "syllabus" in rl_resp.get_json().get("error", "").lower()
    
    # B. Knowledge Transfer Generate
    kt_resp = client.post("/api/transfer/generate", json={
        "subject": "Operating Systems",
        "topic": "Process Scheduling"
    })
    print("\n[Gate Check] Knowledge Transfer without syllabus:", kt_resp.status_code, kt_resp.get_json())
    assert kt_resp.status_code == 400
    assert "syllabus" in kt_resp.get_json().get("error", "").lower()
    
    # C. Challenge Quiz
    quiz_resp = client.get("/api/challenge/quiz?subject=Operating+Systems")
    print("\n[Gate Check] Challenge Quiz without syllabus:", quiz_resp.status_code, quiz_resp.get_json())
    assert quiz_resp.status_code == 400
    assert "syllabus" in quiz_resp.get_json().get("error", "").lower()
    
    # D. Trainer Chat
    chat_resp = client.post("/api/trainer/chat", json={
        "subject": "Operating Systems",
        "message": "Explain CPU scheduling algorithms"
    })
    print("\n[Gate Check] Trainer Chat without syllabus:", chat_resp.status_code, chat_resp.get_json())
    assert chat_resp.status_code == 400
    assert "syllabus" in chat_resp.get_json().get("error", "").lower()
    
    # ── 3. State: NEEDS_REVIEW (Mismatched Syllabus Upload) ───────────────────
    mismatch_syllabus = """
    ANNA UNIVERSITY
    SEMESTER 8 SYLLABUS (Final Year)
    CS8801 Cloud Infrastructure Management
    Unit 1: Datacenter Virtualization
    """
    mismatch_resp = client.post("/api/syllabus/analyze", json={
        "text": mismatch_syllabus,
        "semester": 4
    })
    print("\n[State 2 - NEEDS_REVIEW upload]:", mismatch_resp.status_code, mismatch_resp.get_json().get("validation_status"))
    
    # Query active curriculum under mismatch
    cur_mismatch = client.get("/api/curriculum/active").get_json()
    print("\n[State 2 - NEEDS_REVIEW active curriculum]:", cur_mismatch)
    assert cur_mismatch.get("status") in ["NEEDS_REVIEW", "MISMATCH"]
    assert cur_mismatch.get("is_valid") is False
    assert cur_mismatch.get("subjects") == []
    assert cur_mismatch.get("topics") == []
    
    # ── 4. State: VALID (Authentic Semester 4 Syllabus Upload) ─────────────────
    sem4_syllabus = """
    STATE TECHNOLOGICAL UNIVERSITY
    DEPARTMENT OF INFORMATION TECHNOLOGY
    SEMESTER 4 CURRICULUM
    
    IT401 Database Management Systems
    Unit 1: ER Modeling and Relational Algebra
    Unit 2: SQL and Query Optimization
    Unit 3: Normalization and Transactions
    
    IT402 Operating Systems
    Unit 1: Processes, Threads, CPU Scheduling
    Unit 2: Synchronization, Semaphores, Deadlocks
    Unit 3: Memory Management and Virtual Memory
    
    IT403 Design and Analysis of Algorithms
    Unit 1: Asymptotic Analysis and Divide & Conquer
    Unit 2: Dynamic Programming and Greedy Algorithms
    """
    valid_resp = client.post("/api/syllabus/analyze", json={
        "text": sem4_syllabus,
        "semester": 4
    })
    print("\n[State 3 - VALID upload]:", valid_resp.status_code, valid_resp.get_json().get("validation_status"))
    assert valid_resp.status_code == 200
    assert valid_resp.get_json().get("validation_status") == "VALID"
    
    # Query active curriculum under VALID state
    cur_valid = client.get("/api/curriculum/active").get_json()
    print("\n[State 3 - VALID active curriculum]:", cur_valid.get("status"), len(cur_valid.get("subjects", [])))
    assert cur_valid.get("status") in ["VALID", "ACTIVE"]
    assert cur_valid.get("is_valid") is True
    assert len(cur_valid.get("subjects", [])) == 3
    valid_names = cur_valid.get("extracted_subjects", [])
    assert "Operating Systems" in valid_names
    assert "Database Management Systems" in valid_names
    
    # ── 5. Anti-Hallucination Gate: Reject Subjects Absent from Validated Curriculum ──
    bogus_chat = client.post("/api/trainer/chat", json={
        "subject": "Quantum Astrophysics and Rocket Propulsion",
        "message": "Teach me rocket dynamics"
    })
    print("\n[Anti-Hallucination Gate] Requesting unvalidated subject:", bogus_chat.status_code, bogus_chat.get_json())
    assert bogus_chat.status_code == 400
    assert "not in your validated" in bogus_chat.get_json().get("error", "").lower()
    
    # ── 6. State: Post-Deletion Reversion to NOT_UPLOADED ──────────────────────
    del_resp = client.delete("/api/syllabus")
    assert del_resp.status_code == 200
    
    cur_post_del = client.get("/api/curriculum/active").get_json()
    print("\n[State 4 - Post-Deletion Reversion]:", cur_post_del)
    assert cur_post_del.get("status") in ["NOT_UPLOADED", "NOT_AVAILABLE"]
    assert cur_post_del.get("is_valid") is False
    assert cur_post_del.get("subjects") == []
    assert cur_post_del.get("topics") == []
    
    print("\n" + "="*70)
    print(" >>> ALL STRICT CURRICULUM AVAILABILITY GATES VERIFIED SUCCESSFULLY! <<<")
    print("="*70)

if __name__ == "__main__":
    test_strict_curriculum_availability_gate()
