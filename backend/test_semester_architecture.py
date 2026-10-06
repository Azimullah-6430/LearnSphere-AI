"""
End-to-End Test for Strict Academic-Level and Semester-Aware Profile Architecture & Syllabus Mapping
Tests:
1. College student registration with all required college fields (institution, degree, department, current_year, current_semester, regulation, academic_year).
2. Authoritative profile persistence in database and retrieval via /api/auth/me.
3. Session restoration across logout/login and verification of semester context.
4. Profile update (PUT /api/user/profile) transitioning e.g. Semester 5 -> Semester 6 and persistence.
5. School student registration ensuring no college semester is forced.
6. Multi-semester syllabus mapping (extracting ONLY the student's current semester curriculum).
7. Semester mismatch detection (flagging mismatched document as MISMATCH, preventing silent activation, displaying warning).
8. Ambiguous syllabus detection (setting status to NEEDS_REVIEW).
9. Manual syllabus override confirmation (/api/syllabus/confirm-override).
10. Active curriculum retrieval (/api/syllabus) with scoped student context.
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
        print(f"  [PASS] {name}")
        PASS.append(name)
    else:
        print(f"  [FAIL] {name} -- {detail}")
        FAIL.append(name)

def run_tests():
    print("=" * 65)
    print(" LearnSphere AI: Semester-Aware Architecture & Syllabus E2E Tests")
    print("=" * 65)

    client = create_session()

    # 1. Health Check
    status, body = client("GET", "/health")
    check("Server is healthy", status == 200, f"Status: {status}")

    # Generate unique test emails
    suffix = random.randint(10000, 99999)
    college_email = f"college_student_{suffix}@example.com"
    school_email = f"school_student_{suffix}@example.com"

    print("\n--- 1. College Student Registration (Semester 5) ---")
    college_reg_payload = {
        "name": "Jane Doe Tech",
        "email": college_email,
        "password": "Password123!",
        "role": "student",
        "level": "college",
        "institution_name": "MIT Institute of Technology",
        "degree": "B.Tech",
        "department": "Information Technology",
        "current_year": 3,
        "current_semester": 5,
        "regulation": "R20",
        "academic_year": "2025-2026",
        "subjects": ["Software Engineering", "Web Technologies", "Computer Networks"]
    }
    status, body = client("POST", "/api/auth/register", college_reg_payload)
    check("College registration succeeds (201)", status == 201, f"Status {status}: {body}")
    user = body.get("user", {})
    check("User profile returned has level 'college'", user.get("level") == "college", str(user.get("level")))
    check("User profile has authoritative semester == 5", user.get("semester") == 5 or user.get("current_semester") == 5, f"semester: {user.get('semester')}, current_semester: {user.get('current_semester')}")
    check("User profile has degree 'B.Tech'", user.get("degree") == "B.Tech", str(user.get("degree")))
    check("User profile has department 'Information Technology'", user.get("department") == "Information Technology", str(user.get("department")))
    check("User profile has regulation 'R20'", user.get("regulation") == "R20", str(user.get("regulation")))
    check("User profile has academic_year '2025-2026'", user.get("academic_year") == "2025-2026", str(user.get("academic_year")))

    print("\n--- 2. Authenticated Profile Context (/api/auth/me) ---")
    status, me_body = client("GET", "/api/auth/me")
    check("Authenticated /api/auth/me succeeds (200)", status == 200, f"Status {status}: {me_body}")
    me_user = me_body.get("user", {})
    check("/api/auth/me returns semester == 5", me_user.get("semester") == 5 and me_user.get("current_semester") == 5, f"sem: {me_user.get('semester')}")
    check("/api/auth/me returns degree and department", me_user.get("degree") == "B.Tech" and me_user.get("department") == "Information Technology", f"{me_user.get('degree')}, {me_user.get('department')}")
    check("/api/auth/me returns institution_name", me_user.get("institution_name") == "MIT Institute of Technology", str(me_user.get("institution_name")))

    print("\n--- 3. School Student Registration (Isolation from College Fields) ---")
    school_client = create_session()
    school_reg_payload = {
        "name": "Alex School Student",
        "email": school_email,
        "password": "Password123!",
        "role": "student",
        "level": "school",
        "institution_name": "Delhi Public School",
        "board": "CBSE",
        "classLevel": "10",
        "stream": "General",
        "section": "A",
        "roll_number": "DPS-10A-042",
        "subjects": ["Mathematics", "Science", "Social Science", "English"]
    }
    status, school_body = school_client("POST", "/api/auth/register", school_reg_payload)
    check("School student registration succeeds (201)", status == 201, f"Status {status}: {school_body}")
    s_user = school_body.get("user", {})
    check("School student level is 'school'", s_user.get("level") == "school", str(s_user.get("level")))
    check("School student has board == 'CBSE'", s_user.get("board") == "CBSE", str(s_user.get("board")))
    check("School student has classLevel == '10'", str(s_user.get("classLevel") or s_user.get("class")) == "10", f"class: {s_user.get('classLevel')}")
    check("School student does NOT have college semester forced", s_user.get("semester") is None or s_user.get("semester") == "" or "semester" not in s_user, f"semester: {s_user.get('semester')}")

    print("\n--- 4. Multi-Semester & Exhaustive Subject Extraction (Extract ONLY Semester 5) ---")
    # A complete syllabus document containing Sem 4, Sem 5, Sem 6 with theory, labs, electives, and audits
    multi_sem_syllabus = """
    B.Tech Information Technology - Course Curriculum Scheme (R20)
    
    SEMESTER 4 SCHEME (Total: 3 Courses):
    - Discrete Mathematics (DM401) [Credits: 3, L:3 T:0 P:0] Core Theory
    - Data Structures (DS402) [Credits: 3, L:3 T:0 P:0] Core Theory
    - Operating Systems Lab (OS403L) [Credits: 1.5, L:0 T:0 P:3] Practical Lab

    SEMESTER 5 SCHEME OF INSTRUCTION (Total: 7 Courses):
    1. Software Engineering (IT501) [Credits: 3, L:3 T:0 P:0, Category: Theory Core]
    2. Web Technologies (IT502) [Credits: 3, L:3 T:0 P:0, Category: Theory Core]
    3. Computer Networks (IT503) [Credits: 3, L:3 T:0 P:0, Category: Theory Core]
    4. Professional Elective I: Cloud Infrastructure (IT504) [Credits: 3, L:3 T:0 P:0, Category: Professional Elective]
    5. Web Technologies Laboratory (IT505L) [Credits: 1.5, L:0 T:0 P:3, Category: Laboratory]
    6. Computer Networks Laboratory (IT506L) [Credits: 1.5, L:0 T:0 P:3, Category: Laboratory]
    7. Constitution of India (MC507) [Credits: 0, L:2 T:0 P:0, Category: Mandatory Audit]

    SEMESTER 6 SCHEME (Total: 3 Courses):
    - Cloud Computing (CC601) [Credits: 3, L:3 T:0 P:0]
    - Machine Learning (ML602) [Credits: 3, L:3 T:0 P:0]
    - Information Security Lab (IS603L) [Credits: 1.5, L:0 T:0 P:3]
    """

    status, syl_res = client("POST", "/api/syllabus/analyze", {
        "text": multi_sem_syllabus
    })
    check("Multi-semester syllabus analyze succeeds (200)", status == 200, f"Status: {status}, error: {syl_res.get('error')}")
    check("Multi-semester syllabus is marked VALID", syl_res.get("validation_status") == "VALID", str(syl_res.get("validation_status")))
    check("Multi-semester syllabus is activated immediately (is_active=True)", syl_res.get("is_active") is True, str(syl_res.get("is_active")))
    
    analysis = syl_res.get("analysis", {})
    extracted_subjects = analysis.get("extracted_subjects", [])
    check("Extracted subjects list is populated", len(extracted_subjects) >= 5, f"count: {len(extracted_subjects)}, list: {extracted_subjects}")
    
    # Verify ONLY Semester 5 subjects are present, and Sem 4 / Sem 6 subjects are excluded
    has_se = any("Software Engineering" in s for s in extracted_subjects)
    has_wt = any("Web Technologies" in s for s in extracted_subjects)
    has_discrete_math = any("Discrete Mathematics" in s for s in extracted_subjects)
    has_cloud_computing = any("Cloud Computing" in s for s in extracted_subjects)
    check("Target Semester 5 theory subject (Software Engineering) is present", has_se, str(extracted_subjects))
    check("Target Semester 5 theory subject (Web Technologies) is present", has_wt, str(extracted_subjects))
    check("Semester 4 subject (Discrete Mathematics) is NOT mixed in", not has_discrete_math, str(extracted_subjects))
    check("Semester 6 subject (Cloud Computing) is NOT mixed in", not has_cloud_computing, str(extracted_subjects))

    # Verify Laboratories and Electives were extracted and NOT silently discarded
    has_wt_lab = any("Web Technologies Lab" in s or "IT505L" in str(s) or "Laboratory" in s for s in extracted_subjects)
    has_elective = any("Cloud Infrastructure" in s or "Elective" in s or "IT504" in str(s) for s in extracted_subjects)
    check("Laboratory subjects were NOT discarded", has_wt_lab, str(extracted_subjects))
    check("Elective subjects were NOT discarded", has_elective, str(extracted_subjects))

    detailed_subjects = syl_res.get("syllabus", {}).get("subjects") or syl_res.get("analysis", {}).get("subjects") or []
    check("Detailed subject array is populated", len(detailed_subjects) >= 5, str(detailed_subjects))
    count_recorded = syl_res.get("syllabus", {}).get("extracted_subject_count") or syl_res.get("analysis", {}).get("extracted_subject_count", 0)
    check("Extracted subject count is recorded", count_recorded >= 5, str(count_recorded))

    print("\n--- 5. Active Curriculum Scoping & Retrieval (/api/syllabus) ---")
    status, my_syl = client("GET", "/api/syllabus")
    check("GET /api/syllabus succeeds (200)", status == 200, f"Status {status}")
    active_curriculum = my_syl.get("syllabus") or {}
    check("Retrieved curriculum is active", active_curriculum.get("is_active") is True or active_curriculum.get("status") == "ACTIVE", str(active_curriculum.get("status")))
    check("Retrieved curriculum matches student's semester == 5", active_curriculum.get("semester") == 5 or active_curriculum.get("current_semester") == 5, f"sem: {active_curriculum.get('semester')}")
    check("Retrieved curriculum contains degree/program B.Tech", active_curriculum.get("degree") == "B.Tech" or active_curriculum.get("program") == "B.Tech", str(active_curriculum.get("degree")))
    check("Retrieved curriculum contains department Information Technology", "Information Technology" in str(active_curriculum.get("department") or active_curriculum.get("branch")), str(active_curriculum.get("department")))

    print("\n--- 6. Semester Mismatch Validation (Semester 6 Document for Semester 5 Profile) ---")
    # Upload syllabus explicitly for Semester 6 only
    mismatched_syllabus = """
    B.Tech Information Technology - 6th Semester (Semester VI) Course Blueprint
    Exclusively for Semester 6 Students:
    1. Cloud Infrastructure & Virtualization (Unit I Microservices, Unit II Serverless)
    2. Deep Learning Systems (Unit I CNN, Unit II Transformer Architecture)
    3. DevOps Pipeline & CI/CD (Unit I Docker, Unit II Kubernetes)
    """

    status, mismatch_res = client("POST", "/api/syllabus/analyze", {
        "text": mismatched_syllabus
    })
    check("Mismatch analyze returns 200 with structured evaluation", status == 200, f"Status: {status}")
    check("Mismatched syllabus flagged as MISMATCH", mismatch_res.get("validation_status") == "MISMATCH", str(mismatch_res.get("validation_status")))
    check("Mismatched syllabus is NOT activated (is_active=False)", mismatch_res.get("is_active") is False, str(mismatch_res.get("is_active")))
    check("Clear warning message provided in mismatch_reason", "Semester 5" in str(mismatch_res.get("mismatch_reason", "")), str(mismatch_res.get("mismatch_reason")))

    # Verify that the active curriculum still remains the previous valid Semester 5 curriculum
    status, verify_syl = client("GET", "/api/syllabus")
    cur_syl = verify_syl.get("syllabus", {})
    check("Active syllabus was NOT silently overwritten by mismatched document", cur_syl.get("semester") == 5 and cur_syl.get("is_active") is True, f"status: {cur_syl.get('status')}, sem: {cur_syl.get('semester')}")

    print("\n--- 7. Manual Override / Confirmation Flow ---")
    mismatch_syl_id = mismatch_res.get("syllabus_id")
    check("Mismatched syllabus has syllabus_id", bool(mismatch_syl_id), str(mismatch_syl_id))
    
    status, override_res = client("POST", "/api/syllabus/confirm-override", {
        "syllabus_id": mismatch_syl_id
    })
    check("POST /api/syllabus/confirm-override succeeds (200)", status == 200, f"Status: {status}")
    check("Override syllabus is now active", override_res.get("syllabus", {}).get("is_active") is True, str(override_res.get("syllabus", {}).get("is_active")))

    print("\n--- 8. Session Persistence & Profile Update ---")
    # Update profile to Semester 6
    update_payload = {
        "institution_name": "MIT Institute of Technology",
        "degree": "B.Tech",
        "department": "Information Technology",
        "current_year": 3,
        "current_semester": 6,
        "semester": 6,
        "regulation": "R20",
        "academic_year": "2025-2026"
    }
    status, update_body = client("PUT", "/api/user/profile", update_payload)
    check("PUT /api/user/profile to Semester 6 succeeds", status == 200, f"Status {status}")

    # Logout and re-login
    status, _ = client("POST", "/api/auth/logout")
    relogin_client = create_session()
    status, relogin_body = relogin_client("POST", "/api/auth/login", {
        "email": college_email,
        "password": "Password123!"
    })
    check("Re-login succeeds", status == 200, f"Status {status}")
    check("Re-login returns persisted semester 6", relogin_body.get("user", {}).get("semester") == 6, f"sem: {relogin_body.get('user', {}).get('semester')}")

    print("\n--- 9. Dedicated Curriculum Completeness Validator Unit & API Tests ---")
    # Test valid 7-subject syllabus extraction with full 16-point validation report
    sem6_syllabus = """
    B.Tech Information Technology - 6th Semester Curriculum (7 Courses Total)
    1. Cloud Infrastructure & Virtualization (IT601) [Credits: 3, L:3 T:0 P:0, Category: Theory Core]
    2. Deep Learning Systems (IT602) [Credits: 3, L:3 T:0 P:0, Category: Theory Core]
    3. Compiler Design (IT603) [Credits: 3, L:3 T:0 P:0, Category: Theory Core]
    4. Professional Elective II: Natural Language Processing (PE604) [Credits: 3, L:3 T:0 P:0, Category: Elective]
    5. Open Elective I: Cyber Law & Ethics (OE605) [Credits: 3, L:3 T:0 P:0, Category: Open Elective]
    6. Cloud & DevOps Laboratory (IT606L) [Credits: 1.5, L:0 T:0 P:3, Category: Laboratory]
    7. Deep Learning Practical Lab (IT607L) [Credits: 1.5, L:0 T:0 P:3, Category: Laboratory]
    """
    status, sem6_res = relogin_client("POST", "/api/syllabus/analyze", {
        "text": sem6_syllabus
    })
    check("Semester 6 syllabus analyze succeeds (200)", status == 200, f"Status {status}")
    rep = sem6_res.get("validation_report") or {}
    check("Validation report is generated and attached", bool(rep), str(rep))
    check("Validation report has dynamic semester == 6", rep.get("semester") == 6, str(rep.get("semester")))
    check("Validation report has dynamic subjects_detected == 7 (NOT hardcoded 8)", rep.get("subjects_detected") == 7, str(rep.get("subjects_detected")))
    check("Validation report has subjects_verified == 7", rep.get("subjects_verified") == 7, str(rep.get("subjects_verified")))
    check("Validation report has missing_subjects == 0", rep.get("missing_subjects") == 0, str(rep.get("missing_subjects")))
    check("Validation report has duplicate_subjects == 0", rep.get("duplicate_subjects") == 0, str(rep.get("duplicate_subjects")))
    check("Validation report has cross_semester_subjects == 0", rep.get("cross_semester_subjects") == 0, str(rep.get("cross_semester_subjects")))
    check("Validation report has uncertain_subjects == 0", rep.get("uncertain_subjects") == 0, str(rep.get("uncertain_subjects")))
    check("Validation report has status == 'VALID'", rep.get("status") == "VALID", str(rep.get("status")))
    check("Validation report checks contains all 16 checklist items", len(rep.get("checks", [])) == 16, f"Count: {len(rep.get('checks', []))}")

    # Test incomplete syllabus detection (e.g. expected 8 subjects, only 5 detected)
    from app.curriculum_validator import CurriculumCompletenessValidator
    incomplete_mock_analysis = {
        "course_title": "B.Tech IT Semester 6",
        "expected_subject_count": 8,
        "subjects": [
            {"code": "IT601", "name": "Cloud Infrastructure", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT602", "name": "Deep Learning Systems", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT603", "name": "Compiler Design", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT606L", "name": "Cloud Lab", "type": "Laboratory", "source_section": "Sem 6 Scheme"},
            {"code": "IT607L", "name": "Deep Learning Lab", "type": "Laboratory", "source_section": "Sem 6 Scheme"},
        ],
        "extracted_subjects": ["Cloud Infrastructure", "Deep Learning Systems", "Compiler Design", "Cloud Lab", "Deep Learning Lab"],
        "validation_status": "VALID"
    }
    user_context = {"user_id": "test_user_1", "name": "Jane Doe", "level": "college", "degree": "B.Tech", "department": "Information Technology", "semester": 6}
    inc_rep = CurriculumCompletenessValidator.validate(user=user_context, analysis=incomplete_mock_analysis, target_semester=6)
    check("Incomplete syllabus has missing_subjects == 3", inc_rep.get("missing_subjects") == 3, str(inc_rep.get("missing_subjects")))
    check("Incomplete syllabus has status == 'NEEDS_REVIEW'", inc_rep.get("status") == "NEEDS_REVIEW", str(inc_rep.get("status")))
    check("Incomplete syllabus is_valid == False (not activated)", inc_rep.get("is_valid") is False, str(inc_rep.get("is_valid")))

    # Test duplicate subject detection
    dup_mock_analysis = {
        "course_title": "B.Tech IT Semester 6",
        "expected_subject_count": 4,
        "subjects": [
            {"code": "IT601", "name": "Cloud Infrastructure", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT601", "name": "Cloud Infrastructure", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT602", "name": "Deep Learning Systems", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT603", "name": "Compiler Design", "type": "Theory", "source_section": "Sem 6 Scheme"},
        ],
        "extracted_subjects": ["Cloud Infrastructure", "Cloud Infrastructure", "Deep Learning Systems", "Compiler Design"],
        "validation_status": "VALID"
    }
    dup_rep = CurriculumCompletenessValidator.validate(user=user_context, analysis=dup_mock_analysis, target_semester=6)
    check("Duplicate subjects detected > 0", dup_rep.get("duplicate_subjects") == 1, str(dup_rep.get("duplicate_subjects")))
    check("Duplicate syllabus has status == 'NEEDS_REVIEW'", dup_rep.get("status") == "NEEDS_REVIEW", str(dup_rep.get("status")))
    check("Duplicate syllabus is_valid == False", dup_rep.get("is_valid") is False, str(dup_rep.get("is_valid")))

    # Test cross-semester contamination detection
    cross_mock_analysis = {
        "course_title": "B.Tech IT Semester 6",
        "expected_subject_count": 3,
        "subjects": [
            {"code": "IT601", "name": "Cloud Infrastructure", "type": "Theory", "source_section": "Sem 6 Scheme"},
            {"code": "IT402", "name": "Discrete Mathematics (Semester 4)", "type": "Theory", "source_section": "Sem 4 Scheme"},
            {"code": "IT603", "name": "Compiler Design", "type": "Theory", "source_section": "Sem 6 Scheme"},
        ],
        "extracted_subjects": ["Cloud Infrastructure", "Discrete Mathematics (Semester 4)", "Compiler Design"],
        "validation_status": "VALID"
    }
    cross_rep = CurriculumCompletenessValidator.validate(user=user_context, analysis=cross_mock_analysis, target_semester=6)
    check("Cross-semester subject detected > 0", cross_rep.get("cross_semester_subjects") == 1, str(cross_rep.get("cross_semester_subjects")))
    check("Cross-semester syllabus has status == 'NEEDS_REVIEW'", cross_rep.get("status") == "NEEDS_REVIEW", str(cross_rep.get("status")))
    check("Cross-semester syllabus is_valid == False", cross_rep.get("is_valid") is False, str(cross_rep.get("is_valid")))

    print("\n--- 10. Evidence-Based Extraction & Anti-Hallucination API Tests ---")
    # Query /api/syllabus/evidence
    status, ev_res = relogin_client("GET", "/api/syllabus/evidence")
    check("GET /api/syllabus/evidence returns 200", status == 200, f"Status {status}")
    ev_subjects = ev_res.get("subjects", [])
    check("Evidence endpoint returns subjects list", len(ev_subjects) >= 5, f"count: {len(ev_subjects)}")
    
    first_sub = ev_subjects[0] if ev_subjects else {}
    check("Subject has exact subject name", bool(first_sub.get("name")), str(first_sub))
    check("Subject has source document ID", bool(first_sub.get("source_document_id")), str(first_sub.get("source_document_id")))
    check("Subject has source page numbers", bool(first_sub.get("source_page_numbers") or first_sub.get("source_page")), str(first_sub.get("source_page_numbers")))
    check("Subject has source section reference", bool(first_sub.get("source_section")), str(first_sub.get("source_section")))
    check("Subject has source text excerpt", bool(first_sub.get("source_text")), str(first_sub.get("source_text")))
    check("Subject has semester evidence", bool(first_sub.get("semester_evidence")), str(first_sub.get("semester_evidence")))
    check("Subject has extraction confidence", first_sub.get("confidence") is not None and float(first_sub.get("confidence", 0)) >= 0.70, str(first_sub.get("confidence")))
    check("Subject has evidence_verified == True", first_sub.get("evidence_verified") is True, str(first_sub.get("evidence_verified")))

    # Query specific subject evidence /api/syllabus/subject-evidence/<code_or_name>
    sub_code_to_query = first_sub.get("code") or first_sub.get("name")
    status, single_ev = relogin_client("GET", f"/api/syllabus/subject-evidence/{urllib.parse.quote(str(sub_code_to_query))}")
    check("GET single subject evidence succeeds (200)", status == 200, f"Status {status}")
    ev_detail = single_ev.get("evidence", {})
    check("Single subject evidence answers 'Where did this subject come from?'", bool(ev_detail.get("source_section") and ev_detail.get("source_document_id")), str(ev_detail))

    # Anti-Hallucination verification: Test injection of fabricated subject absent from document
    fabricated_mock_analysis = {
        "course_title": "B.Tech IT Semester 6",
        "expected_subject_count": 3,
        "subjects": [
            {"code": "IT601", "name": "Cloud Infrastructure", "type": "Theory", "source_section": "Page 1"},
            {"code": "FAKE999", "name": "Quantum Superconductivity Astrophysics", "type": "Theory", "source_section": "Page 99"}, # Fabricated
        ],
        "extracted_subjects": ["Cloud Infrastructure", "Quantum Superconductivity Astrophysics"],
        "validation_status": "VALID"
    }
    raw_document_sample = "B.Tech IT Semester 6. 1. Cloud Infrastructure (IT601). 2. Deep Learning Systems (IT602)."
    fab_rep = CurriculumCompletenessValidator.validate(
        user=user_context,
        analysis=fabricated_mock_analysis,
        raw_content_or_file=raw_document_sample,
        target_semester=6
    )
    check("Anti-hallucination check caught fabricated subject", fab_rep.get("uncertain_subjects") >= 1, str(fab_rep.get("uncertain_subjects")))
    check("Fabricated subject prevents curriculum from being marked VALID", fab_rep.get("status") == "NEEDS_REVIEW", str(fab_rep.get("status")))
    check("Fabricated subject prevents curriculum from activating (is_valid=False)", fab_rep.get("is_valid") is False, str(fab_rep.get("is_valid")))

    print("\n" + "=" * 65)
    print(f" TEST RESULTS: {len(PASS)} PASSED, {len(FAIL)} FAILED")
    print("=" * 65)
    if FAIL:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
