export const classTrend = [
  { label: 'W1', value: 71 },
  { label: 'W2', value: 73 },
  { label: 'W3', value: 72 },
  { label: 'W4', value: 75 },
  { label: 'W5', value: 74 },
  { label: 'W6', value: 77 },
  { label: 'W7', value: 76 },
  { label: 'W8', value: 78.4 },
]

export const studentTrend = [
  { label: 'W1', value: 72 },
  { label: 'W2', value: 74 },
  { label: 'W3', value: 75 },
  { label: 'W4', value: 77 },
  { label: 'W5', value: 79 },
  { label: 'W6', value: 80 },
  { label: 'W7', value: 81 },
  { label: 'W8', value: 82.5 },
]

export const subjectPerformance = [
  { label: 'Physics', value: 76 },
  { label: 'Chemistry', value: 81 },
  { label: 'Math', value: 79 },
  { label: 'Biology', value: 84 },
]

export const studentSubjectPerformance = [
  { label: 'Physics', value: 78 },
  { label: 'Chemistry', value: 85 },
  { label: 'Math', value: 91 },
]

export const recentEvaluationsTeacher = [
  { student: 'Arun Kumar', subject: 'Physics', assessment: 'Mid-Term Examination', score: 85, status: 'success', when: '2 hours ago' },
  { student: 'Priya Sharma', subject: 'Chemistry', assessment: 'Unit Test 3', score: 91, status: 'success', when: 'Yesterday' },
  { student: 'Rohan Das', subject: 'Mathematics', assessment: 'Weekly Quiz', score: 64, status: 'warning', when: 'Yesterday' },
  { student: 'Sneha Iyer', subject: 'Physics', assessment: 'Mid-Term Examination', score: 88, status: 'success', when: '2 days ago' },
]

export const recentEvaluationsStudent = [
  { student: '—', subject: 'Physics', assessment: 'Mid-Term Examination', score: 85, status: 'success', when: '2 days ago' },
  { student: '—', subject: 'Mathematics', assessment: 'Weekly Quiz', score: 91, status: 'success', when: '5 days ago' },
  { student: '—', subject: 'Chemistry', assessment: 'Unit Test 3', score: 68, status: 'warning', when: '1 week ago' },
]

export const studentsNeedingSupport = [
  { initials: 'RD', name: 'Rohan Das', note: 'Mathematics — down 12% this term' },
  { initials: 'KV', name: 'Kavya Venkat', note: 'Physics — 3 missed evaluations' },
  { initials: 'AM', name: 'Aman Mehta', note: 'Chemistry — consistently below 55%' },
]

export const recentActivity = [
  { text: 'Plagiarism check completed for Class 12-B, Chemistry', when: '35 minutes ago' },
  { text: 'Report generated for Section A — Mid-Term summary', when: '3 hours ago' },
  { text: '18 answer scripts uploaded for Physics Mid-Term', when: 'Yesterday, 4:12 PM' },
]

export const nextSteps = [
  { title: 'Review Electromagnetic Induction', subject: 'Physics · recommended' },
  { title: 'Practice test: Organic reactions', subject: 'Chemistry' },
  { title: 'Spaced repetition: Calculus formulas', subject: 'Mathematics' },
]

export const allStudents = [
  { name: 'Priya Sharma', section: '12-A', average: 91, trend: 4.2, evaluations: 12, status: 'On track' },
  { name: 'Arun Kumar', section: '12-A', average: 85, trend: 1.8, evaluations: 11, status: 'On track' },
  { name: 'Sneha Iyer', section: '12-A', average: 88, trend: 2.5, evaluations: 10, status: 'On track' },
  { name: 'Rohan Das', section: '12-B', average: 64, trend: -12.1, evaluations: 9, status: 'Needs support' },
  { name: 'Kavya Venkat', section: '12-C', average: 58, trend: -5.4, evaluations: 7, status: 'At risk' },
]

export const reports = [
  { title: 'Mid-Term summary — Section A', scope: '32 students', when: '3 hours ago' },
  { title: 'Physics — Unit 4 breakdown', scope: '28 students', when: 'Yesterday' },
  { title: 'Chemistry — Integrity review', scope: '40 students', when: '2 days ago' },
]

