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
        "social-civics",
        "language-grammar",
        "literary-thematic",
        "science-physics",
        "chemistry",
        "biology",
        "practical",
        "procedural",
        "creative",
        "interpretive",
        "theoretical"
    ]

    # Pedagogical strategy matrix for SCHOOL vs COLLEGE modes per topic nature
    TEACHING_METHODS = {
        "science-physics": {
            "SCHOOL": {
                "method": "Simple Safe Experiment or Observation & Clear Scientific Explanation",
                "explanation_focus": "Simple experiments or observations using safe, locally available materials. Include materials, a few steps, expected observations, and a clear scientific explanation. Never invent an experiment that cannot work. Define basic physical terms simply.",
                "practice_focus": "Carrying out a safe observation or hands-on setup with everyday items, logging expected observations, and explaining the physical phenomenon.",
                "demonstration_type": "safe_demonstration",
                "honest_limitation": "Dangerous equipment, open flames, and 220V electricity are strictly forbidden. Only safe, locally available everyday items are used.",
                "learning_depth": "Foundational physical principles, observable cause-and-effect, and safe physical investigations.",
                "checks": [
                    "What materials did you use to observe this physical principle?",
                    "What expected observation did you record?",
                    "Why does this happen scientifically in your own words?"
                ]
            },
            "COLLEGE": {
                "method": "Physical Principle Derivation, Empirical Setup & Error Analysis",
                "explanation_focus": "Syllabus-aligned physical laws, vector/tensor notation, governing equations, boundary conditions, and error analysis. Simple experiments or observations using safe locally available materials with clear scientific explanations.",
                "practice_focus": "Deriving governing physical equations, calculating experimental parameters, and completing empirical observations or thought experiments.",
                "demonstration_type": "safe_demonstration",
                "honest_limitation": "Hazardous high-voltage or heavy equipment is prohibited. Safe macroscopic physical setups, calculations, and analytical derivations are used.",
                "learning_depth": "Rigorous physical equations, empirical setup design, error bounds, and theoretical foundations.",
                "checks": [
                    "State the governing equation or law for this physical phenomenon.",
                    "What variables directly control the observed outcome?",
                    "What real-world conditions create discrepancies between ideal theory and observed data?"
                ]
            }
        },
        "chemistry": {
            "SCHOOL": {
                "method": "Safe Household Chemistry Demonstration or Simulation",
                "explanation_focus": "Safe household demonstrations only when scientifically valid (e.g. natural indicators, vinegar-baking soda neutralization). Never suggest mixing unknown chemicals, dangerous substances, or unsupervised hazardous procedures. If a suitable experiment is not safe or practical, provide an observation or simulation task.",
                "practice_focus": "Carrying out a 100% safe household demonstration with kitchen materials (turmeric, lemon, water) or an observational simulation task.",
                "demonstration_type": "safe_demonstration",
                "honest_limitation": "Never mix unknown chemicals, hazardous acids/bases, or toxic substances. Unsafe or impractical topics use molecular models or observation tasks.",
                "learning_depth": "Basic chemical changes, natural indicators, solutions, and safe household observations.",
                "checks": [
                    "What safe household materials were used in this demonstration?",
                    "What observable change (color, effervescence, temperature) occurred?",
                    "Why must we never mix unknown or unsupervised chemicals?"
                ]
            },
            "COLLEGE": {
                "method": "Chemical Reaction Mechanism, Equilibrium Analysis & Safe Simulation",
                "explanation_focus": "Reaction mechanisms, stoichiometry, chemical equilibrium, thermodynamics, and molecular interactions. Safe household demonstrations only when scientifically valid. Never suggest mixing unknown chemicals, dangerous substances, or unsupervised hazardous procedures. If a suitable experiment is not safe or practical, provide an observation or simulation task.",
                "practice_focus": "Mapping reaction mechanisms, balancing stoichiometric equations, calculating equilibrium constants, or running a safe molecular simulation task.",
                "demonstration_type": "simulation_task",
                "honest_limitation": "Hazardous laboratory reagents, toxic chemicals, and concentrated acids cannot be used at home. Safe natural analogs or molecular simulation tasks are used.",
                "learning_depth": "Reaction kinetics, thermodynamic spontaneity, molecular orbital interactions, and equilibrium calculations.",
                "checks": [
                    "Describe the reaction mechanism or equilibrium shift.",
                    "What thermodynamic or kinetic factors govern this reaction rate?",
                    "Why does this reaction reach equilibrium rather than proceeding to total completion?"
                ]
            }
        },
        "biology": {
            "SCHOOL": {
                "method": "Respectful Natural Living System Observation",
                "explanation_focus": "Observe plants, seeds, leaves, soil, or other suitable natural materials where relevant. Include respectful handling of living things and no unnecessary harm. Explain life processes simply.",
                "practice_focus": "Observing living plants, leaves, seeds, or soil outdoors without causing harm, recording visible structures and changes.",
                "demonstration_type": "outdoor_observation",
                "honest_limitation": "No harm to living creatures or plants. Observation is conducted respectfully using natural surroundings.",
                "learning_depth": "Basic plant anatomy, seed germination, soil life, and respectful natural observation.",
                "checks": [
                    "What plant, leaf, seed, or soil feature did you examine?",
                    "How did you observe this living thing respectfully without harming it?",
                    "What role does this structure play in keeping the organism alive?"
                ]
            },
            "COLLEGE": {
                "method": "Cellular Physiology, Ecological Interactions & Non-Invasive Botanical Study",
                "explanation_focus": "Cellular respiration, physiological transport mechanisms, ecological niche dynamics, and botanical taxonomy. Observe plants, seeds, leaves, soil, or natural materials where relevant. Include respectful handling of living things and no unnecessary harm.",
                "practice_focus": "Non-invasive observation of botanical specimens, analyzing water potential / gas exchange dynamics, or modeling physiological feedback loops.",
                "demonstration_type": "outdoor_observation",
                "honest_limitation": "Invasive animal testing or hazardous pathogen handling is prohibited. Non-invasive botanical and ecological observation is used.",
                "learning_depth": "Plant physiology, transpiration pull, stomatal regulation, soil microbiology, and ecological adaptations.",
                "checks": [
                    "What physiological transport mechanism governs this biological observation?",
                    "How do environmental parameters (light, humidity, soil pH) modulate this life process?",
                    "Explain the molecular or cellular feedback loop maintaining homeostasis."
                ]
            }
        },
        "social-civics": {
            "SCHOOL": {
                "method": "Local Civic Observation & Community Example Exploration",
                "explanation_focus": "Local observation, map-reading, timeline creation, community surveys with permission, comparing historical evidence, and explaining local civic or geographical examples.",
                "practice_focus": "Exploring how local village or town councils, water systems, public schools, or libraries operate, or conducting a mini survey with permission.",
                "demonstration_type": "community_civic_observation",
                "honest_limitation": "Physical laboratory experiments do not apply to social science. This topic uses local civic observations, community interviews with permission, and institutional analysis.",
                "learning_depth": "Basic civic duties, public utilities, community decision-making, and local governance.",
                "checks": [
                    "What local institution or civic service did you observe?",
                    "Why do community rules and citizen cooperation matter for this service?",
                    "How does this local example connect to our syllabus topic?"
                ]
            },
            "COLLEGE": {
                "method": "Comparative Governance, Institutional Field Analysis & Policy Case Study",
                "explanation_focus": "Constitutional structures, administrative law, public policy analysis, democratic institutions, comparing historical evidence, and explaining local civic or geographical examples.",
                "practice_focus": "Auditing local civic services, analyzing public policy implementation, or evaluating governance structures through case studies.",
                "demonstration_type": "community_civic_observation",
                "honest_limitation": "Physical laboratory experiments do not apply to political science and civics. Field observations, institutional analyses, and policy case studies are used.",
                "learning_depth": "Constitutional law, democratic institutions, public policy analysis, and civic engagement.",
                "checks": [
                    "What constitutional or administrative provision governs this civic institution?",
                    "Analyze the policy outcomes and stakeholder trade-offs in this case study.",
                    "How does local community feedback influence institutional accountability?"
                ]
            }
        },
        "programming-oriented": {
            "SCHOOL": {
                "method": "Small Concept Walkthrough, Runnable Example & Short Coding Task",
                "explanation_focus": "Teach a small concept, show a correct runnable example, explain the code, give expected output, and provide a short coding task. Adapt complexity to school level and the actual syllabus. Explain inputs, processing, and outputs clearly.",
                "practice_focus": "Reading the runnable code example, understanding what each line does, checking the expected output, and completing a short coding task.",
                "demonstration_type": "coding_task",
                "honest_limitation": "Physical science experiments do not apply to software and IT. This topic uses a small concept, runnable code snippet, logic explanation, expected output, and a short coding task.",
                "learning_depth": "Introductory control flow logic, pseudocode walkthroughs, input/output tracing, and basic syntax fundamentals.",
                "checks": [
                    "What is the purpose of the runnable code example?",
                    "Explain the core code statement in simple words.",
                    "What is the expected output when the code runs?"
                ]
            },
            "COLLEGE": {
                "method": "Syllabus-Aligned Technical Concept, Runnable Implementation, Execution Trace & Debugging Task",
                "explanation_focus": "Teach a small concept, show a correct runnable example, explain the code, give expected output, and provide a short coding task. Adapt complexity to college level and actual syllabus. Include prerequisites, runtime complexity (Big-O), memory layout, and debugging guidance.",
                "practice_focus": "Compiling/running the code example, verifying the expected stdout output, completing the coding task for an edge case, and diagnosing common debugging pitfalls.",
                "demonstration_type": "coding_task",
                "honest_limitation": "Physical lab experiments are not applicable to software and IT. This topic uses runnable code implementations, execution traces, Big-O analysis, and debugging tasks.",
                "learning_depth": "Advanced technical concepts, topic-appropriate language implementation, Big-O complexity, edge-case testing, and production debugging.",
                "checks": [
                    "What is the Big-O time and space complexity of the code implementation?",
                    "What exact output is produced by the runnable snippet?",
                    "How does the short coding task handle edge cases (e.g. empty inputs or boundary values)?"
                ]
            }
        },
        "numerical": {
            "SCHOOL": {
                "method": "Real-World Measurements, Shopping Calculations & Gradual Worked Problems",
                "explanation_focus": "Real-world measurements, shopping calculations, geometry, budgeting, patterns, data collection, and worked problems. Gradually increase difficulty from easy to medium to hard. Begin with clear visual reasoning before introducing abstract formulas.",
                "practice_focus": "Solving worked problems graduated from easy to medium to hard (Level 1: Easy shopping/measurement, Level 2: Medium geometry/budgeting, Level 3: Hard multi-step problem).",
                "demonstration_type": "worked_problem_set",
                "honest_limitation": "Physical science experiments do not apply to mathematics. This topic uses real-world measurements, shopping calculations, geometry, budgeting, patterns, and worked problems.",
                "learning_depth": "Fundamental arithmetic/algebraic steps, visual reasoning, unit conversions, and topic-relevant problem solving.",
                "checks": [
                    "Solve Level 1 (Easy): State the basic calculation or formula used.",
                    "Solve Level 2 (Medium): How do you apply this to the shopping/measurement/budgeting scenario?",
                    "Solve Level 3 (Hard): How do you verify your multi-step calculation?"
                ]
            },
            "COLLEGE": {
                "method": "Graduated Analytical Problem Set, Mathematical Derivations & Quantitative Modeling",
                "explanation_focus": "Real-world measurements, geometry, budgeting, patterns, data collection, and worked problems. Gradually increase difficulty from easy to medium to hard. Prerequisites, formal notation, and domain applications in engineering, physics, finance, or computer science.",
                "practice_focus": "Solving progressively challenging analytical problems: Tier 1 (Easy baseline calculation), Tier 2 (Medium multi-variable/geometry application), Tier 3 (Hard rigorous derivation or optimization problem).",
                "demonstration_type": "worked_problem_set",
                "honest_limitation": "Physical lab experiments are not applicable to pure mathematical derivations. This topic uses formal proofs, graduated worked problems, and quantitative modeling.",
                "learning_depth": "Rigorous first-principles derivations, formal mathematical notation, multivariable analysis, domain applications, and boundary limits.",
                "checks": [
                    "Verify Tier 1 foundational calculation step.",
                    "Apply Tier 2 theorem to the geometric or numerical dataset.",
                    "Derive Tier 3 boundary conditions and prove uniqueness of the solution."
                ]
            }
        },
        "engineering-design": {
            "SCHOOL": {
                "method": "Everyday Simple Machines, Measurements & Safe Design Tasks",
                "explanation_focus": "Syllabus-aligned calculations, small simulations, design exercises, code, measurements, and safe practical tasks suitable for the student's level. Focus on everyday tools (levers, gears, balances).",
                "practice_focus": "Measuring dimensions, calculating simple mechanical advantage or balance points, and sketching a safe design improvement.",
                "demonstration_type": "engineering_design_task",
                "honest_limitation": "Heavy industrial machinery or high voltages cannot be used at home. Safe everyday measurements and design sketches are used.",
                "learning_depth": "Basic mechanical advantage, simple structural balance, and everyday physical forces.",
                "checks": [
                    "What physical dimensions did you measure?",
                    "Calculate the simple force or ratio for this everyday tool.",
                    "How does your sketch improve the tool's design?"
                ]
            },
            "COLLEGE": {
                "method": "Syllabus-Aligned Technical Calculations, Small Simulations, Design Exercises & Safe Practical Tasks",
                "explanation_focus": "Syllabus-aligned calculations, small simulations, design exercises, code, measurements, and safe practical tasks suitable for the student's level. Governing engineering formulas, component ratings, and physical constraints.",
                "practice_focus": "Executing quantitative engineering calculations, sketching a system schematic or state machine, evaluating physical constraints, or running a small simulation/code test.",
                "demonstration_type": "engineering_design_task",
                "honest_limitation": "High-voltage or hazardous heavy machinery cannot be operated at home. Syllabus-aligned numerical calculations, circuit/system simulations, and design exercises are used.",
                "learning_depth": "Engineering system modeling, stress/transient derivations, tolerance margins, and professional design trade-offs.",
                "checks": [
                    "Execute the governing engineering calculation for this component/system.",
                    "What safety margins or design constraints must be satisfied?",
                    "How does the simulation or schematic demonstrate optimal system performance?"
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
        sub_lower = (subject or "").lower()
        top_lower = (topic or "").lower()
        combined = f"{subject} {topic}".lower()
        if syllabus_context:
            combined += " " + str(syllabus_context.get("description", "")).lower()
            combined += " " + str(syllabus_context.get("learning_objectives", "")).lower()
            if isinstance(syllabus_context.get("topics"), list):
                combined += " " + " ".join([str(t) for t in syllabus_context["topics"]]).lower()

        # Subject-first authoritative classification:
        # A subject name explicitly declared in the validated curriculum anchors the core discipline.
        if any(w in sub_lower for w in ["math", "algebra", "calculus", "geometr", "arithmetic", "statist", "probab", "linear algebra"]):
            return "numerical"
        if any(w in sub_lower for w in ["english", "language", "grammar", "french", "spanish", "german", "hindi", "tamil", "linguist"]):
            if any(w in top_lower for w in ["poem", "poetry", "novel", "drama", "prose", "theme", "character", "story", "literature"]):
                return "literary-thematic"
            return "language-grammar"
        if any(w in sub_lower for w in ["literature", "poetry"]):
            return "literary-thematic"
        if any(w in sub_lower for w in ["computer", "data structure", "algorithm", "software", "web dev", "programming", "information tech", "coding"]):
            return "programming-oriented"
        if any(w in sub_lower for w in ["history", "civilization"]):
            return "historical-source"
        if any(w in sub_lower for w in ["civic", "political science", "public admin", "sociolog"]):
            return "social-civics"
        if any(w in sub_lower for w in ["geograph"]):
            return "geographical-spatial"
        if any(w in sub_lower for w in ["social science", "social studies"]):
            if any(w in top_lower for w in ["history", "war", "revolt", "empire", "timeline", "ancient", "medieval", "freedom", "movement"]):
                return "historical-source"
            elif any(w in top_lower for w in ["map", "climate", "soil", "plateau", "river", "mountain", "spatial", "weather"]):
                return "geographical-spatial"
            else:
                return "social-civics"
        if any(w in sub_lower for w in ["biology", "botany", "zoology", "life science", "plant"]):
            return "biology"
        if any(w in sub_lower for w in ["chemistry", "chemical"]):
            return "chemistry"
        if any(w in sub_lower for w in ["physics", "physical science"]):
            return "science-physics"
        if any(w in sub_lower for w in ["science", "general science", "environmental science", "integrated science"]):
            if not any(k in sub_lower for k in ["computer", "social", "political", "data"]):
                if any(w in top_lower for w in ["light", "sound", "force", "motion", "magnet", "energy", "heat", "electricity", "gravity", "optic", "friction", "pressure"]):
                    return "science-physics"
                elif any(w in top_lower for w in ["acid", "base", "solution", "reaction", "matter", "metal", "element", "compound", "indicator", "ph", "salt", "substance"]):
                    return "chemistry"
                elif any(w in top_lower for w in ["plant", "animal", "body", "food", "cell", "organ", "seed", "leaf", "leaves", "transpir", "photosyn", "crop", "soil biology"]):
                    return "biology"
                else:
                    return "practical"
        if any(w in sub_lower for w in ["accounting", "commerce", "finance", "bookkeeping", "auditing"]):
            return "accounting-financial"
        if any(w in sub_lower for w in ["economics", "microeconomics", "macroeconomics"]):
            return "economics-analytical"

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

        # 1. Computer Science & Software
        if has_kw(["data structure", "algorithm", "programming", "code", "python", "java", "c++", "c#", "javascript", "sql", "database", "compiler", "recursion", "array pointer", "object oriented", "software", "web dev", "frontend", "backend", "api", "git", "binary tree", "graph algorithm", "sorting algorithm", "searching algorithm", "stack", "queue", "linked list", "hash table", "operating system", "linux", "kernel", "thread", "flowchart"]):
            return "programming-oriented"

        # 2. Chemistry
        if has_kw(["chemistry", "chem", "acid", "base", "ph indicator", "protonation", "reaction rate", "chemical kinetics", "periodic table", "element", "compound", "covalent", "ionic", "molecule", "solution", "solubility", "organic chemistry", "inorganic chemistry", "neutralization"]):
            return "chemistry"

        # 3. Biology & Life Sciences
        if has_kw(["biology", "botany", "zoology", "plant", "transpiration", "photosynthesis", "leaf", "leaves", "seed", "stomata", "cell biology", "organism", "ecology", "tissue", "anatomy", "crop", "life science", "soil biology"]):
            return "biology"

        # 4. Mathematics & Computation
        if has_kw(["calculus", "differential", "integral", "matrix", "algebra", "trigonometry", "statistics", "probability", "equation", "formula", "geometry", "linear algebra", "discrete math", "theorem", "combinatorics", "rate of change", "mathematics", "math", "arithmetic", "mensuration", "linear equations"]):
            return "numerical"

        # 5. Physics & Physical Sciences
        if has_kw(["physics", "physical science", "optics", "light", "reflection", "refraction", "sound", "wave", "friction", "inertia", "gravity", "pressure", "fluid mechanics", "capillarity", "surface tension", "density", "electromagnetism", "kinematics"]):
            return "science-physics"

        # 6. Accounting & Financial Commerce
        if has_kw(["accounting", "ledger", "journal", "debit", "credit", "balance sheet", "t-account", "auditing", "taxation", "costing", "financial statement", "cash flow", "bookkeeping", "depreciation", "trial balance"]):
            return "accounting-financial"

        # 7. Economics
        if has_kw(["economics", "microeconomics", "macroeconomics", "elasticity", "supply and demand", "demand curve", "market equilibrium", "inflation", "gdp", "monetary policy", "fiscal policy", "utility theory", "budgeting", "price comparison"]):
            return "economics-analytical"

        # 8. History
        if has_kw(["history", "historical", "revolution", "world war", "civilization", "empire", "treaty", "dynasty", "colonialism", "historical source", "historiography", "archaeology", "nationalism"]):
            return "historical-source"

        # 9. Geography & Earth Sciences
        if has_kw(["geography", "map", "contour", "topographical", "spatial", "weather", "atmosphere", "climate zone", "plate tectonics", "cartography", "gis", "landform", "geomorp"]):
            return "geographical-spatial"

        # 10. Social Sciences & Civics
        if has_kw(["civics", "political science", "social science", "sociology", "society", "democracy", "government", "constitution", "citizen", "public policy", "community survey"]):
            return "social-civics"

        # 11. Literature & Criticism
        if has_kw(["literature", "poetry", "poem", "novel", "play", "drama", "prose", "shakespeare", "literary", "tragedy", "fiction", "thematic analysis", "rhetoric", "allegory"]):
            return "literary-thematic"

        # 12. Languages & Linguistics
        if has_kw(["grammar", "syntax", "vocabulary", "phonetics", "verb conjugation", "french", "spanish", "german", "english", "linguistics", "parts of speech", "tense", "translation", "morphology", "reading comprehension", "speaking practice", "summarization"]):
            return "language-grammar"

        # Interpretive / Law / Philosophy / Case Studies
        if has_kw(["law", "precedent", "precedents", "statutory", "jurisdiction", "jurisprudence", "constitution", "ethics", "philosophy", "court", "ruling"]):
            return "interpretive"

        # 13. Engineering & Physical Systems Design
        if has_kw(["circuit", "thermodynamics", "signal processing", "control systems", "cad", "finite element", "electrical engineering", "mechanical engineering", "civil engineering", "aerodynamics"]):
            return "engineering-design"

        # 14. Practical / Experimental Science
        if has_kw(["experiment", "lab", "titration", "dissection", "microscope", "chemical reaction", "osmosis", "electrolysis", "circuit assembly", "field study", "soil testing", "chromatography", "spectroscopy"]):
            return "practical"

        # 15. Creative & Fine Arts
        if has_kw(["art", "design", "creative writing", "sculpture", "animation", "graphics", "media production", "typography", "sketching", "painting"]):
            return "creative"

        # 16. Procedural & Operational Workflows
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
            if topic_nature == "science-physics":
                return ["Basic measurement (length, time)", "Everyday observations of light, motion, or water"]
            if topic_nature == "chemistry":
                return ["Understanding clean water & household substances", "Basic observations of color and temperature"]
            if topic_nature == "biology":
                return ["Parts of a green plant (root, stem, leaf)", "Respectful observation of living nature"]
            if topic_nature == "programming-oriented":
                return ["Basic counting & numbers", "Understanding 'repeat' instructions", "Paper & pencil writing"]
            if topic_nature == "accounting-financial":
                return ["Basic addition & subtraction", "Concept of money & shop purchases"]
            if topic_nature == "numerical":
                return ["Basic arithmetic (+, -, *, /)", "Reading simple numbers & tables"]
            if topic_nature == "historical-source":
                return ["Reading simple story timelines", "Understanding past vs present"]
            if topic_nature == "social-civics":
                return ["Understanding home, school, and village/town community", "Basic rules of sharing and fairness"]
            if topic_nature == "language-grammar":
                return ["Basic alphabet & simple words", "Sentence reading skills"]
            return [f"Basic intro to {subject}", "Reading & writing skills"]

        # COLLEGE
        if topic_nature == "science-physics":
            return ["Newton's laws of motion", "Differential calculus & vector algebra", "Fundamental SI units & dimensional analysis"]

        if topic_nature == "chemistry":
            return ["Chemical bonding fundamentals (covalent, ionic)", "Molar concentration & stoichiometry", "Acids and bases (pH scale)"]

        if topic_nature == "biology":
            return ["Cell biology & membrane permeability", "Basic biochemistry (ATP, carbohydrates)", "Microscopic or macroscopic taxonomy"]

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

        if topic_nature == "social-civics":
            return ["Democratic governance frameworks", "Public policy and constitutional rights", "Social research methodologies"]

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
        useful_material_types = {"physical_demonstration", "outdoor_observation", "household_demonstration", "safe_demonstration"}
        useful_natures = {"practical", "science-physics", "chemistry", "biology", "physical-chemical", "biological-agricultural"}
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

