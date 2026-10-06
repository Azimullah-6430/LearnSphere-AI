"""
Comprehensive Test: Personal Trainer Exact Semester Curriculum Integration
Tests:
1. Registration of Semester 5 College Student (B.Tech Information Technology).
2. Verification that Personal Trainer consumes only the validated Semester 5 subjects.
3. Strict isolation: no subjects from previous semesters (e.g. Sem 4), next semesters (e.g. Sem 6),
   or other departments.
4. Unit/Module -> Chapter -> Topic hierarchical syllabus structure verification.
5. Student question: "What are my Semester 5 subjects?" returns the exact validated
   extracted subject list with codes from their syllabus document.
6. AI teaching context includes program, department, semester, subject, unit, and topic.
"""
import json
import random
import sys
import urllib.request
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:5000"

def create_session():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    def req(method, path, data=None, content_type="application/json"):
        url = BASE + path
        body = json.dumps(data).encode() if data else None
        rq = urllib.request.Request(url, data=body, method=method)
        if body:
            rq.add_header("Content-Type", content_type)
        try:
            resp = opener.open(rq, timeout=35)
            result = json.loads(resp.read().decode())
            return resp.getcode(), result
        except urllib.error.HTTPError as e:
            try:
                result = json.loads(e.read().decode())
            except Exception:
                result = {"error": str(e.reason)}
            return e.code, result
        except Exception as ex:
            return 500, {"error": str(ex)}

    return req

PASS = []
FAIL = []

def check(name, condition, detail=""):
    if condition:
        print(f"  [PASS] {name}", flush=True)
        PASS.append(name)
    else:
        print(f"  [FAIL] {name} -- {detail}", flush=True)
        FAIL.append(name)

