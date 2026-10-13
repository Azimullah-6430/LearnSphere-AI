"""
LearnSphere AI - Class Academic Report Derivation Engine

Derives a concise, evidence-based class report from:
  - Authorized teacher class membership records (roster)
  - Completed TEACHER_EVALUATION records for the class

Accuracy guarantees:
  1. Only completed, authorised TEACHER_EVALUATION records are used.
  2. Marks are never invented. Missing marks are never treated as zero.
  3. Normalised percentages are computed per-student using their own total_marks.
  4. Averages are calculated from valid (non-null, non-zero-max) records only.
  5. Strengths and weaknesses are supported by explicit question-level evidence counts.
  6. Students needing support are identified by evidence, not a single mistake.
  7. Progress across assessments is reported only when 2+ comparable records exist.
  8. Data limitations are explicitly listed in the report.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _num(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val, default=""):
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _pct(obtained, total):
    if total <= 0:
        return None
    return round((obtained / total) * 100, 1)


def _grade_from_pct(pct):
    if pct is None:
        return "N/A"
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B+"
    if pct >= 60: return "B"
    if pct >= 50: return "C"
    if pct >= 40: return "D"
    return "F"


def derive_class_report(class_doc, evaluations, assessment_filter=None):
    """
    Derive a complete class academic report from real evaluation data.

    Parameters
    ----------
    class_doc : dict
        The teacher_classes document with 'students' list.
    evaluations : list[dict]
        All TEACHER_EVALUATION records scoped to this teacher + class.
    assessment_filter : str | None
        If provided, restrict to this assessment_title only.

    Returns
    -------
    dict
        Structured report. Numerical fields are measured facts.
        Interpretive labels are documented as rule-based.
    """
    now_str    = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    class_id   = _safe_str(class_doc.get("id") or class_doc.get("_id"), "unknown")
    class_name = _safe_str(class_doc.get("name"), "Unnamed Class")
    level      = _safe_str(class_doc.get("level") or class_doc.get("grade_level") or class_doc.get("gradeLevel"))
    section    = _safe_str(class_doc.get("section"))
    subjects   = class_doc.get("subjects") or []
    if isinstance(subjects, list):
        subjects_str = ", ".join(str(s) for s in subjects) if subjects else ""
    else:
        subjects_str = str(subjects)

    # Build roster
    roster = []
    for s in (class_doc.get("students") or []):
        if not isinstance(s, dict):
            continue
        name = _safe_str(s.get("name") or s.get("student_name"), "").strip()
        if not name:
            continue
        roster.append({
            "name":       name,
            "roll":       _safe_str(s.get("rollNo") or s.get("roll_number") or s.get("roll"), ""),
            "student_id": _safe_str(s.get("id") or s.get("student_id") or s.get("_id"), ""),
            "email":      _safe_str(s.get("email"), ""),
        })
    enrolled_count = len(roster)

    # Filter and validate evaluations
    valid_evals = []
    limitations = []
    invalid_max_count = 0

    for ev in evaluations:
        source = _safe_str(ev.get("evaluation_source") or ev.get("evaluationSource"), "").upper()
        if source and source not in ("TEACHER_EVALUATION", "TEACHER"):
            continue
        if assessment_filter:
            title = _safe_str(ev.get("assessment_title") or ev.get("topic"), "")
            if title.lower() != assessment_filter.lower():
                continue
        total_m = _num(ev.get("total_marks"), 0.0)
        obtained_m = _num(ev.get("obtained_marks"), 0.0)
        if total_m <= 0:
            invalid_max_count += 1
            continue
        ev["_total_marks"]    = total_m
        ev["_obtained_marks"] = obtained_m
        ev["_pct"]            = _pct(obtained_m, total_m)
        valid_evals.append(ev)

    if invalid_max_count:
        limitations.append(
            f"{invalid_max_count} evaluation record(s) excluded: total_marks not recorded "
            "(cannot compute percentage or contribute to class average)."
        )

    # Early return if no valid data
    if not valid_evals:
        return {
            "class_id":       class_id,
            "class_name":     class_name,
            "level":          level,
            "section":        section,
            "subjects":       subjects_str,
            "enrolled_count": enrolled_count,
            "generated_at":   now_str,
            "status":         "no_evaluations",
            "message":        "No completed evaluations available for this report.",
            "roster":         roster,
            "limitations":    limitations,
        }

    # Distinct assessment titles
    assessment_titles = sorted({
        _safe_str(ev.get("assessment_title") or ev.get("topic"), "Assessment")
        for ev in valid_evals
    })

    # Reporting period from dates
    dates = []
    for ev in valid_evals:
        d = str(ev.get("created_at") or ev.get("date") or "")
        if d:
            try:
                dates.append(d[:10])
            except Exception:
                pass
    dates.sort()
    if len(dates) >= 2:
        reporting_period = f"{dates[0]} to {dates[-1]}"
    elif dates:
        reporting_period = dates[0]
    else:
        reporting_period = ""

    # Map evals by student name
    student_evals = defaultdict(list)
    for ev in valid_evals:
        name = _safe_str(ev.get("student_name"), "").strip().lower()
        if name:
            student_evals[name].append(ev)

    # Roster coverage
    evaluated_names = set(student_evals.keys())
    evaluated_roster = []
    not_evaluated_roster = []
    for s in roster:
        key = s["name"].strip().lower()
        if key in evaluated_names:
            evaluated_roster.append(s)
        else:
            not_evaluated_roster.append(s)

    roster_names_lower = {s["name"].strip().lower() for s in roster}
    extra_evaluated = [n for n in evaluated_names if n not in roster_names_lower]
    if extra_evaluated:
        sample = ", ".join(n.title() for n in extra_evaluated[:5])
        suffix = "..." if len(extra_evaluated) > 5 else ""
        limitations.append(
            f"{len(extra_evaluated)} evaluated student(s) could not be matched to "
            f"the class roster (possible name mismatch): {sample}{suffix}. "
            "Included in class average but excluded from roster table."
        )

    evaluated_count     = len(evaluated_names)
    not_evaluated_count = len(not_evaluated_roster)

    # Student-wise results
    # Method: per-student, per-assessment percentage = obtained / total_marks * 100
    # Student average = mean of their percentages (normalised).
    # Class average   = mean of ALL student-assessment percentages.
    all_pcts = []
    student_results = []

    for raw_name, evs in sorted(student_evals.items()):
        display_name = _safe_str(evs[0].get("student_name"), raw_name.title())
        roll = _safe_str(evs[0].get("roll_number") or evs[0].get("roll_number_snapshot"), "")
        assessments_out = []
        student_pcts = []
        for ev in sorted(evs, key=lambda x: str(x.get("created_at", ""))):
            obtained = ev["_obtained_marks"]
            total    = ev["_total_marks"]
            pct      = ev["_pct"]
            assessments_out.append({
                "assessment_title": _safe_str(ev.get("assessment_title") or ev.get("topic"), "Assessment"),
                "subject":          _safe_str(ev.get("subject"), ""),
                "obtained_marks":   obtained,
                "total_marks":      total,
                "percentage":       pct,
                "grade":            _grade_from_pct(pct),
                "evaluation_id":    _safe_str(ev.get("id") or ev.get("_id"), ""),
                "date":             str(ev.get("created_at", ""))[:10],
            })
            if pct is not None:
                student_pcts.append(pct)
                all_pcts.append(pct)

        student_avg_pct = round(sum(student_pcts) / len(student_pcts), 1) if student_pcts else None
        student_results.append({
            "student_name":    display_name,
            "roll_number":     roll,
            "assessments":     assessments_out,
            "average_pct":     student_avg_pct,
            "average_grade":   _grade_from_pct(student_avg_pct),
            "num_assessments": len(assessments_out),
            "data_source":     "TEACHER_EVALUATION (measured)",
        })

    # Class average
    class_avg_pct = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else None
    class_avg_grade = _grade_from_pct(class_avg_pct)
    avg_method_note = (
        f"Class average = mean of (obtained_marks / total_marks x 100) across "
        f"{len(all_pcts)} valid student-assessment record(s). "
        "Assessments with total_marks = 0 are excluded. "
        "This normalised percentage allows fair comparison across assessments "
        "with different maximum marks."
    )

    # Score distribution
    dist = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "Below 50": 0}
    for p in all_pcts:
        if   p >= 90: dist["90-100"]  += 1
        elif p >= 80: dist["80-89"]   += 1
        elif p >= 70: dist["70-79"]   += 1
        elif p >= 60: dist["60-69"]   += 1
        elif p >= 50: dist["50-59"]   += 1
        else:         dist["Below 50"] += 1

    # Question-level concept analysis (strengths / improvement areas)
    # Evidence threshold: >= 2 student responses per concept
    concept_scores = defaultdict(list)
    concept_misconceptions = defaultdict(int)

    for ev in valid_evals:
        questions = ev.get("questions") or ev.get("evaluations") or []
        if not isinstance(questions, list):
            continue
        for q in questions:
            if not isinstance(q, dict):
                continue
            q_max = _num(q.get("maximum_marks") or q.get("max_marks"), 0.0)
            q_aw  = _num(q.get("awarded_marks"), 0.0)
            if q_max <= 0:
                continue
            concept = _safe_str(
                q.get("concept") or q.get("identified_concept") or q.get("topic"),
                f"Question {q.get('question_number', '?')}"
            )
            concept_scores[concept].append((q_aw, q_max))
            if q.get("misconception_detected") or q.get("misconception"):
                concept_misconceptions[concept] += 1

    strengths = []
    improvements = []
    for concept, scores in concept_scores.items():
        if len(scores) < 2:
            continue
        total_aw  = sum(s[0] for s in scores)
        total_max = sum(s[1] for s in scores)
        avg_pct   = _pct(total_aw, total_max)
        if avg_pct is None:
            continue
        misc_count = concept_misconceptions.get(concept, 0)
        item = {
            "concept":             concept,
            "avg_score_pct":       avg_pct,
            "evidence_count":      len(scores),
            "misconception_count": misc_count,
            "data_source":         "TEACHER_EVALUATION question-level (measured)",
        }
        if avg_pct >= 75 and misc_count == 0:
            strengths.append(item)
        elif avg_pct < 60 or misc_count >= 2:
            improvements.append(item)

    strengths.sort(key=lambda x: -x["avg_score_pct"])
    improvements.sort(key=lambda x: (x["avg_score_pct"], -x["misconception_count"]))

    # Students needing support
    # Criteria: avg < 50% across >= 2 assessments, OR >= 2 misconception flags
    # Single-evaluation low scorers are listed separately as "insufficient evidence"
    support_needed = []
    insufficient_evidence = []

    for sr in student_results:
        evs_list = student_evals[sr["student_name"].strip().lower()]
        misc_flags = sum(
            1 for ev in evs_list
            for q in (ev.get("questions") or ev.get("evaluations") or [])
            if isinstance(q, dict) and (q.get("misconception_detected") or q.get("misconception"))
        )
        avg_pct = sr["average_pct"]
        num_a   = sr["num_assessments"]

        if avg_pct is not None and avg_pct < 50 and num_a >= 2:
            support_needed.append({
                "student_name":       sr["student_name"],
                "roll_number":        sr["roll_number"],
                "average_pct":        avg_pct,
                "num_assessments":    num_a,
                "misconception_flags": misc_flags,
                "evidence":           f"Average {avg_pct}% across {num_a} assessments.",
                "recommended_next_step": (
                    "Schedule 1-on-1 diagnostic session. Review weakest assessment "
                    "via Action Center. Assign targeted remedial worksheet."
                ),
                "data_source": "TEACHER_EVALUATION (measured)",
            })
        elif avg_pct is not None and avg_pct < 50 and num_a == 1:
            insufficient_evidence.append({
                "student_name": sr["student_name"],
                "roll_number":  sr["roll_number"],
                "average_pct":  avg_pct,
                "note": (
                    f"Scored {avg_pct}% in 1 assessment. "
                    "More evaluations required before drawing conclusions."
                ),
            })
        elif misc_flags >= 2:
            support_needed.append({
                "student_name":       sr["student_name"],
                "roll_number":        sr["roll_number"],
                "average_pct":        avg_pct,
                "num_assessments":    num_a,
                "misconception_flags": misc_flags,
                "evidence":           f"{misc_flags} conceptual misconceptions detected.",
                "recommended_next_step": (
                    "Review Misconception Map for flagged concepts. "
                    "Assign AI Trainer sessions focused on identified gaps."
                ),
                "data_source": "TEACHER_EVALUATION (measured)",
            })

    # Progress notes: only when >= 2 comparable records per student per subject
    progress_notes = []
    for sr in student_results:
        if sr["num_assessments"] < 2:
            continue
        by_subject = defaultdict(list)
        for a in sr["assessments"]:
            by_subject[a["subject"]].append(a)
        for subj, alist in by_subject.items():
            if len(alist) < 2:
                continue
            pcts = [a["percentage"] for a in alist if a["percentage"] is not None]
            if len(pcts) < 2:
                continue
            delta = round(pcts[-1] - pcts[0], 1)
            if abs(delta) >= 10:
                direction = "improved" if delta > 0 else "declined"
                progress_notes.append({
                    "student_name": sr["student_name"],
                    "subject":      subj,
                    "from_pct":     pcts[0],
                    "to_pct":       pcts[-1],
                    "delta":        delta,
                    "direction":    direction,
                    "num_compared": len(pcts),
                    "data_source":  "TEACHER_EVALUATION (measured)",
                    "note": (
                        f"{sr['student_name']} {direction} by {abs(delta)}% "
                        f"in {subj} across {len(pcts)} comparable assessments."
                    ),
                })
    progress_notes.sort(key=lambda x: -abs(x["delta"]))

    # Compile limitations
    if not_evaluated_count:
        names_sample = ", ".join(s["name"] for s in not_evaluated_roster[:5])
        suffix = "..." if not_evaluated_count > 5 else ""
        limitations.append(
            f"{not_evaluated_count} enrolled student(s) have no completed evaluations "
            f"and are excluded from the class average: {names_sample}{suffix}."
        )
    if insufficient_evidence:
        names_sample = ", ".join(e["student_name"] for e in insufficient_evidence[:5])
        limitations.append(
            f"{len(insufficient_evidence)} student(s) have only 1 evaluation  -  "
            f"not enough to confirm underperformance: {names_sample}."
        )
    if len(assessment_titles) > 1:
        limitations.append(
            f"This report spans {len(assessment_titles)} distinct assessments "
            f"({', '.join(assessment_titles)}). The class average is a normalised "
            "mean percentage  -  raw scores are not directly summed."
        )

    return {
        # Identity
        "class_id":              class_id,
        "class_name":            class_name,
        "level":                 level,
        "section":               section,
        "subjects":              subjects_str,
        "generated_at":          now_str,
        "status":                "ok",

        # Sections 1-3: Coverage
        "enrolled_count":         enrolled_count,
        "evaluated_count":        evaluated_count,
        "not_evaluated_count":    not_evaluated_count,
        "not_evaluated_students": [s["name"] for s in not_evaluated_roster],
        "assessment_titles":      assessment_titles,
        "reporting_period":       reporting_period,
        "total_valid_records":    len(valid_evals),

        # Section 4: Class average
        "class_avg_pct":          class_avg_pct,
        "class_avg_grade":        class_avg_grade,
        "avg_calculation_method": avg_method_note,
        "score_distribution":     dist,

        # Section 5: Student results
        "student_results":        student_results,

        # Section 6: Strengths
        "strengths":              strengths[:8],

        # Section 7: Improvement areas
        "improvement_areas":      improvements[:8],

        # Section 8: Support needed
        "students_needing_support":       support_needed,
        "insufficient_evidence_students": insufficient_evidence,

        # Section 9: Progress
        "progress_notes":         progress_notes[:10],

        # Section 10: Limitations
        "limitations":            limitations,

        # Transparency
        "fact_vs_interpretation_note": (
            "Numerical fields (marks, percentages, counts, distributions) are measured "
            "facts from persisted TEACHER_EVALUATION records. Labels such as 'strength', "
            "'needs_improvement', and 'recommended_next_step' are rule-based "
            "interpretations applied by the derivation engine."
        ),
    }
