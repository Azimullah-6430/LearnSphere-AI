from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.database import StudentProfile, TeacherProfile, Evaluation, PerformanceHistory, FocusSession, Submission
from app.auth import teacher_required, student_required
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@bp.route('/teacher/class', methods=['GET'])
@teacher_required
def get_class_analytics():
    """Get comprehensive class analytics"""
    try:
        identity = get_jwt_identity()
        teacher = TeacherProfile.query.filter_by(user_id=identity['user_id']).first()
        
        # Get all evaluations for teacher's classes
        evaluations = Evaluation.query.filter_by(teacher_id=teacher.id).all()
        
        # Score distribution
        score_ranges = {
            '0-20': 0,
            '20-40': 0,
            '40-60': 0,
            '60-80': 0,
            '80-100': 0
        }
        
        for eval in evaluations:
            if eval.percentage:
                if eval.percentage < 20:
                    score_ranges['0-20'] += 1
                elif eval.percentage < 40:
                    score_ranges['20-40'] += 1
                elif eval.percentage < 60:
                    score_ranges['40-60'] += 1
                elif eval.percentage < 80:
                    score_ranges['60-80'] += 1
                else:
                    score_ranges['80-100'] += 1
        
        # Subject-wise performance
        subject_performance = {}
        for eval in evaluations:
            subject = eval.submission.subject
            if subject not in subject_performance:
                subject_performance[subject] = {'count': 0, 'total_percentage': 0}
            subject_performance[subject]['count'] += 1
            subject_performance[subject]['total_percentage'] += eval.percentage or 0
        
        for subject in subject_performance:
            avg = subject_performance[subject]['total_percentage'] / subject_performance[subject]['count']
            subject_performance[subject]['average'] = round(avg, 2)
        
        # Calculate overall statistics
        percentages = [e.percentage for e in evaluations if e.percentage]
        overall_avg = sum(percentages) / len(percentages) if percentages else 0
        
        return {
            'score_distribution': score_ranges,
            'subject_performance': subject_performance,
            'overall_average': round(overall_avg, 2),
            'total_evaluations': len(evaluations),
            'total_students': teacher.total_students
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/student/performance', methods=['GET'])
@student_required
def get_student_performance():
    """Get student's personal performance analytics"""
    try:
        identity = get_jwt_identity()
        student = StudentProfile.query.filter_by(user_id=identity['user_id']).first()
        
        # Get performance history
        performance = PerformanceHistory.query.filter_by(student_id=student.id).order_by(
            PerformanceHistory.timestamp.desc()
        ).all()
        
        # Subject-wise average
        subject_averages = {}
        for perf in performance:
            subject = perf.subject
            if subject not in subject_averages:
                subject_averages[subject] = {'scores': [], 'count': 0}
            subject_averages[subject]['scores'].append(perf.percentage)
            subject_averages[subject]['count'] += 1
        
        for subject in subject_averages:
            avg = sum(subject_averages[subject]['scores']) / subject_averages[subject]['count']
            subject_averages[subject]['average'] = round(avg, 2)
            del subject_averages[subject]['scores']
        
        # Focus time this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        focus_sessions = FocusSession.query.filter(
            FocusSession.student_id == student.id,
            FocusSession.start_time >= month_ago
        ).all()
        
        total_focus_minutes = sum([s.duration_minutes or 0 for s in focus_sessions])
        avg_focus_score = sum([s.focus_score or 0 for s in focus_sessions]) / len(focus_sessions) if focus_sessions else 0
        
        # Progress trend (last 10 evaluations)
        recent_evaluations = Evaluation.query.filter_by(student_id=student.id).order_by(
            Evaluation.created_at.desc()
        ).limit(10).all()
        
        scores_trend = [e.percentage for e in reversed(recent_evaluations)]
        
        return {
            'total_score': student.total_score,
            'average_score': student.avg_score,
            'total_evaluations': student.total_evaluations,
            'encouragement_tokens': student.encouragement_tokens,
            'subject_averages': subject_averages,
            'focus_time_this_month_minutes': total_focus_minutes,
            'average_focus_score': round(avg_focus_score, 2),
            'scores_trend': scores_trend
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/student/progress-chart', methods=['GET'])
@student_required
def get_progress_chart():
    """Get student progress data for charts"""
    try:
        identity = get_jwt_identity()
        student = StudentProfile.query.filter_by(user_id=identity['user_id']).first()
        
        # Get last 20 evaluations
        evaluations = Evaluation.query.filter_by(student_id=student.id).order_by(
            Evaluation.created_at
        ).limit(20).all()
        
        chart_data = []
        for eval in evaluations:
            chart_data.append({
                'date': eval.created_at.strftime('%Y-%m-%d'),
                'score': eval.percentage,
                'subject': eval.submission.subject
            })
        
        return {'progress_data': chart_data}, 200
    
    except Exception as e:
        return {'error': str(e)}, 500