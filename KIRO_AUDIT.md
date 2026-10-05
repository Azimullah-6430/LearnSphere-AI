# KIRO AUDIT: LearnSphere AI - Complete Repository Analysis

**Date**: October 1, 2026  
**Status**: CRITICAL ISSUES IDENTIFIED  
**Production Ready**: ❌ NO

---

## EXECUTIVE SUMMARY

LearnSphere AI is a production education platform with **CRITICAL security and data integrity vulnerabilities**. The application has a dual-database architecture (MongoDB + SQLite fallback), incomplete authentication implementation, broken frontend state management, and anti-patterns that expose student academic data and fabricate results.

**Critical findings:**
- Authentication system has undefined object reference causing app crashes
- Password comparison falls back to plaintext in some conditions
- Frontend authentication stored in localStorage with indefinite persistence
- Evaluation results can be fabricated with fallback data
- Plagiarism detection based on file size, not content
- Mock/fake data displayed alongside real academic data
- No audit trail for teacher overrides
- Field naming inconsistencies between backend and frontend

---

## SECTION 1: CRITICAL ERRORS (PRODUCTION BLOCKERS)

### 1.1 Undefined DEFAULT_USERS Object

**Severity**: 🔴 CRITICAL  
**File**: `learnsphere-ai/src/context/AppContext.jsx`  
**Lines**: 44, 45, 349  
**Type**: ReferenceError - Application Crash

**Exact Problem**:
```javascript
// Line 44-45 (initial state)
const [currentUser, setCurrentUser] = useState(() => {
  try {
    const saved = localStorage.getItem('ls-user')
    return saved ? JSON.parse(saved) : DEFAULT_USERS['teacher']  // ❌ UNDEFINED
  } catch { return DEFAULT_USERS['teacher'] }  // ❌ UNDEFINED
})
```

**When It Breaks**:
1. Application starts with empty localStorage (new user, private browsing, cookie-cleared session)
2. `localStorage.getItem('ls-user')` returns null
3. Code attempts to access `DEFAULT_USERS['teacher']`
4. JavaScript throws `ReferenceError: DEFAULT_USERS is not defined`
5. App crashes; user sees blank screen or error

**Why It's Dangerous**:
- App is completely inaccessible to users starting fresh
- No graceful fallback or error boundary
- Crashes without user-friendly error message
- Production users cannot use the application

**Required Fix**:
```javascript
// Option A: Define DEFAULT_USERS
const DEFAULT_USERS = {
  teacher: { role: 'teacher', name: null, email: null },
  student: { role: 'student', name: null, email: null }
}

// Option B: Remove fallback and set null
return saved ? JSON.parse(saved) : null

// Option C (RECOMMENDED): Call /api/auth/me to restore from backend
```

**Recommendation**: Option C - validate session with backend on app load

---

### 1.2 Frontend Authentication Entirely localStorage-Based

**Severity**: 🔴 CRITICAL  
**File**: `learnsphere-ai/src/context/AppContext.jsx` (entire file)  
**Type**: Authentication System Architecture Flaw

**Exact Problem**:
The entire authentication system relies on localStorage keys:
- `ls-auth`: true/false
- `ls-role`: teacher/student  
- `ls-user`: Full user object JSON

No validation occurs with backend on app startup or during navigation.

**Code Flow**:
```javascript
// On app startup, no /api/auth/me call
// Just reads localStorage and trusts it
const [authenticated] = useState(() => {
  return localStorage.getItem('ls-auth') === 'true'  // ❌ Not verified with backend
})
```

**Why It's Dangerous**:
1. **No Session Validation**: Invalidated sessions on backend are not detected
2. **Indefinite Persistence**: User remains "logged in" forever (no expiration)
3. **Account Compromise**: If token/session is hijacked, attacker has permanent access
4. **Cross-Device Issues**: User logs in on Device A, logs in as different user on Device B with Device A's localStorage data
5. **Invisible Logout**: Backend session expires but frontend still shows user as logged in
6. **Multi-Device Session Tracking Impossible**: No way to invalidate other devices

**Database Implication**:
If a user's account is compromised or deleted on the server, they remain authenticated in the browser indefinitely.

**Required Fix**:
```javascript
// On app startup, validate session with backend
useEffect(() => {
  async function validateSession() {
    try {
      const response = await fetch('/api/auth/me', { credentials: 'include' })
      if (response.ok) {
        const user = await response.json()
        setCurrentUser(user)
        setAuthenticated(true)
      } else {
        // Backend says session invalid → clear frontend
        localStorage.removeItem('ls-auth')
        localStorage.removeItem('ls-user')
        setCurrentUser(null)
        setAuthenticated(false)
      }
    } catch (error) {
      console.error('Session validation failed', error)
      setAuthenticated(false)  // Fail secure
    }
  }
  validateSession()
}, [])
```

**Recommendation**: Implement server-side session validation on app load

---

### 1.3 Password Hash Comparison Fallback to Plaintext

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py`  
**Lines**: 155-156  
**Type**: Password Security Vulnerability

**Exact Code**:
```python
# server.py line 155-156
stored_hash = user.get('password_hash', '')
if not check_password_hash(stored_hash, password) and stored_hash != password:
    return {'error': 'Invalid credentials'}, 401
```

**Problem**:
- If `stored_hash` doesn't start with "scrypt:" or "pbkdf2:" prefix, `check_password_hash()` returns False
- Code then checks `if stored_hash != password` (plaintext comparison)
- If `stored_hash` is literally the plaintext password, authentication succeeds

**When This Occurs**:
1. Old accounts created before proper hashing was implemented
2. Manually inserted test accounts with plaintext passwords
3. Database migration incomplete

**Why It's Dangerous**:
- **Data Breach Risk**: If database is compromised, plaintext passwords are exposed
- **Regulatory Violation**: FERPA/GDPR violations for plaintext password storage
- **Attack Vector**: Attacker with DB access can immediately use plaintext passwords
- **Silent Vulnerability**: No audit trail of which accounts are plaintext

**Required Fix**:
```python
# Remove plaintext fallback entirely
stored_hash = user.get('password_hash', '')
if not check_password_hash(stored_hash, password):
    return {'error': 'Invalid credentials'}, 401

# For accounts with missing/invalid hashes:
# Force password reset flow instead
if not stored_hash or not stored_hash.startswith(('scrypt:', 'pbkdf2:')):
    return {'error': 'Password reset required', 'reset_token': generate_token()}, 403
```

**Recommendation**: 
1. Audit database for plaintext passwords
2. Reject plaintext comparisons entirely
3. Migrate old accounts with forced password reset
4. Add password hash validation on startup

---

### 1.4 No X-User-ID Header Validation (Authentication Bypass)

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py`  
**Lines**: 134-157 (in `/api/auth/me` endpoint)  
**Type**: Authentication Bypass Vulnerability

**Exact Code**:
```python
# server.py /api/auth/me endpoint
user_id = session.get('user_id') or request.headers.get('X-User-ID')
# If no session, accepts X-User-ID header as identity
user = find_user_by_id(user_id)
return user  # Returns another user's data!
```

**Why It's Dangerous**:
A malicious user can send:
```http
GET /api/auth/me
X-User-ID: student-123-actual-user-id

Response: { name: "Actual Student", email: "student@school.com", ... }
```

**Attack Scenarios**:
1. Student A discovers Student B's user_id
2. Student A sends `X-User-ID: student-b-id` header
3. Backend returns Student B's profile
4. Student A can then:
   - Access `/api/evaluations` with B's ID → read B's scores
   - Access `/api/syllabus` → see B's syllabus
   - Make requests as if they were B
5. No permission check because X-User-ID is not authenticated

**Required Fix**:
```python
# NEVER accept X-User-ID for authentication
user_id = session.get('user_id')
if not user_id:
    return {'error': 'Unauthorized'}, 401  # Force new session

user = find_user_by_id(user_id)
if not user or not user.get('active'):
    return {'error': 'User not found'}, 401
```