export const plagiarismMatches = [
  { pair: 'Priya Sharma ↔ Kavya Venkat', context: 'Chemistry — Unit Test 3, Question 4', similarity: 94, level: 'error' },
  { pair: 'Rohan Das ↔ Aman Mehta', context: 'Chemistry — Unit Test 3, Question 2', similarity: 71, level: 'warning' },
]

export const weakTopics = [
  { title: 'Electromagnetic Induction', subject: 'Physics', mastery: 52 },
  { title: 'Organic Reaction Mechanisms', subject: 'Chemistry', mastery: 64 },
  { title: 'Integration by Parts', subject: 'Mathematics', mastery: 88 },
]

export const techniques = [
  { num: '01', title: 'Active Recall', desc: 'Retrieve information from memory instead of rereading it.', tags: ['Definitions', 'Formulas', 'Concepts'] },
  { num: '02', title: 'Spaced Repetition', desc: 'Review material at increasing intervals to strengthen memory.', tags: ['Vocabulary', 'Formulas', 'Dates'] },
  { num: '03', title: 'Practice Testing', desc: 'Simulate exam conditions to surface gaps early.', tags: ['Mock Tests', 'Timed Practice'] },
  { num: '04', title: 'Interleaving', desc: 'Mix related topics in one session instead of blocking by subject.', tags: ['Problem Sets', 'Mixed Review'] },
  { num: '05', title: 'Elaborative Learning', desc: 'Explain concepts in your own words and connect them to what you know.', tags: ['Concepts', 'Essays'] },
]

export const academicMemory = [
  { year: '2026', month: 'September', subject: 'Physics — Mid-Term Examination', note: 'Improved on Mechanics, slipped slightly on Electromagnetism.', score: 82 },
  { year: '2026', month: 'August', subject: 'Chemistry — Unit Test 3', note: 'Strong grasp of reaction mechanisms.', score: 89 },
  { year: '2026', month: 'July', subject: 'Mathematics — Weekly Quiz', note: 'Struggled with integration techniques.', score: 76 },
]

export const evalQuestions = [
  {
    q: 'Q1',
    question: "State Newton's second law of motion.",
    answer: 'Force equals mass times acceleration, F = ma.',
    max: 10,
    marks: 10,
    status: 'Correct',
    feedback: 'Complete and accurate. You stated the relationship and defined each variable clearly.',
    improve: 'None needed.',
  },
  {
    q: 'Q2',
    question: 'Explain the concept of electromagnetic induction.',
    answer: 'It happens when a magnetic field changes near a conductor.',
    max: 20,
    marks: 11,
    status: 'Partially Correct',
    feedback: 'You identified the main idea correctly, but the explanation misses the relationship between changing flux and induced EMF.',
    improve: "State Faraday's Law first, then explain how changing flux induces a current.",
  },
  {
    q: 'Q3',
    question: 'Derive the equation of motion for uniformly accelerated bodies.',
    answer: 'v = u + at, derived using calculus.',
    max: 20,
    marks: 18,
    status: 'Correct',
    feedback: 'Clear derivation with correct steps and units throughout.',
    improve: 'Show the intermediate integration step for full marks.',
  },
  {
    q: 'Q4',
    question: 'Describe the working of a simple AC generator.',
    answer: 'A coil rotates in a magnetic field, inducing an alternating current.',
    max: 25,
    marks: 14,
    status: 'Needs Improvement',
    feedback: 'The core idea is present but the answer lacks detail on slip rings and brushes.',
    improve: 'Include the role of slip rings in maintaining continuous contact.',
  },
  {
    q: 'Q5',
    question: 'Calculate the induced EMF given the rate of change of flux.',
    answer: 'EMF = -dΦ/dt, calculated as 4.2V.',
    max: 25,
    marks: 22,
    status: 'Correct',
    feedback: 'Correct formula and calculation, with proper sign convention.',
    improve: 'None needed.',
  },
]

