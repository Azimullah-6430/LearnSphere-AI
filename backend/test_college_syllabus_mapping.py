import json
import uuid
from server import app

def test_college_syllabus_mapping():
    """
    Test suite for Authoritative College Academic Profile Syllabus Mapping:
    1. Authenticated student stored profile (program, department, semester) is the sole authority.
    2. Multi-semester syllabus (Semesters 1-6) -> ONLY the student's stored semester (e.g. Sem 5) is extracted.
    3. Multi-department syllabus (Mech + IT) -> ONLY the student's stored department (IT) is mapped.
    4. Missing semester in profile -> Rejection with HTTP 400 ("SEMESTER_REQUIRED") without guessing.
    5. Zero cross-semester or cross-department combination.
    """
    client = app.test_client()

    # ── Test 1: Missing Semester Profile -> Refuse with SEMESTER_REQUIRED ────
    no_sem_email = f"no_sem_student_{uuid.uuid4().hex[:8]}@example.com"
    reg1 = client.post("/api/auth/register", json={
        "name": "No Sem Student",
        "email": no_sem_email,
        "password": "Password123!",
        "role": "student",
        "level": "college",
        "degree": "B.Tech",
        "department": "Information Technology"
        # current_semester is omitted
    })
    assert reg1.status_code in [200, 201]

    # Attempt syllabus upload without semester in profile
    no_sem_upload = client.post("/api/syllabus/analyze", json={
        "text": "SEMESTER 5\nIT501 Database Systems\nIT502 Web Technologies"
    })
    print("\n[Test 1] Upload with missing semester profile:", no_sem_upload.status_code, no_sem_upload.get_json())
    assert no_sem_upload.status_code == 400
    assert no_sem_upload.get_json().get("status") == "SEMESTER_REQUIRED"
    assert "semester information required" in no_sem_upload.get_json().get("error", "").lower()

    # ── Test 2: Multi-Semester Syllabus -> Extract Stored Semester 5 ONLY ─────
    sem5_email = f"sem5_student_{uuid.uuid4().hex[:8]}@example.com"
    reg2 = client.post("/api/auth/register", json={
        "name": "Alex Mercer",
        "email": sem5_email,
        "password": "Password123!",
        "role": "student",
        "level": "college",
        "degree": "B.Tech",
        "department": "Information Technology",
        "current_year": 3,
        "current_semester": 5
    })
    assert reg2.status_code in [200, 201]

    # 6-semester document
    multi_semester_syllabus = """
    ANNA UNIVERSITY :: CHENNAI
    B.TECH INFORMATION TECHNOLOGY CURRICULUM
    
    SEMESTER 1
    CS101 Python Programming Credits: 3
    MA101 Calculus Credits: 4
    
    SEMESTER 2
    CS201 Data Structures in C Credits: 4
    EE201 Electrical Engineering Credits: 3
    
    SEMESTER 3
    IT301 Digital Logic Credits: 3
    IT302 Object Oriented Programming Credits: 3
    
    SEMESTER 4
    IT401 Design and Analysis of Algorithms Credits: 4
    IT402 Operating Systems Credits: 3
    
    SEMESTER 5
    IT501 Database Management Systems Credits: 4
    IT502 Web Technologies Credits: 3
    IT503 Computer Networks Credits: 3
    IT504 Formal Languages and Automata Theory Credits: 4
    IT505 Software Engineering Credits: 3
    IT506 Database Management Systems Laboratory Credits: 2
    IT507 Web Technologies Laboratory Credits: 2
    
    SEMESTER 6
    IT601 Compiler Design Credits: 4
    IT602 Cloud Computing Credits: 3
    IT603 Mobile Application Development Credits: 3
    """

    # Upload without passing semester (or passing a different one) -> backend uses stored semester (5)
    upload_sem5 = client.post("/api/syllabus/analyze", json={
        "text": multi_semester_syllabus
    })
    print("\n[Test 2] Multi-semester upload response status:", upload_sem5.status_code)
    assert upload_sem5.status_code == 200
    res5 = upload_sem5.get_json()
    assert res5.get("validation_status") == "VALID"
    
    active_cur = client.get("/api/curriculum/active").get_json()
    print("\n[Test 2] Active curriculum semester:", active_cur.get("semester"))
    print("[Test 2] Extracted subjects count:", len(active_cur.get("subjects", [])))
    print("[Test 2] Extracted subject names:", active_cur.get("extracted_subjects"))
    
    assert active_cur.get("semester") == 5
    assert len(active_cur.get("subjects", [])) == 7
    extracted_names = active_cur.get("extracted_subjects", [])
    
    # Must contain ONLY Semester 5 subjects
    assert "Database Management Systems" in extracted_names
    assert "Web Technologies" in extracted_names
    assert "Computer Networks" in extracted_names
    assert "Formal Languages and Automata Theory" in extracted_names
    assert "Software Engineering" in extracted_names
    
    # Must NOT contain subjects from other semesters
    assert "Python Programming" not in extracted_names # Sem 1
    assert "Data Structures in C" not in extracted_names # Sem 2
    assert "Digital Logic" not in extracted_names # Sem 3
    assert "Design and Analysis of Algorithms" not in extracted_names # Sem 4
    assert "Compiler Design" not in extracted_names # Sem 6
    assert "Cloud Computing" not in extracted_names # Sem 6

    # ── Test 3: Multi-Department Syllabus -> Extract Stored Department ONLY ──
    multi_dept_syllabus = """
    COLLEGE OF ENGINEERING
    
    DEPARTMENT OF MECHANICAL ENGINEERING
    SEMESTER 5
    ME501 Dynamics of Machinery Credits: 4
    ME502 Heat Transfer Credits: 4
    ME503 Design of Machine Elements Credits: 4
    
    DEPARTMENT OF INFORMATION TECHNOLOGY
    SEMESTER 5
    IT501 Database Management Systems Credits: 4
    IT502 Web Technologies Credits: 3
    IT503 Computer Networks Credits: 3
    """

    upload_dept = client.post("/api/syllabus/analyze", json={
        "text": multi_dept_syllabus
    })
    assert upload_dept.status_code == 200
    dept_cur = client.get("/api/curriculum/active").get_json()
    dept_names = dept_cur.get("extracted_subjects", [])
    print("\n[Test 3] Multi-department extracted subjects:", dept_names)
    
    # Must contain IT subjects
    assert "Database Management Systems" in dept_names
    assert "Web Technologies" in dept_names
    # Must NOT contain Mechanical subjects
    assert "Dynamics of Machinery" not in dept_names
    assert "Heat Transfer" not in dept_names
    assert "Design of Machine Elements" not in dept_names

    print("\n" + "="*70)
    print(" >>> ALL AUTHORITATIVE COLLEGE SYLLABUS MAPPING CHECKS PASSED! <<<")
    print("="*70)

if __name__ == "__main__":
    test_college_syllabus_mapping()
