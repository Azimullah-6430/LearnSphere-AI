from app import db
from datetime import datetime
from uuid import uuid4

class BaseModel(db.Model):
    """Base model for all database models"""
    __abstract__ = True
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class User(BaseModel):
    """User model for authentication"""
    __tablename__ = 'users'
    
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(255))
    
    # Relationships
    teacher_profile = db.relationship('TeacherProfile', uselist=False, backref='user')
    student_profile = db.relationship('StudentProfile', uselist=False, backref='user')
    
    def __repr__(self):
        return f'<User {self.email}>'

class TeacherProfile(BaseModel):
    """Teacher profile model"""
    __tablename__ = 'teacher_profiles'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    qualification = db.Column(db.String(255))
    experience_years = db.Column(db.Integer)
    specialization = db.Column(db.String(255))
    department = db.Column(db.String(100))
    total_students = db.Column(db.Integer, default=0)
    avg_class_score = db.Column(db.Float, default=0.0)
    
    # Relationships
    classes = db.relationship('Class', backref='teacher', lazy=True)
    evaluations = db.relationship('Evaluation', backref='teacher', lazy=True)

class StudentProfile(BaseModel):
    """Student profile model"""
    __tablename__ = 'student_profiles'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    roll_number = db.Column(db.String(50), unique=True)
    class_id = db.Column(db.String(36), db.ForeignKey('classes.id'))
    total_score = db.Column(db.Float, default=0.0)
    avg_score = db.Column(db.Float, default=0.0)
    total_evaluations = db.Column(db.Integer, default=0)
    focus_hours = db.Column(db.Float, default=0.0)
    encouragement_tokens = db.Column(db.Integer, default=0)
    
    # Relationships
    parent_profile = db.relationship('ParentProfile', uselist=False, backref='student')
    submissions = db.relationship('Submission', backref='student', lazy=True)
    evaluations = db.relationship('Evaluation', backref='student', lazy=True)

class ParentProfile(BaseModel):
    """Parent profile model"""
    __tablename__ = 'parent_profiles'
    
    student_id = db.Column(db.String(36), db.ForeignKey('student_profiles.id'), nullable=False, unique=True)
    parent_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    relationship = db.Column(db.String(50))  # Father, Mother, Guardian

class Class(BaseModel):
    """Class/Subject model"""
    __tablename__ = 'classes'
    
    teacher_id = db.Column(db.String(36), db.ForeignKey('teacher_profiles.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)  # School, College
    stream = db.Column(db.String(50))  # Physics, Chemistry, Maths
    total_students = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float, default=0.0)
    
    # Relationships
    students = db.relationship('StudentProfile', backref='class_ref', lazy=True)

class Submission(BaseModel):
    """Student submission model"""
    __tablename__ = 'submissions'
    
    student_id = db.Column(db.String(36), db.ForeignKey('student_profiles.id'), nullable=False)
    question_paper_path = db.Column(db.String(255), nullable=False)
    answer_script_path = db.Column(db.String(255), nullable=False)
    submission_type = db.Column(db.String(20), nullable=False)  # 'teacher_eval' or 'self_eval'
    subject = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)  # School, College
    stream = db.Column(db.String(50), nullable=False)  # Physics, Chemistry, Maths
    status = db.Column(db.String(20), default='pending')  # pending, evaluated, flagged
    is_plagiarism_checked = db.Column(db.Boolean, default=False)
    plagiarism_score = db.Column(db.Float, default=0.0)
    
    # Relationships
    evaluations = db.relationship('Evaluation', backref='submission', lazy=True)
    plagiarism_matches = db.relationship('PlagiarismMatch', backref='submission', lazy=True)

class Evaluation(BaseModel):
    """Evaluation model"""
    __tablename__ = 'evaluations'
    
    submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey('student_profiles.id'), nullable=False)
    teacher_id = db.Column(db.String(36), db.ForeignKey('teacher_profiles.id'))
    ai_score = db.Column(db.Float, nullable=False)
    ai_accuracy = db.Column(db.Float, nullable=False)  # 95%+
    teacher_score = db.Column(db.Float)
    total_marks = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float)
    ai_feedback = db.Column(db.Text)
    teacher_feedback = db.Column(db.Text)
    question_wise_feedback = db.Column(db.JSON)  # Store feedback for each question
    evaluation_status = db.Column(db.String(20), default='ai_pending')  # ai_pending, ai_done, teacher_pending, teacher_done
    
    # Relationships
    report = db.relationship('EvaluationReport', uselist=False, backref='evaluation')

class EvaluationReport(BaseModel):
    """Evaluation report model - sent to student"""
    __tablename__ = 'evaluation_reports'
    
    evaluation_id = db.Column(db.String(36), db.ForeignKey('evaluations.id'), nullable=False, unique=True)
    submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    report_content = db.Column(db.JSON)  # Detailed report with analysis
    overall_analysis = db.Column(db.Text)
    strengths = db.Column(db.JSON)  # List of strengths
    improvements = db.Column(db.JSON)  # List of improvements
    suggestions = db.Column(db.JSON)  # Suggestions for each question
    comparison_with_self_eval = db.Column(db.JSON)  # If exists
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    viewed_at = db.Column(db.DateTime)
    
    # Relationships
    student_notifications = db.relationship('Notification', backref='report', lazy=True)

class PlagiarismMatch(BaseModel):
    """Plagiarism detection model"""
    __tablename__ = 'plagiarism_matches'
    
    submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    matched_submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    similarity_percentage = db.Column(db.Float, nullable=False)
    match_type = db.Column(db.String(50), nullable=False)  # 'renamed_pdf', 'content_similarity', 'exact_match'
    flagged = db.Column(db.Boolean, default=True)
    flagged_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    teacher_reviewed = db.Column(db.Boolean, default=False)
    teacher_review_notes = db.Column(db.Text)
    
    # Get student details
    @property
    def student_1_details(self):
        submission = Submission.query.get(self.submission_id)
        if submission:
            student = submission.student
            return {
                'id': student.id,
                'name': student.user.first_name + ' ' + student.user.last_name,
                'email': student.user.email,
                'roll_number': student.roll_number
            }
        return None
    
    @property
    def student_2_details(self):
        submission = Submission.query.get(self.matched_submission_id)
        if submission:
            student = submission.student
            return {
                'id': student.id,
                'name': student.user.first_name + ' ' + student.user.last_name,
                'email': student.user.email,
                'roll_number': student.roll_number
            }
        return None

class PerformanceHistory(BaseModel):
    """Memory agent - permanent performance history"""
    __tablename__ = 'performance_history'
    
    student_id = db.Column(db.String(36), db.ForeignKey('student_profiles.id'), nullable=False)
    evaluation_id = db.Column(db.String(36), db.ForeignKey('evaluations.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    level = db.Column(db.String(50), nullable=False)
    stream = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Statistics
    rank_in_class = db.Column(db.Integer)
    feedback_summary = db.Column(db.Text)

class FocusSession(BaseModel):
    """Focus session tracking model"""
    __tablename__ = 'focus_sessions'
    
    student_id = db.Column(db.String(36), db.ForeignKey('student_profiles.id'), nullable=False)
    subject = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    focus_score = db.Column(db.Float)  # 0-100
    distractions_blocked = db.Column(db.Integer, default=0)

class Notification(BaseModel):
    """Notification model"""
    __tablename__ = 'notifications'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'evaluation_ready', 'plagiarism_alert', 'encouragement'
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'))
    related_report_id = db.Column(db.String(36), db.ForeignKey('evaluation_reports.id'))
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