export const chatReplies = {
  'Explain this topic':
    "Electromagnetic induction happens when a changing magnetic field creates a voltage in a nearby conductor. Faraday's Law says the induced EMF equals the rate of change of magnetic flux. Lenz's Law tells you the direction — the induced current always opposes the change that created it.",
  'Help me prepare for tomorrow':
    "For tomorrow, focus on two things: Faraday's Law and Lenz's Law. Work through 3-4 numericals on induced EMF, and review the AC generator diagram — that came up in your last two evaluations.",
  'Quiz me on this chapter':
    'Question 1: A coil of 200 turns experiences a flux change of 0.02 Wb in 0.5 seconds. What is the induced EMF?',
  'Why did I lose marks here?':
    "On your Mid-Term, Question 4 asked about the AC generator. You explained the coil rotation correctly but left out the role of slip rings and brushes in maintaining contact — that's where the 11 marks went.",
  'Create a revision plan':
    "Here's a 3-day plan: Day 1 — Faraday's and Lenz's Laws with 5 numericals. Day 2 — AC generators and motors, diagram practice. Day 3 — Full practice test under timed conditions.",
}

// ─── Knowledge Transfer Challenge ──────────────────────────────────────────
export const transferChallengeRounds = [
  {
    round: 1,
    concept: "Newton's Second Law",
    subject: 'Physics',
    scenario:
      'A firefighter pushes a 60 kg door off its hinges with a force of 480 N. Another firefighter applies 120 N to help. Ignoring friction, what is the door\'s acceleration?',
    hint: 'Think about net force and how it relates to acceleration.',
    modelAnswer:
      'Net force = 480 + 120 = 600 N. Using F = ma → a = 600 / 60 = 10 m/s². The door accelerates at 10 m/s².',
    conceptsApplied: ["Newton's 2nd Law (F=ma)", 'Net force addition', 'Units of acceleration'],
    transferScore: 88,
  },
  {
    round: 2,
    concept: 'Conservation of Energy',
    subject: 'Physics',
    scenario:
      'A roller-coaster car starts from rest at the top of a 40 m hill. Ignoring air resistance, what is its speed at the bottom?',
    hint: 'Potential energy at the top converts to kinetic energy at the bottom.',
    modelAnswer:
      'mgh = ½mv² → v = √(2gh) = √(2 × 10 × 40) = √800 ≈ 28.3 m/s.',
    conceptsApplied: ['Gravitational PE = mgh', 'Kinetic Energy = ½mv²', 'Conservation of mechanical energy'],
    transferScore: 74,
  },
  {
    round: 3,
    concept: 'Faraday\'s Law of Induction',
    subject: 'Physics',
    scenario:
      'A generator at a wind farm has a coil of 300 turns. The magnetic flux through the coil changes from 0.05 Wb to 0.02 Wb in 0.1 s. What EMF is induced?',
    hint: 'EMF is proportional to the number of turns and the rate of flux change.',
    modelAnswer:
      'EMF = −N × (ΔΦ/Δt) = −300 × (0.02 − 0.05)/0.1 = −300 × (−0.3) = 90 V.',
    conceptsApplied: ["Faraday's Law", 'Rate of flux change', 'Sign convention (Lenz)'],
    transferScore: 61,
  },
  {
    round: 4,
    concept: 'Molarity and Dilution',
    subject: 'Chemistry',
    scenario:
      'A nurse needs to prepare 250 mL of a 0.5 M saline solution. She has a 2 M stock solution. How much stock solution does she need?',
    hint: 'Use the dilution equation C₁V₁ = C₂V₂.',
    modelAnswer:
      'C₁V₁ = C₂V₂ → 2 × V₁ = 0.5 × 250 → V₁ = 62.5 mL. She needs 62.5 mL of the stock solution.',
    conceptsApplied: ['Dilution equation C₁V₁ = C₂V₂', 'Molarity definition', 'Volume unit conversions'],
    transferScore: 79,
  },
  {
    round: 5,
    concept: 'Integration (Area under a curve)',
    subject: 'Mathematics',
    scenario:
      'A car\'s velocity is modelled by v(t) = 3t² + 2t for 0 ≤ t ≤ 4 seconds. How far does the car travel in those 4 seconds?',
    hint: 'Distance is the integral of velocity over time.',
    modelAnswer:
      '∫₀⁴ (3t² + 2t) dt = [t³ + t²]₀⁴ = (64 + 16) − 0 = 80 metres.',
    conceptsApplied: ['Definite integral as area', 'Polynomial integration rules', 'Distance–velocity relationship'],
    transferScore: 83,
  },
]

