from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.database import StudentProfile, PerformanceHistory, FocusSession, Notification, Evaluation, EvaluationReport
from app.auth import student_required
from datetime import datetime, timedelta

bp = Blueprint('student', __name__, url_prefix='/api/student')

@bp.route('/dashboard', methods=['GET'])
@student_required
def get_dashboard():
    """Get student dashboard"""
    try:
        identity = get_jwt_identity()
        student = StudentProfile.query.filter_by(user_id=identity['user_id']).first()
        
        if not student:
            return {'error': 'Student profile not found'}, 404
        
        # Get performance metrics
        performance_history = PerformanceHistory.query.filter_by(student_id=student.id).order_by(
            PerformanceHistory.timestamp.desc()
        ).limit(10).all()
        
        # Get focus sessions this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        focus_sessions = FocusSession.query.filter(
            FocusSession.student_id == student.id,
            FocusSession.start_time >= month_ago
        ).all()
        
        total_focus_hours = sum([s.duration_minutes or 0 for s in focus_sessions]) / 60
        
        # Get recent notifications
        notifications = Notification.query.filter_by(user_id=identity['user_id']).order_by(
            Notification.created_at.desc()
        ).limit(5).all()
        
        return {
            'student_id': student.id,
            'total_score': student.total_score,
            'avg_score': student.avg_score,
            'total_evaluations': student.total_evaluations,
            'focus_hours_this_month': round(total_focus_hours, 2),
            'encouragement_tokens': student.encouragement_tokens,
            'performance_history': [p.to_dict() for p in performance_history],
            'recent_notifications': [n.to_dict() for n in notifications]
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/focus-session/start', methods=['POST'])
@student_required
def start_focus_session():
    """Start a focus session"""
    try:
        identity = get_jwt_identity()
        student = StudentProfile.query.filter_by(user_id=identity['user_id']).first()
        data = request.get_json()
        
        session = FocusSession(
            student_id=student.id,
            subject=data.get('subject'),
            start_time=datetime.utcnow()
        )
        db.session.add(session)
        db.session.commit()
        
        return {
            'session_id': session.id,
            'message': 'Focus session started',
            'start_time': session.start_time
        }, 201
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500

@bp.route('/focus-session/<session_id>/end', methods=['POST'])
@student_required
def end_focus_session(session_id):
    """End a focus session"""
    try:
        session = FocusSession.query.get(session_id)
        if not session:
            return {'error': 'Session not found'}, 404
        
        data = request.get_json()
        
        session.end_time = datetime.utcnow()
        session.duration_minutes = int((session.end_time - session.start_time).total_seconds() / 60)
        session.focus_score = data.get('focus_score', 0)
        session.distractions_blocked = data.get('distractions_blocked', 0)
        
        db.session.commit()
        
        return {
            'session_id': session.id,
            'duration_minutes': session.duration_minutes,
            'focus_score': session.focus_score,
            'message': 'Focus session ended'
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500

@bp.route('/evaluations', methods=['GET'])
@student_required
def get_evaluations():
    """Get all evaluations for student"""
    try:
        identity = get_jwt_identity()
        student = StudentProfile.query.filter_by(user_id=identity['user_id']).first()
        
        evaluations = Evaluation.query.filter_by(student_id=student.id).order_by(
            Evaluation.created_at.desc()
        ).all()
        
        eval_data = []
        for eval in evaluations:
            report = EvaluationReport.query.filter_by(evaluation_id=eval.id).first()
            eval_data.append({
                'id': eval.id,
                'subject': eval.submission.subject,
                'ai_score': eval.ai_score,
                'teacher_score': eval.teacher_score,
                'percentage': eval.percentage,
                'status': eval.evaluation_status,
                'created_at': eval.created_at,
                'report_id': report.id if report else None
            })
        
        return {
            'total_evaluations': len(evaluations),
            'evaluations': eval_data
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/evaluation/<evaluation_id>/report', methods=['GET'])
@student_required
def get_evaluation_report(evaluation_id):
    """Get evaluation report"""
    try:
        report = EvaluationReport.query.filter_by(evaluation_id=evaluation_id).first()
        
        if not report:
            return {'error': 'Report not found'}, 404
        
        # Mark as viewed
        if not report.viewed_at:
            report.viewed_at = datetime.utcnow()
            db.session.commit()
        
        return {
            'report_id': report.id,
            'overall_analysis': report.overall_analysis,
            'strengths': report.strengths,
            'improvements': report.improvements,
            'suggestions': report.suggestions,
            'comparison_with_self_eval': report.comparison_with_self_eval,
            'sent_at': report.sent_at,
            'viewed_at': report.viewed_at
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/notifications', methods=['GET'])
@student_required
def get_notifications():
    """Get student notifications"""
    try:
        identity = get_jwt_identity()
        
        notifications = Notification.query.filter_by(user_id=identity['user_id']).order_by(
            Notification.created_at.desc()
        ).all()
        
        return {
            'total': len(notifications),
            'unread': len([n for n in notifications if not n.is_read]),
            'notifications': [n.to_dict() for n in notifications]
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/notifications/<notification_id>/read', methods=['PUT'])
@student_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return {'error': 'Notification not found'}, 404
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return {'message': 'Notification marked as read'}, 200
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500