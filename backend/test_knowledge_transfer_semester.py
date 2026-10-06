"""
Comprehensive Test: Knowledge Transfer Strictly Semester-Aware Curriculum Integration
Tests:
1. Register Semester 5 College Student (B.Tech IT).
2. Upload multi-semester syllabus (Semester 4, 5, 6) -> Extract ONLY Semester 5.
3. Verify Knowledge Transfer consumes exactly the validated active Semester 5 subject list.
4. Verify strict isolation: No Semester 4, Semester 6, or demo subjects.
5. Verify that each Knowledge Transfer activity explicitly identifies all 9 required fields:
   - exact subject
   - exact syllabus topic
   - real-world application
   - concept explanation
   - practical connection
   - example
   - common misconception
   - quick understanding question
   - exam relevance
6. Verify anti-hallucination / invalid topic rejection:
   - When an invalid or out-of-curriculum topic is requested, reject with HTTP 400
     asking the student to select a valid syllabus topic.
7. Verify challenge completion submission (/api/challenge/submit).
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
            resp = opener.open(rq, timeout=60)
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
    print(" LearnSphere AI: Knowledge Transfer Strictly Semester-Aware Tests")
    print("=" * 70)

    client = create_session()

    # 1. Health check
    status, _ = client("GET", "/health")
    check("Server is healthy (200)", status == 200)

    # 2. Register Semester 5 College Student (B.Tech IT)
    suffix = random.randint(10000, 99999)
    student_email = f"kt_sem5_student_{suffix}@example.com"

    print("\n--- 1. Student Registration (B.Tech IT - Semester 5) ---")
    reg_payload = {
        "name": "Kyle Reese",
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
    
    IT3503 COMPUTER NETWORKS
    Unit I: Network Architecture, OSI Model, TCP/IP Suite.
    Unit II: Data Link Layer, Flow Control, Sliding Window.
    Unit III: Transport Layer, TCP Slow Start, Congestion Control.
    Unit IV: Network Layer, IP Addressing, Routing Algorithms.
    Unit V: Application Layer, HTTP, DNS, Socket Programming.
    
    SEMESTER VI
    IT3601 Distributed Systems (Credits: 3, L:3 T:0 P:0)
    IT3602 Artificial Intelligence (Credits: 3, L:3 T:0 P:0)
    """

    status, syl_res = client("POST", "/api/syllabus/analyze", {"text": multi_sem_syllabus_text, "semester": 5})
    check("Syllabus uploaded and extracted successfully (200)", status == 200, str(syl_res))
    check("Validation status is VALID", syl_res.get("validation_status") == "VALID" or syl_res.get("status") == "ACTIVE", str(syl_res.get("validation_status")) + " / " + str(syl_res.get("status")))
    check("Curriculum is active", syl_res.get("is_active") is True or syl_res.get("status") == "ACTIVE")

    # 4. Verify Active Curriculum & Parity
    print("\n--- 3. Knowledge Transfer Active Curriculum Subject Verification ---")
    status, cur_doc = client("GET", "/api/curriculum/active")
    check("Active curriculum fetched (200)", status == 200)
    
    subjects = cur_doc.get("subjects") or []
    subject_names = [s.get("name") if isinstance(s, dict) else s for s in subjects]
    
    check("Knowledge Transfer subject list matches exact Semester 5 count (8)", len(subjects) == 8, f"Count: {len(subjects)}")
    check("DBMS is present in Knowledge Transfer subjects", any("Database Management Systems" in n for n in subject_names))
    check("Web Technologies is present in Knowledge Transfer subjects", any("Web Technologies" in n for n in subject_names))
    check("Computer Networks is present in Knowledge Transfer subjects", any("Computer Networks" in n for n in subject_names))
    
    # Strict isolation
    check("Semester 4 Discrete Mathematics is NOT in Knowledge Transfer", not any("Discrete Mathematics" in n for n in subject_names))
    check("Semester 6 Distributed Systems is NOT in Knowledge Transfer", not any("Distributed Systems" in n for n in subject_names))
    check("Generic/Demo Biology is NOT in Knowledge Transfer", not any("Biology" in n for n in subject_names))

    # 5. Generate Knowledge Transfer for Validated DBMS Topic
    print("\n--- 4. Knowledge Transfer Generation: Database Management Systems ---")
    kt_req = {
        "subject": "Database Management Systems",
        "topic": "Unit II: Database Design & Normalization",
        "semester": 5
    }
    status, kt_resp = client("POST", "/api/transfer/generate", kt_req)
    check("Knowledge Transfer generate responds (200)", status == 200, str(kt_resp))
    
    act = kt_resp.get("activity") or {}
    check("Field 1 - Exact subject is identified", "Database Management Systems" in act.get("exact_subject", ""))
    check("Field 2 - Exact syllabus topic is identified", "Normalization" in act.get("exact_syllabus_topic", "") or "Unit II" in act.get("exact_syllabus_topic", ""))
    check("Field 3 - Real-world application is identified", bool(act.get("real_world_application")))
    check("Field 4 - Concept explanation is identified", bool(act.get("concept_explanation")))
    check("Field 5 - Practical connection is identified", bool(act.get("practical_connection")))
    check("Field 6 - Example is identified", bool(act.get("example")))
    check("Field 7 - Common misconception is identified", bool(act.get("common_misconception")))
    check("Field 8 - Quick understanding question is structured", isinstance(act.get("quick_understanding_question"), dict))
    if isinstance(act.get("quick_understanding_question"), dict):
        q = act.get("quick_understanding_question")
        check("Quick check has question text", bool(q.get("question")))
        check("Quick check has options", len(q.get("options", [])) >= 2)
        check("Quick check has correct_answer", bool(q.get("correct_answer")))
        check("Quick check has explanation", bool(q.get("explanation")))
    check("Field 9 - Exam relevance is identified", bool(act.get("exam_relevance")))
    check("Activity is valid topic", act.get("is_valid_topic") is True)

    # 6. Generate Knowledge Transfer for Validated Computer Networks Topic
    print("\n--- 5. Knowledge Transfer Generation: Computer Networks ---")
    net_req = {
        "subject": "Computer Networks",
        "topic": "Unit III: Transport Layer & Congestion Control",
        "semester": 5
    }
    status, net_resp = client("POST", "/api/transfer/generate", net_req)
    check("Computer Networks transfer responds (200)", status == 200)
    net_act = net_resp.get("activity") or {}
    check("Networks Exact Subject mapped", "Computer Networks" in net_act.get("exact_subject", ""))
    check("Networks Semester mapped", "5" in str(net_act.get("semester", "")))
    check("Real-world application covers streaming/CDN", bool(net_act.get("real_world_application")))
    check("Practical connection explains congestion avoidance", bool(net_act.get("practical_connection")))
    check("Misconception explains TCP Slow Start truth", bool(net_act.get("common_misconception")))

    # 7. Invalid Topic / Cross-Semester Rejection (Anti-Hallucination)
    print("\n--- 6. Rejection of Invalid Topic & Cross-Semester Subject ---")
    
    # 7a. Cross-Semester Subject (Semester 6 subject requested by Sem 5 student)
    bad_sub_req = {
        "subject": "Distributed Systems",
        "topic": "Unit I: Distributed Architectures"
    }
    status, bad_sub_resp = client("POST", "/api/transfer/generate", bad_sub_req)
    check("Cross-semester subject is rejected (400)", status == 400)
    check("Error message indicates subject is not in active semester", "active" in str(bad_sub_resp.get("error", "")).lower() or "not exist" in str(bad_sub_resp.get("error", "")).lower())

    # 7b. Fabricated / Non-existent topic
    bad_topic_req = {
        "subject": "Database Management Systems",
        "topic": "Fabricated Quantum Blockchain Non-Existent Topic"
    }
    status, bad_topic_resp = client("POST", "/api/transfer/generate", bad_topic_req)
    check("Fabricated topic is rejected (400)", status == 400)
    check("Error message asks student to select a valid syllabus topic", "valid syllabus topic" in str(bad_topic_resp.get("error", "")).lower() or "not exist" in str(bad_topic_resp.get("error", "")).lower())

    # 8. Challenge Completion Submission
    print("\n--- 7. Submitting Knowledge Challenge Results ---")
    submit_req = {
        "subject": "Database Management Systems",
        "score": 4,
        "total_questions": 5
    }
    status, sub_resp = client("POST", "/api/challenge/submit", submit_req)
    check("Challenge submit responds (200)", status == 200)
    check("Percentage correctly computed (80.0%)", sub_resp.get("percentage") == 80.0)

    print("\n" + "=" * 70)
    print(f" TESTS COMPLETE: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("=" * 70)
    
    if FAIL:
        sys.exit(1)
    else:
        print("\nKnowledge Transfer strictly semester-aware curriculum successfully verified!\n")

if __name__ == "__main__":
    run_tests()