// ─── Classroom Misconception Map ───────────────────────────────────────────
export const misconceptionData = {
  Physics: [
    {
      concept: 'Electromagnetic Induction',
      chapter: 'Chapter 6',
      studentsAffected: 18,
      totalStudents: 32,
      severity: 'high',
      avgMarkLost: 8.4,
      commonErrors: [
        { error: 'Stating EMF = flux instead of rate of change of flux', frequency: 11 },
        { error: 'Ignoring the negative sign (Lenz\'s Law direction)', frequency: 7 },
        { error: 'Confusing turns (N) as additive, not multiplicative', frequency: 5 },
      ],
      correctExplanation:
        "Faraday's Law states EMF = −N(ΔΦ/Δt). The rate of change of flux — not flux itself — induces the EMF. Lenz's Law gives the direction via the negative sign.",
      interventionSuggested: 'Demonstrate with a moving magnet + galvanometer; show slow vs fast motion differences.',
    },
    {
      concept: 'Newton\'s Third Law Pairs',
      chapter: 'Chapter 3',
      studentsAffected: 12,
      totalStudents: 32,
      severity: 'medium',
      avgMarkLost: 4.1,
      commonErrors: [
        { error: 'Applying action-reaction forces on the same body', frequency: 9 },
        { error: 'Claiming forces cancel each other out on a system', frequency: 6 },
      ],
      correctExplanation:
        "Action-reaction force pairs act on *different* bodies, never the same object. They don't cancel because cancellation only occurs when two forces act on the same body.",
      interventionSuggested: 'Free-body diagram workshop: draw all forces on each object separately.',
    },
    {
      concept: 'Refraction at Curved Surfaces',
      chapter: 'Chapter 9',
      studentsAffected: 6,
      totalStudents: 32,
      severity: 'low',
      avgMarkLost: 2.0,
      commonErrors: [
        { error: 'Using mirror formula instead of lens formula', frequency: 6 },
      ],
      correctExplanation:
        'Lenses use the lens formula (1/v − 1/u = 1/f) where sign convention differs from mirrors. Power = 1/f in dioptres.',
      interventionSuggested: 'Side-by-side comparison table of mirror vs lens formulae.',
    },
    {
      concept: 'Work-Energy Theorem',
      chapter: 'Chapter 4',
      studentsAffected: 9,
      totalStudents: 32,
      severity: 'medium',
      avgMarkLost: 5.2,
      commonErrors: [
        { error: 'Confusing work done by net force vs individual forces', frequency: 7 },
        { error: 'Not accounting for negative work done by friction', frequency: 5 },
      ],
      correctExplanation:
        'The Work-Energy Theorem states the net work done on an object equals its change in kinetic energy. Work by friction is negative, reducing KE.',
      interventionSuggested: 'Inclined plane problems with friction — calculate work done by each force separately.',
    },
    {
      concept: 'Kirchhoff\'s Laws',
      chapter: 'Chapter 11',
      studentsAffected: 4,
      totalStudents: 32,
      severity: 'low',
      avgMarkLost: 1.8,
      commonErrors: [
        { error: 'Sign error in KVL loop equations', frequency: 4 },
      ],
      correctExplanation:
        'KVL: sum of all voltages around any closed loop = 0. Choose a consistent direction. EMFs in the direction of traversal are positive; drops are negative.',
      interventionSuggested: 'Circuit loop practice with colour-coded traversal directions.',
    },
  ],
  Chemistry: [
    {
      concept: 'Reaction Mechanisms (Nucleophilic Substitution)',
      chapter: 'Chapter 7',
      studentsAffected: 21,
      totalStudents: 32,
      severity: 'high',
      avgMarkLost: 9.1,
      commonErrors: [
        { error: 'Confusing SN1 and SN2 conditions (substrate, solvent)', frequency: 14 },
        { error: 'Drawing arrow-pushing mechanism incorrectly', frequency: 10 },
      ],
      correctExplanation:
        'SN2: one step, backside attack, inversion of configuration, primary substrates. SN1: two steps, carbocation intermediate, secondary/tertiary substrates, racemisation.',
      interventionSuggested: 'Flowchart decision-tree for SN1 vs SN2 identification.',
    },
    {
      concept: 'Buffer Solutions',
      chapter: 'Chapter 5',
      studentsAffected: 13,
      totalStudents: 32,
      severity: 'medium',
      avgMarkLost: 5.7,
      commonErrors: [
        { error: 'Not using Henderson–Hasselbalch equation correctly', frequency: 9 },
        { error: 'Confusing weak acid + salt vs strong acid system', frequency: 7 },
      ],
      correctExplanation:
        'pH = pKa + log([A⁻]/[HA]). Buffers work only with a weak acid and its conjugate base (or weak base + conjugate acid).',
      interventionSuggested: 'Titration curve analysis — identify buffer regions visually.',
    },
  ],
  Mathematics: [
    {
      concept: 'Integration by Parts',
      chapter: 'Chapter 8',
      studentsAffected: 15,
      totalStudents: 32,
      severity: 'high',
      avgMarkLost: 7.3,
      commonErrors: [
        { error: 'Wrong choice of u and dv (LIATE rule ignored)', frequency: 11 },
        { error: 'Forgetting the constant of integration', frequency: 8 },
        { error: 'Sign errors in repeated integration', frequency: 6 },
      ],
      correctExplanation:
        '∫u dv = uv − ∫v du. Use LIATE to choose u: Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential. Always add C for indefinite integrals.',
      interventionSuggested: 'LIATE poster + 6 graded practice problems with worked solutions.',
    },
    {
      concept: 'Limits and Continuity',
      chapter: 'Chapter 3',
      studentsAffected: 8,
      totalStudents: 32,
      severity: 'medium',
      avgMarkLost: 3.5,
      commonErrors: [
        { error: 'Confusing limit existence with function value at the point', frequency: 8 },
      ],
      correctExplanation:
        'A limit exists if LHL = RHL, regardless of f(a). A function is continuous at a if lim f(x) = f(a).',
      interventionSuggested: 'Graphical exploration of piecewise functions to visualise discontinuities.',
    },
  ],
}

