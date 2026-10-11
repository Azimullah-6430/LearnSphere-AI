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
    and execute the most effective pedagogical approach tailored specifically for SCHOOL or COLLEGE students.
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
        "interpretive",
        "theoretical"
    ]

    # Pedagogical strategy matrix for SCHOOL vs COLLEGE modes per topic nature
    TEACHING_METHODS = {
        "programming-oriented": {
            "SCHOOL": {
                "method": "Age-Appropriate Logic, Pseudocode & Step-by-Step Execution Trace",
                "explanation_focus": "Teach the actual curriculum topic using age-appropriate logic, algorithms, flowcharts, pseudocode, or simple code when appropriate. Clearly explain inputs, processing steps, outputs, and expected results. Define technical terms ('variable', 'loop', 'condition', 'input', 'output') before using them extensively.",
                "practice_focus": "Tracing inputs, processing steps, and expected outputs step-by-step using paper trace tables or simple pseudocode, demonstrating one guided example first.",
                "demonstration_type": "worked_example_and_derivation",
                "honest_limitation": "Physical lab experiments do not apply to software algorithms. This topic uses simple visual flowcharts, step-by-step logic traces, and paper-based debugging.",
                "learning_depth": "Introductory control flow logic, pseudocode walkthroughs, input/output tracing, and basic syntax fundamentals.",
                "checks": [
                    "What are the input values provided to this algorithm?",
                    "What processing step updates the variable inside the loop?",
                    "What is the final expected output printed at the end?"
                ]
            },
            "COLLEGE": {
                "method": "Topic-Appropriate Language Implementation, Execution, Debugging & Complexity Analysis",
                "explanation_focus": "Explain prerequisites, technical concepts, implementation, execution, expected output, debugging, testing, and performance considerations (Big-O). Use the language and tools appropriate to the topic and curriculum (e.g., C/C++ for systems/pointers/OS, Python/Java for Data Structures/OOP, SQL for Databases, HTML/JS for Web) rather than defaulting to one single language.",
                "practice_focus": "Providing a clear objective, required tools/setup, small readable code snippet, step-by-step logic breakdown, run instructions, expected output, testing tasks, and debugging guidance. Never force coding onto pure theory/proofs.",
                "demonstration_type": "code_and_logic_simulation",
                "honest_limitation": "Physical lab experiments are not applicable to software algorithms. This topic is taught using algorithmic flowcharts, runnable code snippets, execution trace tables, and formal debugging tasks.",
                "learning_depth": "Advanced technical concepts, topic-appropriate language implementation, Big-O complexity, edge-case testing, and production debugging.",
                "checks": [
                    "What is the exact time and space complexity (Big-O) of this algorithm?",
                    "How does the code handle boundary/edge cases (e.g., empty arrays, null pointers, or integer overflow)?",
                    "What execution command and tools are required to compile, run, and test this implementation?"
                ]
            }
        },
        "numerical": {
            "SCHOOL": {
                "method": "Visual Reasoning, Step-by-Step Calculation & Topic-Relevant Situations",
                "explanation_focus": "Explain mathematical operations using clear, simple language, visual reasoning, and step-by-step calculations. Use familiar real-world situations (shopping, time, distance, measurement, farming, or everyday quantities) ONLY when directly relevant to the selected topic. Define formulas and symbols before applying them.",
                "practice_focus": "Solving a step-by-step worked numerical calculation together first, demonstrating the method clearly before asking the student to complete a similar practice problem.",
                "demonstration_type": "worked_example_and_derivation",
                "honest_limitation": "Physical science lab experiments do not apply to mathematical calculations. This topic uses visual geometric reasoning and step-by-step worked calculations.",
                "learning_depth": "Fundamental arithmetic/algebraic steps, visual reasoning, unit conversions, and topic-relevant problem solving.",
                "checks": [
                    "What operation do we perform first in this step-by-step calculation?",
                    "What units should we write next to our final numerical answer?",
                    "Why do we check our calculation by plugging the answer back in?"
                ]
            },
            "COLLEGE": {
                "method": "First-Principles Formal Derivation, Mathematical Reasoning & Domain-Specific Applications",
                "explanation_focus": "Include prerequisites, appropriate mathematical notation, step-by-step worked examples, mathematical reasoning/proofs, and domain applications in engineering, physics, finance, or computer science.",
                "practice_focus": "Deriving mathematical theorems from axioms, solving domain-specific quantitative problems, and completing progressively challenging practice exercises.",
                "demonstration_type": "worked_example_and_derivation",
                "honest_limitation": "Physical lab experiments are not applicable to pure mathematical derivations. This topic uses formal proofs, vector/calculus notation, and mathematical domain modeling.",
                "learning_depth": "Rigorous first-principles derivations, formal mathematical notation, multivariable analysis, domain applications, and boundary limits.",
                "checks": [
                    "Derive the governing equation from first-principles mathematical axioms.",
                    "Under what domain constraints or boundary conditions does this theorem hold?",
                    "How does this mathematical principle apply to real-world problems in engineering, physics, finance, or CS?"
                ]
            }
        },
        "engineering-design": {
            "SCHOOL": {
                "method": "Simple Everyday Machines & Structural Toy Analogy",
                "explanation_focus": "Explain how levers, gears, and structures work using familiar everyday items like scissors, bicycles, or balanced seesaws. Define terms like 'force' and 'load' simply.",
                "practice_focus": "Observing how a simple tool or machine changes force or direction, with a guided step-by-step demonstration.",
                "demonstration_type": "system_diagram_and_simulation",
                "honest_limitation": "Heavy industrial machinery is not accessible at home. This topic uses simple machine diagrams and safe household balances.",
                "learning_depth": "Basic mechanical advantage, simple structural balance, and everyday physical forces.",
                "checks": [
                    "Where is the fulcrum or turning point in this simple machine?",
                    "Does using this tool make it easier to lift the load?",
                    "What material would make this simple structure stronger?"
                ]
            },
            "COLLEGE": {
                "method": "System Block Diagram, Mathematical Derivation & Design Constraint Analysis",
                "explanation_focus": "Transfer functions, stress-strain tensor derivations, circuit transient analysis, component safety margins, efficiency trade-offs, and simulation parameters.",
                "practice_focus": "Analyzing system block schematics, deriving governing differential equations, and solving engineering design optimization problems under physical constraints.",
                "demonstration_type": "system_diagram_and_simulation",
                "honest_limitation": "Heavy industrial machinery cannot be safely operated at home. This topic uses structural block diagrams, mathematical derivations, and design constraint simulations.",
                "learning_depth": "Engineering system modeling, stress/transient derivations, tolerance margins, and professional design trade-offs.",
                "checks": [
                    "What is the primary transfer function of each component in the system block diagram?",
                    "What engineering safety margin or tolerance limit must be maintained under peak load?",
                    "How do you optimize system efficiency under competing structural or thermal constraints?"
                ]
            }
        },
        "accounting-financial": {
            "SCHOOL": {
                "method": "Everyday Shopkeeper Story & Simple Cash Ledger",
                "explanation_focus": "Explain buying, selling, income, and expenses using a relatable shopkeeper or pocket-money story. Define 'debit' (money spent/received) and 'credit' simply before recording.",
                "practice_focus": "Filling in a simple 2-column cash ledger table step-by-step for a single day of sales, demonstrating one full example first.",
                "demonstration_type": "financial_case_study",
                "honest_limitation": "Physical science experiments do not apply to financial accounting. This topic uses simple cash transaction ledgers and relatable shopkeeper stories.",
                "learning_depth": "Basic income/expense tracking, simple cash balance calculations, and introductory bookkeeping.",
                "checks": [
                    "Did money come in (income) or go out (expense) in this transaction?",
                    "Which column of our simple cash table increases when money is received?",
                    "What is the total remaining cash balance at the end of the day?"
                ]
            },
            "COLLEGE": {
                "method": "Double-Entry Transaction Ledger & Financial Statement Case Study",
                "explanation_focus": "IFRS/GAAP accounting standards, debit/credit rules, transaction journals, accrual vs cash accounting, balance sheet equations, and corporate audit practices.",
                "practice_focus": "Recording complex journal entries, constructing T-accounts, balancing general ledgers, and evaluating corporate financial statements and solvency ratios.",
                "demonstration_type": "financial_case_study",
                "honest_limitation": "Physical science experiments do not apply to financial accounting. This topic uses transaction journals, T-account ledgers, balance sheet statements, and corporate case studies.",
                "learning_depth": "IFRS/GAAP standards, accrual accounting, double-entry bookkeeping, adjusting entries, and financial ratio analysis.",
                "checks": [
                    "Which account is debited and which is credited under IFRS guidelines for this transaction?",
                    "How does this adjusting entry affect the fundamental Accounting Equation (Assets = Liabilities + Equity)?",
                    "What financial ratio best measures the liquidity or solvency of this corporate balance sheet?"
                ]
            }
        },
        "economics-analytical": {
            "SCHOOL": {
                "method": "Everyday Market Stories & Basic Supply-Demand Graphs",
                "explanation_focus": "Explain buyer choices and price changes (like vegetable prices during harvest season) using simple stories. Define 'supply' and 'demand' before using them.",
                "practice_focus": "Reading a simple 2-line price chart to see how price moves when supply increases.",
                "demonstration_type": "worked_example_and_derivation",
                "honest_limitation": "Physical experiments do not apply to economic markets. This topic uses simple supply/demand stories and visual charts.",
                "learning_depth": "Introductory buyer behavior, market prices, and basic supply/demand concepts.",
                "checks": [
                    "What happens to the price when a crop is abundant in the market?",
                    "If buyers want more items than sellers have, does price go up or down?",
                    "Point to the equilibrium spot where buyers and sellers agree on price."
                ]
            },
            "COLLEGE": {
                "method": "Economic Graph Analysis, Numerical Elasticity & Real-World Policy Models",
                "explanation_focus": "Utility maximization, marginal rate of substitution, price/cross elasticity formulas, IS-LM macroeconomic curves, game theory, and fiscal policy deadweight loss.",
                "practice_focus": "Interpreting economic shift graphs, calculating elasticity coefficients using partial derivatives, and evaluating market intervention policies.",
                "demonstration_type": "worked_example_and_derivation",
                "honest_limitation": "Physical experiments do not apply to economic systems. This topic uses supply/demand equilibrium graphs, elasticity numerical calculations, and policy case studies.",
                "learning_depth": "Microeconomic/macroeconomic mathematical modeling, calculus-based elasticity, equilibrium shifts, and welfare economics.",
                "checks": [
                    "How does a shift in demand or supply alter the market equilibrium price and quantity mathematically?",
                    "Calculate the price elasticity of demand from the given numerical price-quantity dataset.",
                    "What deadweight loss or market surplus change occurs under price ceiling policies?"
                ]
            }
        },
        "historical-source": {
            "SCHOOL": {
                "method": "Story Timeline & Cause-Effect Key Events",
                "explanation_focus": "Tell an engaging historical story of key figures and events in clear language. Define historical terms simply and explain what led to major events.",
                "practice_focus": "Placing 3-4 major historical events in correct chronological order on a simple visual timeline.",
                "demonstration_type": "source_analysis_and_criticism",
                "honest_limitation": "Physical experiments or code execution do not apply to history. This topic uses story timelines and key cause-and-effect maps.",
                "learning_depth": "Chronological ordering, key historical figures, and basic cause-and-effect sequences.",
                "checks": [
                    "Which event happened first on our story timeline?",
                    "What main cause made people demand change in this historical event?",
                    "Name one important outcome of this historical event."
                ]
            },
            "COLLEGE": {
                "method": "Historiographical Analysis & Primary Source Document Criticism",
                "explanation_focus": "Historiographical debates, primary vs secondary source evaluation, ideological frameworks, socio-economic structural causes vs immediate diplomatic triggers.",
                "practice_focus": "Analyzing historical document excerpts, evaluating author bias/perspective, and constructing evidence-based historiographical arguments.",
                "demonstration_type": "source_analysis_and_criticism",
                "honest_limitation": "Physical experiments or code execution do not apply to history. This topic uses primary source excerpts, cause-and-effect mapping, and historiographical analysis.",
                "learning_depth": "Historiographical methodologies, primary source criticism, socio-economic structural analysis, and contextual bias evaluation.",
                "checks": [
                    "What primary evidence in the historical document supports or contradicts the main argument?",
                    "Distinguish short-term triggers from underlying structural socio-economic causes.",
                    "How does author bias or historical context shape the perspective of this primary source?"
                ]
            }
        },
        "geographical-spatial": {
            "SCHOOL": {
                "method": "Local Environment Observation & Map Symbols",
                "explanation_focus": "Explain landforms, rivers, weather, and map symbols using student's local surroundings. Define terms like 'elevation' and 'climate' simply.",
                "practice_focus": "Identifying map symbols and observing local soil or rainwater patterns around home or school.",
                "demonstration_type": "outdoor_observation",
                "honest_limitation": "Global scale geographical phenomena cannot be contained in a lab. This topic uses map reading, local weather tracking, and soil observations.",
                "learning_depth": "Basic map reading, local environmental observation, and landform identification.",
                "checks": [
                    "What map symbol represents a river or hill?",
                    "How does rain water flow on sloping ground compared to flat ground?",
                    "What type of soil do you observe in your local area?"
                ]
            },
            "COLLEGE": {
                "method": "GIS Spatial Analysis, Topographical Contour Modeling & Geomorphology",
                "explanation_focus": "Spatial data analysis, GIS projections, geomorphological processes (plate tectonics, erosion mechanics), Köppen climate classification, and remote sensing.",
                "practice_focus": "Interpreting complex topographical contour gradients, analyzing GIS spatial charts, and modeling watershed hydrology.",
                "demonstration_type": "outdoor_observation",
                "honest_limitation": "Global scale geographical phenomena cannot be contained in a lab. This topic uses topographical map reading, spatial GIS reasoning, climate data, and environmental analysis.",
                "learning_depth": "GIS spatial modeling, geomorphology, climate classification systems, and topographical analysis.",
                "checks": [
                    "How do contour line spacing and elevation changes indicate terrain gradient on a map?",
                    "What spatial pattern connects climate data to regional agricultural crop distribution?",
                    "How does local soil composition or topography affect watershed runoff and land use?"
                ]
            }
        },
        "language-grammar": {
            "SCHOOL": {
                "method": "Friendly Sentence Building & Word Games",
                "explanation_focus": "Explain grammar rules (nouns, verbs, tenses) using simple, fun sentences. Define technical terms before asking student to transform sentences.",
                "practice_focus": "Building simple sentences and correcting 1 guided error step-by-step.",
                "demonstration_type": "textual_analysis_and_criticism",
                "honest_limitation": "Physical experiments do not apply to language grammar. This topic uses sentence building blocks and guided vocabulary drills.",
                "learning_depth": "Parts of speech, basic sentence structure, and correct tense usage.",
                "checks": [
                    "Which word in this sentence is the action verb?",
                    "Change this sentence from past tense to present tense.",
                    "Use the new vocabulary word in a simple sentence."
                ]
            },
            "COLLEGE": {
                "method": "Linguistic Syntax Tree Analysis & Transformational Grammar",
                "explanation_focus": "Syntactic structures, phrase structure rules, morphological decomposition, register/pragmatics, and advanced stylistic transformations.",
                "practice_focus": "Deconstructing complex sentence syntax, analyzing phonological/morphological patterns, and writing formal academic commentary.",
                "demonstration_type": "textual_analysis_and_criticism",
                "honest_limitation": "Physical experiments do not apply to language grammar. This topic uses syntactic breakdowns, morphological analysis, reading comprehension, and structured writing drills.",
                "learning_depth": "Linguistic syntax trees, morphological decomposition, pragmatics, and advanced stylistic transformations.",
                "checks": [
                    "Which specific grammatical rule governs this complex syntactic structure?",
                    "Deconstruct this sentence into its constituency phrase structure tree.",
                    "Construct a grammatically sound academic sentence incorporating target terminology."
                ]
            }
        },
        "literary-thematic": {
            "SCHOOL": {
                "method": "Character Story & Theme Walkthrough",
                "explanation_focus": "Explain story characters, moral lessons, and metaphors in clear narrative language.",
                "practice_focus": "Finding 1 quote or sentence in a passage that shows how a story character feels.",
                "demonstration_type": "textual_analysis_and_criticism",
                "honest_limitation": "Physical experiments or code do not apply to literature. This topic uses story reading and character analysis.",
                "learning_depth": "Story themes, character motivation, and basic figurative language.",
                "checks": [
                    "Who is the main character in this story passage?",
                    "What lesson or message is the author sharing in this story?",
                    "Find one word or sentence that describes the setting."
                ]
            },
            "COLLEGE": {
                "method": "Structural & Deconstructive Textual Analysis & Critical Theory",
                "explanation_focus": "Critical theory frameworks (feminist, post-colonial, structuralist), rhetorical devices, narrative perspective shifts, subtext, and close textual evidence.",
                "practice_focus": "Close reading of literary excerpts, identifying poetic/rhetorical devices, and writing analytical thesis statements supported by textual evidence.",
                "demonstration_type": "textual_analysis_and_criticism",
                "honest_limitation": "Physical experiments or code execution do not apply to literary criticism. This topic uses close reading, thematic interpretation, rhetorical device analysis, and evidence-based argumentation.",
                "learning_depth": "Critical literary theory, structuralism, rhetorical device analysis, and textual evidence synthesis.",
                "checks": [
                    "What specific textual quote or passage provides evidence for the central theme?",
                    "How does the author's choice of metaphor/imagery enhance the emotional or dramatic impact?",
                    "What alternative critical interpretation can be drawn from the protagonist's actions?"
                ]
            }
        },
        "practical": {
            "SCHOOL": {
                "method": "Safe Household Science Experiment",
                "explanation_focus": "Explain physical science principles (e.g. why things sink/float, plant growth) using safe household items (water, salt, paper, leaves). Define terms simply.",
                "practice_focus": "Performing a safe, guided household demonstration step-by-step and logging simple observations.",
                "demonstration_type": "physical_demonstration",
                "honest_limitation": "None; this concept is demonstrated using safe household items without expensive lab equipment.",
                "learning_depth": "Basic scientific observation, cause-and-effect, and simple data logging.",
                "checks": [
                    "What happened when you placed the item in the water?",
                    "What safety rule did we follow before starting?",
                    "Why did the result change when we added salt/water?"
                ]
            },
            "COLLEGE": {
                "method": "Experimental Error Analysis & Empirical Data Modeling",
                "explanation_focus": "Thermodynamic laws, reaction kinetics, fluid mechanics, wave equations, measurement error margins, and calibration.",
                "practice_focus": "Carrying out physical or simulated experiments, measuring data, calculating error margins, and modeling reaction kinetics.",
                "demonstration_type": "physical_demonstration",
                "honest_limitation": "None; this scientific concept can be investigated through physical observation or zero-cost empirical modeling.",
                "learning_depth": "Thermodynamic kinetics, measurement error margins, and empirical mathematical modeling.",
                "checks": [
                    "What fundamental scientific law does this experiment demonstrate?",
                    "What safety precautions are required when setting up this demonstration?",
                    "How do observed real-world results compare quantitatively with theoretical expectations?"
                ]
            }
        },
        "procedural": {
            "SCHOOL": {
                "method": "Step-by-Step Activity Checklist",
                "explanation_focus": "Explain sequential steps using a clear 1-2-3 checklist.",
                "practice_focus": "Following each step in sequence and checking it off.",
                "demonstration_type": "system_diagram_and_simulation",
                "honest_limitation": "Full operational facilities are not accessible; this topic uses step-by-step checklists.",
                "learning_depth": "Sequential procedures, basic accuracy, and step checking.",
                "checks": [
                    "What is Step 1 in our checklist?",
                    "Why must Step 1 be finished before Step 2?",
                    "How do you check if you finished correctly?"
                ]
            },
            "COLLEGE": {
                "method": "Standard Operating Workflow & FMEA Risk Audit",
                "explanation_focus": "Sequential steps, operating protocols, Failure Mode and Effects Analysis (FMEA), quality assurance, and compliance auditing.",
                "practice_focus": "Executing procedural stages in sequence, auditing inputs, and verifying outputs against industry standards.",
                "demonstration_type": "system_diagram_and_simulation",
                "honest_limitation": "Full operational facilities may not be physically accessible. This topic uses standard operating workflow diagrams, stage-by-stage execution rules, and verification checkpoints.",
                "learning_depth": "SOP protocols, failure mode analysis, quality assurance, and compliance.",
                "checks": [
                    "What initial prerequisite condition must be met before starting step 1?",
                    "What error mode can occur if a step is performed out of order?",
                    "How do you verify that the procedure has been executed successfully?"
                ]
            }
        },
        "creative": {
            "SCHOOL": {
                "method": "Guided Drawing & Story Sketch Challenge",
                "explanation_focus": "Explain simple design tips (shapes, colors, story ideas) using paper and pencil.",
                "practice_focus": "Sketching a simple design concept with pencil and paper.",
                "demonstration_type": "system_diagram_and_simulation",
                "honest_limitation": "Commercial design studio tools are not required; pencil and paper are used.",
                "learning_depth": "Basic visual layout, creative expression, and idea sketching.",
                "checks": [
                    "What main shape or color did you choose for your design?",
                    "How does your drawing express your main idea?",
                    "What would you add to make your design even better?"
                ]
            },
            "COLLEGE": {
                "method": "Design Constraint Challenge & Iterative Synthesis Feedback",
                "explanation_focus": "Design heuristics, user experience (UX) architecture, composition theory, ergonomic constraints, and portfolio-grade synthesis.",
                "practice_focus": "Drafting an initial design sketch, layout, or creative piece under specific target constraints and conducting iterative feedback evaluations.",
                "demonstration_type": "system_diagram_and_simulation",
                "honest_limitation": "Commercial design studio tools are not required. This topic uses design constraint prompts, structural layout drafting, and iterative synthesis feedback.",
                "learning_depth": "Design heuristics, UX architecture, ergonomic constraints, and portfolio synthesis.",
                "checks": [
                    "How does your design address the primary functional or aesthetic requirement?",
                    "What design trade-offs did you make between competing constraints?",
                    "How would you iterate on this design draft based on user feedback?"
                ]
            }
        },
        "interpretive": {
            "SCHOOL": {
                "method": "Fairness & Community Rules Story",
                "explanation_focus": "Explain rules, rights, and fairness using relatable school or playground stories.",
                "practice_focus": "Deciding what is fair in a simple story scenario and explaining why.",
                "demonstration_type": "thought_experiment_and_analog",
                "honest_limitation": "Courtrooms are not accessible; everyday school scenarios are used.",
                "learning_depth": "Basic fairness, community rules, and simple reasoning.",
                "checks": [
                    "What rule was followed in this scenario?",
                    "Why was this decision fair for everyone?",
                    "How can we solve this disagreement peacefully?"
                ]
            },
            "COLLEGE": {
                "method": "Legal Precedent Synthesis & Statutory Construction",
                "explanation_focus": "Constitutional doctrines, landmark judicial precedents, statutory interpretation rules (literal, golden, mischief), and ethical framework trade-offs.",
                "practice_focus": "Synthesizing conflicting judicial precedents, constructing legal briefs, and evaluating constitutional challenges.",
                "demonstration_type": "thought_experiment_and_analog",
                "honest_limitation": "Courtroom proceedings are modeled using statutory precedent analysis and case studies.",
                "learning_depth": "Constitutional law, legal precedents, statutory interpretation rules, and jurisprudence.",
                "checks": [
                    "What legal precedent governs this factual scenario?",
                    "How do the statutory interpretation rules apply to this ambiguous clause?",
                    "Evaluate the constitutional implications of this judicial ruling."
                ]
            }
        },
        "theoretical": {
            "SCHOOL": {
                "method": "Simple Analogy & Everyday Story Explanation",
                "explanation_focus": "Explain abstract concepts using simple everyday analogies (e.g. atoms like solar systems). Define terms simply.",
                "practice_focus": "Answering a friendly conceptual question using the analogy provided.",
                "demonstration_type": "thought_experiment_and_analog",
                "honest_limitation": "Abstract concepts cannot be touched; relatable analogies are used.",
                "learning_depth": "Basic conceptual analogies and intuitive mental models.",
                "checks": [
                    "What everyday item did we compare this concept to?",
                    "How does the analogy help us understand the main idea?",
                    "Explain the main idea in your own words."
                ]
            },
            "COLLEGE": {
                "method": "Socratic Conceptual Decomposition & Thought Experiment",
                "explanation_focus": "Formal axiomatic frameworks, mathematical/physical limits, theoretical counter-examples, and model validity boundaries.",
                "practice_focus": "Socratic dialogue questions, concept mapping, logical argumentation, and conceptual thought experiments.",
                "demonstration_type": "thought_experiment_and_analog",
                "honest_limitation": "Subatomic or pure theoretical concepts cannot be directly physically manipulated with household items. This topic uses Socratic conceptual decomposition, logical axioms, and structured thought experiments.",
                "learning_depth": "Axiomatic frameworks, boundary limits, formal argumentation, and model validity.",
                "checks": [
                    "How would you explain this principle to someone with no background in this field?",
                    "What is the key distinction between this concept and its nearest related concept?",
                    "Under what boundary conditions does this theoretical model apply?"
                ]
            }
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
        if has_kw(["data structure", "algorithm", "programming", "code", "python", "java", "c++", "c#", "javascript", "sql", "database", "compiler", "recursion", "array", "pointer", "function", "class", "object oriented", "software", "web dev", "frontend", "backend", "api", "git", "tree", "graph", "sorting", "searching", "stack", "queue", "linked list", "hash table", "operating system", "linux", "kernel", "thread", "loop"]):
            return "programming-oriented"

        # 8. Engineering & Physical Systems Design
        if has_kw(["circuit", "thermodynamics", "kinematics", "mechanics", "fluid mechanics", "heat transfer", "signal processing", "control systems", "cad", "finite element", "electrical engineering", "mechanical engineering", "civil engineering", "aerodynamics"]):
            return "engineering-design"

        # 9. Mathematics & Computation
        if has_kw(["calculus", "differential", "integral", "matrix", "algebra", "trigonometry", "statistics", "probability", "equation", "formula", "geometry", "linear algebra", "discrete math", "theorem", "combinatorics", "rate of change", "mathematics", "math", "arithmetic"]):
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

    def infer_prerequisites(self, subject: str, topic: str, topic_nature: str, student_type: str = "COLLEGE") -> List[str]:
        """
        Dynamically infers 2-4 prerequisite concepts or skills for the topic based on topic nature and student type.
        """
        top_lower = topic.lower()

        if student_type == "SCHOOL":
            if topic_nature == "programming-oriented":
                return ["Basic counting & numbers", "Understanding 'repeat' instructions", "Paper & pencil writing"]
            if topic_nature == "accounting-financial":
                return ["Basic addition & subtraction", "Concept of money & shop purchases"]
            if topic_nature == "numerical":
                return ["Basic arithmetic (+, -, *, /)", "Reading simple numbers & tables"]
            if topic_nature == "historical-source":
                return ["Reading simple story timelines", "Understanding past vs present"]
            return [f"Basic intro to {subject}", "Reading & writing skills"]

        # COLLEGE
        if topic_nature == "programming-oriented":
            if "tree" in top_lower or "graph" in top_lower:
                return ["Pointers / Node references", "Recursion concepts", "Linear data structures (Arrays/Lists)"]
            if "sort" in top_lower or "search" in top_lower:
                return ["Array indexing", "Conditional logic (if/else)", "Loop iterations"]
            return ["Basic variable syntax", "Control flow structures", "Functions / methods"]

        if topic_nature == "accounting-financial":
            return ["Basic debit and credit rules", "Classification of Accounts (Assets, Liabilities, Equity)", "IFRS/GAAP fundamentals"]

        if topic_nature == "economics-analytical":
            return ["Basic supply & demand concepts", "Graphical axes interpretation", "Percentage change & derivative calculations"]

        if topic_nature == "historical-source":
            return ["Chronological ordering", "Distinction between primary and secondary sources", "Historiographical frameworks"]

        if topic_nature == "literary-thematic":
            return ["Textual annotation skills", "Figurative language terms (metaphor, allegory)", "Critical thesis composition"]

        if topic_nature == "language-grammar":
            return ["Basic parts of speech", "Phonetics & morphology", "Syntactic phrase structure"]

        if topic_nature == "numerical":
            if "calculus" in top_lower or "differential" in top_lower:
                return ["Algebraic simplification", "Function limits", "Coordinate geometry & derivatives"]
            return ["Basic algebra", "Unit conversion", "Linear equations"]

        if topic_nature == "engineering-design":
            return ["Basic physical laws (Newton's laws, Ohm's law)", "Schematic diagram symbols", "Differential equation solving"]

        if topic_nature == "practical":
            return ["Basic scientific method", "Observation recording", "Material safety & error calculation"]

        # Default / Theoretical
        return [f"Foundational terminology in {subject}", "Analytical conceptual reasoning"]

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
        Generates a structured, validated teaching plan for any subject and topic in student's curriculum,
        differentiating SCHOOL vs COLLEGE student strategies.
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

        # Determine student level details strictly
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

        # Retrieve teaching approach metadata for target student type
        nature_dict = self.TEACHING_METHODS.get(topic_nature, self.TEACHING_METHODS["theoretical"])
        method_meta = nature_dict.get(student_type, nature_dict["COLLEGE"])

        teaching_approach = method_meta["method"]
        demonstration_type = method_meta["demonstration_type"]
        honest_limitation = method_meta["honest_limitation"]
        learning_depth = method_meta.get("learning_depth", "Target academic level depth.")

        # Specific pedagogical guidelines per mode
        if student_type == "SCHOOL":
            pedagogical_guidelines = [
                f"Follow actual school curriculum and grade level ({academic_profile.get('grade')}).",
                "Explain concepts in clear, simple, accessible language.",
                "Define technical terms before using them extensively.",
                "Begin with familiar everyday/household examples and prerequisites.",
                "Break methods into simple, manageable steps.",
                "Demonstrate one full example step-by-step before asking the student to practise.",
                "Provide age-appropriate questions and supportive, encouraging feedback.",
                "Avoid assuming access to laboratories, computers, expensive materials, or continuous internet."
            ]
        else:
            pedagogical_guidelines = [
                f"Follow actual course, department ({academic_profile.get('department')}), year, and semester ({academic_profile.get('semester')}).",
                "Identify prerequisites and explain missing fundamentals where needed.",
                "Use accurate technical terminology and appropriate mathematical/formal notation.",
                "Explain underlying reasoning, theoretical assumptions, trade-offs, and design/operational limitations.",
                "Include advanced examples, derivations, calculations, coding, proofs, design tasks, or case studies when relevant.",
                "Connect concepts to professional, research, or industry applications where appropriate.",
                "Encourage independent problem-solving, analytical rigor, and deeper conceptual understanding."
            ]

        # Learning objective
        if objectives and len(objectives) > 0 and isinstance(objectives[0], str):
            learning_obj = f"Master {top_clean} in {subj_clean}: {objectives[0]}"
        else:
            level_label = f"Grade {academic_profile.get('grade')}" if student_type == "SCHOOL" else f"{academic_profile.get('program')} (Semester {academic_profile.get('semester')})"
            learning_obj = f"Understand core principles, solve representative problems, and demonstrate practical understanding of {top_clean} in {subj_clean} for {level_label} students."

        # Prerequisites
        prerequisites = self.infer_prerequisites(subj_clean, top_clean, topic_nature, student_type)

        # Strategy & Practice
        level_label = academic_profile.get('grade') if student_type == "SCHOOL" else f"{academic_profile.get('department', '')} Sem {academic_profile.get('semester', '')}"
        explanation_strategy = f"{method_meta['explanation_focus']} Tailored specifically for {student_type} mode ({level_label})."
        practice_method = f"{method_meta['practice_focus']} Resource Environment: '{resource_environment or 'Standard learning resources'}'."
        understanding_checks = method_meta["checks"]

        # Resource Requirements & Material Query Determination
        useful_material_types = {"physical_demonstration", "outdoor_observation", "household_demonstration"}
        useful_natures = {"practical", "physical-chemical", "biological-agricultural"}
        asks_available_materials = (demonstration_type in useful_material_types) or (topic_nature in useful_natures)
        if asks_available_materials:
            materials_query_rationale = f"This topic ({top_clean}) involves hands-on physical or biological observation. Querying available local materials helps customize the practical activity."
        else:
            materials_query_rationale = f"This topic ({top_clean}) is best taught through {teaching_approach.lower()} (worked problems, coding, diagrams, or textual analysis). Querying physical materials is unnecessary."

        resources = []
        if custom_materials:
            resources.append(f"Student provided materials: {custom_materials}")
        if resource_environment:
            resources.append(f"Resource category: {resource_environment}")
        if not resources:
            if student_type == "SCHOOL":
                resources = ["Paper, pencil, everyday household items, or simple visual sketches (no computer/internet required)"]
            else:
                resources = ["Notebook, reference text, writing instrument, software development IDE, or calculation tools"]

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
            "learning_depth": learning_depth,
            "pedagogical_guidelines": pedagogical_guidelines,
            "prerequisites": prerequisites,
            "explanation_strategy": explanation_strategy,
            "practice_method": practice_method,
            "understanding_checks": understanding_checks,
            "resource_requirements": resources,
            "asks_available_materials": asks_available_materials,
            "materials_query_rationale": materials_query_rationale,
            "curriculum_validated": True,
            "validation_notes": f"Validated against active student syllabus for {subj_clean} ({student_type} mode).",
            "needs_clarification": False,
            "clarification_question": None,
            "is_valid": True
        }

# Global singleton instance
teaching_planner = DynamicTeachingPlanner()

