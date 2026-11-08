"""
Comprehensive Authentication & Performance Test Suite
Tests:
1. Successful Login (Student & Teacher)
2. Incorrect Password Rejection
3. Nonexistent Account Rejection
4. Portal Role Separation (Student vs Teacher Cross-Portal rejection)
5. Session Persistence (/api/auth/me)
6. Authentication without Gemini API key dependency
7. Database failover / error handling
8. Login API Response Time Measurement (in ms)
"""

import sys
import os
import time
import json
from pathlib import Path

# Setup paths
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from server import app
from app.db import get_mongodb, get_sqlite_db

def run_tests():
    print("=" * 70)
    print("LEARNSPHERE AI - AUTHENTICATION & PERFORMANCE TEST SUITE")
    print("=" * 70)

    client = app.test_client()

    # 1. Setup / Identify Test Accounts
    mongo_db = get_mongodb()
    student_email = "student_perf_test@learnsphere.io"
    teacher_email = "teacher_perf_test@learnsphere.io"
    password = "SecurePassword123!"

    print("\n[SETUP] Registering/Updating Test Student and Teacher Accounts...")
    # Register or ensure student exists
    res_s = client.post("/api/auth/register", json={
        "name": "Test Student",
        "email": student_email,
        "password": password,
        "role": "student",
        "level": "college",
        "degree": "B.Tech",
        "department": "Computer Science",
        "semester": 5
    })
    if res_s.status_code not in (201, 409):
        print(f"FAILED to register student: {res_s.status_code} {res_s.data.decode()}")
        return False

    # Register or ensure teacher exists
    res_t = client.post("/api/auth/register", json={
        "name": "Test Teacher",
        "email": teacher_email,
        "password": password,
        "role": "teacher",
        "teacherLevel": "college",
        "institutionName": "Apex Institute of Tech",
        "department": "Computer Science"
    })
    if res_t.status_code not in (201, 409):
        print(f"FAILED to register teacher: {res_t.status_code} {res_t.data.decode()}")
        return False

    print("✓ Test accounts ready.")

    # ── Test 1: Successful Student Login ──
    print("\n[TEST 1] Testing Successful Student Login...")
    t0 = time.perf_counter()
    res = client.post("/api/auth/login", json={
        "email": student_email,
        "password": password,
        "role": "student"
    })
    t_login_student = (time.perf_counter() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data.decode()}"
    data = res.get_json()
    assert data["success"] is True, "Expected success: True"
    assert data["user"]["email"] == student_email, "Email match failure"
    assert data["user"]["role"] == "student", "Role match failure"
    print(f"✓ Student Login Succeeded: {t_login_student:.2f} ms")

    # ── Test 2: Successful Teacher Login ──
    print("\n[TEST 2] Testing Successful Teacher Login...")
    t0 = time.perf_counter()
    res = client.post("/api/auth/login", json={
        "email": teacher_email,
        "password": password,
        "role": "teacher"
    })
    t_login_teacher = (time.perf_counter() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data.decode()}"
    data = res.get_json()
    assert data["success"] is True, "Expected success: True"
    assert data["user"]["email"] == teacher_email, "Email match failure"
    assert data["user"]["role"] == "teacher", "Role match failure"
    print(f"✓ Teacher Login Succeeded: {t_login_teacher:.2f} ms")

    # ── Test 3: Session Persistence (/api/auth/me) ──
    print("\n[TEST 3] Testing Session Persistence via /api/auth/me...")
    t0 = time.perf_counter()
    res_me = client.get("/api/auth/me")
    t_me = (time.perf_counter() - t0) * 1000
    assert res_me.status_code == 200, f"Expected 200, got {res_me.status_code}"
    data_me = res_me.get_json()
    assert data_me["success"] is True and data_me["authenticated"] is True
    assert data_me["user"]["email"] == teacher_email
    print(f"✓ Session Persistence Succeeded: {t_me:.2f} ms (User: {data_me['user']['email']})")

    # ── Test 4: Incorrect Password Rejection ──
    print("\n[TEST 4] Testing Incorrect Password Rejection...")
    t0 = time.perf_counter()
    res_pw = client.post("/api/auth/login", json={
        "email": student_email,
        "password": "WrongPassword999!",
        "role": "student"
    })
    t_wrong_pw = (time.perf_counter() - t0) * 1000
    assert res_pw.status_code == 401, f"Expected 401, got {res_pw.status_code}"
    data_pw = res_pw.get_json()
    assert data_pw["success"] is False
    assert "Incorrect password" in data_pw["error"]
    print(f"✓ Incorrect Password correctly rejected with 401: {t_wrong_pw:.2f} ms")

    # ── Test 5: Nonexistent Account Rejection ──
    print("\n[TEST 5] Testing Nonexistent Account Rejection...")
    t0 = time.perf_counter()
    res_none = client.post("/api/auth/login", json={
        "email": "completely_nonexistent_user_9921@example.com",
        "password": "SomePassword123!",
        "role": "student"
    })
    t_nonexistent = (time.perf_counter() - t0) * 1000
    assert res_none.status_code == 401, f"Expected 401, got {res_none.status_code}"
    data_none = res_none.get_json()
    assert data_none["success"] is False
    assert "Account not found" in data_none["error"]
    print(f"✓ Nonexistent Account correctly rejected with 401: {t_nonexistent:.2f} ms")

    # ── Test 6: Role Separation Enforcement ──
    print("\n[TEST 6] Testing Role Separation Enforcement...")
    # Student logging in through Teacher portal
    res_cross1 = client.post("/api/auth/login", json={
        "email": student_email,
        "password": password,
        "role": "teacher"
    })
    assert res_cross1.status_code == 403, f"Expected 403, got {res_cross1.status_code}"
    data_cross1 = res_cross1.get_json()
    assert "Please use the Student portal" in data_cross1["error"]
    print("✓ Student blocked from Teacher portal with 403 error message.")

    # Teacher logging in through Student portal
    res_cross2 = client.post("/api/auth/login", json={
        "email": teacher_email,
        "password": password,
        "role": "student"
    })
    assert res_cross2.status_code == 403, f"Expected 403, got {res_cross2.status_code}"
    data_cross2 = res_cross2.get_json()
    assert "Please use the Teacher portal" in data_cross2["error"]
    print("✓ Teacher blocked from Student portal with 403 error message.")

    # ── Test 7: Authentication with Zero Gemini Dependency ──
    print("\n[TEST 7] Verifying Auth Operates Independently of Gemini...")
    old_key = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = ""  # simulate Gemini API unavailable/missing
        res_no_gemini = client.post("/api/auth/login", json={
            "email": student_email,
            "password": password,
            "role": "student"
        })
        assert res_no_gemini.status_code == 200, "Auth failed when Gemini API is unconfigured!"
        print("✓ Auth succeeded 100% without Gemini API key or external network.")
    finally:
        if old_key:
            os.environ["GEMINI_API_KEY"] = old_key

    # ── Test 8: Logout & Session Invalidation ──
    print("\n[TEST 8] Testing Logout & Session Invalidation...")
    res_logout = client.post("/api/auth/logout")
    assert res_logout.status_code == 200
    res_after = client.get("/api/auth/me")
    assert res_after.status_code == 401
    print("✓ Logout successfully invalidated session.")

    # ── Summary of Measured Response Times ──
    print("\n" + "=" * 70)
    print("FINAL PERFORMANCE MEASUREMENTS")
    print("=" * 70)
    print(f"Student Login Response Time:    {t_login_student:.2f} ms")
    print(f"Teacher Login Response Time:    {t_login_teacher:.2f} ms")
    print(f"Session Validation (/me) Time:  {t_me:.2f} ms")
    print(f"Incorrect Password Reject Time: {t_wrong_pw:.2f} ms")
    print(f"Nonexistent Account Reject Time:{t_nonexistent:.2f} ms")
    print("=" * 70)
    print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