export const misconceptionInterventions = [
  { concept: 'Electromagnetic Induction', subject: 'Physics', impact: 'High · 18 students', priority: 1 },
  { concept: 'Nucleophilic Substitution', subject: 'Chemistry', impact: 'High · 21 students', priority: 2 },
  { concept: 'Integration by Parts', subject: 'Mathematics', impact: 'High · 15 students', priority: 3 },
  { concept: 'Buffer Solutions', subject: 'Chemistry', impact: 'Medium · 13 students', priority: 4 },
]

// ─── Knowledge-to-Reality Lab ───────────────────────────────────────────────
export const realityScenarios = [
  {
    id: 1,
    title: 'Why does a microwave heat food but not a plastic container?',
    context: 'Everyday Kitchen',
    subject: 'Physics / Chemistry',
    difficulty: 'Medium',
    image: 'kitchen',
    expectedConcepts: [
      { concept: 'Polar molecules and dipole rotation', required: true },
      { concept: 'Electromagnetic radiation (microwave frequency)', required: true },
      { concept: 'Dielectric heating mechanism', required: true },
      { concept: 'Thermal conductivity differences', required: false },
      { concept: 'Resonance frequency of water molecules', required: false },
    ],
    modelAnswer:
      'Microwaves emit electromagnetic radiation at ~2.45 GHz, matching the resonance frequency of water molecules (polar molecules). The oscillating electric field causes water dipoles to rotate rapidly, generating heat through friction. Plastic containers lack polar molecules that rotate at this frequency, so they absorb little energy and stay cool.',
    qualityScore: null,
  },
  {
    id: 2,
    title: 'Why does a sports car stop faster than a truck even with the same brakes?',
    context: 'Road Safety',
    subject: 'Physics',
    difficulty: 'Easy',
    image: 'road',
    expectedConcepts: [
      { concept: "Newton's Second Law (F = ma)", required: true },
      { concept: 'Inertia and mass', required: true },
      { concept: 'Braking force (friction)', required: true },
      { concept: 'Kinetic energy = ½mv²', required: false },
    ],
    modelAnswer:
      'With the same braking force F, deceleration a = F/m. The truck has much greater mass (m), so its deceleration is smaller (a = F/m). Greater mass also means greater kinetic energy (½mv²) to dissipate. The sports car has lower mass so the same force produces much higher deceleration.',
    qualityScore: null,
  },
  {
    id: 3,
    title: 'How does an antibiotic resistance crisis develop in a hospital ward?',
    context: 'Healthcare',
    subject: 'Biology / Chemistry',
    difficulty: 'Hard',
    image: 'hospital',
    expectedConcepts: [
      { concept: 'Natural selection and survival of the fittest', required: true },
      { concept: 'Genetic mutation and variation', required: true },
      { concept: 'Horizontal gene transfer (plasmids)', required: true },
      { concept: 'Selective pressure from antibiotics', required: true },
      { concept: 'Enzyme-mediated resistance (beta-lactamase)', required: false },
    ],
    modelAnswer:
      'Random mutations in bacterial populations create variants resistant to antibiotics. When antibiotics are applied, sensitive bacteria die (selective pressure) while resistant variants survive and reproduce — natural selection. Resistance genes on plasmids can be transferred horizontally between bacteria. Overuse of antibiotics intensifies selective pressure, accelerating the spread of resistance across the ward.',
    qualityScore: null,
  },
  {
    id: 4,
    title: 'Why do bridges sway and sometimes collapse during earthquakes?',
    context: 'Engineering',
    subject: 'Physics / Mathematics',
    difficulty: 'Hard',
    image: 'bridge',
    expectedConcepts: [
      { concept: 'Resonance and natural frequency', required: true },
      { concept: 'Forced oscillations', required: true },
      { concept: 'Amplitude amplification at resonance', required: true },
      { concept: 'Damping and energy dissipation', required: false },
      { concept: 'Wave propagation through solids', required: false },
    ],
    modelAnswer:
      'Every structure has a natural frequency of oscillation. Earthquake waves contain a spectrum of frequencies. If the seismic wave frequency matches the bridge\'s natural frequency, resonance occurs — the forced oscillation amplitude grows rapidly. Without sufficient damping to dissipate energy, oscillations can exceed structural limits, causing collapse. Modern bridges use dampers (e.g., tuned mass dampers) to shift or dampen resonance.',
    qualityScore: null,
  },
  {
    id: 5,
    title: 'Why does adding salt to icy roads melt the ice faster?',
    context: 'Winter Roads',
    subject: 'Chemistry',
    difficulty: 'Easy',
    image: 'road',
    expectedConcepts: [
      { concept: 'Freezing point depression (colligative property)', required: true },
      { concept: 'Ionic dissociation in solution', required: true },
      { concept: 'Lowering of vapour pressure', required: false },
      { concept: 'Molality and van\'t Hoff factor', required: false },
    ],
    modelAnswer:
      'Salt (NaCl) dissociates into Na⁺ and Cl⁻ ions when dissolved, increasing the number of solute particles. This causes freezing point depression — a colligative property. The freezing point of water drops below 0°C, so existing ice melts as the equilibrium shifts. The more ions in solution, the greater the depression (ΔTf = iKfm).',
    qualityScore: null,
  },
]

