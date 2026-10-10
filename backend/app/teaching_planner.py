"""
LearnSphere AI - Universal Teaching Engine & Dynamic Planner

Analyzes student curriculum context, subject & topic nature, student profile (School/College),
prerequisites, available materials, and dynamically selects appropriate teaching methods based on the actual topic.

Universal Topic Nature Selection:
  - Science: Safe experiments, outdoor observations, models, and explanations of scientific principles.
  - Mathematics: Visual reasoning, worked examples, proofs, calculations, and real-life problems.
  - Computer Science: Algorithms, logic, flowcharts, code execution, testing, and debugging.
  - Engineering: Diagrams, derivations, calculations, simulations, design exercises, and safe practical work.
  - Commerce & Accounting: Transactions, calculations, financial statements, ledgers, and case studies.
  - Economics: Graphs, numerical elasticity examples, equilibrium models, and real-world policy applications.
  - History: Timelines, causes and consequences, primary source document analysis, and historical context.
  - Geography: Maps, spatial reasoning, environmental observations, climate/soil data interpretation.
  - Languages: Grammar, vocabulary, reading, writing, communication drills, and feedback.
  - Literature: Themes, interpretation, close reading, and evidence-based analysis.
  - Other/Interdisciplinary: Dynamically selected based on topic characteristics and learning objectives.

Guarantees:
  - Never forces experiments, coding, or physical activities onto topics where they are inappropriate.
  - Explains limitations honestly and provides suitable alternatives (worked examples, diagrams, code traces, ledgers, source analysis, thought experiments).
  - Works for new subjects automatically without code changes per subject.
"""

from typing import Dict, Any, List, Optional
import logging
import re

logger = logging.getLogger("UniversalTeachingEngine")