**Recommendation**: Remove X-User-ID header as an authentication mechanism entirely

---

### 1.5 Evaluation Results Can Be Fabricated with Fallback Data

**Severity**: 🔴 CRITICAL  
**File**: `backend/app/evaluation/store.py` and frontend evaluation display  
**Type**: Data Integrity - Fabricated Academic Results

**Exact Problems**:

**Problem 1: Fallback Marks**
```javascript
// Frontend displays evaluation
const displayed_marks = evaluation.obtained_marks || 100  // ❌ FALLBACK
```

If `obtained_marks` is 0 (legitimate score) or undefined (failed evaluation):
- Displays 100 as fallback
- Student sees 100/100 when they scored 0 or evaluation failed

**Problem 2: Fallback Percentage**
```javascript
const percentage = (marks / total) || 50  // ❌ FALLBACK GUESS
```

If calculation fails, hardcode 50% as "average"

**Problem 3: Fabricated Questions**
```python
# In evaluation result, if question extraction fails:
if not questions:
    questions = [  # ❌ FAKE QUESTION
        {'id': 'Q1', 'max_marks': 100, 'text': 'Question'}
    ]
```

**Why It's Dangerous**:
1. **Academic Dishonesty**: Student appears to have passed when they failed
2. **Transcript Impact**: False grades on permanent record
3. **College Admissions**: Fraudulent performance data
4. **Regulatory Violation**: Falsification of academic records
5. **Teacher Blind**: Teachers cannot identify true assessment results
6. **Silent Failure**: No error indication; appears as successful evaluation

**Required Fix**:
```javascript
// Frontend - explicit null checking
if (evaluation.obtained_marks === null || evaluation.obtained_marks === undefined) {
  return <div>Evaluation pending or failed. Status: {evaluation.status}</div>
}

// Backend - never fabricate results
if evaluation_status is not COMPLETED:
  return {
    status: evaluation_status,
    obtained_marks: None,  # Not a number
    percentage: None,
    message: "Evaluation incomplete or requires review"
  }
```

**Recommendation**: Fail explicitly; never fabricate academic data

---

## SECTION 2: AUTHENTICATION ERRORS

### 2.1 Plaintext Email in Request Body Trusted for Authorization

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py`  
**Type**: Authorization Bypass

**Problem**:
```python
# /api/evaluations endpoint
email = request.json.get('email')  # ❌ From client
evaluations = find_evaluations_by_email(email)
return evaluations
```

A student can send `email: teacher@school.com` and retrieve another user's evaluations.

**Required Fix**:
```python
user_id = session.get('user_id')  # From authenticated session
evaluations = find_evaluations_by_user_id(user_id)
return evaluations
```

**Recommendation**: Every protected endpoint must derive identity from session, never from request body

---

### 2.2 No CSRF Protection on State-Changing Endpoints

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (login, register, evaluate, override)  
**Type**: Cross-Site Request Forgery Vulnerability

**Problem**:
```python
@app.route('/api/auth/login', methods=['POST'])
def login():
    # No CSRF token validation
    # No origin checking
    # No SameSite cookie enforcement
```

Attack:
1. Student visits `attacker.com`
2. Attacker's site contains: `<img src="https://learnsphere.render.com/api/auth/login?email=attacker@mail.com&password=newpass">`
3. If browser has existing session cookie, request is sent with credentials
4. Student's account password changed without consent

**Required Fix**:
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

@app.route('/api/auth/login', methods=['POST'])
@csrf.protect  # Require CSRF token in request
def login():
    ...
```

And in frontend:
```javascript
// Fetch CSRF token before making requests
const response = await fetch('/api/csrf-token')
const { token } = await response.json()

// Include in headers
fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'X-CSRF-Token': token },
  body: JSON.stringify({ email, password })
})
```

**Recommendation**: Implement CSRF protection on all state-changing endpoints

---

### 2.3 No Session Expiration (Indefinite Authentication)

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` and `learnsphere-ai/src/context/AppContext.jsx`  
**Type**: Session Management

**Problem**:
- Flask session expires per Flask config (default: never)
- localStorage keys never expire
- User remains authenticated after logout if browser history accessed

**Required Fix**:
```python
# In Flask app initialization
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.before_request
def make_session_permanent():
    session.permanent = True
```

And frontend:
```javascript
// Implement JWT with expiration
const token = response.data.token  // Expires in 24h
localStorage.setItem('auth_token', token)
localStorage.setItem('token_expires', Date.now() + 24*60*60*1000)

// Check expiration on app load
if (Date.now() > localStorage.getItem('token_expires')) {
  logout()  // Force re-login
}
```

**Recommendation**: Implement 24-hour session expiration with refresh tokens

---

## SECTION 3: MONGODB PERSISTENCE ERRORS

### 3.1 Dual Database Architecture (MongoDB + SQLite Fallback)

**Severity**: 🔴 CRITICAL  
**File**: `backend/app/db.py`  
**Type**: Data Consistency & Architectural Flaw

**Exact Problem**:
```python
# db.py lines 50-100
def get_db_connection():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1500)
        client.admin.command('ping')
        return 'mongodb'
    except:
        # Silently fallback to SQLite
        return 'sqlite'
```

**Consequences**:
1. **Data Loss**: User registers on MongoDB (primary); logs in from backend that falls back to SQLite → user doesn't exist
2. **Split Database**: Teacher's evaluations in MongoDB; student retrieving from SQLite finds nothing
3. **Inconsistent State**: Same user has different data in different backends
4. **Production Instability**: Transient MongoDB outage causes silent data corruption
5. **Regulatory Risk**: Cannot audit where data is actually stored

**Example Scenario**:
1. September 1: Student registers on MongoDB → user_id = abc123
2. September 2: MongoDB connection times out
3. Backend falls back to SQLite
4. Same student tries to login
5. SQLite queries `SELECT * FROM users WHERE email=...` → not found
6. Backend auto-creates new SQLite user → user_id = 1 (different!)
7. Student sees empty progress; original eval data inaccessible
8. Database now has two "Jane Doe" users in different systems

**Required Fix**:
```python
# FAIL LOUDLY if MongoDB unavailable in production
def get_db_connection():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1500)
        client.admin.command('ping')
        return 'mongodb'
    except Exception as e:
        if os.getenv('ENV') == 'production':
            logger.critical(f'MongoDB connection failed: {e}')
            raise SystemExit('Database unavailable - cannot start in production')
        else:
            logger.warning(f'MongoDB unavailable, using SQLite for development')
            return 'sqlite'
```

**Recommendation**: Make MongoDB mandatory in production; remove SQLite fallback

---

### 3.2 No Unique Index on Email (Duplicate Users Possible)

**Severity**: 🔴 CRITICAL  
**File**: `backend/app/db.py` (MongoDB initialization)  
**Type**: Data Integrity

**Problem**:
```python
# MongoDB collections don't enforce unique email index on creation
db.users.create_index('email')  # ❌ Not unique!
```

Result: Same email can register twice

**Attack/Incident Scenario**:
1. Student "Arun Kumar" registers with arun@school.com
2. System creates evaluation history
3. Later, teacher admin accidentally re-registers arun@school.com
4. Two documents in MongoDB with same email
5. Login finds first document → uses wrong account
6. Evaluation data mismatch

**Required Fix**:
```python
# Enforce unique constraint on email
db.users.create_index('email', unique=True)

# Also create indexes on frequently queried fields
db.users.create_index('user_id', unique=True)
db.users.create_index('role')
db.users.create_index('created_at')

db.evaluations.create_index([('student_id', 1), ('created_at', -1)])
db.evaluations.create_index('status')