// ─── Study Techniques for Personal Trainer ───────────────────────────────────
export const studyTechniques = [
  {
    id: 'active-recall',
    name: 'Active Recall',
    emoji: '🧠',
    tagline: 'Test yourself — don\'t reread',
    description: 'Actively retrieve information from memory through self-testing. Research shows it is 2–3× more effective than rereading or highlighting.',
    evidence: 'Roediger & Karpicke (2006) — Science journal',
    chatIntro: 'Active Recall session started. I\'ll ask you questions on the concept you chose. Answer from memory — no looking at notes. Let\'s go!',
    promptSuggestions: ['Test me on this', 'I got that wrong — explain', 'Next question please', 'Give me a harder question'],
    color: 'var(--accent)',
    softColor: 'var(--accent-soft)',
  },
  {
    id: 'spaced-repetition',
    name: 'Spaced Repetition',
    emoji: '⏱',
    tagline: 'Review at increasing intervals',
    description: 'Study material at increasing time intervals based on the Ebbinghaus forgetting curve. Widely used in language learning and medical education.',
    evidence: 'Ebbinghaus (1885) — Forgetting Curve research',
    chatIntro: 'Spaced Repetition mode. We\'ll start with fundamentals, then build in complexity. I\'ll flag which items to review again in 1 day, 3 days, and 1 week.',
    promptSuggestions: ['Mark this as memorised', 'I need to review this again', 'Schedule my next review', 'Show me what to review today'],
    color: 'var(--warning)',
    softColor: 'var(--warning-soft)',
  },
  {
    id: 'interleaving',
    name: 'Interleaving',
    emoji: '🔀',
    tagline: 'Mix topics for deeper learning',
    description: 'Switch between related topics during a session instead of blocking by subject. Counterintuitive but research shows dramatically better long-term retention.',
    evidence: 'Kornell & Bjork (2008) — Psychological Science',
    chatIntro: 'Interleaving session. We\'ll mix related concepts together to build stronger connections. I\'ll switch topics every 2–3 questions — this feels harder but helps you remember far longer.',
    promptSuggestions: ['Switch to a related concept', 'How do these two concepts relate?', 'Give me a mixed question', 'Compare these ideas'],
    color: 'var(--success)',
    softColor: 'var(--success-soft)',
  },
  {
    id: 'elaborative-interrogation',
    name: 'Elaborative Interrogation',
    emoji: '✍️',
    tagline: 'Ask "why" until you truly understand',
    description: 'Generate detailed explanations for facts by repeatedly asking "why does this happen?" Forces deep processing and connects new knowledge to existing understanding.',
    evidence: 'Pressley et al. (1992) — Applied Cognitive Psychology',
    chatIntro: 'Elaborative Interrogation mode. I\'ll keep asking "why?" and "how?" until we reach the root understanding. No surface answers — we want the deep mechanism.',
    promptSuggestions: ['Why does this happen?', 'Give me a real-world analogy', 'Connect it to something I already know', 'What would change if this were different?'],
    color: 'var(--gold)',
    softColor: 'var(--gold-soft)',
  },
  {
    id: 'practice-testing',
    name: 'Practice Testing',
    emoji: '📝',
    tagline: 'Simulate exam conditions',
    description: 'Take timed mini-tests under exam-like conditions. The single strongest predictor of actual exam performance — more effective than any other study strategy.',
    evidence: 'Dunlosky et al. (2013) — Psychological Science in the Public Interest',
    chatIntro: 'Practice Test mode. I\'ll give you 5 questions, exam-style. You have 10 minutes. No hints. Attempt each fully before I reveal the answer. Starting now!',
    promptSuggestions: ['Start the timed test', 'Mark my answer', 'Show the solution', 'Give me the next question'],
    color: 'var(--error)',
    softColor: 'var(--error-soft)',
  },
]

