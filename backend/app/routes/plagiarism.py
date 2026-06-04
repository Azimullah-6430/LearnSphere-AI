from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.database import Submission, PlagiarismMatch, Notification
from app.auth import teacher_required, student_required
from app.services.plagiarism_service import PlagiarismDetectionService
from datetime import datetime

bp = Blueprint('plagiarism', __name__, url_prefix='/api/plagiarism')

@bp.route('/check/<submission_id>', methods=['POST'])
@teacher_required
def check_plagiarism(submission_id):
    """Check submission for plagiarism"""
    try:
        submission = Submission.query.get(submission_id)
        
        if not submission:
            return {'error': 'Submission not found'}, 404
        
        # Initialize plagiarism detection service
        plagiarism_service = PlagiarismDetectionService()
        
        # Get all other submissions
        all_submissions = Submission.query.filter(Submission.id != submission_id).all()
        
        matches = []
        
        for other_submission in all_submissions:
            # Compare with other submission
            similarity = plagiarism_service.compare_documents(
                submission.answer_script_path,
                other_submission.answer_script_path
            )
            
            # Also check if PDF was renamed (same content, different name)
            hash_match = plagiarism_service.check_file_hash_match(
                submission.answer_script_path,
                other_submission.answer_script_path
            )
            
            if similarity > 0.85 or hash_match:  # 85% threshold
                match_type = 'exact_match' if hash_match else 'content_similarity'
                
                # Create plagiarism match record
                plagiarism_match = PlagiarismMatch(
                    submission_id=submission.id,
                    matched_submission_id=other_submission.id,
                    similarity_percentage=similarity * 100,
                    match_type=match_type,
                    flagged=True
                )
                db.session.add(plagiarism_match)
                
                # Store student details
                student_1 = submission.student
                student_2 = other_submission.student
                
                matches.append({
                    'match_id': plagiarism_match.id,
                    'similarity_percentage': round(similarity * 100, 2),
                    'match_type': match_type,
                    'student_1': {
                        'id': student_1.id,
                        'name': student_1.user.first_name + ' ' + student_1.user.last_name,
                        'email': student_1.user.email,
                        'roll_number': student_1.roll_number
                    },
                    'student_2': {
                        'id': student_2.id,
                        'name': student_2.user.first_name + ' ' + student_2.user.last_name,
                        'email': student_2.user.email,
                        'roll_number': student_2.roll_number
                    }
                })
                
                # Send notifications to both students
                notification_1 = Notification(
                    user_id=student_1.user_id,
                    type='plagiarism_alert',
                    title='Plagiarism Alert',
                    message=f'Your submission has {similarity*100:.1f}% similarity with another submission.',
                    related_submission_id=submission.id
                )
                notification_2 = Notification(
                    user_id=student_2.user_id,
                    type='plagiarism_alert',
                    title='Plagiarism Alert',
                    message=f'Your submission has {similarity*100:.1f}% similarity with another submission.',
                    related_submission_id=other_submission.id
                )
                db.session.add(notification_1)
                db.session.add(notification_2)
        
        submission.is_plagiarism_checked = True
        submission.plagiarism_score = max([m['similarity_percentage'] for m in matches]) if matches else 0
        
        if matches:
            submission.status = 'flagged'
        
        db.session.commit()
        
        return {
            'submission_id': submission.id,
            'total_matches': len(matches),
            'plagiarism_score': submission.plagiarism_score,
            'matches': matches,
            'status': submission.status
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}, 500

@bp.route('/flags', methods=['GET'])
@teacher_required
def get_plagiarism_flags():
    """Get all flagged plagiarism cases"""
    try:
        flagged_submissions = Submission.query.filter_by(status='flagged').all()
        
        flags_data = []
        for submission in flagged_submissions:
            matches = PlagiarismMatch.query.filter_by(submission_id=submission.id).all()
            
            flags_data.append({
                'submission_id': submission.id,
                'student': {
                    'id': submission.student.id,
                    'name': submission.student.user.first_name + ' ' + submission.student.user.last_name,
                    'email': submission.student.user.email,
                    'roll_number': submission.student.roll_number
                },
                'subject': submission.subject,
                'plagiarism_score': submission.plagiarism_score,
                'matches_count': len(matches),
                'created_at': submission.created_at,
                'matches': [{
                    'match_id': m.id,
                    'matched_student': {
                        'id': m.student_2_details['id'],
                        'name': m.student_2_details['name'],
                        'email': m.student_2_details['email'],
                        'roll_number': m.student_2_details['roll_number']
                    },
                    'similarity': m.similarity_percentage,
                    'match_type': m.match_type
                } for m in matches]
            })
        
        return {
            'total_flagged': len(flagged_submissions),
            'flagged_submissions': flags_data
        }, 200
    
    except Exception as e:
        return {'error': str(e)}, 500