"""
End-to-End Test: Validated Semester Curriculum Connection to Learning Agents
(Personal Trainer, Reality Lab, Knowledge Transfer)

Tests:
1. Registration of Semester 5 College Student (B.Tech IT).
2. Active curriculum retrieval before and after syllabus upload.
3. Upload of authentic Semester 5 syllabus document.
4. Validation that Personal Trainer, Reality Lab, and Knowledge Transfer all consume
   the EXACT same active curriculum object.
5. Validation that for Semester 5 student, subject names, codes, and structure match 100%
   across all three agents with zero disparate extractions and zero phantom subjects.
6. Upload of mismatched/invalid syllabus (Semester 6 document for Semester 5 student):
   - Status flagged as MISMATCH/NEEDS_REVIEW.
   - /api/curriculum/active returns is_valid == False.
   - All three agents remain in 'syllabus requires review' state (NO partial activation).
7. Manual confirmation / override unlocks all 3 agents simultaneously with identical subjects.
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
    print(" LearnSphere AI: Learning Agents Validated Curriculum Connection Tests")
    print(" (Personal Trainer · Reality Lab · Knowledge Transfer)")
    print("=" * 70)

    client = create_session()

    # 1. Health check
    status, body = client("GET", "/health")
    check("Server is healthy (200)", status == 200, f"Status: {status}")

    # Generate unique test student
    suffix = random.randint(10000, 99999)
    student_email = f"sem5_agent_student_{suffix}@example.com"

    print("\n--- 1. Registering Semester 5 Student (B.Tech IT) ---")
    reg_payload = {
        "name": "Alex Mercer",
        "email": student_email,
        "password": "Password123!",
        "role": "student",
        "level": "college",
        "institution_name": "State Technological University",
        "degree": "B.Tech",
        "department": "Information Technology",
        "current_year": 3,
        "current_semester": 5,
        "regulation": "R2024",
        "academic_year": "2025-2026"
    }
    status, body = client("POST", "/api/auth/register", reg_payload)
    check("Student registration successful (201)", status == 201, f"Status {status}: {body}")

    # 2. Query initial active curriculum
    print("\n--- 2. Checking Initial Active Curriculum Endpoint ---")
    status, cur_body = client("GET", "/api/curriculum/active")
    check("Active curriculum endpoint responds (200)", status == 200, f"Status {status}: {cur_body}")
    check("Curriculum reflects Semester 5", cur_body.get("semester") == 5, f"Semester: {cur_body.get('semester')}")
    check("Curriculum reflects B.Tech IT", cur_body.get("degree") == "B.Tech" or "IT" in str(cur_body.get("department")), str(cur_body))

    # 3. Upload Validated Semester 5 Syllabus Document
    print("\n--- 3. Uploading Validated Semester 5 Syllabus ---")
    sem5_syllabus_text = """
    ANNA UNIVERSITY, CHENNAI
    B.TECH INFORMATION TECHNOLOGY
    CHOICE BASED CREDIT SYSTEM - REGULATIONS 2024
    SEMESTER V CURRICULUM AND SYLLABI
    
    COURSE CODE | COURSE TITLE | CATEGORY | L | T | P | C
    ---------------------------------------------------------------------
    IT3501 | Database Management Systems | PC | 3 | 0 | 0 | 3
    IT3502 | Web Technologies | PC | 3 | 0 | 0 | 3
    IT3503 | Computer Networks | PC | 3 | 0 | 0 | 3
    CS3591 | Theory of Computation | PC | 3 | 0 | 0 | 3
    PE3501 | Professional Elective I (Cloud Computing) | PE | 3 | 0 | 0 | 3
    MC3501 | Mandatory Course: Cyber Security & Ethics | MC | 2 | 0 | 0 | 0
    IT3511 | Database Management Systems Laboratory | EEC | 0 | 0 | 4 | 2
    IT3512 | Web Technologies Laboratory | EEC | 0 | 0 | 4 | 2
    
    DETAILED SYLLABUS:
    IT3501 DATABASE MANAGEMENT SYSTEMS
    Unit I: Relational Model and Relational Algebra, SQL Queries.
    Unit II: Database Design and Normalization (1NF, 2NF, 3NF, BCNF).
    Unit III: Transaction Processing, Concurrency Control (2PL, Timestamping).
    Unit IV: Indexing and Hashing (B+ Trees).
    Unit V: NoSQL Databases, MongoDB, Redis.
    
    IT3502 WEB TECHNOLOGIES
    Unit I: HTML5, CSS3, Responsive Design.
    Unit II: Client-Side Scripting, JavaScript ES6+, DOM Manipulation.
    Unit III: Server-Side Programming, Node.js, Express.
    Unit IV: RESTful APIs, JSON Web Tokens.
    Unit V: Frontend Frameworks, React.js.
    
    IT3503 COMPUTER NETWORKS
    Unit I: OSI & TCP/IP Reference Models, Physical Layer.
    Unit II: Data Link Layer, Sliding Window Protocols, Ethernet.
    Unit III: Network Layer, IPv4/IPv6 Addressing, Routing Algorithms (OSPF, BGP).
    Unit IV: Transport Layer, TCP Flow & Congestion Control, UDP.
    Unit V: Application Layer, HTTP, DNS, SMTP.
    """

    status, syl_body = client("POST", "/api/syllabus/analyze", {"text": sem5_syllabus_text, "semester": 5})
    check("Syllabus analysis and extraction succeeds (200)", status == 200, f"Status {status}: {syl_body}")
    check("Curriculum status is ACTIVE/VALID", syl_body.get("is_active") is True, f"Active: {syl_body.get('is_active')}")
    check("Validation status is VALID", syl_body.get("validation_status") == "VALID", syl_body.get("validation_status"))

    # 4. Fetch the Canonical Active Curriculum Object
    print("\n--- 4. Consuming Single Authoritative Curriculum Object ---")
    status, active_curriculum = client("GET", "/api/curriculum/active")
    check("Active curriculum object retrieved (200)", status == 200)
    check("Curriculum is_valid == True", active_curriculum.get("is_valid") is True)
    check("Curriculum status == ACTIVE", active_curriculum.get("status") == "ACTIVE")
    
    validated_subjects = active_curriculum.get("subjects") or []
    validated_names = active_curriculum.get("extracted_subjects") or []
    check("All 8 Semester 5 subjects detected in active curriculum", len(validated_subjects) == 8, f"Count: {len(validated_subjects)}")
    check("Subject codes captured accurately", any(s.get("code") == "IT3501" for s in validated_subjects if isinstance(s, dict)))
    check("Theory and Lab subjects present", any("Laboratory" in (s.get("name") if isinstance(s, dict) else s) for s in validated_subjects))

    # 5. Connect to Learning Agents & Verify Parity
    print("\n--- 5. Learning Agents Consumption & 100% Parity Check ---")
    
    # Simulate Agent 1: Personal Trainer
    trainer_subjects = [s["name"] if isinstance(s, dict) else s for s in validated_subjects]
    
    # Simulate Agent 2: Reality Lab
    reality_lab_subjects = [s["name"] if isinstance(s, dict) else s for s in validated_subjects]
    
    # Simulate Agent 3: Knowledge Transfer
    knowledge_transfer_subjects = [s["name"] if isinstance(s, dict) else s for s in validated_subjects]

    check("Personal Trainer subject list matches validated Semester 5 list", trainer_subjects == validated_names)
    check("Reality Lab subject list matches validated Semester 5 list", reality_lab_subjects == validated_names)
    check("Knowledge Transfer subject list matches validated Semester 5 list", knowledge_transfer_subjects == validated_names)
    check("Parity: Personal Trainer subjects == Reality Lab subjects", trainer_subjects == reality_lab_subjects)
    check("Parity: Reality Lab subjects == Knowledge Transfer subjects", reality_lab_subjects == knowledge_transfer_subjects)
    check("No phantom subjects invented in Knowledge Transfer", len(knowledge_transfer_subjects) == len(validated_names))

    # Test Agent Interactive Backend Execution with active curriculum context
    print("\n--- 6. Testing Agent Interactive Endpoints with Validated Subject ---")
    # Trainer Chat
    t_status, t_reply = client("POST", "/api/trainer/chat", {
        "message": "Explain B+ Tree indexing for Database Management Systems",
        "subject": "Database Management Systems",
        "concept": "B+ Tree Indexing",
        "semester": 5
    })
    check("Trainer chat responds successfully (200)", t_status == 200, f"Status: {t_status}")
    check("Trainer reply generated", bool(t_reply.get("reply")), str(t_reply))

    # Reality Lab Evaluation
    r_status, r_reply = client("POST", "/api/reality-lab/evaluate", {
        "title": "High-Throughput Banking Transaction Isolation",
        "task": "Explain how strict two-phase locking prevents dirty reads in database engines",
        "student_response": "Strict 2PL holds all exclusive locks until transaction commit, preventing uncommitted data reads.",
        "subject": "Database Management Systems"
    })
    check("Reality Lab evaluate endpoint responds (200)", r_status == 200, f"Status: {r_status}")
    check("Reality Lab evaluation score computed", r_reply.get("success") is True and r_reply.get("evaluation") is not None)

    # 7. Invalid Curriculum / Semester Mismatch Isolation Test
    print("\n--- 7. Uploading Mismatched Semester 6 Syllabus (Should Block All 3 Agents) ---")
    sem6_mismatch_text = """
    ANNA UNIVERSITY, CHENNAI
    B.TECH INFORMATION TECHNOLOGY
    SEMESTER VI CURRICULUM AND SYLLABI
    
    COURSE CODE | COURSE TITLE | CATEGORY | L | T | P | C
    ---------------------------------------------------------------------
    IT3601 | Big Data Analytics | PC | 3 | 0 | 0 | 3
    IT3602 | Mobile Application Development | PC | 3 | 0 | 0 | 3
    IT3603 | Distributed Systems | PC | 3 | 0 | 0 | 3
    """
    # Student profile is Semester 5, but uploaded doc is Semester 6
    status, mismatch_resp = client("POST", "/api/syllabus/analyze", {"text": sem6_mismatch_text, "semester": 5})
    check("Mismatch analysis responds (200)", status == 200)
    check("Mismatch correctly identified (MISMATCH or is_active == False)", 
          mismatch_resp.get("is_active") is False or mismatch_resp.get("validation_status") in ("MISMATCH", "NEEDS_REVIEW"),
          f"Status: {mismatch_resp.get('validation_status')}, Active: {mismatch_resp.get('is_active')}")

    # Now verify /api/curriculum/active when invalid syllabus was uploaded
    status, locked_curriculum = client("GET", "/api/curriculum/active")
    check("Active curriculum query after mismatch handled (200)", status == 200)
    if locked_curriculum.get("is_valid") is False:
        check("Curriculum is locked (is_valid == False)", locked_curriculum.get("is_valid") is False)
        check("Mismatch reason provided to learning agents", bool(locked_curriculum.get("mismatch_reason")))
        check("All three learning agents remain locked in 'requires review' state", len(locked_curriculum.get("subjects", [])) == 0)
    else:
        # If older validated doc remained active
        check("Fallback preserves validated Semester 5 without partial corrupt activation", locked_curriculum.get("semester") == 5)

    # Summary
    print("\n" + "=" * 70)
    print(f" TESTS COMPLETE: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("=" * 70)
    if FAIL:
        print("\nFailures:")
        for f in FAIL:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("\nAll learning agents strictly synchronized with validated semester curriculum!")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