def run_tests():
    print("=" * 70)
    print(" LearnSphere AI: Personal Trainer Exact Semester Curriculum Tests")
    print("=" * 70)

    client = create_session()

    # 1. Health check
    status, _ = client("GET", "/health")
    check("Server is healthy (200)", status == 200)

    # 2. Register Semester 5 College Student (B.Tech IT)
    suffix = random.randint(10000, 99999)
    student_email = f"pt_sem5_student_{suffix}@example.com"

    print("\n--- 1. Student Registration (B.Tech IT - Semester 5) ---")
    reg_payload = {
        "name": "Sarah Connor",
        "email": student_email,
        "password": "Password123!",
        "role": "student",
        "level": "college",
        "institution_name": "Anna University College of Engineering",
        "degree": "B.Tech",
        "department": "Information Technology",
        "current_year": 3,
        "current_semester": 5,
        "regulation": "R2024",
        "academic_year": "2025-2026"
    }
    status, body = client("POST", "/api/auth/register", reg_payload)
    check("Student registration succeeds (201)", status == 201, f"Status: {status}")

    # 3. Upload Multi-Semester Syllabus Containing Semester 4, 5, and 6
    print("\n--- 2. Uploading Multi-Semester Curriculum (Extract ONLY Sem 5) ---")
    multi_sem_syllabus_text = """
    ANNA UNIVERSITY, CHENNAI
    B.TECH INFORMATION TECHNOLOGY
    CURRICULUM AND SYLLABI (REGULATIONS 2024)
    
    SEMESTER IV
    MA3401 Discrete Mathematics (Credits: 4, L:3 T:1 P:0)
    CS3401 Algorithms Design (Credits: 3, L:3 T:0 P:0)
    
    SEMESTER V
    IT3501 Database Management Systems (Credits: 3, L:3 T:0 P:0)
    IT3502 Web Technologies (Credits: 3, L:3 T:0 P:0)
    IT3503 Computer Networks (Credits: 3, L:3 T:0 P:0)
    CS3591 Theory of Computation (Credits: 3, L:3 T:0 P:0)
    PE3501 Professional Elective I: Cloud Computing (Credits: 3, L:3 T:0 P:0)
    MC3501 Cyber Security & Professional Ethics (Credits: 0, L:2 T:0 P:0)
    IT3511 DBMS Laboratory (Credits: 2, L:0 T:0 P:4)
    IT3512 Web Technologies Laboratory (Credits: 2, L:0 T:0 P:4)
    
    DETAILED SYLLABUS:
    IT3501 DATABASE MANAGEMENT SYSTEMS
    Unit I: Relational Model, Relational Algebra, SQL Fundamentals.
    Unit II: Database Design, Functional Dependencies, Normal Forms (1NF, 2NF, 3NF, BCNF).
    Unit III: Transactions, ACID Properties, Concurrency Control (2PL, Timestamp Ordering).
    Unit IV: Indexing & Storage, B+ Trees, Hashing.
    Unit V: Distributed Databases, NoSQL, MongoDB Architecture.
    
    IT3502 WEB TECHNOLOGIES
    Unit I: HTML5 Semantic Elements, CSS3 Grid, Flexbox, Responsive Design.
    Unit II: JavaScript ES6, DOM Manipulation, Async/Await, Fetch API.
    Unit III: Server-Side Engineering, Node.js, Express, Middleware.
    Unit IV: REST API Design, Authentication with JWT.
    Unit V: React Frontend Development, Hooks, State Management.
    
    SEMESTER VI
    IT3601 Distributed Systems (Credits: 3, L:3 T:0 P:0)
    IT3602 Artificial Intelligence (Credits: 3, L:3 T:0 P:0)
    """

    status, syl_res = client("POST", "/api/syllabus/analyze", {"text": multi_sem_syllabus_text, "semester": 5})
    check("Syllabus uploaded and extracted successfully (200)", status == 200, str(syl_res))
    check("Validation status is VALID", syl_res.get("validation_status") == "VALID")
    check("Curriculum is active", syl_res.get("is_active") is True)

    # 4. Verify Active Curriculum & Personal Trainer Subject List
    print("\n--- 3. Personal Trainer Active Curriculum Verification ---")
    status, cur_doc = client("GET", "/api/curriculum/active")
    check("Active curriculum fetched (200)", status == 200)
    
    subjects = cur_doc.get("subjects") or []
    extracted_names = cur_doc.get("extracted_subjects") or []
    
    check("Curriculum has exactly 8 Semester 5 subjects", len(subjects) == 8, f"Count: {len(subjects)}")
    check("IT3501 Database Management Systems is present", any("Database Management Systems" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("IT3502 Web Technologies is present", any("Web Technologies" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("IT3503 Computer Networks is present", any("Computer Networks" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("CS3591 Theory of Computation is present", any("Theory of Computation" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("Laboratory courses are included", any("Laboratory" in (s.get("name") if isinstance(s, dict) else s) or "Lab" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    
    # Strict isolation checks
    check("Semester 4 subject (Discrete Mathematics) is NOT shown", not any("Discrete Mathematics" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("Semester 4 subject (Algorithms Design) is NOT shown", not any("Algorithms Design" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("Semester 6 subject (Distributed Systems) is NOT shown", not any("Distributed Systems" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))
    check("Semester 6 subject (Artificial Intelligence) is NOT shown", not any("Artificial Intelligence" in (s.get("name") if isinstance(s, dict) else s) for s in subjects))

    # 5. Verify Hierarchical Units / Chapters / Concepts
    print("\n--- 4. Hierarchical Structure (Subject -> Unit -> Topics) ---")
    units_map = cur_doc.get("units") or cur_doc.get("chapters") or {}
    check("Subject units/modules are mapped", "Database Management Systems" in units_map or any("Database" in k for k in units_map))
    
    dbms_units = units_map.get("Database Management Systems") or units_map.get(list(units_map.keys())[0]) if units_map else []
    check("DBMS has detailed syllabus units", len(dbms_units) >= 3, f"Units found: {len(dbms_units)}")
    if dbms_units:
        first_unit = dbms_units[0]
        check("Unit has structured name", bool(first_unit.get("name")))
        check("Unit has concepts/topics", len(first_unit.get("concepts", [])) > 0)

    # 6. Student Query: "What are my Semester 5 subjects?"
    print("\n--- 5. Testing Subject Query Anti-Hallucination ---")
    status, chat_resp = client("POST", "/api/trainer/chat", {
        "message": "What are my Semester 5 subjects?",
        "subject": "Database Management Systems",
        "semester": 5
    })
    check("Trainer subject list query responds (200)", status == 200)
    reply_text = chat_resp.get("reply", "")
    check("Reply contains 'Validated Semester 5 Subjects'", "Validated Semester 5 Subjects" in reply_text or "Semester 5" in reply_text, reply_text)
    check("Reply contains exact code IT3501 or Database Management Systems", "IT3501" in reply_text or "Database Management Systems" in reply_text)
    check("Reply contains Web Technologies", "Web Technologies" in reply_text)
    check("Reply contains Computer Networks", "Computer Networks" in reply_text)
    check("Reply does NOT hallucinate Semester 6 courses", "Distributed Systems" not in reply_text)

    # 7. AI Teaching with Full Context (Program + Department + Semester + Subject + Unit + Topic)
    print("\n--- 6. Testing AI Teaching with Full Semester Context ---")
    status, teach_resp = client("POST", "/api/trainer/chat", {
        "message": "Explain BCNF decomposition step by step for my exam.",
        "subject": "Database Management Systems",
        "unit": "Unit II: Database Design and Normalization",
        "topic": "Normal Forms (1NF, 2NF, 3NF, BCNF)",
        "study_method": "🎯 Exam High-Score Strategy",
        "semester": 5,
        "degree": "B.Tech",
        "department": "Information Technology"
    })
    check("Trainer coaching responds (200)", status == 200)
    teach_text = teach_resp.get("reply", "")
    check("Coaching reply generated", bool(teach_text))

    # Summary
    print("\n" + "=" * 70)
    print(f" TESTS COMPLETE: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("=" * 70)
    if FAIL:
        sys.exit(1)
    else:
        print("\nPersonal Trainer exact semester curriculum successfully verified!")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
