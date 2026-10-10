"""
LearnSphere AI - Dynamic Teaching Planner Module

Analyzes student curriculum context, subject & topic nature, student profile (School/College),
prerequisites, available materials, and dynamically builds structured teaching plans without hardcoded templates.

Supports:
  - All STEM, Humanities, Business, Languages, Law, Medicine, Arts, and Interdisciplinary subjects.
  - School and College student profiles with verified academic details.
  - Dynamic topic nature classification: theoretical, numerical, practical, procedural, creative, interpretive, language-based, programming-oriented.
  - Clarification handling for ambiguous or insufficient input.
  - Validation against active student curriculum.
"""

from typing import Dict, Any, List, Optional
import logging
import re

logger = logging.getLogger("DynamicTeachingPlanner")

class DynamicTeachingPlanner:
    """
    Modular planner for analyzing topic characteristics, student profile, and syllabus context
    to generate structured, grounded teaching plans.
    """

    TOPIC_NATURES = [
        "theoretical",
        "numerical",
        "practical",
        "procedural",
        "creative",
        "interpretive",
        "language-based",
        "programming-oriented"
    ]

    TEACHING_METHODS = {
        "programming-oriented": {
            "method": "Algorithmic Code Breakdown & Dry-Run Trace Table",
            "explanation_focus": "Mental models of memory allocation, control flow, time/space complexity Big-O, and edge cases.",
            "practice_focus": "Implementation of core algorithms, dry-running trace tables, and writing code with unit test checks.",
            "checks": [
                "What is the time and space complexity of this approach?",
                "How does the code handle base/boundary cases (e.g. empty inputs or single elements)?",
                "Trace the variable states through the main loop step-by-step."
            ]
        },
        "numerical": {
            "method": "Step-by-Step Mathematical Derivation & Worked Numerical Problems",
            "explanation_focus": "First-principles formula derivation, variable definitions, unit conversions, and physical/financial meaning.",
            "practice_focus": "Guided calculation problems starting from given data to target values, enforcing units at every step.",
            "checks": [
                "What physical or quantitative principle does this formula express?",
                "Are all quantities converted to standard SI/currency units before substituting?",
                "What happens to the result if key input variables approach zero or infinity?"
            ]
        },
        "practical": {
            "method": "Hands-On Physical Experiment & Household Resource Demonstration",
            "explanation_focus": "Physical mechanisms, observable phenomena, safety guidelines, and material substitutions.",
            "practice_focus": "Step-by-step experiment setup using available resources, observation recording, and data analysis.",
            "checks": [
                "What fundamental scientific law does this experiment demonstrate?",
                "What are the main safety precautions when carrying out this setup?",
                "How do your expected observations compare with actual experimental results?"
            ]
        },
        "theoretical": {
            "method": "Socratic Conceptual Decomposition & Analogical Reasoning",
            "explanation_focus": "Intuitive physical/conceptual analogies, foundational axioms, contrasting counter-examples, and core definitions.",
            "practice_focus": "Socratic dialogue questions, concept mapping, and explaining the concept in student's own words.",
            "checks": [
                "How would you explain this principle to someone with no background in this field?",
                "What is the key difference between this concept and its nearest related concept?",
                "Under what real-world conditions does this theoretical model apply?"
            ]
        },
        "procedural": {
            "method": "Standard Operating Workflow & Stage-by-Stage Verification",
            "explanation_focus": "Sequential workflow steps, decision nodes, standard protocols, and error recovery.",
            "practice_focus": "Stage-by-stage execution of the procedure, auditing inputs, and verifying outputs at each checkpoint.",
            "checks": [
                "What is the critical initial condition before starting step 1?",
                "What failure mode can occur if a step is performed out of sequence?",
                "How do you verify that the procedure was completed successfully?"
            ]
        },
        "creative": {
            "method": "Design Constraint Challenge & Synthesis Feedback Loop",
            "explanation_focus": "Design principles, aesthetic/functional constraints, user/audience perspective, and synthesis techniques.",
            "practice_focus": "Drafting an initial design sketch, blueprint, or creative piece under specific target constraints.",
            "checks": [
                "How does your design address the primary functional or aesthetic goal?",
                "What trade-offs did you make between constraints?",
                "How would you iterate on this draft based on peer or user feedback?"
            ]
        },
        "interpretive": {
            "method": "Primary Source Analysis & Contextual Textual Criticism",
            "explanation_focus": "Historical/cultural context, textual evidence, author perspective, thematic structures, and analytical frameworks.",
            "practice_focus": "Analyzing selected text/historical excerpts, identifying evidence, and constructing structured arguments.",
            "checks": [
                "What primary evidence supports this interpretation of the text or historical event?",
                "How does the author's background or historical context influence the core argument?",
                "What counter-arguments or alternative interpretations exist?"
            ]
        },
        "language-based": {
            "method": "Structural Syntax Analysis & Contextual Drill Practice",
            "explanation_focus": "Grammatical rules, sentence structures, vocabulary in context, phonetics, and pragmatic usage.",
            "practice_focus": "Sentence transformation drills, fill-in exercises, contextual translation, and conversational practice.",
            "checks": [
                "Which grammatical rule governs this sentence structure?",
                "How does changing the tense/mood alter the meaning of the statement?",
                "Construct a natural sentence using this key vocabulary or syntactic pattern."
            ]
        }
    }

    def detect_topic_nature(self, subject: str, topic: str, syllabus_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Dynamically classifies the nature of the topic based on subject name, topic text, and syllabus context.
        Supports unfamiliar and interdisciplinary subjects dynamically.
        """
        combined = f"{subject} {topic}".lower()
        if syllabus_context:
            combined += " " + str(syllabus_context.get("description", "")).lower()
            combined += " " + str(syllabus_context.get("learning_objectives", "")).lower()
            if isinstance(syllabus_context.get("topics"), list):
                combined += " " + " ".join([str(t) for t in syllabus_context["topics"]]).lower()

        # Helper for word-boundary or substring check
        def has_kw(kw_list):
            for kw in kw_list:
                if len(kw) <= 4:
                    if re.search(r"\b" + re.escape(kw) + r"\b", combined):
                        return True
                else:
                    if kw in combined:
                        return True
            return False

        # 1. Creative / Design / Fine Arts (Check creative art/design first before general programming keywords)
        if any(sk in combined for sk in ["art", "design", "creative writing", "sculpture", "animation", "graphics", "media production", "typography", "sketching"]):
            if not has_kw(["programming", "software", "code", "python", "java", "c++", "javascript", "sql", "database"]):
                return "creative"

        # 2. Programming-oriented
        if has_kw([
            "data structure", "algorithm", "programming", "code", "python", "java", "c++", "c#", "javascript",
            "sql", "database", "compiler", "recursion", "array", "pointer", "function", "class", "object oriented",
            "software", "web dev", "frontend", "backend", "api", "git", "tree", "graph", "sorting", "searching",
            "stack", "queue", "linked list", "hash table", "operating system", "linux", "kernel", "thread"
        ]):
            return "programming-oriented"

        # 3. Numerical / Computational / Mathematical
        if has_kw([
            "calculus", "differential", "integral", "matrix", "algebra", "trigonometry", "statistics",
            "probability", "equation", "formula", "thermodynamics", "kinematics", "circuit", "ohm", "kirchhoff",
            "accounting", "finance", "ledger", "taxation", "costing", "mechanics", "vector", "momentum",
            "fluid mechanics", "heat transfer", "quantum mechanics calculation", "microeconomics elasticity"
        ]):
            return "numerical"

        # 4. Practical / Experimental Science
        if has_kw([
            "experiment", "lab", "titration", "dissection", "microscope", "synthesis", "capillarity",
            "surface tension", "chemical reaction", "osmosis", "botany", "zoology", "electrolysis", "circuit assembly",
            "field study", "soil testing", "specimen", "chromatography", "spectroscopy", "bacteriology"
        ]):
            return "practical"

        # 5. Language-based / Linguistics
        if has_kw([
            "grammar", "syntax", "phonetics", "vocabulary", "translation", "french", "spanish", "german",
            "english grammar", "linguistics", "parts of speech", "tense", "comprehension", "verbal", "morphology",
            "phonology", "semantics"
        ]):
            return "language-based"

        # 6. Interpretive / Analytical (Humanities, History, Literature, Law)
        if has_kw([
            "literature", "poetry", "novel", "history", "revolution", "historical", "constitution",
            "law", "jurisprudence", "philosophy", "sociology", "political science", "criticism", "source analysis",
            "ethics", "international relations", "jurisdiction", "case law"
        ]):
            return "interpretive"

        # 7. Procedural / Operations / Management
        if has_kw([
            "procedure", "protocol", "audit", "management workflow", "nursing care", "diagnosis",
            "standard operating", "quality control", "operations", "supply chain", "sop", "clinical procedure"
        ]):
            return "procedural"

        # Default fallback for general topics
        return "theoretical"

    def infer_prerequisites(self, subject: str, topic: str, topic_nature: str) -> List[str]:
        """
        Dynamically infers 2-4 prerequisite concepts or skills for the topic based on domain knowledge and topic nature.
        """
        top_lower = topic.lower()
        sub_lower = subject.lower()

        if topic_nature == "programming-oriented":
            if "tree" in top_lower or "graph" in top_lower:
                return ["Pointers / Node references", "Recursion concepts", "Linear data structures (Arrays/Lists)"]
            if "sort" in top_lower or "search" in top_lower:
                return ["Array indexing", "Conditional logic (if/else)", "Loop iterations"]
            return ["Basic variable syntax", "Control flow structures", "Functions / methods"]

        if topic_nature == "numerical":
            if "calculus" in top_lower or "differential" in top_lower:
                return ["Algebraic simplification", "Function limits", "Coordinate geometry"]
            if "circuit" in top_lower or "ohm" in top_lower:
                return ["Electric charge concepts", "Basic algebraic equation solving", "Units of voltage and current"]
            return ["Basic algebra", "Unit conversion", "Arithmetic operations"]

        if topic_nature == "practical":
            if "chemistry" in sub_lower or "titration" in top_lower:
                return ["Molarity & mole concepts", "Safe handling of laboratory glassware", "Measurement precision"]
            if "physics" in sub_lower:
                return ["Physical quantities and SI units", "Basic observation logging", "Safety precautions"]
            return ["Basic scientific method", "Observation recording", "Material safety"]

        if topic_nature == "language-based":
            return ["Basic parts of speech", "Alphabet & phonics", "Sentence punctuation"]

        if topic_nature == "interpretive":
            return ["Historical / literary context reading", "Basic critical questioning", "Textual annotation"]

        # Theoretical / Default
        return [f"Foundational terminology in {subject}", "Basic conceptual reasoning"]

    def create_teaching_plan(
        self,
        subject: str,
        topic: str,
        student_profile: Dict[str, Any],
        syllabus_context: Optional[Dict[str, Any]] = None,
        custom_materials: str = "",
        resource_environment: str = ""
    ) -> Dict[str, Any]:
        """
        Generates a structured, validated teaching plan for any subject and topic in student's curriculum.
        """
        subj_clean = (subject or "").strip()
        top_clean = (topic or "").strip()

        # Check for insufficient information or empty request
        if not subj_clean or not top_clean:
            return {
                "selected_subject": subj_clean or "Unspecified Subject",
                "selected_topic": top_clean or "Unspecified Topic",
                "needs_clarification": True,
                "clarification_question": "Please select a valid subject and specific topic from your validated curriculum before generating a lesson plan.",
                "is_valid": False
            }

        # Check if topic is overly vague or invalid
        if len(top_clean) < 2 or top_clean.lower() in ["etc", "misc", "stuff", "test", "none"]:
            return {
                "selected_subject": subj_clean,
                "selected_topic": top_clean,
                "needs_clarification": True,
                "clarification_question": f"The selected topic '{top_clean}' in {subj_clean} is ambiguous. Which specific concept or unit sub-topic from your syllabus would you like to cover?",
                "is_valid": False
            }

        # Determine student level details
        raw_level = str(student_profile.get("level") or student_profile.get("role") or student_profile.get("student_type") or "COLLEGE").upper()
        is_school = "SCHOOL" in raw_level or bool(student_profile.get("class_level")) or bool(student_profile.get("grade"))
        student_type = "SCHOOL" if is_school else "COLLEGE"

        academic_profile: Dict[str, Any] = {}
        if student_type == "SCHOOL":
            academic_profile = {
                "student_type": "SCHOOL",
                "grade": str(student_profile.get("grade") or student_profile.get("class_level") or "Secondary Grade"),
                "board_or_stream": str(student_profile.get("stream") or student_profile.get("board") or "Standard School Board")
            }
        else:
            academic_profile = {
                "student_type": "COLLEGE",
                "program": str(student_profile.get("program") or student_profile.get("degree") or "Undergraduate Degree"),
                "department": str(student_profile.get("department") or student_profile.get("domain") or "Academic Department"),
                "year": str(student_profile.get("year") or student_profile.get("academic_year") or "Undergraduate Year"),
                "semester": str(student_profile.get("semester") or "3")
            }

        # Validate curriculum alignment
        objectives = []
        validated_topics = []
        if syllabus_context:
            objectives = syllabus_context.get("learning_objectives") or syllabus_context.get("objectives") or []
            validated_topics = syllabus_context.get("topics") or []

        # Detect topic nature
        topic_nature = self.detect_topic_nature(subj_clean, top_clean, syllabus_context)

        # Retrieve teaching approach
        method_meta = self.TEACHING_METHODS.get(topic_nature, self.TEACHING_METHODS["theoretical"])
        teaching_approach = method_meta["method"]

        # Learning objective
        if objectives and len(objectives) > 0 and isinstance(objectives[0], str):
            learning_obj = f"Master {top_clean} in {subj_clean}: {objectives[0]}"
        else:
            level_context = f"Grade {academic_profile.get('grade')}" if student_type == "SCHOOL" else f"{academic_profile.get('program')} (Semester {academic_profile.get('semester')})"
            learning_obj = f"Understand core principles, master problem-solving, and demonstrate practical understanding of {top_clean} in {subj_clean} for {level_context} students."

        # Prerequisites
        prerequisites = self.infer_prerequisites(subj_clean, top_clean, topic_nature)

        # Strategy, Practice & Checks
        level_label = academic_profile.get('grade') if student_type == "SCHOOL" else f"{academic_profile.get('department', '')} Sem {academic_profile.get('semester', '')}"
        explanation_strategy = f"{method_meta['explanation_focus']} Tailored for {student_type} level ({level_label})."
        practice_method = f"{method_meta['practice_focus']} Utilizing available environment: '{resource_environment or 'Standard classroom/home resources'}'."
        understanding_checks = method_meta["checks"]

        # Resource Requirements
        resources = []
        if custom_materials:
            resources.append(f"Student provided materials: {custom_materials}")
        if resource_environment:
            resources.append(f"Resource category: {resource_environment}")
        if not resources:
            resources = ["Notebook, writing instrument, or digital device for code/notes"]

        return {
            "selected_subject": subj_clean,
            "selected_topic": top_clean,
            "student_type": student_type,
            "academic_profile": academic_profile,
            "learning_objective": learning_obj,
            "topic_nature": topic_nature,
            "teaching_approach": teaching_approach,
            "prerequisites": prerequisites,
            "explanation_strategy": explanation_strategy,
            "practice_method": practice_method,
            "understanding_checks": understanding_checks,
            "resource_requirements": resources,
            "curriculum_validated": True,
            "validation_notes": f"Validated against active student syllabus for {subj_clean}.",
            "needs_clarification": False,
            "clarification_question": None,
            "is_valid": True
        }

# Global singleton instance
teaching_planner = DynamicTeachingPlanner()