// ─── Parent Agent — Activity Feed ─────────────────────────────────────────────
export const parentFeed = [
  { type: 'session', icon: '🧠', text: 'Completed Active Recall session on Electromagnetic Induction — 85% accuracy', when: 'Today, 8:14 AM', score: 85 },
  { type: 'challenge', icon: '⚡', text: 'Finished Knowledge Transfer Challenge (Physics) — Transfer Score: 83/100', when: 'Today, 7:30 AM', score: 83 },
  { type: 'lab', icon: '🔬', text: 'Reality Lab: Explained "Why does iron rust but gold doesn\'t?" — covered 4/5 concepts', when: 'Yesterday, 9:15 PM', score: 80 },
  { type: 'evaluation', icon: '📋', text: 'Evaluation returned: Chemistry Unit Test 3 — Score: 68/100', when: 'Yesterday, 4:00 PM', score: 68 },
  { type: 'session', icon: '🧠', text: 'Spaced Repetition session on Matrices & Determinants — 30 minutes', when: 'Yesterday, 7:00 AM', score: null },
  { type: 'challenge', icon: '⚡', text: 'Knowledge Transfer Challenge (Mathematics) — Transfer Score: 79/100', when: '2 days ago', score: 79 },
  { type: 'evaluation', icon: '📋', text: 'Physics Mid-Term Examination submitted for evaluation', when: '3 days ago', score: null },
  { type: 'lab', icon: '🔬', text: 'Reality Lab: "Why do bridges have expansion joints?" — Perfect concept coverage', when: '3 days ago', score: 100 },
  { type: 'session', icon: '🧠', text: 'Practice Testing on Waves & Oscillations — 4 of 5 questions correct', when: '4 days ago', score: 80 },
  { type: 'session', icon: '🧠', text: 'Elaborative Interrogation on Le Chatelier\'s Principle — 45 minutes deep dive', when: '5 days ago', score: null },
]

