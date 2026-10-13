import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
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
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 30, 576, 30)
        self.drawString(36, 18, "LearnSphere AI — Confidential Class Academic Report")
        self.drawRightString(576, 18, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def generate_class_report_pdf(report: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A')
    )
    subtitle_style = ParagraphStyle(
        'RepSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    h2_style = ParagraphStyle(
        'RepH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'RepBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    body_bold = ParagraphStyle(
        'RepBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )
    badge_style = ParagraphStyle(
        'RepBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#2563EB')
    )

    story = []

    # Title Banner
    class_name = report.get("class_name", "Class Academic Report")
    generated_at = report.get("generated_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    period = report.get("reporting_period", "All Assessments")

    story.append(Paragraph(f"Class Academic Report: {class_name}", title_style))
    story.append(Paragraph(f"Reporting Period / Assessments: {period} &bull; Generated: {generated_at}", subtitle_style))
    story.append(Spacer(1, 10))

    # Summary Metrics Table
    enrolled = report.get("enrolled_count", 0)
    evaluated = report.get("evaluated_count", 0)
    not_evaluated = report.get("not_evaluated_count", 0)
    avg_pct = report.get("class_avg_pct")
    avg_str = f"{avg_pct}%" if avg_pct is not None else "N/A"
    avg_grade = report.get("class_avg_grade", "N/A")

    metrics_data = [
        [
            Paragraph("<b>Enrolled Students</b>", body_style),
            Paragraph("<b>Evaluated</b>", body_style),
            Paragraph("<b>Pending Evaluation</b>", body_style),
            Paragraph("<b>Class Average</b>", body_style),
            Paragraph("<b>Overall Grade</b>", body_style)
        ],
        [
            Paragraph(f"<font size=12><b>{enrolled}</b></font>", body_bold),
            Paragraph(f"<font size=12><b>{evaluated}</b></font>", body_bold),
            Paragraph(f"<font size=12><b>{not_evaluated}</b></font>", body_bold),
            Paragraph(f"<font size=12 color='#2563EB'><b>{avg_str}</b></font>", body_bold),
            Paragraph(f"<font size=12 color='#16A34A'><b>{avg_grade}</b></font>", body_bold)
        ]
    ]

    t_metrics = Table(metrics_data, colWidths=[108, 108, 108, 108, 108])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 12))

    # Note on calculation method
    calc_note = report.get("avg_calculation_method", "")
    if calc_note:
        story.append(Paragraph(f"<i>Note: {calc_note}</i>", subtitle_style))
        story.append(Spacer(1, 8))

    # Section: Student Results
    student_results = report.get("student_results", [])
    if student_results:
        story.append(Paragraph("Student-Wise Performance Breakdown", h2_style))
        headers = ["Student Name", "Roll / ID", "Assessments", "Avg %", "Grade", "Status"]
        table_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in headers]]

        for s in student_results:
            name = s.get("student_name", "Unknown")
            roll = s.get("roll_number", "—")
            num_a = s.get("num_assessments", 0)
            pct = s.get("average_pct")
            pct_s = f"{pct}%" if pct is not None else "Not Evaluated"
            grd = s.get("grade", "—")
            eval_status = s.get("evaluation_status", "evaluated")
            status_text = "Evaluated" if eval_status == "evaluated" else "Pending"

            table_rows.append([
                Paragraph(name, body_style),
                Paragraph(str(roll), body_style),
                Paragraph(str(num_a), body_style),
                Paragraph(pct_s, body_bold),
                Paragraph(grd, body_style),
                Paragraph(status_text, body_style)
            ])

        t_students = Table(table_rows, colWidths=[150, 70, 80, 80, 60, 100])
        t_students.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_students)
        story.append(Spacer(1, 12))

    # Strengths & Improvement Areas
    strengths = report.get("strengths", [])
    improvements = report.get("improvement_areas", [])

    if strengths or improvements:
        story.append(Paragraph("Class-Wide Mastery & Focus Areas", h2_style))
        analysis_data = [
            [
                Paragraph("<b>Demonstrated Strengths (>= 75% Average)</b>", body_bold),
                Paragraph("<b>Topics Requiring Attention (&lt; 60% or Misconceptions)</b>", body_bold)
            ]
        ]
        
        str_bullets = "<br/>".join([
            f"&bull; <b>{s.get('concept', '')}</b> ({s.get('avg_score_pct', '')}% across {s.get('evidence_count', 0)} answers)"
            for s in strengths
        ]) if strengths else "No topics met the 75%+ threshold across multiple students."

        imp_bullets = "<br/>".join([
            f"&bull; <b>{i.get('concept', '')}</b> ({i.get('avg_score_pct', '')}% score, {i.get('misconception_count', 0)} misconceptions detected)"
            for i in improvements
        ]) if improvements else "No critical weakness trends detected across questions."

        analysis_data.append([
            Paragraph(str_bullets, body_style),
            Paragraph(imp_bullets, body_style)
        ])

        t_analysis = Table(analysis_data, colWidths=[270, 270])
        t_analysis.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_analysis)
        story.append(Spacer(1, 12))

    # Support Needed
    support_needed = report.get("students_needing_support", [])
    if support_needed:
        story.append(Paragraph("Targeted Support & Intervention Recommendations", h2_style))
        sup_rows = [
            [
                Paragraph("<b>Student</b>", body_style),
                Paragraph("<b>Evidence</b>", body_style),
                Paragraph("<b>Recommended Next Step</b>", body_style)
            ]
        ]
        for sup in support_needed:
            sup_rows.append([
                Paragraph(sup.get("student_name", "Student"), body_bold),
                Paragraph(sup.get("evidence", ""), body_style),
                Paragraph(sup.get("recommended_next_step", ""), body_style)
            ])
        t_sup = Table(sup_rows, colWidths=[120, 200, 220])
        t_sup.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEF2F2')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FCA5A5')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_sup)
        story.append(Spacer(1, 12))

    # Limitations & Transparency Note
    story.append(Spacer(1, 8))
    fact_note = report.get("fact_vs_interpretation_note", "")
    if fact_note:
        story.append(Paragraph(f"<b>Data Transparency & Evidence Assurance:</b> {fact_note}", subtitle_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
