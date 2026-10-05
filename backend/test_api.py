"""
End-to-end API verification — run while server is running on :5000
Tests: health, register, login, auth/me, logout, evaluations, syllabus
"""
import json, sys
import urllib.request, urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:5000"

# Session manager to keep cookies across requests
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def req(method, path, data=None, content_type="application/json"):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    rq = urllib.request.Request(url, data=body, method=method)
    if body:
        rq.add_header("Content-Type", content_type)
    try:
        resp = opener.open(rq, timeout=10)
        result = json.loads(resp.read().decode())
        return resp.getcode(), result
    except urllib.error.HTTPError as e:
        try:
            result = json.loads(e.read().decode())
        except Exception:
            result = {"error": e.reason}
        return e.code, result

PASS = []
FAIL = []

def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
        PASS.append(name)
    else:
        print(f"  FAIL  {name} — {detail}")
        FAIL.append(name)

print("\n=== LearnSphere AI — API Verification ===\n")

# 1. Health check
status, body = req("GET", "/health")
check("Health endpoint returns 200", status == 200, f"got {status}")
check("Health reports service name", "LearnSphere" in str(body.get("service", "")), str(body))
check("Health reports database", "database" in body, str(body))
print(f"  Database: {body.get('database')}")

# 2. Register teacher
print("\n--- Registration ---")
status, body = req("POST", "/api/auth/register", {
    "name": "Test Teacher",
    "email": "test_teacher_kiro@example.com",
    "password": "TestPass123",
    "role": "teacher",
    "teacherLevel": "school",
    "institutionName": "Test School",
    "level": "school"
})
check("Register teacher: 201 or 409", status in (201, 409), f"got {status}: {body}")
if status == 201:
    check("Register returns user object", "user" in body, str(body))
    check("Register does NOT return password_hash", "password_hash" not in str(body.get("user", {})), "SECURITY: hash exposed")
    check("Register returns user_id", bool(body.get("user", {}).get("id") or body.get("user", {}).get("user_id")), str(body.get("user")))

# 3. Register student
status2, body2 = req("POST", "/api/auth/register", {
    "name": "Test Student",
    "email": "test_student_kiro@example.com",
    "password": "TestPass123",
    "role": "student",
    "level": "school",
    "board": "CBSE",
    "classLevel": 12,
    "stream": "Science"
})
check("Register student: 201 or 409", status2 in (201, 409), f"got {status2}: {body2}")

# 4. Register duplicate (should fail with 409)
status3, body3 = req("POST", "/api/auth/register", {
    "name": "Dup",
    "email": "test_teacher_kiro@example.com",
    "password": "anypass",
    "role": "teacher"
})
check("Duplicate email returns 409", status3 == 409, f"got {status3}: {body3}")

# 5. Login with wrong role (student logging in as teacher)
print("\n--- Login ---")
status4, body4 = req("POST", "/api/auth/login", {
    "email": "test_student_kiro@example.com",
    "password": "TestPass123",
    "role": "teacher"  # WRONG portal
})
check("Wrong portal role returns 403", status4 == 403, f"got {status4}: {body4}")

# 6. Login with wrong password
status5, body5 = req("POST", "/api/auth/login", {
    "email": "test_teacher_kiro@example.com",
    "password": "WrongPassword",
    "role": "teacher"
})
check("Wrong password returns 401", status5 == 401, f"got {status5}")

# 7. Valid login
status6, body6 = req("POST", "/api/auth/login", {
    "email": "test_teacher_kiro@example.com",
    "password": "TestPass123",
    "role": "teacher"
})
check("Valid login returns 200", status6 == 200, f"got {status6}: {body6}")
check("Login returns user", "user" in body6, str(body6))
check("Login does NOT return password_hash", "password_hash" not in str(body6.get("user", {})), "SECURITY")
print(f"  Logged in as: {body6.get('user', {}).get('name')} (role={body6.get('user', {}).get('role')})")

# 8. /api/auth/me — session should be valid
print("\n--- Session Validation ---")
status7, body7 = req("GET", "/api/auth/me")
check("/api/auth/me authenticated=True", body7.get("authenticated") is True, str(body7))
check("/api/auth/me returns user", "user" in body7, str(body7))
check("/api/auth/me role is teacher", body7.get("user", {}).get("role") == "teacher", str(body7.get("user", {}).get("role")))

# 9. Protected endpoint: students list (teacher only)
print("\n--- Authorization ---")
status8, body8 = req("GET", "/api/students")
check("Teacher can access /api/students", status8 == 200, f"got {status8}")

# 10. Evaluations list (teacher sees their own)
status9, body9 = req("GET", "/api/evaluations")
check("Teacher gets evaluations list", status9 == 200, f"got {status9}: {body9}")
check("Evaluations returns array", isinstance(body9.get("evaluations"), list), str(type(body9.get("evaluations"))))

