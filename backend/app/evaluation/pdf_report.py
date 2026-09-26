import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw 'Page X of Y' footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        # Header line & footer text
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 30, 576, 30)
        self.drawString(36, 18, "LearnSphere AI — Confidential Academic Evaluation & Feedback Report")
        self.drawRightString(576, 18, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def generate_evaluation_pdf(eval_data: dict) -> bytes:
    """
    Generates an official, publication-quality PDF Evaluation Report using ReportLab.
    Includes strict human teacher grading, choice option rules, summary table, and detailed feedback.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Custom Brand Colors
    primary_color = colors.HexColor("#3B82F6") # LearnSphere Blue/Indigo
    dark_text = colors.HexColor("#0F172A")
    soft_text = colors.HexColor("#475569")
    bg_light = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#CBD5E1")
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        alignment=TA_LEFT
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=soft_text,
        alignment=TA_LEFT
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_text
    )

    bold_body = ParagraphStyle(
        'BoldBody',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=dark_text
    )

    green_bullet = ParagraphStyle(
        'GreenBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#166534")
    )

    amber_bullet = ParagraphStyle(
        'AmberBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#9A3412")
    )

    story = []

    # 1. Header & Branding Banner
    header_data = [
        [
            Paragraph("<b>LEARNSPHERE AI</b><br/><font size=8 color='#64748B'>Academic Intelligence & Strict Paper Evaluation System</font>", title_style),
            Paragraph(f"<b>OFFICIAL EVALUATION REPORT</b><br/><font size=8 color='#64748B'>Date: {datetime.now().strftime('%d %b %Y, %H:%M IST')}</font>", ParagraphStyle('RightHead', parent=subtitle_style, alignment=TA_RIGHT))
        ]
    ]
    header_table = Table(header_data, colWidths=[310, 230])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4)
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=4, spaceAfter=10))

    # 2. Student & Meta Info Scorecard
    student_info = eval_data.get("student", {})
    if not isinstance(student_info, dict):
        student_info = {}

    student_name = student_info.get("name") or eval_data.get("student_name") or "Student"
    roll_no = student_info.get("roll_number") or eval_data.get("roll_number") or "N/A"
    subject = student_info.get("subject") or eval_data.get("subject") or "General"
    level = (student_info.get("level") or eval_data.get("level") or "School").upper()
    assessment = eval_data.get("assessment_title") or f"{subject} Examination"
    
    obtained_marks = eval_data.get("obtained_marks") if eval_data.get("obtained_marks") is not None else eval_data.get("score") or 0
    total_marks = eval_data.get("total_marks") if eval_data.get("total_marks") is not None else eval_data.get("total") or 100
    percentage = eval_data.get("percentage") if eval_data.get("percentage") is not None else round((obtained_marks / total_marks * 100) if total_marks else 0, 2)
    grade = eval_data.get("grade") or "N/A"

    meta_table_data = [
        [
            Paragraph(f"<b>Student Name:</b> {student_name}", body_style),
            Paragraph(f"<b>Roll Number:</b> {roll_no}", body_style),
            Paragraph(f"<b>Total Score:</b> <font color='#2563EB'><b>{obtained_marks} / {total_marks}</b></font>", body_style)
        ],
        [
            Paragraph(f"<b>Subject:</b> {subject}", body_style),
            Paragraph(f"<b>Academic Level:</b> {level}", body_style),
            Paragraph(f"<b>Percentage:</b> <b>{percentage}%</b>", body_style)
        ],
        [
            Paragraph(f"<b>Assessment:</b> {assessment}", body_style),
            Paragraph(f"<b>Evaluation Standard:</b> Strict Human Teacher Rules", body_style),
            Paragraph(f"<b>Final Grade:</b> <b>{grade}</b>", body_style)
        ]
    ]
    
    meta_table = Table(meta_table_data, colWidths=[180, 180, 180])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Overall Evaluation Feedback Box
    story.append(Paragraph("Overall Teacher Evaluation & Performance Remarks", section_heading))
    overall_text = eval_data.get("overall_feedback") or "Evaluation completed according to strict examination marking rubrics."
    summary_box = Table([[Paragraph(overall_text, body_style)]], colWidths=[540])
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 10))

    # 4. Score Sheet Summary Table
    questions = eval_data.get("evaluations") or eval_data.get("questions") or []
    if isinstance(questions, list) and len(questions) > 0:
        story.append(Paragraph("Question Score Sheet Summary", section_heading))
        summary_rows = [
            [
                Paragraph("<b>Q. No.</b>", bold_body),
                Paragraph("<b>Type</b>", bold_body),
                Paragraph("<b>Max Marks</b>", bold_body),
                Paragraph("<b>Awarded Marks</b>", bold_body),
                Paragraph("<b>Status / Choice Rule</b>", bold_body)
            ]
        ]
        
        has_extra_choice = False
        for q in questions:
            q_num = str(q.get("question_number", ""))
            q_type = str(q.get("question_type", "short_answer"))
            max_m = float(q.get("maximum_marks", 0))
            awarded = float(q.get("awarded_marks", 0))
            is_extra = bool(q.get("is_extra_choice", False))
            
            if is_extra:
                has_extra_choice = True
                status_p = Paragraph("<font color='#DC2626'><b>Choice Option (0 Marks - 1st Attempt Counted)</b></font>", body_style)
            elif awarded == max_m:
                status_p = Paragraph("<font color='#16A34A'><b>Full Marks</b></font>", body_style)
            elif awarded > 0:
                status_p = Paragraph("<font color='#D97706'><b>Partial Credit</b></font>", body_style)
            else:
                status_p = Paragraph("<font color='#DC2626'><b>Incorrect / No Credit</b></font>", body_style)

            summary_rows.append([
                Paragraph(q_num, body_style),
                Paragraph(q_type, body_style),
                Paragraph(str(max_m), body_style),
                Paragraph(f"<b>{awarded}</b>", body_style),
                status_p
            ])

        summary_table = Table(summary_rows, colWidths=[65, 85, 75, 95, 220])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        story.append(summary_table)

        if has_extra_choice:
            story.append(Spacer(1, 6))
            choice_notice = Table([[Paragraph("<b>Choice Option Rule Applied:</b> When multiple questions are attempted in a choice group (e.g. Q3A OR Q3B), evaluation is conducted for both, but marks are allotted ONLY for the first attempted answer towards the total score.", ParagraphStyle('ChoiceNotice', parent=body_style, textColor=colors.HexColor("#B45309")))]], colWidths=[540])
            choice_notice.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF3C7")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#F59E0B")),
                ('PADDING', (0,0), (-1,-1), 6)
            ]))
            story.append(choice_notice)

        story.append(Spacer(1, 12))

    # 5. Question-by-Question Detailed Assessment Cards
    story.append(Paragraph("Detailed Question-by-Question Diagnostic Feedback", section_heading))

    if isinstance(questions, list) and len(questions) > 0:
        for idx, q in enumerate(questions):
            q_num = q.get("question_number") or f"Q{idx+1}"
            q_type = q.get("question_type") or "Question"
            awarded = float(q.get("awarded_marks", 0))
            max_m = float(q.get("maximum_marks", 0))
            is_extra = bool(q.get("is_extra_choice", False))
            summary_ans = q.get("answer_summary") or "Student response evaluated."
            
            fb = q.get("feedback") if isinstance(q.get("feedback"), dict) else {}
            done_well = fb.get("what_was_done_well") or q.get("what_was_done_well") or []
            missing = fb.get("missing_points") or q.get("missing_points") or []
            expected = fb.get("expected_answer") or q.get("expected_answer") or ""
            improvement = fb.get("improvement") or q.get("improvement_advice") or ""

            if not isinstance(done_well, list): done_well = [str(done_well)]
            if not isinstance(missing, list): missing = [str(missing)]

            if is_extra:
                score_str = "<font color='#DC2626'><b>0 / " + str(max_m) + " (Choice Option Attempt)</b></font>"
            else:
                score_color = "#16A34A" if awarded == max_m else "#D97706" if awarded > 0 else "#DC2626"
                score_str = f"<b>Marks: <font color='{score_color}'>{awarded} / {max_m}</font></b>"
            
            q_rows = [
                [
                    Paragraph(f"<b>Question {q_num}</b> <font size=8 color='#64748B'>({q_type})</font>", bold_body),
                    Paragraph(score_str, ParagraphStyle('QScore', parent=bold_body, alignment=TA_RIGHT))
                ],
                [
                    Paragraph(f"<b>Student Response Analysis:</b><br/>{summary_ans}", body_style),
                    ""
                ]
            ]

            if is_extra:
                q_rows.append([
                    Paragraph("<b>Choice Option Rule Notice:</b> Both choice options were attempted in this question paper section. Marks are allotted for the first attempted answer only. This second attempt is evaluated for diagnostic feedback with 0 marks allotted.", amber_bullet),
                    ""
                ])

            # Append Good points
            if done_well:
                pts_str = "<br/>".join([f"• {pt}" for pt in done_well if pt])
                if pts_str:
                    q_rows.append([
                        Paragraph(f"<b>Correct Working Points:</b><br/>{pts_str}", green_bullet),
                        ""
                    ])

            # Append Missing points
            if missing:
                pts_str = "<br/>".join([f"• {pt}" for pt in missing if pt])
                if pts_str:
                    q_rows.append([
                        Paragraph(f"<b>Missing / Incorrect Points & Errors:</b><br/>{pts_str}", amber_bullet),
                        ""
                    ])

            # Append Expected Answer
            if expected:
                q_rows.append([
                    Paragraph(f"<b>Expected Standard Solution / Marking Scheme:</b><br/><i>{expected}</i>", body_style),
                    ""
                ])

            # Append Advice
            if improvement:
                q_rows.append([
                    Paragraph(f"<b>Actionable Improvement Advice:</b><br/><font color='#2563EB'><b>{improvement}</b></font>", body_style),
                    ""
                ])

            q_table = Table(q_rows, colWidths=[380, 160])
            t_style = [
                ('BACKGROUND', (0,0), (-1,-1), bg_light),
                ('SPAN', (0,1), (1,1)), # span summary
                ('BOX', (0,0), (-1,-1), 1, border_color),
                ('LINEBELOW', (0,0), (-1,0), 0.5, primary_color),
                ('PADDING', (0,0), (-1,-1), 6),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]
            
            curr_row = 2
            if is_extra:
                t_style.append(('SPAN', (0, curr_row), (1, curr_row)))
                curr_row += 1
            if done_well:
                t_style.append(('SPAN', (0, curr_row), (1, curr_row)))
                curr_row += 1
            if missing:
                t_style.append(('SPAN', (0, curr_row), (1, curr_row)))
                curr_row += 1
            if expected:
                t_style.append(('SPAN', (0, curr_row), (1, curr_row)))
                curr_row += 1
            if improvement:
                t_style.append(('SPAN', (0, curr_row), (1, curr_row)))
                curr_row += 1

            q_table.setStyle(TableStyle(t_style))
            story.append(KeepTogether([q_table, Spacer(1, 8)]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