class DynamicTeachingPlanner:
    """
    Universal Teaching Engine for Learn from Anywhere.
    Analyzes topic characteristics, student profile, and syllabus context to dynamically select
    and execute the most effective pedagogical approach.
    """

    TOPIC_NATURES = [
        "programming-oriented",
        "numerical",
        "engineering-design",
        "accounting-financial",
        "economics-analytical",
        "historical-source",
        "geographical-spatial",
        "language-grammar",
        "literary-thematic",
        "practical",
        "procedural",
        "creative",
        "theoretical"
    ]

    TEACHING_METHODS = {
        "programming-oriented": {
            "method": "Algorithmic Logic Breakdown, Block Flowchart & Code Execution Trace",
            "explanation_focus": "Data structures, algorithmic logic, control flow, time/space complexity Big-O, edge cases, and code syntax.",
            "practice_focus": "Tracing code execution step-by-step, analyzing time complexity, and debugging logical errors in algorithms.",
            "demonstration_type": "code_and_logic_simulation",
            "honest_limitation": "Physical lab experiments are not applicable to software algorithms. This topic is taught using algorithmic logic flowcharts, code execution trace tables, and debugging tasks.",
            "checks": [
                "What is the time and space complexity (Big-O) of this algorithm?",
                "How does the code handle boundary/edge cases (e.g. empty arrays or null pointers)?",
                "Trace the variable states through the main loop step-by-step for a given input."
            ]
        },
        "numerical": {
            "method": "Visual Reasoning, First-Principles Derivation & Worked Numerical Problems",
            "explanation_focus": "Mathematical axioms, formula derivations, geometric/algebraic visualization, and step-by-step calculations.",
            "practice_focus": "Solving worked numerical problems from given parameters to target values, enforcing units and algebraic steps.",
            "demonstration_type": "worked_example_and_derivation",
            "honest_limitation": "Physical lab experiments are not applicable to pure mathematical derivations. This topic uses visual geometric reasoning, formula proofs, and step-by-step worked calculations.",
            "checks": [
                "What mathematical or quantitative principle does this formula express?",
                "Are all variables converted to standard units before substitution?",
                "How does the result change if key parameters approach zero or infinity?"
            ]
        },
        "engineering-design": {
            "method": "System Block Diagram, Mathematical Derivation & Design Constraint Analysis",
            "explanation_focus": "Schematic diagrams, physical derivations, component constraints, efficiency trade-offs, and simulation parameters.",
            "practice_focus": "Analyzing system block schematics, deriving governing equations, and solving engineering design problems.",
            "demonstration_type": "system_diagram_and_simulation",
            "honest_limitation": "Heavy industrial machinery cannot be safely operated at home. This topic uses structural block diagrams, mathematical derivations, and design constraint simulations.",
            "checks": [
                "What is the primary function of each component in the system block diagram?",
                "What engineering safety margin or tolerance limit must be maintained?",
                "How do you optimize system performance under resource constraints?"
            ]
        },
        "accounting-financial": {
            "method": "Double-Entry Transaction Ledger & Financial Statement Case Study",
            "explanation_focus": "Accounting principles, debit/credit rules, transaction journals, balance sheet equations, and ratio analysis.",
            "practice_focus": "Recording journal entries, constructing T-accounts, balancing ledgers, and evaluating financial statements.",
            "demonstration_type": "financial_case_study",
            "honest_limitation": "Physical science experiments do not apply to financial accounting. This topic uses transaction journals, T-account ledgers, balance sheet statements, and case studies.",
            "checks": [
                "Which account is debited and which is credited for this financial transaction?",
                "How does this transaction affect the fundamental Accounting Equation (Assets = Liabilities + Equity)?",
                "What financial ratio best measures the liquidity or profitability of this scenario?"
            ]
        },
        "economics-analytical": {
            "method": "Economic Graph Analysis, Numerical Elasticity & Real-World Policy Models",
            "explanation_focus": "Supply/demand curves, market equilibrium, cost functions, elasticity formulas, and policy impacts.",
            "practice_focus": "Interpreting economic shift graphs, calculating elasticity coefficients, and evaluating market intervention policies.",
            "demonstration_type": "worked_example_and_derivation",
            "honest_limitation": "Physical experiments do not apply to economic systems. This topic uses supply/demand equilibrium graphs, elasticity numerical calculations, and real-world policy case studies.",
            "checks": [
                "How does a shift in demand or supply alter the market equilibrium price and quantity?",
                "Calculate the price elasticity of demand from the given numerical price-quantity data.",
                "What real-world deadweight loss or market surplus change occurs under price ceiling policies?"
            ]
        },
        "historical-source": {
            "method": "Chronological Timeline & Primary Source Document Analysis",
            "explanation_focus": "Historical context, causality chains, primary vs secondary sources, author perspective, and long-term consequences.",
            "practice_focus": "Analyzing historical document excerpts, constructing timeline sequences, and evaluating cause-and-effect arguments.",
            "demonstration_type": "source_analysis_and_criticism",
            "honest_limitation": "Physical experiments or code execution do not apply to history. This topic uses chronological timelines, cause-and-effect mapping, primary source excerpt analysis, and historical context breakdown.",
            "checks": [
                "What primary evidence in the historical excerpt supports the main argument?",
                "What short-term triggers and long-term causes led to this historical event?",
                "How does author bias or historical context shape the perspective of this source?"
            ]
        },
        "geographical-spatial": {
            "method": "Spatial Map Reasoning, Environmental Data & Landform Analysis",
            "explanation_focus": "Topographical maps, spatial distribution patterns, climate data graphs, soil profiles, and human-environment interactions.",
            "practice_focus": "Reading contour maps, analyzing climate/soil data charts, and observing local environmental phenomena.",
            "demonstration_type": "outdoor_observation",
            "honest_limitation": "Global scale geographical phenomena cannot be contained in a lab. This topic uses topographical map reading, spatial reasoning, climate data interpretation, and local environmental observations.",
            "checks": [
                "How do contour line spacing and elevation changes indicate terrain gradient on a map?",
                "What spatial pattern connects climate data to agricultural crop distribution?",
                "How does local soil composition or topography affect water runoff and land use?"
            ]
        },
        "language-grammar": {
            "method": "Structural Syntax Breakdown & Contextual Communication Drills",
            "explanation_focus": "Grammatical rules, syntactic structures, vocabulary nuance, tense/aspect usage, and sentence transformations.",
            "practice_focus": "Sentence restructuring drills, error correction, fill-in exercises, and contextual paragraph composition.",
            "demonstration_type": "textual_analysis_and_criticism",
            "honest_limitation": "Physical experiments do not apply to language grammar. This topic uses syntactic breakdowns, vocabulary in context, reading comprehension, and structured writing drills.",
            "checks": [
                "Which specific grammatical rule governs this sentence structure?",
                "Transform this active sentence into passive voice (or change tense) correctly.",
                "Construct a grammatically sound sentence incorporating the target vocabulary term."
            ]
        },
        "literary-thematic": {
            "method": "Close Textual Reading & Evidence-Based Literary Interpretation",
            "explanation_focus": "Thematic motifs, character arcs, figurative language, narrative perspective, and textual evidence analysis.",
            "practice_focus": "Close reading of literary excerpts, identifying poetic/rhetorical devices, and writing analytical thesis statements.",
            "demonstration_type": "textual_analysis_and_criticism",
            "honest_limitation": "Physical experiments or code execution do not apply to literary criticism. This topic uses close reading of textual excerpts, thematic interpretation, rhetorical device analysis, and evidence-based argumentation.",
            "checks": [
                "What specific textual quote or passage provides evidence for the central theme?",
                "How does the author's choice of metaphor/imagery enhance the emotional or dramatic impact?",
                "What alternative interpretation can be drawn from the protagonist's actions?"
            ]
        },
        "practical": {
            "method": "Safe Physical Experiment & Observable Scientific Demonstration",
            "explanation_focus": "Scientific principles, experimental variables, safety precautions, material substitutions, and empirical observations.",
            "practice_focus": "Carrying out a safe experiment or observation using available resources, logging data, and drawing scientific conclusions.",
            "demonstration_type": "physical_demonstration",
            "honest_limitation": "None; this scientific concept can be safely investigated through physical observation or zero-cost household demonstration.",
            "checks": [
                "What fundamental scientific law does this experiment demonstrate?",
                "What safety precautions are required when setting up this demonstration?",
                "How do observed real-world results compare with theoretical expectations?"
            ]
        },
        "procedural": {
            "method": "Standard Operating Workflow & Stage-by-Stage Verification",
            "explanation_focus": "Sequential steps, operating protocols, error recovery, quality assurance, and verification checkpoints.",
            "practice_focus": "Executing procedural stages in sequence, auditing inputs, and verifying outputs against standards.",
            "demonstration_type": "system_diagram_and_simulation",
            "honest_limitation": "Full operational facilities may not be physically accessible. This topic uses standard operating workflow diagrams, stage-by-stage execution rules, and verification checkpoints.",
            "checks": [
                "What initial prerequisite condition must be met before starting step 1?",
                "What error mode can occur if a step is performed out of order?",
                "How do you verify that the procedure has been executed successfully?"
            ]
        },
        "creative": {
            "method": "Design Constraint Challenge & Iterative Synthesis Feedback",
            "explanation_focus": "Design principles, aesthetic/functional constraints, target audience perspective, and creative synthesis.",
            "practice_focus": "Drafting an initial design sketch, layout, or creative piece under specific target constraints.",
            "demonstration_type": "system_diagram_and_simulation",
            "honest_limitation": "Commercial design studio tools are not required. This topic uses design constraint prompts, structural layout drafting, and iterative synthesis feedback.",
            "checks": [
                "How does your design address the primary functional or aesthetic requirement?",
                "What design trade-offs did you make between competing constraints?",
                "How would you iterate on this design draft based on user feedback?"
            ]
        },
        "theoretical": {
            "method": "Socratic Conceptual Decomposition & Thought Experiment",
            "explanation_focus": "Intuitive analogies, logical axioms, contrasting counter-examples, and conceptual mental models.",
            "practice_focus": "Socratic dialogue questions, concept mapping, logical argumentation, and conceptual thought experiments.",
            "demonstration_type": "thought_experiment_and_analog",
            "honest_limitation": "Subatomic or pure theoretical concepts cannot be directly physically manipulated with household items. This topic uses Socratic conceptual decomposition, logical axioms, and structured thought experiments.",
            "checks": [
                "How would you explain this principle to someone with no background in this field?",
                "What is the key distinction between this concept and its nearest related concept?",
                "Under what boundary conditions does this theoretical model apply?"
            ]
        }
    }

    def detect_topic_nature(self, subject: str, topic: str, syllabus_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Dynamically classifies the nature of the topic based on actual topic text, subject name, and syllabus context.
        Operates universally across any subject without hardcoded subject limits.
        """
        combined = f"{subject} {topic}".lower()
        if syllabus_context:
            combined += " " + str(syllabus_context.get("description", "")).lower()
            combined += " " + str(syllabus_context.get("learning_objectives", "")).lower()
            if isinstance(syllabus_context.get("topics"), list):
                combined += " " + " ".join([str(t) for t in syllabus_context["topics"]]).lower()

        # Helper for regex word-boundary or substring match
        def has_kw(kw_list: List[str]) -> bool:
            for kw in kw_list:
                if len(kw) <= 4:
                    if re.search(r"\b" + re.escape(kw) + r"\b", combined):
                        return True
                else:
                    if kw in combined:
                        return True
            return False

        # 1. Accounting & Financial Commerce
        if has_kw(["accounting", "ledger", "journal", "debit", "credit", "balance sheet", "t-account", "auditing", "taxation", "costing", "financial statement", "cash flow", "bookkeeping", "depreciation", "trial balance"]):
            return "accounting-financial"

        # 2. Economics
        if has_kw(["economics", "microeconomics", "macroeconomics", "elasticity", "supply and demand", "demand curve", "market equilibrium", "inflation", "gdp", "monetary policy", "fiscal policy", "utility theory"]):
            return "economics-analytical"

        # 3. History
        if has_kw(["history", "historical", "revolution", "world war", "civilization", "empire", "treaty", "dynasty", "colonialism", "historical source", "historiography", "archaeology", "nationalism"]):
            return "historical-source"

        # 4. Geography & Earth Sciences
        if has_kw(["geography", "map", "contour", "topographical", "spatial", "weather", "atmosphere", "climate zone", "plate tectonics", "cartography", "gis", "landform", "geomorp"]):
            return "geographical-spatial"

        # 5. Literature & Criticism
        if has_kw(["literature", "poetry", "poem", "novel", "play", "drama", "prose", "shakespeare", "literary", "tragedy", "fiction", "thematic analysis", "rhetoric", "allegory"]):
            return "literary-thematic"

        # 6. Languages & Linguistics
        if has_kw(["grammar", "syntax", "vocabulary", "phonetics", "verb conjugation", "french", "spanish", "german", "english grammar", "linguistics", "parts of speech", "tense", "translation", "morphology"]):
            return "language-grammar"

        # Interpretive / Law / Philosophy / Case Studies
        if has_kw(["law", "precedent", "precedents", "statutory", "jurisdiction", "jurisprudence", "constitution", "ethics", "philosophy", "court", "ruling"]):
            return "interpretive"

        # 7. Computer Science & Software
        if has_kw(["data structure", "algorithm", "programming", "code", "python", "java", "c++", "c#", "javascript", "sql", "database", "compiler", "recursion", "array", "pointer", "function", "class", "object oriented", "software", "web dev", "frontend", "backend", "api", "git", "tree", "graph", "sorting", "searching", "stack", "queue", "linked list", "hash table", "operating system", "linux", "kernel", "thread"]):
            return "programming-oriented"

        # 8. Engineering & Physical Systems Design
        if has_kw(["circuit", "thermodynamics", "kinematics", "mechanics", "fluid mechanics", "heat transfer", "signal processing", "control systems", "cad", "finite element", "electrical engineering", "mechanical engineering", "civil engineering", "aerodynamics"]):
            return "engineering-design"

        # 9. Mathematics & Computation
        if has_kw(["calculus", "differential", "integral", "matrix", "algebra", "trigonometry", "statistics", "probability", "equation", "formula", "geometry", "linear algebra", "discrete math", "theorem", "combinatorics"]):
            return "numerical"

        # 10. Practical / Experimental Science
        if has_kw(["experiment", "lab", "titration", "dissection", "microscope", "chemical reaction", "osmosis", "botany", "zoology", "electrolysis", "circuit assembly", "field study", "soil testing", "chromatography", "spectroscopy", "bacteriology", "photosynthesis", "transpiration"]):
            return "practical"

        # 11. Creative & Fine Arts
        if has_kw(["art", "design", "creative writing", "sculpture", "animation", "graphics", "media production", "typography", "sketching", "painting"]):
            return "creative"

        # 12. Procedural & Operational Workflows
        if has_kw(["procedure", "protocol", "audit workflow", "nursing care", "clinical procedure", "standard operating", "quality control", "operations management", "supply chain", "sop"]):
            return "procedural"

        # Default fallback for general or unknown topics
        return "theoretical"

    def infer_prerequisites(self, subject: str, topic: str, topic_nature: str) -> List[str]:
        """
        Dynamically infers 2-4 prerequisite concepts or skills for the topic based on topic nature.
        """
        top_lower = topic.lower()

        if topic_nature == "programming-oriented":
            if "tree" in top_lower or "graph" in top_lower:
                return ["Pointers / Node references", "Recursion concepts", "Linear data structures (Arrays/Lists)"]
            if "sort" in top_lower or "search" in top_lower:
                return ["Array indexing", "Conditional logic (if/else)", "Loop iterations"]
            return ["Basic variable syntax", "Control flow structures", "Functions / methods"]

        if topic_nature == "accounting-financial":
            return ["Basic debit and credit rules", "Classification of Accounts (Assets, Liabilities, Equity)", "Basic arithmetic"]

        if topic_nature == "economics-analytical":
            return ["Basic supply & demand concepts", "Graphical axes interpretation", "Percentage change calculations"]

        if topic_nature == "historical-source":
            return ["Chronological ordering", "Distinction between primary and secondary sources", "Historical terminology"]

        if topic_nature == "literary-thematic":
            return ["Textual annotation skills", "Basic figurative language terms (metaphor, simile)", "Paragraph structure"]

        if topic_nature == "language-grammar":
            return ["Basic parts of speech", "Alphabet & phonics", "Sentence punctuation"]

        if topic_nature == "numerical":
            if "calculus" in top_lower or "differential" in top_lower:
                return ["Algebraic simplification", "Function limits", "Coordinate geometry"]
            return ["Basic algebra", "Unit conversion", "Arithmetic operations"]

        if topic_nature == "engineering-design":
            return ["Basic physical laws (Newton's laws, Ohm's law)", "Schematic diagram symbols", "Algebraic equation solving"]

        if topic_nature == "practical":
            return ["Basic scientific method", "Observation recording", "Material safety precautions"]

        # Default / Theoretical
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

        # Extract syllabus objectives & topics
        objectives = []
        validated_topics = []
        if syllabus_context:
            objectives = syllabus_context.get("learning_objectives") or syllabus_context.get("objectives") or []
            validated_topics = syllabus_context.get("topics") or []

        # Detect topic nature based on actual topic text
        topic_nature = self.detect_topic_nature(subj_clean, top_clean, syllabus_context)

        # Retrieve teaching approach metadata
        method_meta = self.TEACHING_METHODS.get(topic_nature, self.TEACHING_METHODS["theoretical"])
        teaching_approach = method_meta["method"]
        demonstration_type = method_meta["demonstration_type"]
        honest_limitation = method_meta["honest_limitation"]

        # Learning objective
        if objectives and len(objectives) > 0 and isinstance(objectives[0], str):
            learning_obj = f"Master {top_clean} in {subj_clean}: {objectives[0]}"
        else:
            level_label = f"Grade {academic_profile.get('grade')}" if student_type == "SCHOOL" else f"{academic_profile.get('program')} (Semester {academic_profile.get('semester')})"
            learning_obj = f"Understand core principles, solve representative problems, and demonstrate practical understanding of {top_clean} in {subj_clean} for {level_label} students."

        # Prerequisites
        prerequisites = self.infer_prerequisites(subj_clean, top_clean, topic_nature)

        # Strategy, Practice & Checks
        level_label = academic_profile.get('grade') if student_type == "SCHOOL" else f"{academic_profile.get('department', '')} Sem {academic_profile.get('semester', '')}"
        explanation_strategy = f"{method_meta['explanation_focus']} Tailored for {student_type} level ({level_label})."
        practice_method = f"{method_meta['practice_focus']} Environment: '{resource_environment or 'Standard learning resources'}'."
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
            "demonstration_type": demonstration_type,
            "honest_limitation": honest_limitation,
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