db.syllabus.create_index([('student_id', 1), ('version', -1)])
```

**Recommendation**: Create unique index on email; prevent duplicates at database level

---

### 3.3 No Transaction Support for Multi-Document Updates

**Severity**: 🟡 HIGH  
**File**: `backend/server.py` (evaluation endpoint)  
**Type**: Data Consistency

**Problem**:
When teacher overrides marks:
```python
# server.py /api/evaluations/{id}/override
evaluation = db.evaluations.update_one(...)  # Update doc 1
evaluation_questions = [
    db.evaluation_questions.update_one(...)  # Update doc 2
    for q in questions
]
# ❌ No transaction: If server crashes between updates, data is partially updated
```

**Consequence**:
- Evaluation marked as overridden, but some questions still have old marks
- Recalculation shows wrong total

**Required Fix**:
```python
from pymongo import MongoClient
from pymongo.errors import OperationFailure

session = client.start_session()
try:
    with session.start_transaction():
        db.evaluations.update_one(..., session=session)
        for q in questions:
            db.evaluation_questions.update_one(..., session=session)
        # All succeed or all fail
except OperationFailure:
    # Rollback automatic
    return {'error': 'Update failed; no partial changes'}, 500
finally:
    session.end_session()
```

**Recommendation**: Use MongoDB transactions for multi-document updates

---

## SECTION 4: AUTHORIZATION ERRORS

### 4.1 Teacher Can Access Any Student's Evaluations

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (`/api/evaluations` endpoint)  
**Type**: Unauthorized Data Access (IDOR)

**Exact Problem**:
```python
@app.route('/api/evaluations', methods=['GET'])
def get_evaluations():
    role = session.get('role')
    if role == 'teacher':
        # Returns ALL evaluations in system, regardless of which students teacher actually teaches
        return db.evaluations.find({})
```

**Attack**:
1. Teacher A (Physics) logs in
2. Calls `GET /api/evaluations`
3. Receives evaluations from:
   - Students they teach (correct)
   - Students from other teachers (violation)
   - Students from other subjects (violation)
4. Can see Mathematics evaluation scores for students they're not authorized to grade

**Why It's Dangerous**:
- **Privacy Violation**: Teacher sees students they don't teach
- **Grade Tampering**: Can override marks for students they shouldn't access
- **Regulatory Violation**: FERPA/data privacy regulations
- **Unfair Assessment**: Can tamper with another teacher's grades

**Required Fix**:
```python
@app.route('/api/evaluations', methods=['GET'])
def get_evaluations():
    user_id = session.get('user_id')
    if not user_id:
        return {'error': 'Unauthorized'}, 401
    
    role = session.get('role')
    if role == 'teacher':
        # Only return evaluations for students this teacher teaches
        teacher = db.users.find_one({'_id': ObjectId(user_id)})
        student_ids = teacher.get('assigned_students', [])
        return list(db.evaluations.find({'student_id': {'$in': student_ids}}))
    
    elif role == 'student':
        # Only return this student's evaluations
        return list(db.evaluations.find({'student_id': user_id}))
```

**Recommendation**: Add teacher-student relationship verification; enforce scope on all endpoints

---

### 4.2 Student Can Override Own Marks (No Teacher-Only Enforcement)

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (`/api/evaluations/{id}/override` endpoint)  
**Type**: Authorization Bypass - Grade Tampering

**Exact Problem**:
```python
@app.route('/api/evaluations/<id>/override', methods=['PUT'])
def override_marks(id):
    # ❌ Only checks if role == 'teacher', not if THIS teacher is authorized
    if session.get('role') != 'teacher':
        return {'error': 'Forbidden'}, 403
    
    # Any teacher can override any evaluation
    new_marks = request.json.get('obtained_marks')
    db.evaluations.update_one({'_id': id}, {'$set': {'obtained_marks': new_marks}})
    return {'success': True}
```

**Attack**:
1. Student logs in
2. Frontend is checked: only teacher portal shows override button
3. But frontend protection is NOT security
4. Student directly sends: `PUT /api/evaluations/eval-123 { "obtained_marks": 100 }`
5. Backend checks `session.get('role')` — but student can forge this in localStorage if frontend stores role
6. OR, student is a "cooperative teacher account" and overrides their own student scores

**Why It's Dangerous**:
- Students can change their own marks to 100
- Grades fabricated without authorization
- Permanent record falsification

**Required Fix**:
```python
@app.route('/api/evaluations/<id>/override', methods=['PUT'])
def override_marks(id):
    teacher_id = session.get('user_id')
    
    # 1. Verify teacher role from database (not from localStorage)
    teacher = db.users.find_one({'_id': ObjectId(teacher_id)})
    if teacher.get('role') != 'teacher':
        return {'error': 'Forbidden'}, 403
    
    # 2. Verify teacher is assigned to this evaluation's student
    evaluation = db.evaluations.find_one({'_id': ObjectId(id)})
    if evaluation['teacher_id'] != teacher_id:
        return {'error': 'Not assigned to this student'}, 403
    
    # 3. Validate marks are reasonable
    new_marks = request.json.get('obtained_marks')
    if new_marks < 0 or new_marks > evaluation['total_marks']:
        return {'error': 'Marks out of range'}, 400
    
    # 4. Audit log
    db.audit_log.insert_one({
        'teacher_id': teacher_id,
        'evaluation_id': id,
        'original_marks': evaluation['obtained_marks'],
        'new_marks': new_marks,
        'timestamp': datetime.utcnow()
    })
    
    db.evaluations.update_one({'_id': ObjectId(id)}, {'$set': {
        'obtained_marks': new_marks,
        'is_teacher_overridden': True,
        'teacher_override_id': teacher_id,
        'teacher_override_at': datetime.utcnow()
    }})
    
    return {'success': True, 'audit_id': str(db.audit_log.inserted_ids[0])}
```

**Recommendation**: 
1. Verify role from database, never from localStorage
2. Verify teacher-student relationship
3. Validate reasonable mark ranges
4. Audit all overrides with before/after values

---

### 4.3 No Authorization Checks on Teacher-Only Endpoints

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (multiple endpoints)  
**Type**: Privilege Escalation

**Endpoints with Missing Checks**:
```python
# Teacher Analytics - no check if user is teacher
GET /api/teacher/analytics

# Create Class - no check if user is teacher  
POST /api/classes

# View All Students - no check if user is teacher
GET /api/students

# Action Center - no check if user is authorized
GET /api/action-center