# 11. Action center (teacher only)
status10, body10 = req("GET", "/api/action-center")
check("Action center accessible by teacher", status10 == 200, f"got {status10}: {body10}")

# 12. Logout
print("\n--- Logout ---")
status11, body11 = req("POST", "/api/auth/logout")
check("Logout returns 200", status11 == 200, f"got {status11}")

# 13. After logout, /api/auth/me should return 401
status12, body12 = req("GET", "/api/auth/me")
check("After logout, /api/auth/me returns 401", status12 == 401, f"got {status12}: {body12}")
check("After logout, authenticated=False", body12.get("authenticated") is False, str(body12))

# 14. Protected endpoint returns 401 when not logged in
status13, body13 = req("GET", "/api/students")
check("Unauthenticated request to /api/students returns 401", status13 == 401, f"got {status13}: {body13}")

# 15. Student login and cross-user protection
print("\n--- Student isolation ---")
req("POST", "/api/auth/login", {
    "email": "test_student_kiro@example.com",
    "password": "TestPass123",
    "role": "student"
})
# Student should NOT access teacher-only endpoint
status14, body14 = req("GET", "/api/students")
check("Student CANNOT access /api/students (403)", status14 == 403, f"got {status14}: {body14}")

status15, body15 = req("GET", "/api/action-center")
check("Student CANNOT access /api/action-center (403)", status15 == 403, f"got {status15}: {body15}")

status16, body16 = req("GET", "/api/plagiarism/matches")
check("Student CANNOT access /api/plagiarism/matches (403)", status16 == 403, f"got {status16}: {body16}")

# 16. No X-User-ID bypass
print("\n--- Security: X-User-ID bypass ---")
req("POST", "/api/auth/logout")  # logout first

url = BASE + "/api/evaluations"
rq2 = urllib.request.Request(url, method="GET")
rq2.add_header("X-User-ID", "some-fake-id")  # attempt bypass
try:
    resp2 = opener.open(rq2, timeout=5)
    status17 = resp2.getcode()
    body17 = json.loads(resp2.read().decode())
except urllib.error.HTTPError as e:
    status17 = e.code
    body17 = {}
check("X-User-ID header does NOT bypass auth (401)", status17 == 401, f"got {status17}: {body17}")

# 17. Account Switch Scenario & Empty Profile verification
print("\n--- Account Switch & Profile Isolation Tests ---")
# Student A (Class 10)
req("POST", "/api/auth/register", {
    "name": "Student Alpha",
    "email": "student_alpha@example.com",
    "password": "Password123",
    "role": "student",
    "level": "school",
    "grade_level": "10",
    "section": "A",
    "institution_name": "Alpha High School"
})
status_a, login_a = req("POST", "/api/auth/login", {
    "email": "student_alpha@example.com",
    "password": "Password123",
    "role": "student"
})
check("Student A login successful", status_a == 200, str(login_a))
user_a = login_a.get("user", {})
check("Student A grade is 10", user_a.get("grade_level") == "10", str(user_a))
check("Student A school is Alpha High School", user_a.get("institution_name") == "Alpha High School", str(user_a))

# Logout A
req("POST", "/api/auth/logout")

# Student B (Empty profile — no school/class configured)
req("POST", "/api/auth/register", {
    "name": "Student Beta",
    "email": "student_beta@example.com",
    "password": "Password123",
    "role": "student",
    "level": "school"
})
status_b, login_b = req("POST", "/api/auth/login", {
    "email": "student_beta@example.com",
    "password": "Password123",
    "role": "student"
})
check("Student B login successful", status_b == 200, str(login_b))
user_b = login_b.get("user", {})
check("Student B has NO fake 12B/Class 12 fallback", user_b.get("grade_level") in (None, "", "null") and user_b.get("section") in (None, "", "null"), str(user_b))
check("Student B does NOT see Student A's school", user_b.get("institution_name") != "Alpha High School", str(user_b))

# Student B dashboard analytics isolation
status_dash, dash_b = req("GET", "/api/analytics/dashboard")
check("Student B dashboard returns 200", status_dash == 200, str(dash_b))
check("Student B dashboard recentEvaluations is empty list", dash_b.get("recentEvaluations") == [], str(dash_b.get("recentEvaluations")))

req("POST", "/api/auth/logout")

# Summary
print(f"\n{'='*50}")
print(f"PASSED: {len(PASS)}/{len(PASS)+len(FAIL)}")
if FAIL:
    print(f"FAILED: {len(FAIL)}")
    for f in FAIL:
        print(f"  - {f}")
else:
    print("ALL TESTS PASSED")
print("="*50)
