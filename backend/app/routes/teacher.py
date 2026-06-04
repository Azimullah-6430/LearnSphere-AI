from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.database import User, TeacherProfile, StudentProfile, Class, Submission, Evaluation, EvaluationReport
from app.auth import teacher_required
from sqlalchemy import func

bp = Blueprint('teacher', __name__, url_prefix='/api/teacher')

@bp.route('/dashboard', methods=['GET'])
@teacher_required
def get_dashboard():
    """Get teacher dashboard analytics"""
    try:
        identity = get_jwt_identity()
        teacher = TeacherProfile.query.filter_by(user_id=identity['user_id']).first()
        
        if not teacher:
            return {'error': 'Teacher profile not found'}, 404
        
        # Get statistics
        total_students = len(teacher.classes) if teacher.classes else 0
        total_evaluations = len(teacher.evaluations) if teacher.evaluations else 0
        
        # Calculate class average
        evaluations = Evaluation.query.filter_by(teacher_id=teacher.id).all()
        class_avg = sum([e.percentage for e in evaluations]) / len(evaluations) if evaluations else 0
        
        # Get recent submissions
        recent_submissions = Submission.query.order_by(Submission.created_at.desc()).limit(10).all()
        
        return {
            'total_students': total_students,
            'total_evaluations': total_evaluations,
            'class_average': round(class_avg, 2),
            'classes': [c.to_dict() for c in teacher.classes],
            'recent_submissions': [s.to_dict() for s in recent_submissions]
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/submissions/pending', methods=['GET'])
@teacher_required
def get_pending_submissions():
    """Get pending submissions for evaluation"""
    try:
        identity = get_jwt_identity()
        
        # Get teacher's students
        teacher = TeacherProfile.query.filter_by(user_id=identity['user_id']).first()
        
        # Get pending submissions
        pending = Submission.query.filter_by(status='pending').all()
        
        return {
            'pending_count': len(pending),
            'submissions': [{
                'id': s.id,
                'student_name': s.student.user.first_name + ' ' + s.student.user.last_name,
                'student_email': s.student.user.email,
                'subject': s.subject,
                'level': s.level,
                'stream': s.stream,
                'created_at': s.created_at,
                'status': s.status
            } for s in pending]
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/evaluate/<submission_id>', methods=['POST'])
@teacher_required
def evaluate_submission(submission_id):
    """Teacher evaluates AI-generated evaluation"""
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        submission = Submission.query.get(submission_id)
        if not submission:
            return {'error': 'Submission not found'}, 404
        
        # Find or create evaluation
        evaluation = Evaluation.query.filter_by(submission_id=submission_id).first()
        if not evaluation:
            return {'error': 'Evaluation not found'}, 404
        
        # Teacher adds feedback
        evaluation.teacher_score = data.get('teacher_score')
        evaluation.teacher_feedback = data.get('teacher_feedback')
        evaluation.question_wise_feedback = data.get('question_wise_feedback')
        evaluation.evaluation_status = 'teacher_done'
        
        submission.status = 'evaluated'
        
        db.session.commit()
        
        # Create report to send to student
        report = EvaluationReport(
            evaluation_id=evaluation.id,
            submission_id=submission_id,
            report_content={
                'ai_score': evaluation.ai_score,
                'teacher_score': evaluation.teacher_score,
                'feedback': evaluation.teacher_feedback
            },
            overall_analysis=data.get('overall_analysis'),
            strengths=data.get('strengths'),
            improvements=data.get('improvements'),
            suggestions=data.get('suggestions')
        )
        db.session.add(report)
        db.session.commit()
        
        return {
            'message': 'Evaluation submitted successfully',
            'report_id': report.id,
            'sent_to_student': True
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500

@bp.route('/analytics', methods=['GET'])
@teacher_required
def get_analytics():
    """Get comprehensive analytics"""
    try:
        identity = get_jwt_identity()
        teacher = TeacherProfile.query.filter_by(user_id=identity['user_id']).first()
        
        # Get all evaluations
        evaluations = Evaluation.query.filter_by(teacher_id=teacher.id).all()
        
        # Calculate statistics
        scores = [e.percentage for e in evaluations if e.percentage]
        total_evaluations = len(evaluations)
        avg_score = sum(scores) / len(scores) if scores else 0
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0
        
        # Subject-wise analytics
        subject_stats = {}
        for eval in evaluations:
            subject = eval.submission.subject
            if subject not in subject_stats:
                subject_stats[subject] = {'count': 0, 'total_score': 0}
            subject_stats[subject]['count'] += 1
            subject_stats[subject]['total_score'] += eval.percentage
        
        # Calculate averages per subject
        for subject in subject_stats:
            subject_stats[subject]['avg_score'] = round(
                subject_stats[subject]['total_score'] / subject_stats[subject]['count'], 2
            )
        
        return {
            'total_evaluations': total_evaluations,
            'class_average': round(avg_score, 2),
            'highest_score': highest_score,
            'lowest_score': lowest_score,
            'subject_wise_stats': subject_stats,
            'total_students': teacher.total_students,
            'avg_class_score': teacher.avg_class_score
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500