# Misconceptions Map - no check if user is teacher
GET /api/misconceptions/map
```

**Attack**: Student can directly call these endpoints and receive teacher-only data

**Required Fix**: Create authorization middleware
```python
def require_role(required_role):
    def decorator(f):
        def wrapper(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return {'error': 'Unauthorized'}, 401
            
            user = db.users.find_one({'_id': ObjectId(user_id)})
            if not user or user.get('role') != required_role:
                return {'error': 'Forbidden'}, 403
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Usage:
@app.route('/api/teacher/analytics', methods=['GET'])
@require_role('teacher')
def get_teacher_analytics():
    ...
```

**Recommendation**: Create centralized authorization middleware; apply to all protected endpoints

---

## SECTION 5: DATA OWNERSHIP ERRORS

### 5.1 No User-Scoped Isolation on Academic Data

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (evaluation, syllabus, misconception endpoints)  
**Type**: IDOR (Insecure Direct Object Reference)

**Problem**:
```python
@app.route('/api/evaluations/<eval_id>', methods=['GET'])
def get_evaluation(eval_id):
    # ❌ No check if current user owns this evaluation
    return db.evaluations.find_one({'_id': ObjectId(eval_id)})
```

**Attack**:
1. Student A is logged in with session
2. Student A knows Student B's evaluation ID (from URL or API response)
3. Student A requests: `GET /api/evaluations/B-eval-id`
4. Backend returns B's evaluation details
5. A now has access to B's marks, feedback, misconceptions

**Required Fix**:
```python
@app.route('/api/evaluations/<eval_id>', methods=['GET'])
def get_evaluation(eval_id):
    user_id = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    evaluation = db.evaluations.find_one({'_id': ObjectId(eval_id)})
    
    if user.get('role') == 'student':
        # Students can only view their own evaluations
        if evaluation.get('student_id') != user_id:
            return {'error': 'Forbidden'}, 403
    
    elif user.get('role') == 'teacher':
        # Teachers can only view students they teach
        if evaluation.get('teacher_id') != user_id:
            return {'error': 'Forbidden'}, 403
    
    return evaluation
```

**Recommendation**: Every protected endpoint must check user ownership before returning data

---

### 5.2 Student Names Used as Identifiers (Anti-Pattern)

**Severity**: 🔴 CRITICAL  
**File**: Database schema, `backend/server.py`, frontend API calls  
**Type**: Data Integrity & Privacy

**Problem**:
```python
# MongoDB documents
{
    'student_name': 'Arun Kumar',  # ❌ Used as query key
    'email': 'arun@school.com',
    ...
}

# Query: db.users.find_one({'student_name': 'Arun Kumar'})
# This is fragile: what if two students have same name?
```

**Consequence**:
1. Two "Arun Kumar" students in system
2. Query returns first match → wrong student's data accessed
3. No way to disambiguate

**Required Fix**:
```python
# Every user must have stable user_id (UUID or MongoDB ObjectId)
{
    '_id': ObjectId('...'),  # Immutable primary key
    'user_id': 'uuid-arun-123',  # Stable, never changes
    'name': 'Arun Kumar',  # Display field only
    'email': 'arun@school.com',  # Unique index
    'role': 'student'
}

# Query by user_id, never by name
db.users.find_one({'user_id': 'uuid-arun-123'})
```

**Recommendation**: Use UUID or MongoDB ObjectId for all identities; names are display-only

---

## SECTION 6: EVALUATION ERRORS

### 6.1 No Validation of Question Paper Extraction

**Severity**: 🔴 CRITICAL  
**File**: `backend/app/evaluation/evaluator.py` (lines 36-57)  
**Type**: Data Validation

**Problem**:
```python
def extract_question_paper(pdf_path):
    # Calls Gemini to extract questions
    prompt = "Extract questions from this paper"
    gemini_response = call_gemini(prompt, pdf_path)
    
    # ❌ No validation of response
    # If Gemini fails or hallucinates:
    if not gemini_response.get('questions'):
        # Returns empty or dummy questions
        return {'questions': [], 'total_marks': None}
    
    return gemini_response  # Could contain any structure
```

**What Can Go Wrong**:
1. Gemini returns incomplete JSON
2. Gemini extracts wrong marks (100 instead of 50)
3. Gemini creates fake questions not in paper
4. Network timeout returns None
5. API quota exceeded returns error

**Why It's Dangerous**:
- Student evaluated against wrong question structure
- Marks calculated on wrong basis
- Status reported as "success" when QP extraction actually failed

**Required Fix**:
```python
def extract_question_paper(pdf_path):
    try:
        gemini_response = call_gemini(prompt, pdf_path)
        
        # Validate structure
        if not isinstance(gemini_response, dict):
            raise ValueError('Invalid response format')
        
        questions = gemini_response.get('questions', [])
        if not questions or not isinstance(questions, list):
            return {
                'status': 'EXTRACTION_FAILED',
                'error': 'Could not extract questions',
                'questions': None
            }
        
        # Validate each question
        for q in questions:
            if 'id' not in q or 'max_marks' not in q:
                raise ValueError('Question missing required fields')
            if not isinstance(q['max_marks'], (int, float)) or q['max_marks'] <= 0:
                raise ValueError('Invalid marks value')
        
        # Validate total marks is reasonable
        total = sum(q['max_marks'] for q in questions)
        if total <= 0 or total > 500:  # Sanity check
            raise ValueError(f'Unreasonable total marks: {total}')
        
        return {
            'status': 'SUCCESS',
            'questions': questions,
            'total_marks': total
        }
    
    except Exception as e:
        logger.error(f'QP extraction failed: {e}')
        return {
            'status': 'EXTRACTION_FAILED',
            'error': str(e),
            'questions': None
        }
```

**Recommendation**: Add comprehensive validation; fail explicitly if extraction unsuccessful

---

### 6.2 Evaluation Status Never Progresses (Stuck in Processing)

**Severity**: 🟡 HIGH  
**File**: `backend/server.py` (`/api/evaluate` endpoint)  
**Type**: User Experience & Feedback

**Problem**:
Evaluation endpoint processes synchronously (calls Gemini, waits for response).
For large papers, this can take 30+ seconds.

```python
@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    # Blocks for up to 60 seconds
    result = evaluate_full_pipeline(question_paper, answer_script)
    return result
```

**Frontend Impact**:
1. Frontend sends request
2. Shows "Processing..." for 60+ seconds
3. Browser may timeout (typical timeout is 30s)
4. User doesn't know if evaluation succeeded or failed
5. User refreshes page → duplicate evaluation created
6. No way to poll status

**Required Fix - Implement Async Processing**:
```python
@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    evaluation_id = str(uuid.uuid4())
    
    # Store evaluation record with PROCESSING status
    db.evaluations.insert_one({
        'evaluation_id': evaluation_id,
        'student_id': session['user_id'],
        'status': 'UPLOADING',
        'created_at': datetime.utcnow(),
        'files': {...}
    })
    
    # Queue async task (Celery, background thread, etc.)
    queue_evaluation_task.delay(evaluation_id)
    
    # Return immediately
    return {
        'evaluation_id': evaluation_id,
        'status': 'QUEUED'
    }

# Frontend can poll status
@app.route('/api/evaluations/<id>/status', methods=['GET'])
def get_evaluation_status(id):
    evaluation = db.evaluations.find_one({'evaluation_id': id})
    return {
        'status': evaluation['status'],  # UPLOADING, EXTRACTING_QP, EVALUATING, COMPLETED, etc.
        'progress': evaluation.get('progress', 0),
        'result': evaluation.get('result', None)
    }
```

**Recommendation**: Implement async evaluation with status polling

---

### 6.3 Fallback Marks Displayed Without Indication

**Severity**: 🔴 CRITICAL  
**File**: `learnsphere-ai/src/pages/HistoryPage.jsx` and similar  
**Type**: Fabricated Data Display

**Problem**:
```javascript
// HistoryPage displays evaluations
const displayed_marks = evaluation.obtained_marks || 100
const displayed_percentage = (evaluation.obtained_marks / evaluation.total_marks * 100) || 50
```

If evaluation failed or marks missing, hardcoded fallbacks displayed as real scores.

**Why It's Dangerous**:
- Teacher sees student achieved 100% when evaluation actually failed
- Student thinks they scored well when result unknown
- Permanent record shows fabricated grades
- Falsifies academic performance

**Required Fix**:
```javascript
function EvaluationResult({ evaluation }) {
  // Check if evaluation is actually complete
  if (evaluation.status !== 'COMPLETED') {
    return (
      <div className="status-alert">
        <p>Status: {evaluation.status}</p>
        {evaluation.status === 'NEEDS_TEACHER_REVIEW' && (
          <p>This evaluation requires teacher verification.</p>
        )}
        {evaluation.status === 'FAILED' && (
          <p>Evaluation could not be processed. {evaluation.error_message}</p>
        )}
      </div>
    )
  }
  
  // Only display if marks actually exist
  const marks = evaluation.obtained_marks
  const total = evaluation.total_marks
  
  if (marks === null || marks === undefined || total === null) {
    return <div>Marks not available</div>
  }
  
  const percentage = (marks / total) * 100
  return (
    <div>
      <p>Marks: {marks}/{total}</p>
      <p>Percentage: {percentage.toFixed(1)}%</p>
    </div>
  )
}
```

**Recommendation**: Check status before displaying; show truthful empty/error/review states

---

## SECTION 7: SYLLABUS ERRORS

### 7.1 Syllabus Data Not Persisted to Database

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (`/api/syllabus/analyze`)  
**Type**: Persistence Missing

**Problem**:
```python
@app.route('/api/syllabus/analyze', methods=['POST'])
def analyze_syllabus():
    # Analyzes syllabus
    result = gemini_service.analyze_syllabus(file)
    
    # ❌ Does NOT store in database
    # Result returned to frontend but immediately lost
    return result
```

**Consequence**:
1. Student uploads syllabus → analyzed → data returned to frontend
2. Frontend displays subjects/topics
3. Student refreshes page → syllabus data gone
4. Uploaded file deleted (if not persisted)
5. Student must re-upload to see syllabus again
6. When student takes evaluation, no syllabus context available
7. No audit of which students analyzed which syllabus

**Why It's Dangerous**:
- Students cannot access their own syllabus history
- Teachers cannot see student syllabi
- Syllabus data not linked to student
- Lost on logout/refresh

**Required Fix**:
```python
@app.route('/api/syllabus/analyze', methods=['POST'])
def analyze_syllabus():
    user_id = session.get('user_id')
    
    # Save file
    file = request.files['syllabus']
    file_hash = hashlib.sha256(file.read()).hexdigest()
    file_path = f'uploads/syllabus/{file_hash}_{file.filename}'
    file.save(file_path)
    
    # Analyze
    analysis = gemini_service.analyze_syllabus(file_path)
    
    # Validate response
    if not analysis or 'subjects' not in analysis:
        return {'error': 'Analysis failed'}, 400
    
    # Store in database
    syllabus_id = str(uuid.uuid4())
    db.syllabi.insert_one({
        'syllabus_id': syllabus_id,
        'student_id': user_id,
        'file_path': file_path,
        'file_hash': file_hash,
        'file_name': file.filename,
        'analysis': analysis,
        'status': 'READY',
        'version': 1,
        'created_at': datetime.utcnow()
    })
    
    return {
        'syllabus_id': syllabus_id,
        'analysis': analysis,
        'status': 'READY'
    }
```

**Recommendation**: Persist syllabus analysis to database with version control

---

### 7.2 No Syllabus Status Workflow (Analysis Never Completes)

**Severity**: 🟡 HIGH  
**File**: Frontend syllabus components  
**Type**: Feature Incomplete

**Problem**:
No state machine for syllabus status:
```
NOT_UPLOADED → UPLOADING → ANALYZING → READY
                                     ↓
                                   FAILED
```

Frontend shows upload button but no indication of analysis progress.

**Required Fix**:
```python
# Database schema with status
{
    'syllabus_id': '...',
    'student_id': '...',
    'status': 'NOT_UPLOADED|UPLOADING|ANALYZING|READY|FAILED',
    'progress': 0-100,
    'error_message': '...',
    'file_path': '...',
    'analysis': {...}
}

# Endpoints
POST /api/syllabus/upload  # Returns UPLOADING status
GET /api/syllabus/status   # Poll status
GET /api/syllabus          # Returns current syllabus if READY
```

**Recommendation**: Implement proper async syllabus workflow with status tracking

---

### 7.3 Subjects Loaded from Default List Instead of Syllabus

**Severity**: 🔴 CRITICAL  
**File**: Frontend (multiple pages)  
**Type**: Data Source Mismatch

**Problem**:
When no real syllabus exists, frontend displays hardcoded subjects:
```javascript
const subjects = syllabus?.subjects || ['Physics', 'Chemistry', 'Mathematics']
```

**Consequence**:
- Student sees default subjects even if their syllabus has different ones
- Student evaluations evaluated against wrong subject (subject mismatch in marks)
- Trainer features (practice) show wrong content
- Misconceptions tagged with wrong subject

**Required Fix**:
```javascript
// Only use subjects from actual parsed syllabus
const subjects = syllabus?.subjects || null

if (!subjects) {
  return (
    <div className="empty-state">
      <p>Please upload your syllabus first</p>
      <Link to="/upload-syllabus">Upload Syllabus</Link>
    </div>
  )
}

// Now safe to use subjects
return <SubjectList subjects={subjects} />
```

**Recommendation**: Block features until syllabus is actually uploaded and analyzed

---

## SECTION 8: FRONTEND STATE ERRORS

### 8.1 Mock Data Displayed Alongside Real Data (No Clear Distinction)

**Severity**: 🔴 CRITICAL  
**File**: `learnsphere-ai/src/data/mockData.js` and components using it  
**Type**: Data Integrity - Fake Data in Production

**Problem**:
```javascript
// Dashboard.jsx
const [evaluations, setEvaluations] = useState([])

useEffect(() => {
  try {
    const data = await api.getEvaluations()
    setEvaluations(data)
  } catch {
    // ❌ Fallback to mock data
    setEvaluations(mockData.recentEvaluationsTeacher)
  }
}, [])

// Renders mock data if API fails (no indication it's fake)
return <EvaluationList evals={evaluations} />
```

**Real Consequences**:
1. Backend API fails (network issue, server down)
2. Dashboard automatically shows mock data
3. User thinks they see real evaluations
4. Makes teaching decisions based on fabricated data
5. No error indication; appears normal

**Example in mockData.js**:
```javascript
const recentEvaluationsTeacher = [
  {
    id: 1,
    student: 'Rohan Das',
    subject: 'Physics',
    marks: '64/100',
    percentage: '64%',
    timestamp: '2 days ago'
  },
  // ... More hardcoded fake evaluations
]
```

**Why It's Dangerous**:
- Teachers believe they're reviewing real student work
- Grades are fabricated
- Permanent records affected
- Regulatory violations (FERPA)

**Required Fix**:
```javascript
// Dashboard.jsx
const [evaluations, setEvaluations] = useState(null)
const [error, setError] = useState(null)

useEffect(() => {
  async function loadEvaluations() {
    try {
      const data = await api.getEvaluations()
      setEvaluations(data)
      setError(null)
    } catch (err) {
      setEvaluations([])
      setError('Could not load evaluations. Please try again.')
    }
  }
  loadEvaluations()
}, [])

// Don't display mock data
if (error) {
  return <ErrorAlert message={error} />
}

if (evaluations.length === 0) {
  return <EmptyState message="No evaluations yet" />
}

return <EvaluationList evals={evaluations} />
```

**Recommendation**: Remove mockData.js from production; show error states instead

---

### 8.2 18+ localStorage Keys With No Cleanup

**Severity**: 🟡 HIGH  
**File**: `learnsphere-ai/src/context/AppContext.jsx`  
**Type**: Storage Management

**LocalStorage Keys**:
1. `ls-auth`
2. `ls-role`
3. `ls-user`
4. `ls-profile`
5. `ls-theme`
6. `ls-streak`
7. `ls-last-active-date`
8. `ls-study-sessions`
9. `ls-current-session-id`
10. `ls-activity-log`
11. `ls-syllabus-data`
12. `learnsphere_institution_mode`
13. `learnsphere_teacher_classes`
14. `learnsphere_active_class_id`
15. `learnsphere_action_center_items`
16. `learnsphere_saved_opps`
17. `ls-streak-{email}` (multiple per user)
18. `ls-last-active-date-{email}` (multiple per user)

**Problems**:
1. No size limits → can grow to MB if app used for years
2. No expiration → data persists indefinitely
3. No versioning → old keys never cleaned up
4. Privacy risk → all data visible in DevTools
5. Multiple keys per user → hard to track what belongs to who

**Required Fix**:
```javascript
// Centralized storage manager
class StorageManager {
  static readonly KEYS = {
    USER: 'app:user',
    AUTH: 'app:auth',
    SYLLABUS: 'app:syllabus'
  }
  
  static readonly TTL = {
    USER: 24 * 60 * 60 * 1000,      // 24 hours
    SYLLABUS: 30 * 24 * 60 * 60 * 1000  // 30 days
  }
  
  static set(key, value, ttl = null) {
    const item = {
      value,
      timestamp: Date.now(),
      ttl
    }
    localStorage.setItem(key, JSON.stringify(item))
  }
  
  static get(key) {
    const item = JSON.parse(localStorage.getItem(key))
    if (!item) return null
    
    // Check expiration
    if (item.ttl && Date.now() - item.timestamp > item.ttl) {
      localStorage.removeItem(key)
      return null
    }
    
    return item.value
  }
  
  static logout() {
    // Clear only auth-related keys
    localStorage.removeItem(StorageManager.KEYS.USER)
    localStorage.removeItem(StorageManager.KEYS.AUTH)
    // Keep syllabus for offline use (if applicable)
  }
}
```

**Recommendation**: Centralize storage with TTL support; clean up on logout

---

### 8.3 Streak Calculation Using localStorage (Not Validated)

**Severity**: 🟡 HIGH  
**File**: `learnsphere-ai/src/context/AppContext.jsx`  
**Type**: Data Integrity

**Problem**:
```javascript
// Streak stored in localStorage, never validated
const lastDate = localStorage.getItem(`ls-last-active-date-${email}`)
const today = new Date().toDateString()

if (lastDate === today) {
  // Already counted today
} else if (isYesterday(lastDate)) {
  // Increment streak
  streak += 1
} else {
  // Reset streak
  streak = 1
}

localStorage.setItem(`ls-streak-${email}`, streak)
```

**Attack**:
1. Student opens DevTools
2. Sets `localStorage.setItem('ls-streak-arun@school.com', 365)`
3. Frontend displays 365-day streak
4. No backend validation
5. Student falsifies engagement metrics

**Required Fix**:
```python
# Server tracks streak
{
    'user_id': '...',
    'streak_count': 10,
    'streak_started_date': datetime(2026, 9, 20),
    'last_activity_date': datetime(2026, 10, 1)
}

# Backend endpoint validates and increments
POST /api/user/streak/check
returns {
    'current_streak': 10,
    'activity_today': true/false,
    'last_activity': '2026-10-01'
}
```

**Recommendation**: Move streak tracking to backend; frontend only displays server value

---

## SECTION 9: MOBILE/PRODUCTION ERRORS

### 9.1 Localhost Assumption in Frontend API Calls

**Severity**: 🔴 CRITICAL  
**File**: `learnsphere-ai/src/api.js`  
**Type**: Production Configuration

**Problem**:
```javascript
// api.js
const API_BASE_URL = 'http://localhost:5000'

export const api = {
  login: (email, password) => 
    fetch(`${API_BASE_URL}/api/auth/login`, {...})
}
```

**Consequence**:
1. Build app for production
2. Deploy to `learnsphere.render.com`
3. Frontend hardcoded to `localhost:5000`
4. All API calls fail (CORS + wrong URL)
5. Application completely non-functional
6. Users on mobile/different network see blank app

**Deployment Scenario**:
- Student on iOS accesses `learnsphere.render.com`
- JavaScript tries to call `http://localhost:5000` (student's device)
- API call fails instantly
- App shows no data
- Teacher sees errors but not the root cause

**Required Fix**:
```javascript
// api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (window.location.hostname === 'localhost' 
    ? 'http://localhost:5000'
    : `https://${window.location.hostname}/api`)

// .env.production
VITE_API_URL=https://learnsphere-api.render.com

// vite.config.js
export default {
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL)
  }
}
```

**Recommendation**: Use environment variables for API URL; build separate production config

---

### 9.2 Backend Hardcoded to Port 5000 (Render Uses Dynamic PORT)

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` or `backend/app.py`  
**Type**: Deployment Configuration

