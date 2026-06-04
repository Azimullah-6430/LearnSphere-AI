from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from app.database import Submission, Evaluation, StudentProfile, EvaluationReport, Notification
from app.auth import student_required, teacher_required
from app.services.ml_service import BertEvaluationService
from app.services.ocr_service import extract_text_from_pdf, extract_text_from_image
import os
from datetime import datetime

bp = Blueprint('evaluation', __name__, url_prefix='/api/evaluation')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/submit', methods=['POST'])
@student_required
def submit_for_evaluation():
    """Student submits answer script for evaluation"""
    try:
        identity = get_jwt_identity()
        student = StudentProfile.query.filter_by(user_id=identity['user_id']).first()
        
        if not student:
            return {'error': 'Student profile not found'}, 404
        
        # Check if files are present
        if 'question_paper' not in request.files or 'answer_script' not in request.files:
            return {'error': 'Both question paper and answer script required'}, 400
        
        question_paper = request.files['question_paper']
        answer_script = request.files['answer_script']
        
        if not allowed_file(question_paper.filename) or not allowed_file(answer_script.filename):
            return {'error': 'Invalid file format'}, 400
        
        # Get form data
        data = request.form
        subject = data.get('subject')  # Physics, Chemistry, Maths
        level = data.get('level')  # School, College
        stream = data.get('stream')
        submission_type = data.get('submission_type')  # 'teacher_eval' or 'self_eval'
        
        # Create upload directory
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], student.id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save files
        qp_filename = secure_filename(f"qp_{datetime.utcnow().timestamp()}_{question_paper.filename}")
        as_filename = secure_filename(f"as_{datetime.utcnow().timestamp()}_{answer_script.filename}")
        
        qp_path = os.path.join(upload_dir, qp_filename)
        as_path = os.path.join(upload_dir, as_filename)
        
        question_paper.save(qp_path)
        answer_script.save(as_path)
        
        # Create submission
        submission = Submission(
            student_id=student.id,
            question_paper_path=qp_path,
            answer_script_path=as_path,
            subject=subject,
            level=level,
            stream=stream,
            submission_type=submission_type,
            status='pending'
        )
        db.session.add(submission)
        db.session.flush()
        
        # Extract text from files
        try:
            if question_paper.filename.lower().endswith('.pdf'):
                question_text = extract_text_from_pdf(qp_path)
            else:
                question_text = extract_text_from_image(qp_path)
            
            if answer_script.filename.lower().endswith('.pdf'):
                answer_text = extract_text_from_pdf(as_path)
            else:
                answer_text = extract_text_from_image(as_path)
            
            # Perform AI evaluation
            bert_service = BertEvaluationService()
            ai_eval_result = bert_service.evaluate(
                question_text=question_text,
                answer_text=answer_text,
                subject=subject,
                level=level
            )
            
            # Create evaluation record
            evaluation = Evaluation(
                submission_id=submission.id,
                student_id=student.id,
                ai_score=ai_eval_result['score'],
                ai_accuracy=ai_eval_result['accuracy'],
                total_marks=ai_eval_result.get('total_marks', 100),
                percentage=ai_eval_result['percentage'],
                ai_feedback=ai_eval_result['feedback'],
                question_wise_feedback=ai_eval_result.get('question_feedback', {}),
                evaluation_status='ai_done'
            )
            db.session.add(evaluation)
            
            submission.status = 'evaluated'
            
            db.session.commit()
            
            # Send notification
            notification = Notification(
                user_id=identity['user_id'],
                type='evaluation_ready',
                title='Evaluation Complete',
                message=f'Your {subject} answer script has been evaluated by AI with {ai_eval_result["accuracy"]:.1f}% accuracy.',
                related_submission_id=submission.id
            )
            db.session.add(notification)
            db.session.commit()
            
            return {
                'message': 'Submission successful',
                'submission_id': submission.id,
                'evaluation': {
                    'id': evaluation.id,
                    'ai_score': evaluation.ai_score,
                    'accuracy': evaluation.ai_accuracy,
                    'percentage': evaluation.percentage,
                    'feedback': evaluation.ai_feedback
                }
            }, 201
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Evaluation failed: {str(e)}'}, 500
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500

@bp.route('/submission/<submission_id>', methods=['GET'])
@student_required
def get_submission(submission_id):
    """Get submission details"""
    try:
        submission = Submission.query.get(submission_id)
        
        if not submission:
            return {'error': 'Submission not found'}, 404
        
        evaluation = Evaluation.query.filter_by(submission_id=submission_id).first()
        
        return {
            'submission_id': submission.id,
            'subject': submission.subject,
            'level': submission.level,
            'status': submission.status,
            'evaluation': evaluation.to_dict() if evaluation else None,
            'created_at': submission.created_at
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500