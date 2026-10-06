"""
Comprehensive Test: Reality Lab Strictly Semester-Aware Curriculum Integration
Tests:
1. Register Semester 5 College Student (B.Tech IT).
2. Upload multi-semester syllabus (Semester 4, 5, 6) -> Extract ONLY Semester 5.
3. Verify Reality Lab consumes exactly the validated active Semester 5 subject list.
4. Verify strict isolation: No Semester 4, Semester 6, or demo subjects.
5. Verify that each practical activity explicitly identifies all 10 required fields:
   - Subject
   - Semester
   - Syllabus topic
   - Real-world / practical concept
   - Materials
   - Procedure
   - Observation
   - Theory connection
   - Learning outcome
   - Exam relevance
6. Verify anti-hallucination / unsupported topic handling:
   - When a purely abstract or unsupported topic is requested, return is_supported = False
     with an explicit unsupported message rather than fabricating a false connection.
7. Verify practical evaluation endpoint (/api/reality-lab/evaluate).
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
    print(" LearnSphere AI: Reality Lab Strictly Semester-Aware Tests")
    print("=" * 70)

    client = create_session()

    # 1. Health check
    status, _ = client("GET", "/health")
    check("Server is healthy (200)", status == 200)

    # 2. Register Semester 5 College Student (B.Tech IT)
    suffix = random.randint(10000, 99999)
    student_email = f"rl_sem5_student_{suffix}@example.com"

    print("\n--- 1. Student Registration (B.Tech IT - Semester 5) ---")
    reg_payload = {
        "name": "Marcus Wright",
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
    check("Validation status is VALID", syl_res.get("validation_status") == "VALID")
    check("Curriculum is active", syl_res.get("is_active") is True)

    # 4. Verify Active Curriculum & Parity
    print("\n--- 3. Reality Lab Active Curriculum Subject Verification ---")
    status, cur_doc = client("GET", "/api/curriculum/active")
    check("Active curriculum fetched (200)", status == 200)
    
    subjects = cur_doc.get("subjects") or []
    subject_names = [s.get("name") if isinstance(s, dict) else s for s in subjects]
    
    check("Reality Lab subject list matches exact Semester 5 count (8)", len(subjects) == 8, f"Count: {len(subjects)}")
    check("DBMS is present in Reality Lab subjects", any("Database Management Systems" in n for n in subject_names))
    check("Web Technologies is present in Reality Lab subjects", any("Web Technologies" in n for n in subject_names))
    check("Computer Networks is present in Reality Lab subjects", any("Computer Networks" in n for n in subject_names))
    
    # Strict isolation
    check("Semester 4 Discrete Mathematics is NOT in Reality Lab", not any("Discrete Mathematics" in n for n in subject_names))
    check("Semester 6 Distributed Systems is NOT in Reality Lab", not any("Distributed Systems" in n for n in subject_names))
    check("Generic/Demo Biology is NOT in Reality Lab", not any("Biology" in n for n in subject_names))

    # 5. Generate Reality Lab Practical Activity for Database Management Systems
    print("\n--- 4. Reality Lab Practical Activity: Database Management Systems ---")
    lab_req = {
        "subject": "Database Management Systems",
        "module": "Unit II: Database Design, Normalization & Indexing",
        "difficulty": "Medium",
        "syllabus_context": "B.Tech IT Semester 5 Database Management Systems"
    }
    status, lab_resp = client("POST", "/api/reality-lab/generate", lab_req)
    check("Reality Lab generate responds (200)", status == 200, str(lab_resp))
    
    lab = lab_resp.get("lab") or {}
    check("Field 1 - Subject is explicitly identified", "Database Management Systems" in lab.get("subject", ""))
    check("Field 2 - Semester is explicitly identified", "5" in str(lab.get("semester", "")))
    check("Field 3 - Syllabus topic is explicitly identified", bool(lab.get("syllabus_topic")))
    check("Field 4 - Real-world/practical concept is explicitly identified", bool(lab.get("practical_concept")))
    check("Field 5 - Materials list is non-empty", isinstance(lab.get("materials"), list) and len(lab.get("materials")) > 0)
    check("Field 6 - Procedure steps are non-empty", isinstance(lab.get("procedure"), list) and len(lab.get("procedure")) >= 3)
    check("Field 7 - Observation is explicitly identified", bool(lab.get("observation")))
    check("Field 8 - Theory connection is explicitly identified", bool(lab.get("theory_connection")))
    check("Field 9 - Learning outcome is explicitly identified", bool(lab.get("learning_outcome")))
    check("Field 10 - Exam relevance is explicitly identified", bool(lab.get("exam_relevance")))
    check("Practical activity is supported by syllabus", lab.get("is_supported") is True)

    # 6. Generate Reality Lab Practical Activity for Computer Networks
    print("\n--- 5. Reality Lab Practical Activity: Computer Networks ---")
    net_req = {
        "subject": "Computer Networks",
        "module": "Unit III: Transport Layer Protocols & Congestion Control",
        "difficulty": "Hard"
    }
    status, net_resp = client("POST", "/api/reality-lab/generate", net_req)
    check("Computer Networks activity responds (200)", status == 200)
    net_lab = net_resp.get("lab") or {}
    check("Networks Subject correctly mapped", "Computer Networks" in net_lab.get("subject", ""))
    check("Networks Semester correctly mapped", "5" in str(net_lab.get("semester", "")))
    check("Materials include networking tools", any("Wireshark" in m or "Linux" in m or "Tool" in m for m in net_lab.get("materials", [])))
    check("Theory connection maps to TCP / Congestion algorithms", bool(net_lab.get("theory_connection")))
    check("Exam relevance mapped for Computer Networks", bool(net_lab.get("exam_relevance")))

    # 7. Unsupported / Pure Abstract Topic Handling (Anti-Hallucination)
    print("\n--- 6. Unsupported / Purely Abstract Theoretical Topic Handling ---")
    unsupported_req = {
        "subject": "Theory of Computation",
        "module": "Pure Abstract Non-Practical Topic",
        "difficulty": "Hard"
    }
    status, unsupp_resp = client("POST", "/api/reality-lab/generate", unsupported_req)
    check("Unsupported query responds (200)", status == 200)
    unsupp_lab = unsupp_resp.get("lab") or {}
    check("is_supported is False for unsupported theoretical topic", unsupp_lab.get("is_supported") is False)
    check("Clear unsupported explanation message provided", bool(unsupp_lab.get("unsupported_message")))

    # 8. Practical Solution AI Evaluation
    print("\n--- 7. Reality Lab Practical Solution AI Evaluation ---")
    eval_req = {
        "title": lab.get("title") or "High-Throughput E-Commerce Schema Optimization",
        "task": lab.get("task") or "Explain BCNF decomposition and B+ tree index latency reduction.",
        "student_response": "Decomposing into BCNF eliminates update anomalies by ensuring every determinant is a superkey. Composite B+ tree indexes replace O(N) table scans with O(log N) tree lookups.",
        "subject": "Database Management Systems"
    }
    status, eval_res = client("POST", "/api/reality-lab/evaluate", eval_req)
    check("Reality Lab evaluation responds (200)", status == 200)
    eval_data = eval_res.get("evaluation") or {}
    check("Evaluation score computed", eval_data.get("score") is not None and eval_data.get("score") > 0)
    check("Feedback provided", bool(eval_data.get("feedback")))

    print("\n" + "=" * 70)
    print(f" TESTS COMPLETE: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("=" * 70)
    
    if FAIL:
        sys.exit(1)
    else:
        print("\nReality Lab strictly semester-aware curriculum successfully verified!\n")

if __name__ == "__main__":
    run_tests()