**Problem**:
```python
# server.py
if __name__ == '__main__':
    app.run(host='localhost', port=5000)  # ❌ Hardcoded
```

**Render Deployment Issue**:
1. Render assigns dynamic PORT via env var
2. App listens on 5000
3. Render expects app on PORT (e.g., 54321)
4. Request to 54321 → not listening → timeout/error
5. App never starts successfully

**Workaround to Detect**:
- Check Render dashboard → shows "Service failed to start"
- Logs show port binding failure

**Required Fix**:
```python
# server.py
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = '0.0.0.0'  # Listen on all interfaces
    
    app.run(host=host, port=port, debug=False)
```

**Or use gunicorn (production-ready)**:
```bash
# Procfile (for Render)
web: gunicorn backend.wsgi:app

# wsgi.py
from backend.app import app

if __name__ == '__main__':
    app.run()
```

**Recommendation**: Use environment variable PORT; deploy with gunicorn

---

### 9.3 No Health Check Endpoint (Render Cannot Verify Startup)

**Severity**: 🟡 HIGH  
**File**: `backend/server.py`  
**Type**: Deployment Monitoring

**Problem**:
Render waits for HTTP 200 response to determine if app is ready.
Without health check, Render may restart app constantly.

**Required Fix**:
```python
@app.route('/health', methods=['GET'])
def health_check():
    # Verify app is running
    # Optionally check database connection
    try:
        if use_mongodb:
            client.admin.command('ping')
        return {
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }, 503
```