// ─── Parent Agent — Token Badges ──────────────────────────────────────────────
export const tokenBadges = [
  { id: 'study-star', name: 'Study Star', emoji: '⭐', description: 'Complete 5 study sessions', condition: '5 sessions', earned: true, earnedDate: '14 Sep 2026' },
  { id: 'seven-streak', name: '7-Day Streak', emoji: '🔥', description: 'Study 7 consecutive days', condition: '7 days in a row', earned: true, earnedDate: '12 Sep 2026' },
  { id: 'transfer-champion', name: 'Transfer Champion', emoji: '🎯', description: 'Achieve avg Transfer Score ≥ 80', condition: 'Avg score ≥ 80', earned: true, earnedDate: '10 Sep 2026' },
  { id: 'concept-explorer', name: 'Concept Explorer', emoji: '💡', description: 'Use 3 or more study techniques', condition: '3+ techniques used', earned: true, earnedDate: '8 Sep 2026' },
  { id: 'reality-master', name: 'Reality Master', emoji: '🔬', description: 'Complete 10 Reality Lab scenarios', condition: '10 scenarios done', earned: false, progress: 7, total: 10 },
  { id: 'perfect-recall', name: 'Perfect Recall', emoji: '🧠', description: 'Score 100% in an Active Recall session', condition: '100% in one session', earned: false, progress: 85, total: 100 },
  { id: 'challenge-ace', name: 'Challenge Ace', emoji: '🏆', description: 'Score 90+ in a Knowledge Transfer Challenge', condition: 'Score 90+ in one session', earned: false, progress: 88, total: 90 },
  { id: 'month-warrior', name: 'Month Warrior', emoji: '📅', description: 'Study every day for 30 days', condition: '30-day streak', earned: false, progress: 7, total: 30 },
]

// ─── Parent Agent — Weekly Performance Trend ──────────────────────────────────
export const parentWeeklyTrend = [
  { week: 'W1', avgScore: 71, studyHours: 4.2, sessions: 5 },
  { week: 'W2', avgScore: 73, studyHours: 5.1, sessions: 6 },
  { week: 'W3', avgScore: 72, studyHours: 4.8, sessions: 5 },
  { week: 'W4', avgScore: 75, studyHours: 6.0, sessions: 7 },
  { week: 'W5', avgScore: 74, studyHours: 5.5, sessions: 6 },
  { week: 'W6', avgScore: 77, studyHours: 6.8, sessions: 8 },
  { week: 'W7', avgScore: 80, studyHours: 7.2, sessions: 9 },
  { week: 'W8', avgScore: 82, studyHours: 6.9, sessions: 9 },
]

// ─── Motivational Messages ────────────────────────────────────────────────────
export const motivationalMessages = [
  { title: 'Consistency beats intensity', body: 'Aditi has shown up every day this week. 7 days of consistent study builds habits that last a lifetime — not just for exams.' },
  { title: 'Progress, not perfection', body: 'From 71% in Week 1 to 82% in Week 8. That\'s 11 percentage points of real growth through hard work and smart study techniques.' },
  { title: 'The transfer is real', body: 'Scoring 83 on the Knowledge Transfer Challenge means Aditi isn\'t just memorising — she\'s understanding deeply enough to apply knowledge to completely new situations.' },
  { title: 'Every expert was once a beginner', body: 'Chemistry started rough at 68% on Unit Test 3. But the consistent effort in Active Recall and Reality Lab sessions is already showing results.' },
  { title: 'You\'re raising a curious mind', body: 'Aditi completed 7 Reality Lab scenarios, exploring questions from space exploration to road safety chemistry. Curiosity is the root of all real learning.' },
]