**Render Configuration** (render.yaml):
```yaml
services:
  - type: web
    name: learnsphere-backend
    healthCheckPath: /health
    healthCheckInterval: 30
    healthCheckTimeout: 5
```

**Recommendation**: Add `/health` endpoint; configure Render health checks

---

## SECTION 10: SECURITY ERRORS

### 10.1 No Rate Limiting on Login (Brute Force Vulnerability)

**Severity**: 🟡 HIGH  
**File**: `backend/server.py` (`/api/auth/login`)  
**Type**: Brute Force Attack

**Problem**:
```python
@app.route('/api/auth/login', methods=['POST'])
def login():
    # No rate limiting
    # Attacker can try 1000 passwords per second
    email = request.json['email']
    password = request.json['password']
    ...
```

**Attack**:
```bash
# Attacker script
for password in wordlist.txt:
  POST /api/auth/login { email: student@school.com, password }
  
# After 10000 attempts, finds correct password
```

**Required Fix**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=['200 per day', '50 per hour']
)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit('5 per minute')  # Max 5 login attempts per minute per IP
def login():
    email = request.json['email']
    password = request.json['password']
    ...
```

**Recommendation**: Implement rate limiting on auth endpoints

---

### 10.2 No Input Validation on API Endpoints

**Severity**: 🟡 HIGH  
**File**: `backend/server.py` (all endpoints)  
**Type**: Injection Attacks / Data Corruption

**Problem**:
```python
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    # No validation of email, name, password
    
    name = data.get('name')  # Could be 50000 chars
    email = data.get('email')  # Could be invalid
    password = data.get('password')  # Could be 1 char
    
    # Insert directly
    db.users.insert_one({
        'name': name,
        'email': email,
        'password_hash': hash(password)
    })
```

**Required Fix**:
```python
from email_validator import validate_email, EmailNotValidError

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    
    # Validate name
    name = data.get('name', '').strip()
    if not name or len(name) < 2 or len(name) > 100:
        return {'error': 'Name must be 2-100 characters'}, 400
    
    # Validate email
    try:
        email = validate_email(data.get('email', '')).lower()
    except EmailNotValidError as e:
        return {'error': f'Invalid email: {str(e)}'}, 400
    
    # Validate password
    password = data.get('password', '')
    if len(password) < 8:
        return {'error': 'Password must be at least 8 characters'}, 400
    if not any(c.isupper() for c in password):
        return {'error': 'Password must contain uppercase letter'}, 400
    
    # Check duplicate email
    if db.users.find_one({'email': email}):
        return {'error': 'Email already registered'}, 409
    
    # Create user
    password_hash = generate_password_hash(password)
    db.users.insert_one({
        'user_id': str(uuid.uuid4()),
        'name': name,
        'email': email,
        'password_hash': password_hash,
        'role': data.get('role'),
        'created_at': datetime.utcnow()
    })
    
    return {'success': True}, 201
```

**Recommendation**: Add input validation to all endpoints

---

### 10.3 No File Upload Security Validation

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (`/api/evaluate` endpoint)  
**Type**: Arbitrary File Upload

**Problem**:
```python
@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    question_paper = request.files['question_paper']
    answer_script = request.files['answer_script']
    
    # No validation
    question_paper.save(f'uploads/{question_paper.filename}')  # ❌ Path traversal risk
```

**Attacks**:
1. **Path Traversal**: Upload file named `../../etc/passwd` → overwrites system files
2. **Arbitrary Code Execution**: Upload `.py` file → executed by server
3. **Resource Exhaustion**: Upload 1GB file → fills disk
4. **MIME Mismatch**: Upload `.exe` disguised as `.pdf`

**Required Fix**:
```python
import os
import magic
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'txt'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_file_upload(file):
    # Check filename
    filename = secure_filename(file.filename)
    if not filename:
        raise ValueError('Invalid filename')
    
    # Check extension
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'File type .{ext} not allowed')
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValueError(f'File too large: {size / 1024 / 1024}MB')
    
    # Check MIME type (magic bytes)
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(file.read(1024))
    file.seek(0)
    
    if mime_type not in ['application/pdf', 'image/jpeg', 'image/png', 'text/plain']:
        raise ValueError(f'MIME type {mime_type} not allowed')
    
    return filename

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    try:
        question_paper = request.files['question_paper']
        answer_script = request.files['answer_script']
        
        qp_name = validate_file_upload(question_paper)
        as_name = validate_file_upload(answer_script)
        
        # Store with secure path
        qp_hash = hashlib.sha256(question_paper.read()).hexdigest()
        question_paper.seek(0)
        qp_path = f'uploads/{qp_hash}_{qp_name}'
        question_paper.save(qp_path)
        
        # ... continue evaluation
    
    except ValueError as e:
        return {'error': str(e)}, 400
```

**Recommendation**: Validate file uploads (size, type, MIME, safe names)

---

## SECTION 11: API CONTRACT ERRORS

### 11.1 Snake_case vs camelCase Field Name Inconsistencies

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` (snake_case) ↔ `learnsphere-ai/src/api.js` (camelCase)  
**Type**: Data Format Mismatch

**Examples**:
```python
# Backend (server.py) returns:
{
    "teacher_level": "school",
    "grade_level": "10",
    "student_name": "Arun Kumar",
    "created_at": "2026-10-01T10:00:00Z"
}

# Frontend (AppContext.jsx) expects:
{
    "teacherLevel": "school",
    "gradeLevel": "10",
    "studentName": "Arun Kumar",
    "createdAt": "2026-10-01T10:00:00Z"
}

// Result: frontend receives null/undefined values
this.state.teacherLevel  // undefined (backend sends teacher_level)
```

**Fields with Mismatch**:
| Backend | Frontend | Issue |
|---------|----------|-------|
| `teacher_level` | `teacherLevel` | Registration form fails |
| `grade_level` | `classLevel` or `gradeLevel` | Profile incomplete |
| `institution_name` | `institutionName` | Dropdown empty |
| `created_at` | `createdAt` | Timestamp parsing fails |
| `student_name` | `studentName` | Display shows undefined |

**Consequence**:
- User registration shows empty values after submit
- Profile page incomplete
- Dashboard displays "undefined" for names
- Teacher cannot see student info

**Required Fix - Option 1: Standardize Backend to camelCase**:
```python
# server.py - use a response formatter
def format_user_response(user):
    return {
        'userId': str(user.get('_id')),
        'name': user.get('name'),
        'email': user.get('email'),
        'role': user.get('role'),
        'teacherLevel': user.get('teacher_level'),
        'gradeLevel': user.get('grade_level'),
        'institutionName': user.get('institution_name'),
        'createdAt': user.get('created_at').isoformat() if user.get('created_at') else None
    }

@app.route('/api/auth/login', methods=['POST'])
def login():
    ...
    return {'user': format_user_response(user)}, 200
```

**Required Fix - Option 2: Keep Backend snake_case, Format in Frontend**:
```javascript
// api.js
function formatUser(backendUser) {
  return {
    userId: backendUser.user_id,
    name: backendUser.name,
    email: backendUser.email,
    role: backendUser.role,
    teacherLevel: backendUser.teacher_level,
    gradeLevel: backendUser.grade_level,
    institutionName: backendUser.institution_name,
    createdAt: backendUser.created_at
  }
}

export const api = {
  login: async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, ...)
    const data = await response.json()
    return { ...data, user: formatUser(data.user) }
  }
}
```

**Recommendation**: Choose ONE standard; apply consistently to all endpoints

---

### 11.2 Multiple Field Names for Same Data (Questions/Evaluations)

**Severity**: 🟡 HIGH  
**File**: `backend/server.py`  
**Type**: API Inconsistency

**Problem**:
Same endpoint returns different field names in different responses.

```python
# Endpoint 1: /api/evaluations/{id}
{
    "id": "...",
    "questions": [...]  # Field name: "questions"
}

# Endpoint 2: /api/evaluations (list)
{
    "evaluation_id": "...",
    "evaluations": [...]  # Field name: "evaluations"
}
```

**Frontend Confusion**:
```javascript
// Frontend checks for different names
evaluation.questions  // Works for GET /{id}
evaluations[i].evaluations  // Works for list
// But inconsistent naming causes parsing errors
```

**Required Fix**:
```python
# Standardize field names
@app.route('/api/evaluations', methods=['GET'])
def list_evaluations():
    evaluations = db.evaluations.find({'student_id': user_id})
    return {
        'evaluations': [
            {
                'evaluation_id': str(e['_id']),
                'student_id': e['student_id'],
                'questions': e.get('questions', []),
                'status': e['status'],
                'created_at': e['created_at'].isoformat()
            }
            for e in evaluations
        ]
    }

@app.route('/api/evaluations/<id>', methods=['GET'])
def get_evaluation(id):
    evaluation = db.evaluations.find_one({'_id': ObjectId(id)})
    return {
        'evaluation': {
            'evaluation_id': str(evaluation['_id']),
            'student_id': evaluation['student_id'],
            'questions': evaluation.get('questions', []),
            'status': evaluation['status'],
            'created_at': evaluation['created_at'].isoformat()
        }
    }
```

**Recommendation**: Document and enforce API schema; use OpenAPI/Swagger

---

## SECTION 12: MOCK/FALLBACK-DATA ERRORS

### 12.1 Mock Data Never Cleared (Persists Across Users)

**Severity**: 🔴 CRITICAL  
**File**: `learnsphere-ai/src/data/mockData.js` and components  
**Type**: Data Contamination Across Users

**Problem**:
```javascript
// mockData.js contains hardcoded students
const allStudents = [
  { id: 1, name: 'Rohan Das', score: 64 },
  { id: 2, name: 'Kavya Venkat', score: 58 },
  { id: 3, name: 'Priya Sharma', score: 72 }
]

// Dashboard.jsx uses it
function TeacherDashboard() {
  const [students, setStudents] = useState(mockData.allStudents)  // ❌ Mock data
}
```

**Scenario**:
1. Teacher A logs in → sees mock students (Rohan Das, Kavya, Priya)
2. API fails
3. Dashboard shows mock data
4. Teacher A makes decisions based on fake data
5. Teacher A logs out
6. Teacher B logs in → ALSO sees Rohan Das, Kavya, Priya (wrong teacher's mock data!)
7. Teacher B thinks these are their students

**Why It's Dangerous**:
- Data from one teacher leaks to another
- False sense of knowledge about students
- Decisions made on wrong data
- Students could be penalized for data that doesn't belong to them

**Required Fix**:
```javascript
// Remove mockData from imports
// Replace with proper error handling

function TeacherDashboard() {
  const [students, setStudents] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadStudents() {
      try {
        const data = await api.getMyStudents()
        setStudents(data)
      } catch (err) {
        setError('Failed to load students. Please try again.')
        setStudents([])  // Empty list, NOT mock data
      } finally {
        setLoading(false)
      }
    }
    loadStudents()
  }, [])

  if (loading) return <Loading />
  if (error) return <ErrorAlert message={error} />
  if (!students || students.length === 0) {
    return <EmptyState message="No students assigned yet" />
  }
  
  return <StudentList students={students} />
}
```

**Recommendation**: Remove mockData.js; implement proper error states

---

### 12.2 Hardcoded Marks Returned as Evaluation Results

**Severity**: 🔴 CRITICAL  
**File**: `backend/app/evaluation/store.py`  
**Type**: Fabricated Academic Data

**Problem**:
```python
# If evaluation fails or data missing, fallback marks inserted:
if obtained_marks is None:
    obtained_marks = 0  # ❌ Hardcoded fallback

percentage = (obtained_marks / total_marks) * 100 if total_marks else 50  # ❌ Fallback

# Result stored as if evaluation succeeded
db.evaluations.insert_one({
    'obtained_marks': obtained_marks or 0,
    'percentage': percentage or 50,
    'status': 'COMPLETED'  # ❌ Should be FAILED
})
```

**Consequence**:
1. Evaluation fails (Gemini API error, PDF unreadable)
2. Instead of returning error, system inserts evaluation with marks=0 or 50
3. Student/Teacher sees "evaluation completed"
4. Marks look real but are fabricated
5. Permanent record now contains false grade

**Example**:
- Student uploads illegible handwritten PDF
- Gemini cannot extract answers
- Backend should return error
- Instead: evaluation created with 50 marks (guessed average)
- Student's transcript shows 50% for work they didn't complete properly

**Required Fix**:
```python
def store_evaluation_result(evaluation_data):
    # Validate BEFORE storing
    if not evaluation_data.get('questions'):
        return {'error': 'Question extraction failed', 'status': 'FAILED'}, 400
    
    obtained = evaluation_data.get('obtained_marks')
    total = evaluation_data.get('total_marks')
    
    # Never allow None or 0 without evidence
    if obtained is None or total is None:
        return {'error': 'Marks calculation incomplete', 'status': 'NEEDS_TEACHER_REVIEW'}, 400
    
    # Validate range
    if not (0 <= obtained <= total):
        return {'error': 'Invalid marks range', 'status': 'FAILED'}, 400
    
    # Calculate percentage (only if marks valid)
    percentage = round((obtained / total) * 100, 2)
    
    # Determine status
    status = 'COMPLETED' if percentage >= 0 else 'NEEDS_TEACHER_REVIEW'
    
    # Store with explicit status
    result = db.evaluations.insert_one({
        'obtained_marks': obtained,
        'total_marks': total,
        'percentage': percentage,
        'status': status,
        'is_verified': False
    })
    
    return {'success': True, 'evaluation_id': str(result.inserted_id)}, 201
```

**Recommendation**: Validate all data before storing; reject evaluations with missing/guessed values

---

## SECTION 13: DEPLOYMENT ERRORS

### 13.1 No Environment Variable Validation on Startup

**Severity**: 🔴 CRITICAL  
**File**: `backend/server.py` and `backend/.env`  
**Type**: Configuration Management

**Problem**:
```python
# App starts even if critical env vars missing
MONGODB_URI = os.getenv('MONGODB_URI')  # Could be None
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Could be None

# Later, when evaluation attempted:
response = call_gemini(prompt)  # ❌ Crash: API key None
```

**Deployment Consequence**:
1. Deploy to Render
2. Forget to set MONGODB_URI env var
3. App starts successfully (no validation)
4. User tries to login
5. App crashes when querying MongoDB (None as connection string)
6. Render marks service as unhealthy
7. Auto-restart loop; users see "Service Unavailable"

**Required Fix**:
```python
import sys

def validate_environment():
    """Validate all required environment variables on startup"""
    
    required_vars = {
        'MONGODB_URI': 'MongoDB connection string',
        'MONGODB_DB_NAME': 'MongoDB database name',
        'GEMINI_API_KEY': 'Google Gemini API key',
        'GEMINI_MODEL': 'Gemini model identifier',
        'SECRET_KEY': 'Flask session secret key'
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f'{var} ({description})')
    
    if missing:
        logger.critical(f'Missing required environment variables:')
        for var in missing:
            logger.critical(f'  - {var}')
        sys.exit(1)
    
    # Validate values are not defaults
    secret = os.getenv('SECRET_KEY')
    if secret in ['dev-secret', 'test-secret', 'learnsphere-ai-secret-key']:
        logger.critical('SECRET_KEY is using a default value. Set a strong random key in production.')
        sys.exit(1)
    
    logger.info('All environment variables validated')

# Call on app startup
if __name__ == '__main__':
    validate_environment()
    app.run()
```

**Render Configuration** (render.yaml):
```yaml
env:
  - key: MONGODB_URI
    scope: "*"
  - key: GEMINI_API_KEY
    scope: "*"
    secure: true  # Encrypted in Render dashboard
  - key: SECRET_KEY
    scope: "*"
    secure: true
```

**Recommendation**: Validate environment on startup; fail explicitly if missing

---

### 13.2 No Database Health Check on Startup

**Severity**: 🟡 HIGH  
**File**: `backend/server.py`  
**Type**: Startup Validation

**Problem**:
```python
# App starts without verifying MongoDB is actually accessible
app = Flask(__name__)

@app.route('/api/auth/login', methods=['POST'])
def login():
    # First login attempt reveals MongoDB is down
    user = db.users.find_one(...)  # ❌ Crash: connection failed
```

**User Impact**:
1. App starts (appears ready)
2. User navigates to login
3. Sudden crash/timeout
4. No error message explaining database is down

**Required Fix**:
```python
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging

logger = logging.getLogger(__name__)

def check_database_health():
    """Verify database is accessible on startup"""
    try:
        client = MongoClient(
            os.getenv('MONGODB_URI'),
            serverSelectionTimeoutMS=5000
        )
        client.admin.command('ping')
        logger.info('✓ MongoDB connection verified')
        return True
    except ConnectionFailure as e:
        logger.error(f'✗ MongoDB connection failed: {e}')
        if os.getenv('ENV') == 'production':
            logger.critical('Cannot start in production without MongoDB')
            sys.exit(1)
        return False

# Before running app
if __name__ == '__main__':
    validate_environment()
    check_database_health()
    app.run()
```

**Recommendation**: Verify database connection before accepting requests

---

## CRITICAL SUMMARY TABLE

| Issue | Severity | Impact | Fix Complexity |
|-------|----------|--------|-----------------|
| DEFAULT_USERS undefined | 🔴 CRITICAL | App crashes on startup | Low |
| Plaintext password fallback | 🔴 CRITICAL | Data breach risk | Medium |
| X-User-ID auth bypass | 🔴 CRITICAL | Account takeover | Low |
| Fabricated evaluation marks | 🔴 CRITICAL | False academic records | High |
| localStorage authentication | 🔴 CRITICAL | Indefinite session | High |
| Dual database architecture | 🔴 CRITICAL | Data inconsistency | High |
| No teacher-student verification | 🔴 CRITICAL | Student data leakage | Medium |
| Teacher override no audit | 🔴 CRITICAL | Grade tampering untracked | Low |
| Mock data in production | 🔴 CRITICAL | Fabricated student data | Low |
| Localhost hardcoded | 🔴 CRITICAL | App non-functional in production | Low |
| No rate limiting | 🟡 HIGH | Brute force attacks | Medium |
| No file upload validation | 🟡 HIGH | Arbitrary file upload | Medium |
| Field naming inconsistencies | 🟡 HIGH | API parsing failures | Medium |
| No email verification | 🟡 HIGH | Email spoofing possible | Medium |
| No CSRF protection | 🟡 HIGH | Cross-site attacks | Medium |

---

## NEXT STEPS

**PHASE 2-12 implementation required** (See task breakdown in requirements document).

Start with:
1. Fix DEFAULT_USERS crash
2. Remove X-User-ID authentication
3. Implement MongoDB validation
4. Implement proper login flow with server-side session
5. Remove mock data
6. Fix evaluation status workflow
7. Add comprehensive tests

**DO NOT** ship to production until:
- [ ] All CRITICAL issues resolved
- [ ] Tests pass
- [ ] Database persistence verified
- [ ] Mobile/network tested
- [ ] Security hardening complete
- [ ] Documentation updated

---

**Audit completed**: October 1, 2026  
**Recommended action**: Begin PHASE 2 immediately
