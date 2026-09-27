// Board / Level Constants
export const BOARDS = ["CBSE", "State Board", "ICSE", "IB", "Cambridge (IGCSE)", "Other"]
export const COLLEGE_SEMESTERS = [1, 2, 3, 4, 5, 6, 7, 8]
export const CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

export const STREAMS = {
  Science: ["Physics", "Chemistry", "Mathematics", "Biology"],
  Commerce: ["Accountancy", "Business Studies", "Economics", "Mathematics"],
  Arts: ["History", "Geography", "Political Science", "Economics"],
}

export const COLLEGE_STREAMS = [
  "Engineering & Technology",
  "Business & Commerce",
  "Medical & Allied Health Sciences",
  "Computer Applications & IT",
  "Basic & Applied Sciences",
  "Arts, Humanities & Law"
]

export const COLLEGE_DOMAINS = {
  "Engineering & Technology": [
    "Computer Science & AI",
    "Data Science & Analytics",
    "Electronics & Communication",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Biotechnology & Bioengineering"
  ],
  "Business & Commerce": [
    "Finance & Banking",
    "Marketing & Digital Strategy",
    "Accounting & Auditing",
    "Business Analytics",
    "Human Resource Management"
  ],
  "Medical & Allied Health Sciences": [
    "Medicine & Surgery (MBBS)",
    "Pharmacy & Pharmacology",
    "Nursing & Healthcare Management",
    "Biomedical Sciences"
  ],
  "Computer Applications & IT": [
    "Full-Stack Web & Cloud Computing",
    "Cybersecurity & Networks",
    "Artificial Intelligence & ML",
    "Software Engineering"
  ],
  "Basic & Applied Sciences": [
    "Physics & Nanotechnology",
    "Chemistry & Chemical Technology",
    "Mathematics & Statistics",
    "Biochemistry & Genetics"
  ],
  "Arts, Humanities & Law": [
    "Economics & Public Policy",
    "Corporate & Criminal Law",
    "Psychology & Cognitive Science",
    "International Relations & History"
  ]
}

export const syllabusChapters = {
  CBSE: {
    11: {
      Physics: [
        { name: "Physical World & Units", concepts: ["Fundamental forces", "SI units", "Dimensional analysis", "Significant figures"] },
        { name: "Kinematics", concepts: ["Uniform motion", "Relative velocity", "Projectile motion", "Circular motion"] },
        { name: "Laws of Motion", concepts: ["Newton's first law", "Newton's second law", "Newton's third law", "Friction", "Free body diagrams"] },
        { name: "Work, Energy & Power", concepts: ["Work-energy theorem", "Conservation of energy", "Power", "Elastic collisions"] },
        { name: "Rotational Motion", concepts: ["Torque", "Angular momentum", "Moment of inertia", "Rolling motion"] },
        { name: "Gravitation", concepts: ["Kepler's laws", "Universal gravitation", "Escape velocity", "Orbital velocity"] },
        { name: "Thermodynamics", concepts: ["Zeroth law", "First law", "Second law", "Carnot engine", "Entropy"] },
        { name: "Waves & Oscillations", concepts: ["Simple harmonic motion", "Resonance", "Sound waves", "Doppler effect"] },
      ],
      Chemistry: [
        { name: "Structure of Atom", concepts: ["Bohr model", "Quantum numbers", "Orbital shapes", "Electronic configuration"] },
        { name: "Periodic Table", concepts: ["Periodicity", "Atomic radius", "Ionisation energy", "Electronegativity"] },
        { name: "Chemical Bonding", concepts: ["Ionic bonds", "Covalent bonds", "VSEPR theory", "Hybridisation"] },
        { name: "Thermodynamics", concepts: ["Enthalpy", "Entropy", "Gibbs energy", "Hess's law"] },
        { name: "Equilibrium", concepts: ["Le Chatelier's principle", "Kp and Kc", "pH and buffers", "Solubility product"] },
        { name: "Redox Reactions", concepts: ["Oxidation state", "Balancing redox", "Electrochemical series"] },
        { name: "Hydrocarbons", concepts: ["Alkanes", "Alkenes", "Alkynes", "Aromaticity", "Markovnikov's rule"] },
      ],
      Mathematics: [
        { name: "Sets & Functions", concepts: ["Set operations", "Venn diagrams", "Relations", "Domain and range"] },
        { name: "Trigonometry", concepts: ["Identities", "Inverse trig functions", "Solutions of equations"] },
        { name: "Algebra", concepts: ["Complex numbers", "Quadratic equations", "Permutations & combinations", "Binomial theorem"] },
        { name: "Sequences & Series", concepts: ["Arithmetic progression", "Geometric progression", "Sum of series", "Infinite GP"] },
        { name: "Coordinate Geometry", concepts: ["Straight lines", "Circle", "Parabola", "Ellipse"] },
        { name: "Limits & Derivatives", concepts: ["Limits", "L'Hopital's rule", "Differentiation rules", "Chain rule"] },
        { name: "Statistics & Probability", concepts: ["Mean median mode", "Standard deviation", "Classical probability"] },
      ],
      Biology: [
        { name: "Cell Biology", concepts: ["Cell organelles", "Prokaryotic vs eukaryotic", "Biomolecules", "Enzymes"] },
        { name: "Cell Division", concepts: ["Mitosis phases", "Meiosis phases", "Cell cycle regulation"] },
        { name: "Plant Physiology", concepts: ["Photosynthesis", "Calvin cycle", "Transpiration", "Plant hormones"] },
        { name: "Human Physiology", concepts: ["Digestive enzymes", "Cardiac cycle", "Breathing mechanism", "Excretory system"] },
        { name: "Biological Classification", concepts: ["Five-kingdom system", "Viruses & bacteria", "Binomial nomenclature"] },
      ],
    },
    12: {
      Physics: [
        { name: "Electrostatics", concepts: ["Coulomb's law", "Electric field", "Electric potential", "Capacitance", "Gauss's law"] },
        { name: "Current Electricity", concepts: ["Ohm's law", "Kirchhoff's laws", "Wheatstone bridge", "Potentiometer"] },
        { name: "Magnetism & EM Induction", concepts: ["Magnetic field", "Biot-Savart law", "Faraday's law", "Lenz's law", "Mutual inductance"] },
        { name: "Alternating Current", concepts: ["Phasor diagrams", "LC resonance", "Transformer", "Power factor"] },
        { name: "Optics", concepts: ["Reflection", "Refraction", "Total internal reflection", "Lenses", "Interference", "Diffraction"] },
        { name: "Modern Physics", concepts: ["Photoelectric effect", "De Broglie wavelength", "Nuclear reactions", "Radioactive decay"] },
        { name: "Semiconductors", concepts: ["p-n junction", "Diode characteristics", "Transistor action", "Logic gates"] },
      ],
      Chemistry: [
        { name: "Solutions", concepts: ["Colligative properties", "Raoult's law", "Osmotic pressure", "Molarity vs molality"] },
        { name: "Electrochemistry", concepts: ["Electrochemical cells", "Nernst equation", "Electrolysis", "Corrosion"] },
        { name: "Chemical Kinetics", concepts: ["Rate laws", "Order of reaction", "Activation energy", "Arrhenius equation"] },
        { name: "p-Block Elements", concepts: ["Group 15", "Group 16", "Halogens", "Noble gases"] },
        { name: "Organic Chemistry", concepts: ["Haloalkanes", "Alcohols & ethers", "Aldehydes & ketones", "Amines", "Biomolecules", "Polymers"] },
        { name: "Coordination Chemistry", concepts: ["Werner's theory", "Ligands", "Crystal field theory", "Isomerism"] },
      ],
      Mathematics: [
        { name: "Matrices & Determinants", concepts: ["Matrix operations", "Determinant properties", "Inverse matrix", "Cramer's rule"] },
        { name: "Calculus", concepts: ["Continuity", "Derivatives", "Integration techniques", "Differential equations"] },
        { name: "Application of Calculus", concepts: ["Maxima & minima", "Rate of change", "Area under curve"] },
        { name: "Vectors & 3D Geometry", concepts: ["Vector addition", "Dot product", "Cross product", "Lines in 3D", "Planes"] },
        { name: "Probability", concepts: ["Conditional probability", "Bayes' theorem", "Binomial distribution", "Mean & variance"] },
        { name: "Linear Programming", concepts: ["Feasible region", "Corner point method", "Maximisation & minimisation"] },
      ],
      Biology: [
        { name: "Genetics & Heredity", concepts: ["Mendelian inheritance", "Dihybrid cross", "Linkage", "Mutation types", "Sex-linked traits"] },
        { name: "Molecular Biology", concepts: ["DNA replication", "Transcription", "Translation", "Gene expression"] },
        { name: "Evolution", concepts: ["Natural selection", "Hardy-Weinberg equilibrium", "Speciation"] },
        { name: "Human Health & Disease", concepts: ["Immunity types", "Vaccines", "Cancer biology", "AIDS"] },
        { name: "Ecology", concepts: ["Population dynamics", "Ecosystem energy flow", "Nutrient cycles", "Biodiversity"] },
        { name: "Biotechnology", concepts: ["Recombinant DNA technology", "PCR", "ELISA", "GM crops"] },
      ],
    },
  },
  "State Board": {
    11: {
      Physics: [
        { name: "Physical World", concepts: ["SI units", "Dimensional analysis"] },
        { name: "Laws of Motion", concepts: ["Newton's laws", "Friction", "Momentum"] },
        { name: "Thermodynamics", concepts: ["Heat transfer", "Laws of thermodynamics"] },
        { name: "Waves", concepts: ["Sound waves", "Doppler effect", "Resonance"] },
      ],
      Chemistry: [
        { name: "Atomic Structure", concepts: ["Bohr model", "Quantum numbers"] },
        { name: "Chemical Bonding", concepts: ["Ionic bonds", "Covalent bonds"] },
        { name: "Thermodynamics", concepts: ["Enthalpy", "Gibbs energy"] },
        { name: "Organic Chemistry", concepts: ["Hydrocarbons", "Functional groups"] },
      ],
      Mathematics: [
        { name: "Algebra", concepts: ["Sets", "Complex numbers", "Sequences"] },
        { name: "Trigonometry", concepts: ["Identities", "Solutions of triangles"] },
        { name: "Calculus", concepts: ["Limits", "Differentiation rules"] },
        { name: "Coordinate Geometry", concepts: ["Straight lines", "Circles"] },
      ],
      Biology: [
        { name: "Cell Biology", concepts: ["Cell structure", "Cell division"] },
        { name: "Plant Physiology", concepts: ["Photosynthesis", "Respiration"] },
        { name: "Human Physiology", concepts: ["Digestion", "Circulation", "Excretion"] },
      ],
    },
    12: {
      Physics: [
        { name: "Electrostatics", concepts: ["Electric field", "Potential", "Capacitors"] },
        { name: "Current Electricity", concepts: ["Ohm's law", "Kirchhoff's laws"] },
        { name: "Electromagnetic Induction", concepts: ["Faraday's law", "Lenz's law"] },
        { name: "Optics", concepts: ["Lenses", "Interference", "Diffraction"] },
        { name: "Modern Physics", concepts: ["Photoelectric effect", "Nuclear reactions", "Semiconductors"] },
      ],
      Chemistry: [
        { name: "Electrochemistry", concepts: ["Galvanic cells", "Electrolysis", "Corrosion"] },
        { name: "Chemical Kinetics", concepts: ["Rate laws", "Activation energy"] },
        { name: "Organic Chemistry", concepts: ["Alcohols", "Aldehydes", "Amines"] },
      ],
      Mathematics: [
        { name: "Calculus", concepts: ["Integration", "Differential equations"] },
        { name: "Vectors & 3D", concepts: ["Vector algebra", "Lines in 3D", "Planes"] },
        { name: "Probability", concepts: ["Conditional probability", "Bayes' theorem"] },
      ],
      Biology: [
        { name: "Genetics", concepts: ["Mendelian genetics", "DNA replication", "Protein synthesis"] },
        { name: "Evolution", concepts: ["Natural selection", "Speciation"] },
        { name: "Ecology", concepts: ["Ecosystems", "Biodiversity", "Environmental issues"] },
      ],
    },
  },
}

export function getSyllabus(board, classLevel) {
  const boardData = syllabusChapters[board] || syllabusChapters["CBSE"]
  return boardData[classLevel] || boardData[12]
}

// ─── Reality Lab scenarios per subject ───────────────────────────────────────
export const realityLabBySubject = {
  "Information Coding Techniques": [
    // Easy
    { id: "ict-e1", title: "Why do retail barcodes and QR codes include extra check bits at the end?", context: "Retail & E-Commerce", difficulty: "Easy", chapter: "Module III: Block Codes",
      expectedConcepts: [
        { concept: "Parity Check Bits", required: true },
        { concept: "Error Detection Fundamentals", required: true },
        { concept: "Data Integrity Verification", required: false }
      ],
      modelAnswer: "Barcode scanners compute a mathematical sum of digits. The final parity check digit detects optical reading mistakes, preventing incorrect product pricing at checkout." },
    { id: "ict-e2", title: "How does a CD player read music accurately even when the disc surface has micro-scratches?", context: "Consumer Media", difficulty: "Easy", chapter: "Module IV: Error Control Coding",
      expectedConcepts: [
        { concept: "Reed-Solomon Error Correction", required: true },
        { concept: "Data Interleaving", required: true },
        { concept: "Redundant Symbol Recovery", required: false }
      ],
      modelAnswer: "CDs use Reed-Solomon cross-interleaved codes. Scratched data bursts are spread out across multiple sectors, allowing the laser pickup to mathematically reconstruct missing audio bytes." },
    { id: "ict-e3", title: "Why does saving an image as JPEG reduce file size while PNG keeps text lines sharp?", context: "Digital Photography", difficulty: "Easy", chapter: "Module V: Compression Techniques",
      expectedConcepts: [
        { concept: "Lossy vs Lossless Compression", required: true },
        { concept: "Discrete Cosine Transform (DCT)", required: true },
        { concept: "Human Visual System Thresholds", required: false }
      ],
      modelAnswer: "JPEG uses lossy DCT compression by discarding high-frequency color variations humans barely notice. PNG uses lossless Run-Length/Huffman coding, preserving exact pixel edges for text." },
    // Medium
    { id: "ict-m1", title: "Why does Spotify compress music files using Huffman & Psychoacoustic coding without losing sound quality?", context: "Audio Streaming Systems", difficulty: "Medium", chapter: "Module V: Compression Techniques",
      expectedConcepts: [
        { concept: "Entropy Reduction & Huffman Coding", required: true },
        { concept: "Lossy vs Lossless Compression", required: true },
        { concept: "Perceptual Psychoacoustic Masking", required: true }
      ],
      modelAnswer: "Audio streaming uses entropy reduction (Huffman/Arithmetic coding) combined with psychoacoustic masking to remove frequencies imperceptible to human ears, slashing file size while preserving audio quality." },
    { id: "ict-m2", title: "How does ZIP compression reduce a 1GB raw document folder to 200MB?", context: "File Storage Systems", difficulty: "Medium", chapter: "Module I: Information Entropy Fundamentals",
      expectedConcepts: [
        { concept: "Information Entropy & Uncertainty", required: true },
        { concept: "Shannon-Fano & Huffman Variable Length Coding", required: true },
        { concept: "Source Coding Theorem Limit", required: true }
      ],
      modelAnswer: "ZIP compression calculates symbol probabilities. Frequent characters get short bit codes (Huffman), approaching the theoretical Shannon entropy limit." },
    { id: "ict-m3", title: "How do 4G and 5G cell towers adjust adaptive modulation (QAM) when you walk away from the tower?", context: "Mobile Networks", difficulty: "Medium", chapter: "Module II: Data & Voice Coding",
      expectedConcepts: [
        { concept: "Channel Capacity & Signal-to-Noise Ratio (SNR)", required: true },
        { concept: "Quadrature Amplitude Modulation (QAM)", required: true },
        { concept: "Shannon-Hartley Theorem Limit", required: true }
      ],
      modelAnswer: "Near the tower high SNR allows 256-QAM (8 bits per symbol). As distance increases and noise rises, the system dynamically drops to 16-QAM or QPSK, trading throughput to maintain link stability under the Shannon capacity limit." },
    // Hard
    { id: "ict-h1", title: "How does a 5G network detect and repair corrupted data packets during rapid vehicle motion?", context: "Wireless Communications", difficulty: "Hard", chapter: "Module IV: Error Control Coding",
      expectedConcepts: [
        { concept: "Convolutional Codes & Viterbi Decoding", required: true },
        { concept: "Linear Block Codes & Cyclic Redundancy Check (CRC)", required: true },
        { concept: "Generator and Parity Check Polynomials", required: true }
      ],
      modelAnswer: "5G adds parity bits via generator polynomials. The receiver applies Viterbi decoding to trace state transitions, correcting noise-induced bit flips in real time." },
    { id: "ict-h2", title: "How do Mars Rovers stream high-definition photos across 200 million km with ultra-low transmit power?", context: "Deep Space Communications", difficulty: "Hard", chapter: "Module IV: Error Control Coding",
      expectedConcepts: [
        { concept: "Low-Density Parity-Check (LDPC) Codes", required: true },
        { concept: "Iterative Belief Propagation Decoding", required: true },
        { concept: "Near-Shannon Limit Efficiency", required: true }
      ],
      modelAnswer: "Spacecraft use LDPC matrix codes operating within fraction of a dB of the Shannon limit. Iterative belief propagation decoders resolve deep space noise at tiny power levels." }
  ],

  "Object Oriented Analysis and Design": [
    // Easy
    { id: "ooad-e1", title: "Why does an e-commerce website model ShoppingCart and User as separate objects instead of one huge script?", context: "Web App Architecture", difficulty: "Easy", chapter: "Module I: Introduction",
      expectedConcepts: [
        { concept: "Encapsulation & Single Responsibility", required: true },
        { concept: "Modular Object Architecture", required: true },
        { concept: "Reusability & Maintainability", required: false }
      ],
      modelAnswer: "Separating User and ShoppingCart keeps state managed inside distinct objects (Encapsulation), allowing independent UI updates and preventing bug propagation." },
    { id: "ooad-e2", title: "How does a Smart Home app use Inheritance to control different brands of smart light bulbs?", context: "IoT Smart Home", difficulty: "Easy", chapter: "Module II: OO Methodologies & UML",
      expectedConcepts: [
        { concept: "Polymorphism & Base Class Inheritance", required: true },
        { concept: "Method Overriding", required: true },
        { concept: "Abstract Device Interface", required: false }
      ],
      modelAnswer: "A base SmartLight class defines turnOn() and setBrightness(). Philips and Wipro subclasses inherit this interface and override methods to send brand-specific network packets." },
    // Medium
    { id: "ooad-m1", title: "Why do enterprise banking applications separate database access from user screens using Access and View Layers?", context: "FinTech Architecture", difficulty: "Medium", chapter: "Module V: Access & View Layers",
      expectedConcepts: [
        { concept: "Access Layer Object Storage & Interoperability", required: true },
        { concept: "View Layer Interface Objects", required: true },
        { concept: "Design Axioms & System Decoupling", required: true }
      ],
      modelAnswer: "Decoupling View objects from Access objects ensures changes to database schemas do not break the UI, improving security, testability, and multi-platform support." },
    { id: "ooad-m2", title: "How does a food delivery app (like Zomato) use Factory Pattern to instantiate delivery vehicle objects dynamically?", context: "Logistics Software", difficulty: "Medium", chapter: "Module IV: Object Oriented Design I",
      expectedConcepts: [
        { concept: "Factory Creational Pattern", required: true },
        { concept: "Interface Abstraction", required: true },
        { concept: "Loose Coupling", required: true }
      ],
      modelAnswer: "The order dispatcher calls VehicleFactory.create(distance). The factory instantiates a Bicycle, Scooter, or Drone object adhering to a common DeliveryVehicle interface without client coupling." },
    // Hard
    { id: "ooad-h1", title: "How does Tesla design its Autopilot software system using UML & Object-Oriented Principles?", context: "Autonomous Driving Architecture", difficulty: "Hard", chapter: "Module II: OO Methodologies & UML",
      expectedConcepts: [
        { concept: "Use Case & Class Diagrams", required: true },
        { concept: "Polymorphism & Interface Abstraction", required: true },
        { concept: "State Diagram Transitions", required: true }
      ],
      modelAnswer: "Tesla models obstacles as abstract classes with polymorphic detect() and react() methods. State diagrams govern vehicle state transitions (e.g., cruising to emergency braking)." },
    { id: "ooad-h2", title: "How does the Observer Pattern allow 1,000 subscribers to receive instant notifications when a YouTube creator uploads a video?", context: "Cloud Notification Systems", difficulty: "Hard", chapter: "Module IV: Object Oriented Design I",
      expectedConcepts: [
        { concept: "Observer Behavioral Pattern", required: true },
        { concept: "Subject-Observer Registration", required: true },
        { concept: "Event-Driven Asynchronous Dispatch", required: true }
      ],
      modelAnswer: "The Channel object acts as Subject maintaining a list of Subscriber objects. Upon upload, notifySubscribers() iterates through active observers, triggering push notifications." }
  ],

  "Mean Stack Web Development": [
    // Easy
    { id: "mean-e1", title: "Why do modern websites load product details instantly using JSON instead of reloading the full HTML page?", context: "Single Page Apps", difficulty: "Easy", chapter: "Module II: JavaScript & AngularJS",
      expectedConcepts: [
        { concept: "Asynchronous JavaScript & Fetch API", required: true },
        { concept: "JSON Lightweight Data Exchange", required: true },
        { concept: "DOM Updating", required: false }
      ],
      modelAnswer: "Client scripts fetch raw JSON data asynchronously in background, updating specific DOM elements without repainting the entire HTML document tree." },
    { id: "mean-e2", title: "How does HTML5 LocalStorage keep your shopping cart items intact even if you close the browser tab?", context: "Browser Storage", difficulty: "Easy", chapter: "Module I: Introduction to Web & MongoDB",
      expectedConcepts: [
        { concept: "Client-Side Persistent Key-Value Storage", required: true },
        { concept: "Session vs LocalStorage Lifecycle", required: true },
        { concept: "JSON Serialization", required: false }
      ],
      modelAnswer: "LocalStorage saves serialized key-value strings on client disk across browser sessions, re-hydrating app state immediately upon tab re-opening." },
    // Medium
    { id: "mean-m1", title: "Why do e-commerce sites like Amazon use MongoDB (NoSQL) alongside SQL for product catalogs?", context: "Cloud E-Commerce", difficulty: "Medium", chapter: "Module I: Introduction to Web & MongoDB",
      expectedConcepts: [
        { concept: "NoSQL Flexible BSON Document Model", required: true },
        { concept: "Dynamic Collections without Rigid Schemas", required: true },
        { concept: "Horizontal Scalability & Sharding", required: true }
      ],
      modelAnswer: "Different products (clothing vs electronics) have completely different attributes. MongoDB stores varied schemas as flexible JSON/BSON documents without costly SQL ALTER TABLE migrations." },
    { id: "mean-m2", title: "How does Express.js Middleware verify JWT authentication tokens before letting users access private dashboard routes?", context: "Web Security Architecture", difficulty: "Medium", chapter: "Module III: Node.js & Express.js",
      expectedConcepts: [
        { concept: "Express Middleware Pipeline (req, res, next)", required: true },
        { concept: "JSON Web Token (JWT) Signature Verification", required: true },
        { concept: "HTTP Authorization Headers", required: true }
      ],
      modelAnswer: "Express middleware intercepts requests, decodes bearer token signatures using a secret key, attaches user payload to req.user, and calls next() to pass control to route handlers." },
    // Hard
    { id: "mean-h1", title: "How does Uber match 10,000 riders with nearby drivers in real time without crashing?", context: "Ride-Sharing Cloud Platform", difficulty: "Hard", chapter: "Module III: Node.js & Express.js",
      expectedConcepts: [
        { concept: "Node.js Single-Threaded Non-Blocking Event Loop", required: true },
        { concept: "MongoDB Geospatial Indexing (2dsphere)", required: true },
        { concept: "Express RESTful APIs & Middleware", required: true }
      ],
      modelAnswer: "Node.js handles thousands of concurrent socket connections asynchronously without thread overhead. MongoDB's 2dsphere indexing performs rapid geospatial queries to locate nearby drivers." },
    { id: "mean-h2", title: "Why does React's Virtual DOM update screen elements faster than directly manipulating the browser DOM?", context: "Frontend Performance Optimization", difficulty: "Hard", chapter: "Module IV: RESTful Web Services & React.js",
      expectedConcepts: [
        { concept: "Virtual DOM Tree Diffing Algorithm", required: true },
        { concept: "Batch Rendering & Reconciliation", required: true },
        { concept: "Minimizing Browser Reflow & Repaint", required: true }
      ],
      modelAnswer: "React keeps an in-memory Virtual DOM tree. When state changes, reconciliation diffs memory trees and batches minimal layout mutations, eliminating costly browser reflows." }
  ],

  "AI and Machine Learning": [
    // Easy
    { id: "aiml-e1", title: "How does your smartphone camera automatically detect and frame human faces in real time?", context: "Computer Vision", difficulty: "Easy", chapter: "Module IV: Learning by Examples",
      expectedConcepts: [
        { concept: "Feature Extraction & Pattern Recognition", required: true },
        { concept: "Supervised Image Classification", required: true },
        { concept: "Bounding Box Bounding", required: false }
      ],
      modelAnswer: "Vision algorithms scan frame pixels for facial feature patterns (eyes, nose alignment) trained on millions of labeled face photos, drawing bounding boxes in real time." },
    { id: "aiml-e2", title: "Why does an email spam filter get better at catching phishing scams as you mark unwanted messages?", context: "Smart Email Filtering", difficulty: "Easy", chapter: "Module IV: Learning by Examples",
      expectedConcepts: [
        { concept: "Naive Bayes Text Classification", required: true },
        { concept: "Supervised Learning Feedback Loop", required: true },
        { concept: "Word Frequency Probabilities", required: false }
      ],
      modelAnswer: "Marking spam updates word probability tables (Bayesian classification). Spammer keywords gain higher spam weights, automatically blocking similar future messages." },
    // Medium
    { id: "aiml-m1", title: "Why does a credit card fraud system flag transactions made in two distant cities within 5 minutes?", context: "FinTech Anomaly Detection", difficulty: "Medium", chapter: "Module IV: Learning by Examples",
      expectedConcepts: [
        { concept: "Anomaly Detection & Distance Metrics", required: true },
        { concept: "Unsupervised Clustering & Outlier Thresholds", required: true },
        { concept: "Velocity & Spatial Rules", required: true }
      ],
      modelAnswer: "System calculates transaction velocity. Impossible geographic velocity exceeds normal behavior cluster thresholds, triggering immediate account locks." },
    { id: "aiml-m2", title: "How does a streaming platform like Netflix recommend movies tailored to your watch history?", context: "Recommendation Engines", difficulty: "Medium", chapter: "Module IV: Learning by Examples",
      expectedConcepts: [
        { concept: "Collaborative Filtering", required: true },
        { concept: "Matrix Factorization & Similarity Metrics", required: true },
        { concept: "User Interest Embeddings", required: true }
      ],
      modelAnswer: "Collaborative filtering maps user ratings into vector embeddings. Users with similar vector cosine angles receive recommendations based on what peer users enjoyed." },
    // Hard
    { id: "aiml-h1", title: "How does Google Maps calculate the fastest route through heavy city traffic in milliseconds?", context: "Smart City Navigation", difficulty: "Hard", chapter: "Module II: Problem Solving by Search",
      expectedConcepts: [
        { concept: "Heuristic Search Function h(n)", required: true },
        { concept: "A* Search Algorithm f(n) = g(n) + h(n)", required: true },
        { concept: "State Space Graph Edge Weights", required: true }
      ],
      modelAnswer: "Google Maps models intersections as graph nodes. The A* algorithm evaluates total cost f(n) = g(n) + h(n), where h(n) is the estimated distance to destination, pruning sub-optimal roads." },
    { id: "aiml-h2", title: "How does a medical AI detect cancerous tumors in X-ray scans before human doctors?", context: "Healthcare AI", difficulty: "Hard", chapter: "Module IV: Learning by Examples",
      expectedConcepts: [
        { concept: "Supervised Learning & Labeled Datasets", required: true },
        { concept: "Artificial Neural Networks (ANN) & Deep Layers", required: true },
        { concept: "Classification Metrics & Decision Trees", required: true }
      ],
      modelAnswer: "Neural networks extract micro-features (edges, textures) across millions of annotated medical scans, minimizing loss to classify tissue as benign or malignant." }
  ],

  "Signals and Systems": [
    // Easy
    { id: "sig-e1", title: "Why do music equalizer apps let you boost bass frequencies without distorting singer voices?", context: "Consumer Audio", difficulty: "Easy", chapter: "Module I: Introduction to Signals & Systems",
      expectedConcepts: [
        { concept: "Frequency Domain Separation", required: true },
        { concept: "Low-Pass vs High-Pass Filtering", required: true },
        { concept: "Linear Time-Invariant Invariance", required: false }
      ],
      modelAnswer: "Equalizers separate sound into frequency bands. Low-pass filters amplify bass (20-250 Hz) independently without altering vocal frequencies (500-3000 Hz)." },
    { id: "sig-e2", title: "How does a smartphone digital microphone convert human voice into digital numbers?", context: "Mobile Telephony", difficulty: "Easy", chapter: "Module I: Introduction to Signals & Systems",
      expectedConcepts: [
        { concept: "Sampling Theorem & Nyquist Rate", required: true },
        { concept: "Analog-to-Digital Conversion (ADC)", required: true },
        { concept: "Quantization Noise", required: false }
      ],
      modelAnswer: "Microphones sample continuous sound pressure 44,100 times per second (above double max voice frequency), quantizing voltage amplitudes into 16-bit binary numbers." },
    // Medium
    { id: "sig-m1", title: "Why do active noise-canceling headphones cancel airplane engine hum instantly?", context: "Consumer Electronics", difficulty: "Medium", chapter: "Module I: Introduction to Signals & Systems",
      expectedConcepts: [
        { concept: "Destructive Phase Interference", required: true },
        { concept: "LTI System Real-Time Inversion", required: true },
        { concept: "180 Degree Phase Reversal", required: true }
      ],
      modelAnswer: "Headphone microphones capture ambient engine noise. The onboard DSP generates an inverted sound wave (180° out of phase), causing destructive interference that cancels the noise." },
    { id: "sig-m2", title: "Why do helicopter blades appear to spin backwards in high-speed smartphone video recordings?", context: "Digital Video Processing", difficulty: "Medium", chapter: "Module I: Introduction to Signals & Systems",
      expectedConcepts: [
        { concept: "Temporal Aliasing", required: true },
        { concept: "Nyquist-Shannon Sampling Criteria Failure", required: true },
        { concept: "Frame Rate Strobe Effect", required: true }
      ],
      modelAnswer: "Camera frame rate (30 fps) is lower than double blade rotation frequency. Under-sampling creates temporal aliasing, folding high frequencies into apparent reverse motion." },
    // Hard
    { id: "sig-h1", title: "How does an MRI machine construct a 3D image of a human brain using magnetic signals?", context: "Biomedical Imaging", difficulty: "Hard", chapter: "Module II: Fourier Analysis",
      expectedConcepts: [
        { concept: "Continuous & Discrete Fourier Transform (2D FFT)", required: true },
        { concept: "k-Space Frequency Domain to Spatial Domain", required: true },
        { concept: "LTI Systems & Impulse Response", required: true }
      ],
      modelAnswer: "MRI sensors record radio-frequency emissions from hydrogen atoms in k-space (frequency domain). Applying Inverse 2D Fourier Transform converts k-space data into clear 3D spatial tissue images." },
    { id: "sig-h2", title: "How does aircraft radar calculate both distance and velocity of a jet simultaneously?", context: "Avionics & Radar Systems", difficulty: "Hard", chapter: "Module II: Fourier Analysis",
      expectedConcepts: [
        { concept: "Doppler Shift Frequency Analysis", required: true },
        { concept: "Matched Filter Pulse Compression", required: true },
        { concept: "Ambiguity Function & FFT Processing", required: true }
      ],
      modelAnswer: "Radar measures echo time delay for range distance, and evaluates frequency shift (Doppler effect) via FFT to compute velocity in real time." }
  ],

  Physics: [
    // Easy
    { id: "phy-e1", title: "Why does a sports car stop faster than a bus with the same brakes?", context: "Road Safety", difficulty: "Easy", chapter: "Laws of Motion",
      expectedConcepts: [
        { concept: "Newton's Second Law a = F/m", required: true },
        { concept: "Inertia and mass", required: true },
        { concept: "Braking force (friction)", required: true }
      ],
      modelAnswer: "Same braking force F acts on both. Deceleration a = F/m. Bus has much greater mass so smaller deceleration. Same force gives sports car far higher deceleration." },
    { id: "phy-e2", title: "Why does an iron nail sink in water while a giant steel cargo ship floats?", context: "Maritime Engineering", difficulty: "Easy", chapter: "Physical World",
      expectedConcepts: [
        { concept: "Archimedes' Principle & Buoyancy", required: true },
        { concept: "Average Density (Mass / Total Volume)", required: true },
        { concept: "Displaced Water Weight", required: false }
      ],
      modelAnswer: "The cargo ship's hollow hull encloses air, making its total average density less than water. The buoyant force equal to displaced water weight balances total ship gravity." },
    // Medium
    { id: "phy-m1", title: "Why does a microwave heat food but not a plastic container?", context: "Kitchen Physics", difficulty: "Medium", chapter: "Electromagnetic Waves",
      expectedConcepts: [
        { concept: "Polar molecules and dipole rotation", required: true },
        { concept: "EM radiation resonance at 2.45 GHz", required: true },
        { concept: "Resonance frequency of water molecules", required: true }
      ],
      modelAnswer: "Microwaves emit EM radiation at ~2.45 GHz matching water's resonance frequency. Water molecules (polar) rotate rapidly generating heat. Plastics lack such polar molecules so stay cool." },
    { id: "phy-m2", title: "Why do high-voltage power lines step up electricity to 400,000V for long-distance transport?", context: "Power Grid Engineering", difficulty: "Medium", chapter: "Current Electricity",
      expectedConcepts: [
        { concept: "Joule Heating P_loss = I^2 R", required: true },
        { concept: "Power Conservation P = V x I", required: true },
        { concept: "Transformer Voltage Step-Up", required: true }
      ],
      modelAnswer: "Stepping up voltage V reduces line current I proportionally for fixed power P. Since transmission cable heating loss drops with I^2 R, high voltage dramatically prevents power waste." },
    // Hard
    { id: "phy-h1", title: "How does Fiber Optic Internet transmit gigabit data across ocean floors without light escaping?", context: "Global Communications", difficulty: "Hard", chapter: "Optics",
      expectedConcepts: [
        { concept: "Total Internal Reflection (TIR)", required: true },
        { concept: "Critical Angle sin(theta_c) = n2/n1", required: true },
        { concept: "Refractive Index Core vs Cladding", required: true }
      ],
      modelAnswer: "Glass core has higher refractive index n1 than cladding n2. Light signals strike the boundary at angles greater than critical angle theta_c, reflecting 100% internally with zero light loss." },
    { id: "phy-h2", title: "How do Maglev trains levitate above tracks and travel at 600 km/h without touching rails?", context: "High-Speed Rail", difficulty: "Hard", chapter: "Magnetism & EM Induction",
      expectedConcepts: [
        { concept: "Superconducting Electromagnets", required: true },
        { concept: "Meissner Effect & Magnetic Levitation", required: true },
        { concept: "Linear Synchronous Motor Propulsion", required: true }
      ],
      modelAnswer: "Superconducting magnets produce powerful magnetic repulsion lifting the train 10cm. Alternating track electromagnets pull and push train poles forward, eliminating mechanical friction." }
  ],

  Chemistry: [
    // Easy
    { id: "chem-e1", title: "Why does adding salt to icy roads melt the ice in freezing winter?", context: "Winter Road Safety", difficulty: "Easy", chapter: "Solutions",
      expectedConcepts: [
        { concept: "Freezing point depression (colligative property)", required: true },
        { concept: "Ionic dissociation in solution", required: true }
      ],
      modelAnswer: "NaCl dissociates raising solute particle count. This lowers the freezing point (colligative property). Ice melts into liquid at the new lower freezing point." },
    { id: "chem-e2", title: "Why does rubbing lemon juice on cut apple slices prevent them from turning brown?", context: "Food Science", difficulty: "Easy", chapter: "Redox Reactions",
      expectedConcepts: [
        { concept: "Antioxidants & Ascorbic Acid", required: true },
        { concept: "Inhibition of Enzymatic Oxidation", required: true }
      ],
      modelAnswer: "Citric and ascorbic acid in lemon juice act as reducing agents (antioxidants), reacting with oxygen before polyphenol oxidase enzymes can oxidize apple phenols to brown melanin." },
    // Medium
    { id: "chem-m1", title: "Why does soap wash away greasy oil from hands while plain water fails?", context: "Hygiene & Surfactants", difficulty: "Medium", chapter: "Chemical Bonding",
      expectedConcepts: [
        { concept: "Amphiphilic Surfactant Molecules", required: true },
        { concept: "Hydrophobic Tail vs Hydrophilic Head", required: true },
        { concept: "Micelle Formation & Emulsification", required: true }
      ],
      modelAnswer: "Soap molecules have non-polar hydrophobic tails that bind grease and polar hydrophilic heads that bind water. They trap oil inside spherical micelles, allowing water to flush them away." },
    { id: "chem-m2", title: "How do catalytic converters in car exhausts transform toxic carbon monoxide into safe CO2?", context: "Environmental Tech", difficulty: "Medium", chapter: "Chemical Kinetics",
      expectedConcepts: [
        { concept: "Heterogeneous Catalysis (Platinum/Palladium)", required: true },
        { concept: "Lowering Activation Energy Ea", required: true },
        { concept: "Redox Gas Surface Reaction", required: true }
      ],
      modelAnswer: "Exhaust gases pass over hot platinum/rhodium honeycomb surfaces. The metal catalyst adsorbs CO and O2, lowering activation energy to rapidly oxidize CO into non-toxic CO2 gas." },
    // Hard
    { id: "chem-h1", title: "How does kidney dialysis use artificial semi-permeable membranes to clean metabolic wastes from blood?", context: "Medical Technology", difficulty: "Hard", chapter: "Solutions",
      expectedConcepts: [
        { concept: "Hemodialysis Osmotic Gradient", required: true },
        { concept: "Selective Permeability & Urea Diffusion", required: true },
        { concept: "Colligative Osmotic Pressure Balance", required: true }
      ],
      modelAnswer: "Blood flows alongside dialysate fluid separated by cellulose membrane. Waste urea diffuses down concentration gradient into dialysate while essential proteins are retained due to size." }
  ],

  Mathematics: [
    // Easy
    { id: "math-e1", title: "How do surveyors calculate the height of a mountain without climbing it?", context: "Civil Surveying", difficulty: "Easy", chapter: "Trigonometry",
      expectedConcepts: [
        { concept: "Right-Angle Trigonometry (tan theta = opp/adj)", required: true },
        { concept: "Angle of Elevation Measurement", required: true }
      ],
      modelAnswer: "Surveyors measure distance to mountain base (adj) and angle of elevation theta using a theodolite. Height is calculated directly via h = baseline x tan(theta)." },
    { id: "math-e2", title: "How does compound interest double investment savings faster than simple interest?", context: "Personal Finance", difficulty: "Easy", chapter: "Sequences & Series",
      expectedConcepts: [
        { concept: "Exponential Growth A = P(1 + r/n)^(nt)", required: true },
        { concept: "Geometric Growth Rate", required: true }
      ],
      modelAnswer: "Compound interest calculates interest on both initial principal and accumulated interest each period, generating exponential geometric growth compared to linear simple interest." },
    // Medium
    { id: "math-m1", title: "How does Amazon route 500 delivery vans to minimize fuel cost using Linear Programming?", context: "Logistics Optimization", difficulty: "Medium", chapter: "Linear Programming",
      expectedConcepts: [
        { concept: "Objective Function Cost Minimization", required: true },
        { concept: "Feasible Region Constraint Boundaries", required: true },
        { concept: "Simplex Corner Point Optimization", required: true }
      ],
      modelAnswer: "Systems formulate fuel cost as objective function subject to van capacity and delivery window constraints. Simplex algorithm evaluates corner points of the feasible polytope." },
    { id: "math-m2", title: "How do 3D video game engines rotate player characters smoothly in space?", context: "Game Engine Math", difficulty: "Medium", chapter: "Matrices & Determinants",
      expectedConcepts: [
        { concept: "3D Rotation Matrices", required: true },
        { concept: "Vector Multiplication & Transformation", required: true },
        { concept: "Coordinate Space Mapping", required: true }
      ],
      modelAnswer: "Character vertex vectors are multiplied by 3x3 rotational transformation matrices containing sine and cosine functions of rotation angle theta, computing new 3D spatial coordinates." },
    // Hard
    { id: "math-h1", title: "How does GPS calculate your exact 3D location using satellites?", context: "Global Navigation", difficulty: "Hard", chapter: "Coordinate Geometry",
      expectedConcepts: [
        { concept: "Trilateration (intersection of 3 spheres)", required: true },
        { concept: "Distance formula in 3D", required: true },
        { concept: "System of simultaneous equations", required: true }
      ],
      modelAnswer: "Each satellite defines a sphere of radius r = c x t. Your position is the exact intersection of 4 satellite spheres — solving 3D simultaneous equations yields latitude, longitude, elevation, and time sync." }
  ],

  Biology: [
    // Easy
    { id: "bio-e1", title: "Why do you sweat profusely when running on a hot summer afternoon?", context: "Human Homeostasis", difficulty: "Easy", chapter: "Human Physiology",
      expectedConcepts: [
        { concept: "Evaporative Cooling Heat Loss", required: true },
        { concept: "Thermoregulation & Homeostasis", required: true }
      ],
      modelAnswer: "Sweat glands secrete water onto skin. Evaporating 1g of sweat absorbs 2.26 kJ of latent heat from skin capillaries, cooling body core temperature back to 37°C." },
    { id: "bio-e2", title: "Why do potted plants bending toward a sunlit window straighten if turned around?", context: "Botany", difficulty: "Easy", chapter: "Plant Physiology",
      expectedConcepts: [
        { concept: "Auxin Plant Hormone Phototropism", required: true },
        { concept: "Differential Cell Elongation", required: true }
      ],
      modelAnswer: "Auxin hormone accumulates on shaded side of plant stem, stimulating faster cell elongation on dark side, causing stem to bend physically toward sunlight." },
    // Medium
    { id: "bio-m1", title: "How does a vaccine teach your immune system to fight a new virus before you get sick?", context: "Immunology & Public Health", difficulty: "Medium", chapter: "Human Health & Disease",
      expectedConcepts: [
        { concept: "Antigen-antibody response", required: true },
        { concept: "Memory B-cells and T-cells", required: true },
        { concept: "Adaptive immunity vs innate immunity", required: true }
      ],
      modelAnswer: "A vaccine introduces harmless antigens. B-cells produce specific antibodies and memory cells. On real infection, memory cells trigger rapid secondary immune response before symptoms develop." },
    { id: "bio-m2", title: "Why are type O-negative individuals called universal blood donors?", context: "Transfusion Genetics", difficulty: "Medium", chapter: "Genetics & Heredity",
      expectedConcepts: [
        { concept: "ABO Surface Antigens & Rh Factor", required: true },
        { concept: "Absence of A/B Antigens preventing Agglutination", required: true }
      ],
      modelAnswer: "Type O-negative red blood cells lack A, B, and Rh antigens. Recipient immune antibodies do not recognize foreign markers, preventing deadly blood agglutination." },
    // Hard
    { id: "bio-h1", title: "How does mRNA technology instruct human muscle cells to produce viral antigens safely?", context: "Biotechnology & Vaccines", difficulty: "Hard", chapter: "Biotechnology",
      expectedConcepts: [
        { concept: "Ribosomal Translation of mRNA", required: true },
        { concept: "Lipid Nanoparticle Delivery", required: true },
        { concept: "Transient Expression without DNA Integration", required: true }
      ],
      modelAnswer: "Synthetic mRNA encapsulated in lipid nanoparticles enters cell cytoplasm. Host ribosomes translate code into spike protein antigens, triggering immune memory without altering genomic DNA." }
  ]
}

// ─── Transfer Challenge questions per subject ─────────────────────────────────
export const transferBySubject = {
  "Information Coding Techniques": [
    { round: 1, difficulty: "Easy", concept: "Parity Checking", chapter: "Module III: Block Codes",
      scenario: "A barcode scanner at a store reads a 12-digit UPC code. The last digit is '4'. How does the scanner instantly know if a dirt spot caused a misread digit?",
      hint: "It calculates an odd/even weighted sum of the first 11 digits.",
      modelAnswer: "Scanner multiplies alternate digits by 3 and adds them. If total mod 10 doesn't equal check digit, scanner beeps to request re-scan.",
      conceptsApplied: ["Parity check digit", "Error detection"], transferScore: 92 },
    { round: 2, difficulty: "Medium", concept: "Huffman Coding & Source Entropy", chapter: "Module I: Information Entropy Fundamentals",
      scenario: "A satellite telemetry module must stream 500 MB of sensor logs over a 50 kbps link. How does Huffman variable-length coding reduce transmission time without loss?",
      hint: "High-frequency symbols get short bit codes.",
      modelAnswer: "Huffman coding calculates symbol probabilities and assigns shorter bit sequences to high-frequency events, minimizing average code length toward the Shannon entropy limit without losing data.",
      conceptsApplied: ["Huffman Coding", "Shannon Entropy Limit", "Lossless Source Coding"], transferScore: 88 },
    { round: 3, difficulty: "Medium", concept: "Linear Block Codes & CRC", chapter: "Module III: Block Codes",
      scenario: "An IoT weather station sends readings over a noisy radio channel. How does CRC parity checking detect bit flips during transmission?",
      hint: "Sender divides payload by a generator polynomial and appends the remainder.",
      modelAnswer: "The sender divides message bits by a generator polynomial and appends the remainder (CRC). The receiver repeats the division; a non-zero remainder signals corrupted data packet.",
      conceptsApplied: ["Cyclic Redundancy Check (CRC)", "Generator Polynomial", "Parity Bit Checking"], transferScore: 82 },
    { round: 4, difficulty: "Hard", concept: "Convolutional Codes & Viterbi Decoding", chapter: "Module IV: Error Control Coding",
      scenario: "Deep space probes like Voyager emit faint signals affected by space noise. How does Viterbi decoding recover the original bit sequence?",
      hint: "Viterbi traces the maximum-likelihood path through a trellis diagram.",
      modelAnswer: "Convolutional encoders insert correlation between bits. The Viterbi algorithm computes path metrics across a trellis diagram to find the sequence with minimum Hamming distance.",
      conceptsApplied: ["Convolutional Codes", "Viterbi Trellis Decoding", "Maximum Likelihood Path"], transferScore: 79 }
  ],

  "Object Oriented Analysis and Design": [
    { round: 1, difficulty: "Easy", concept: "Encapsulation", chapter: "Module I: Introduction",
      scenario: "In a multiplayer game, a player's health point variable is declared private. Why must external enemy scripts call takeDamage(amount) instead of directly setting health = health - 10?",
      hint: "Prevents illegal values like negative health and centralizes death checks.",
      modelAnswer: "Encapsulation protects private state. takeDamage() validates input, clamps health >= 0, and triggers death events if health reaches zero.",
      conceptsApplied: ["Encapsulation", "State Protection"], transferScore: 94 },
    { round: 2, difficulty: "Medium", concept: "Sequence Diagrams & Message Flow", chapter: "Module II: OO Methodologies & UML",
      scenario: "Designing a ride-hailing app (like Uber) where users track driver location. Which UML diagram captures the chronological interaction between User, Order Controller, Driver, and Map API?",
      hint: "Sequence diagrams emphasize chronological interaction across lifelines.",
      modelAnswer: "A UML Sequence Diagram models objects along vertical lifelines, showing horizontal synchronous and asynchronous calls in exact chronological order.",
      conceptsApplied: ["UML Sequence Diagram", "Lifeline Interaction", "Chronological Messaging"], transferScore: 90 },
    { round: 3, difficulty: "Hard", concept: "Design Axioms & Interface Abstraction", chapter: "Module IV: Object Oriented Design I",
      scenario: "A banking platform needs to switch payment gateways from Stripe to PayPal. How does programming to an interface prevent refactoring client code?",
      hint: "High cohesion and low coupling isolate system components.",
      modelAnswer: "By depending on an abstract PaymentGateway interface rather than concrete classes, client logic remains unchanged when swapping implementations (Axiom of Independence).",
      conceptsApplied: ["Interface Abstraction", "Low Coupling", "Dependency Inversion"], transferScore: 85 }
  ],

  "Mean Stack Web Development": [
    { round: 1, difficulty: "Easy", concept: "Client-Side DOM Manipulation", chapter: "Module II: JavaScript & AngularJS",
      scenario: "When clicking 'Like' on a social media post, why does the heart icon immediately turn red before waiting for server response?",
      hint: "Optimistic UI rendering updates DOM first.",
      modelAnswer: "Optimistic UI updates local DOM state immediately for zero perceived latency, while sending asynchronous AJAX request in background.",
      conceptsApplied: ["DOM Manipulation", "Asynchronous AJAX", "Optimistic UI"], transferScore: 95 },
    { round: 2, difficulty: "Medium", concept: "MongoDB 2dsphere Geospatial Indexing", chapter: "Module I: Introduction to Web & MongoDB",
      scenario: "A delivery service calculates the 5 nearest drivers within a 3km radius. How does MongoDB's 2dsphere index accelerate this spatial query?",
      hint: "Uses spherical geometry ($near queries) over GeoJSON point coordinates.",
      modelAnswer: "MongoDB 2dsphere indices partition the earth's surface into quadtree cells (S2 geometry). $near queries execute logarithmic bounding box lookups instead of scanning all documents.",
      conceptsApplied: ["MongoDB 2dsphere Index", "GeoJSON Points", "$near Spherical Query"], transferScore: 87 },
    { round: 3, difficulty: "Hard", concept: "Node.js Event Loop & Non-Blocking I/O", chapter: "Module III: Node.js & Express.js",
      scenario: "A ticket booking platform receives 50,000 concurrent requests during a flash sale. How does Node.js handle this traffic on a single thread?",
      hint: "Single-threaded event loop delegates I/O calls to libuv worker pool asynchronously.",
      modelAnswer: "Node.js runs an event loop that delegates file and network I/O asynchronously to libuv without blocking the main event thread, supporting high concurrency with low RAM.",
      conceptsApplied: ["Event Loop", "Non-Blocking Asynchronous I/O", "libuv Worker Pool"], transferScore: 92 }
  ],

  "AI and Machine Learning": [
    { round: 1, difficulty: "Easy", concept: "Supervised Learning", chapter: "Module IV: Learning by Examples",
      scenario: "A spam filter is trained on 100,000 emails labeled as 'Spam' or 'Inbox'. What type of machine learning paradigm is this?",
      hint: "Uses input features paired with target output labels.",
      modelAnswer: "Supervised Learning. The algorithm learns mapping function f(x) -> y from labeled dataset examples.",
      conceptsApplied: ["Supervised Learning", "Labeled Datasets"], transferScore: 96 },
    { round: 2, difficulty: "Medium", concept: "A* Search Algorithm & Heuristics", chapter: "Module II: Problem Solving by Search",
      scenario: "An autonomous delivery drone calculates the fastest path around high-rise buildings. How does A* search evaluate routes faster than BFS?",
      hint: "Evaluates f(n) = g(n) + h(n), where h(n) is estimated distance to goal.",
      modelAnswer: "A* calculates f(n) = g(n) + h(n), combining path cost g(n) with estimated distance heuristic h(n). It prioritizes nodes closest to the goal, pruning unpromising branches.",
      conceptsApplied: ["A* Search Algorithm", "Heuristic Function h(n)", "State Space Graph"], transferScore: 89 },
    { round: 3, difficulty: "Hard", concept: "Minimax & Alpha-Beta Pruning", chapter: "Module III: Adversarial Search & Logical Agents",
      scenario: "A chess engine searches 10 levels deep. How does Alpha-Beta pruning double search speed without missing optimal moves?",
      hint: "Skips branches that yield worse outcomes than previously searched nodes.",
      modelAnswer: "Alpha-Beta maintains bounds (alpha for MAX, beta for MIN). If a sub-node produces a value worse than the current bound, the remaining child nodes are pruned immediately.",
      conceptsApplied: ["Minimax Algorithm", "Alpha-Beta Pruning", "Adversarial Game Tree"], transferScore: 84 }
  ],

  "Signals and Systems": [
    { round: 1, difficulty: "Easy", concept: "Sampling Rate", chapter: "Module I: Introduction to Signals & Systems",
      scenario: "Audio CDs sample sound at 44.1 kHz. Human hearing reaches up to 20 kHz. Why must sampling rate exceed 40 kHz?",
      hint: "Nyquist theorem requires sampling rate > 2x max frequency.",
      modelAnswer: "By Nyquist-Shannon theorem fs >= 2 f_max. Sampling at 44.1 kHz (> 40 kHz) prevents aliasing distortion of 20 kHz sound.",
      conceptsApplied: ["Nyquist Theorem", "Sampling Rate"], transferScore: 93 },
    { round: 2, difficulty: "Medium", concept: "Fourier Transform & Frequency Domain", chapter: "Module II: Fourier Analysis",
      scenario: "An audio studio engineer removes a 60 Hz hum from a podcast recording. Why is frequency domain filtering cleaner than time domain editing?",
      hint: "Convolution in time domain becomes direct multiplication in frequency domain.",
      modelAnswer: "Transforming the signal to frequency domain via Fourier Transform isolates 60 Hz as a sharp frequency spike, allowing a notch filter multiplication to silence it cleanly.",
      conceptsApplied: ["Fourier Transform", "Frequency Domain Analysis", "Notch Filtering"], transferScore: 86 },
    { round: 3, difficulty: "Hard", concept: "Destructive Phase Interference", chapter: "Module I: Introduction to Signals & Systems",
      scenario: "Active noise-canceling headphones eliminate jet engine noise in real time. What principle of LTI systems makes this work?",
      hint: "Microphone captures ambient sound and plays back a 180° inverted wave.",
      modelAnswer: "The DSP samples ambient wave x(t) and outputs inverted wave -x(t) (180° phase shifted). By superposition, x(t) + (-x(t)) = 0, canceling the sound wave at the ear.",
      conceptsApplied: ["Destructive Interference", "180° Phase Inversion", "LTI Superposition"], transferScore: 91 }
  ]
}

// ─── College simulation scenarios (from uploaded syllabus) ───────────────────
export const collegeScenarios = [
  { id: "col-1", title: "Why do modern CPUs use multi-core instead of just increasing clock speed?",
    context: "Computer Architecture", subject: "Computer Science", difficulty: "Hard", semester: "3+",
    expectedConcepts: [
      { concept: "Power dissipation P = CV^2 f", required: true },
      { concept: "Thermal limits of silicon (power wall)", required: true },
      { concept: "Amdahl's law limits parallel speedup", required: false },
    ],
    modelAnswer: "Increasing clock frequency f raises power as P = CV^2 f causing overheating (power wall). Multi-core allows parallel execution at lower frequency with less total power. Amdahl's law limits speedup for serial code but parallel workloads benefit greatly." },
  { id: "col-2", title: "How does an MRI machine create images of soft tissue without X-rays?",
    context: "Medical Imaging", subject: "Physics / Biomedical Engg", difficulty: "Hard", semester: "4+",
    expectedConcepts: [
      { concept: "Nuclear magnetic resonance (NMR) of hydrogen protons", required: true },
      { concept: "Strong magnetic field aligns proton spins", required: true },
      { concept: "RF pulse excites protons; relaxation emits signal", required: true },
    ],
    modelAnswer: "Strong magnetic field aligns hydrogen proton spins. RF pulse knocks them out of alignment. As they relax back they emit RF signals. Different tissues have different relaxation times (T1, T2) creating contrast for imaging." },
  { id: "col-3", title: "How does a transformer step up voltage without violating energy conservation?",
    context: "Electrical Engineering", subject: "Physics / Electrical Engg", difficulty: "Medium", semester: "2+",
    expectedConcepts: [
      { concept: "Faraday's law of mutual induction", required: true },
      { concept: "Turns ratio V2/V1 = N2/N1", required: true },
      { concept: "Power conservation I1V1 = I2V2", required: true },
    ],
    modelAnswer: "Changing primary current induces changing flux. Secondary EMF: V2/V1 = N2/N1. Higher voltage means proportionally lower current (P = VI constant). Energy is conserved — an ideal transformer is 100% efficient." },
  { id: "col-4", title: "How do mRNA vaccines work differently from traditional vaccines?",
    context: "Molecular Biology", subject: "Biology / Pharmacy", difficulty: "Hard", semester: "5+",
    expectedConcepts: [
      { concept: "mRNA encodes spike protein antigen", required: true },
      { concept: "Host cells translate mRNA to produce antigen temporarily", required: true },
      { concept: "mRNA never enters nucleus; cannot alter DNA", required: true },
    ],
    modelAnswer: "mRNA vaccines inject synthetic mRNA encoding the viral antigen. Host ribosomes translate it, producing antigen. Immune system responds and generates memory cells. The mRNA degrades within days — it never enters the nucleus and cannot alter DNA." },
  { id: "col-5", title: "Why does a suspension bridge cable form a parabola and not a catenary?",
    context: "Structural Engineering", subject: "Civil Engineering / Mathematics", difficulty: "Hard", semester: "3+",
    expectedConcepts: [
      { concept: "Uniform load per unit horizontal distance (deck weight)", required: true },
      { concept: "Parabola y = wx^2 / 2H from force equilibrium", required: true },
      { concept: "Catenary forms when load is per unit cable length (cable's own weight)", required: true },
    ],
    modelAnswer: "Suspension bridge cable supports the deck — load uniform per horizontal distance. Solving cable equilibrium gives y = wx^2/(2H), a parabola. A catenary forms when load is per unit cable length (chain's own weight). Deck weight dominates, producing a parabola." },
]

// ─── Dynamic College Semesters & Native Language Syllabus Data ────────────────
export const COLLEGE_SEMESTER_DATA = {
  // Computer Science & AI / IT
  "Computer Science & AI": {
    1: {
      "Engineering Mathematics I": [
        { name: "Calculus & Linear Algebra", concepts: ["Matrices & Eigenvalues", "Taylor & Maclaurin Series", "Partial Derivatives", "Multiple Integrals"] },
        { name: "Vector Calculus", concepts: ["Gradient, Divergence & Curl", "Green's Theorem", "Gauss Divergence Theorem", "Stokes' Theorem"] }
      ],
      "Engineering Physics": [
        { name: "Quantum Physics & Lasers", concepts: ["Wave-Particle Duality", "Schrödinger Wave Equation", "Laser Action & Population Inversion", "Optical Fibres & Attenuation"] },
        { name: "Electromagnetism", concepts: ["Maxwell's Equations", "EM Wave Propagation", "Poynting Vector", "Dielectric Materials"] }
      ],
      "Programming in C": [
        { name: "Fundamentals of C", concepts: ["Data Types & Operators", "Control Structures & Loops", "Functions & Recursion", "Array Manipulation"] },
        { name: "Pointers & Memory", concepts: ["Pointer Arithmetic", "Dynamic Memory (malloc/free)", "Structures & Unions", "File I/O Streams"] }
      ],
      "Basic Electrical Engg": [
        { name: "DC & AC Circuits", concepts: ["Kirchhoff's Laws & Theorems", "R-L-C Series Resonance", "Phasor Diagrams", "Transformer Principle"] }
      ]
    },
    2: {
      "Engineering Mathematics II": [
        { name: "Differential Equations", concepts: ["First Order ODEs", "Higher Order Linear ODEs", "Laplace Transforms", "Fourier Series"] }
      ],
      "Data Structures": [
        { name: "Linear Data Structures", concepts: ["Arrays & Linked Lists", "Stacks & Queues", "Infix to Postfix Conversion", "Circular & Doubly Linked Lists"] },
        { name: "Non-Linear Structures", concepts: ["Binary Search Trees (BST)", "AVL Trees & B-Trees", "Graph Traversals (BFS & DFS)", "Dijkstra's Shortest Path"] },
        { name: "Sorting & Searching", concepts: ["QuickSort & MergeSort", "HeapSort", "Binary Search & Hashing", "Collision Resolution"] }
      ],
      "Digital Logic Design": [
        { name: "Boolean Algebra & Gates", concepts: ["Karnaugh Maps (K-Maps)", "Combinational Circuits", "Multiplexers & Encoders", "Quine-McCluskey Method"] },
        { name: "Sequential Logic", concepts: ["Flip-Flops (JK, D, T)", "Shift Registers", "Synchronous Counters", "Finite State Machines (FSM)"] }
      ],
      "Engineering Chemistry": [
        { name: "Water & Polymer Tech", concepts: ["Hardness of Water & EDTA", "Electrochemistry & Batteries", "Polymerisation & Composites", "Corrosion Prevention"] }
      ]
    },
    3: {
      "Object Oriented Programming": [
        { name: "OOP Principles", concepts: ["Classes & Objects", "Encapsulation & Abstraction", "Inheritance & Polymorphism", "Operator Overloading"] },
        { name: "Advanced Java/C++", concepts: ["Virtual Functions & Interfaces", "Exception Handling", "Generics & Templates", "Multi-threading & Synchronization"] }
      ],
      "Discrete Mathematics": [
        { name: "Logic & Proofs", concepts: ["Propositional & Predicate Logic", "Mathematical Induction", "Relations & Equivalence", "Lattices & Boolean Algebras"] },
        { name: "Combinatorics & Graph Theory", concepts: ["Pigeonhole Principle", "Recurrence Relations", "Eulerian & Hamiltonian Graphs", "Graph Coloring & Trees"] }
      ],
      "Computer Architecture": [
        { name: "Processor Design", concepts: ["Instruction Set Architecture (ISA)", "ALU & Control Unit Design", "Pipelining & Hazard Detection", "RISC vs CISC"] },
        { name: "Memory Hierarchy", concepts: ["Cache Mapping (Direct, Associative)", "Virtual Memory & Paging", "TLB & Page Faults", "RAID Storage Systems"] }
      ],
      "Database Management Systems": [
        { name: "Relational Data Model", concepts: ["ER Diagrams to Schemas", "Relational Algebra & SQL", "Normalization (1NF to 3NF, BCNF)", "Indexes & B+ Trees"] },
        { name: "Transaction Processing", concepts: ["ACID Properties", "Concurrency Control & Locking", "Deadlock Handling", "NoSQL & MongoDB Basics"] }
      ]
    },
    4: {
      "Operating Systems": [
        { name: "Process Management", concepts: ["Process Lifecycle & PCB", "CPU Scheduling (FCFS, SJF, RR)", "Inter-Process Communication", "Threads & Synchronization"] },
        { name: "Concurrency & Deadlocks", concepts: ["Semaphores & Mutexes", "Banker's Algorithm", "Deadlock Prevention & Detection", "Dining Philosophers Problem"] },
        { name: "Memory & Storage", concepts: ["Paging & Segmentation", "Page Replacement (LRU, FIFO)", "File System Layout & Inodes", "Disk Scheduling (SCAN, C-SCAN)"] }
      ],
      "Design & Analysis of Algorithms": [
        { name: "Asymptotic Analysis", concepts: ["Big-O, Omega, Theta Notations", "Master Theorem", "Divide and Conquer (MergeSort)", "Recurrence Solving"] },
        { name: "Algorithm Paradigms", concepts: ["Greedy Strategy (Knapsack, Huffman)", "Dynamic Programming (LCS, 0/1 Knapsack)", "Backtracking (N-Queens)", "NP-Completeness & P vs NP"] }
      ],
      "Software Engineering": [
        { name: "SDLC & Methodologies", concepts: ["Agile & Scrum Framework", "Waterfall & Spiral Models", "Requirement Engineering (SRS)", "UML Diagrams (Class, Use-Case)"] }
      ],
      "Computer Networks": [
        { name: "Protocol Stack & Layers", concepts: ["OSI & TCP/IP Reference Models", "Data Link Control & MAC", "IPv4/IPv6 Addressing & Subnetting", "Routing Protocols (RIP, OSPF, BGP)"] }
      ]
    },
    5: {
      "Information Coding Techniques": [
        { name: "Module I: Information Entropy Fundamentals", concepts: ["Uncertainty & Entropy", "Source Coding Theorem", "Huffman Coding", "Shannon-Fano Coding", "Channel Capacity Theorem"] },
        { name: "Module II: Data & Voice Coding", concepts: ["DPCM & ADPCM", "Adaptive Subband Coding", "Delta Modulation", "Vocoders & LPC Speech Signal"] },
        { name: "Module III: Block Codes", concepts: ["Hamming Weight & Distance", "Linear Block Codes", "Cyclic Codes", "Syndrome Calculation & CRC"] },
        { name: "Module IV: Error Control Coding", concepts: ["Generator & Parity Polynomials", "Convolutional Codes", "Viterbi Algorithm", "Turbo Coding"] },
        { name: "Module V: Compression Techniques", concepts: ["Static & Dynamic Huffman Coding", "Arithmetic Coding", "Image Compression (GIF, TIFF)", "JPEG Standards"] }
      ],
      "Object Oriented Analysis and Design": [
        { name: "Module I: Introduction", concepts: ["OO Systems Development", "Object Basics", "OO System Lifecycle"] },
        { name: "Module II: OO Methodologies & UML", concepts: ["Unified Approach", "Use Case Diagrams", "Class Diagrams", "Sequence & State Diagrams", "Activity & Package Diagrams"] },
        { name: "Module III: Object Oriented Analysis", concepts: ["Identifying Use Cases", "Classification Methods", "Attributes & Relationships"] },
        { name: "Module IV: Object Oriented Design I", concepts: ["Design Axioms", "Designing Classes", "Creational & Structural Patterns"] },
        { name: "Module V: Object Oriented Design II", concepts: ["Access Layer & Object Storage", "View Layer & Interface Objects", "Database Interoperability"] }
      ],
      "Mean Stack Web Development": [
        { name: "Module I: Introduction to Web & MongoDB", concepts: ["Protocols (HTTP, FTP, SMTP)", "HTML5 & CSS3 Anatomy", "XML, DOM & SAX", "MongoDB Architecture & Database Creation"] },
        { name: "Module II: JavaScript & AngularJS", concepts: ["JS Primitives & Objects", "Regular Expressions", "AngularJS Expressions & Directives", "Single Page Application (SPA)"] },
        { name: "Module III: Node.js & Express.js", concepts: ["Node Process Model & Modules", "Express Routing & Middleware", "MVC Architecture", "API Handling & Debugging"] },
        { name: "Module IV: RESTful Web Services & React.js", concepts: ["RESTful Principles", "Virtual DOM & ReactDOM", "React Components & State", "Cloud Deployment"] }
      ],
      "AI and Machine Learning": [
        { name: "Module I: Intelligent Agents", concepts: ["Rational Agents & Environments", "Agent Structure", "Uninformed Search (BFS, DFS)"] },
        { name: "Module II: Problem Solving by Search", concepts: ["Heuristic Search & A*", "Local Search & Optimization", "Constraint Satisfaction Problems"] },
        { name: "Module III: Adversarial Search & Logical Agents", concepts: ["Minimax & Alpha-Beta Pruning", "Monte-Carlo Tree Search", "Propositional Logic & Theorem Proving"] },
        { name: "Module IV: Learning by Examples", concepts: ["Supervised Learning", "Decision Trees", "Linear Regression & Classification", "Artificial Neural Networks"] },
        { name: "Module V: Knowledge in Learning", concepts: ["Explanation-Based Learning", "Inductive Logic Programming", "Statistical Learning"] }
      ],
      "Signals and Systems": [
        { name: "Module I: Introduction to Signals & Systems", concepts: ["Continuous & Discrete Signals", "LTI Systems", "Impulse Response", "Convolution"] },
        { name: "Module II: Fourier Analysis", concepts: ["Fourier Series", "Continuous-Time Fourier Transform", "Discrete-Time Fourier Transform (DTFT)"] },
        { name: "Module III: Laplace Transform Analysis", concepts: ["Unilateral & Bilateral Laplace", "Region of Convergence (ROC)", "Inverse Laplace Transform"] },
        { name: "Module IV: Z-Transform Analysis", concepts: ["Z-Plane & ROC", "Inverse Z-Transform", "System Function Analysis"] }
      ],
      "CASE Tools Laboratory": [
        { name: "Module I: Feasibility & Requirements", concepts: ["Project Scope & Cost Estimation", "Scenario-based Modeling", "Behavioral Modeling"] },
        { name: "Module II: Data Modeling & UML", concepts: ["Business Flow Diagrams", "Class & Sequence Diagrams", "Software Testing Tools"] }
      ],
      "Communication Skills for Career Success": [
        { name: "Module I: Brief Exchanges", concepts: ["Telephonic Conversations", "Matching Tasks", "Short Notes & Messages"] },
        { name: "Module II: Workplace Communication", concepts: ["Mini Presentations", "Memo & Email Writing", "Conference & Seminar Reports"] }
      ]
    },
    6: {
      "Software Testing": [
        { name: "Module I: Software Testing Introduction", concepts: ["Testing as Engineering Activity", "TMM Levels", "Defect Classes & Repository"] },
        { name: "Module II: Test Case Design Strategies", concepts: ["Black-Box Approach", "Equivalence Partitioning", "Boundary Value Analysis", "White-Box & Code Coverage"] },
        { name: "Module III: Levels of Testing", concepts: ["Unit & Integration Testing", "System & Acceptance Testing", "Test Planning & Policies"] }
      ],
      "Cloud Computing Technologies": [
        { name: "Module I: Cloud Basics & Deployment", concepts: ["Service Models (IaaS, PaaS, SaaS)", "AWS, Azure & GCP", "Virtualization"] },
        { name: "Module II: Cloud Storage & Security", concepts: ["GFS, HDFS, HBase & DynamoDB", "Data Protection & Access Policies", "Virtual Machine Provisioning"] }
      ],
      "Fundamentals of Entrepreneurship": [
        { name: "Module I: Opportunity & Business Model", concepts: ["Design Thinking", "Value Proposition Canvas", "Lean Canvas", "Minimum Viable Product (MVP)"] }
      ]
    },
    7: {
      "Internet of Things": [
        { name: "Module I: Introduction to IoT", concepts: ["IoT Network Architecture", "Smart Objects", "Connecting Smart Objects"] },
        { name: "Module II: IoT Protocols", concepts: ["IEEE 802.15.4 & ZigBee", "MQTT, CoAP & RESTful APIs", "M2M & WSN Protocols"] }
      ],
      "Full Stack Web Development": [
        { name: "Module I: Advanced Web Stack", concepts: ["React & Node.js Integration", "REST APIs", "Cloud Deployment (AWS/Firebase)"] }
      ]
    },
    8: {
      "Project Work & Capstone": [
        { name: "Module I: Engineering Project Execution", concepts: ["Requirements Elicitation", "System Architecture & Design", "Testing, Implementation & Documentation"] }
      ]
    }
  }
}

// Native Language Support for School Students
export const SCHOOL_LANGUAGES_DATA = {
  "Tamil": [
    { name: "இலக்கணம் (Grammar)", concepts: ["எழுத்திலக்கணம்", "சொல்லிலக்கணம்", "பொருளிலக்கணம்", "யாப்பிலக்கணம் & அணியிலக்கணம்"] },
    { name: "செய்யுள் & இலக்கியம் (Literature)", concepts: ["திருக்குறள் & நெறிமுறைகள்", "சிலப்பதிகாரம் & மணிமேகலை", "பாரதியார் & பாரதிதாசன் கவிதைகள்", "சங்க இலக்கியப் பாடல்கள்"] },
    { name: "உரைநடை & உரைத்திறன் (Prose & Essay)", concepts: ["கட்டுரை எழுதுதல்", "படைப்பாற்றல் & மொழிபெயர்ப்பு", "பத்தி வினா-விடை", "கடித வரைவு"] }
  ],
  "Hindi": [
    { name: "व्याकरण (Grammar)", concepts: ["वर्ण विचार एवं वर्तनी", "संधि एवं समास", "पद परिचय एवं कारक", "मुहावरे एवं लोकोक्तियाँ"] },
    { name: "साहित्य एवं काव्य (Literature)", concepts: ["कबीर एवं सूरदास के पद", "निराला एवं महादेवी की कविताएँ", "गद्य खंड - कहानियाँ एवं निबंध", "एकांकी एवं नाटक"] },
    { name: "अपठित एवं लेखन (Comprehension & Essay)", concepts: ["अपठित गद्यांश एवं काव्यांश", "निबंध एवं पत्र लेखन", "अनुच्छेद लेखन", "संवाद लेखन"] }
  ],
  "Telugu": [
    { name: "వ్యాకరణము (Grammar)", concepts: ["సంధులు & సమాసాలు", "ఛందస్సు & అలంకారాలు", "పదజాలం & జాతీయాలు", "వాక్య నిర్మాణము"] },
    { name: "సాహిత్యము (Literature)", concepts: ["పద్య భాగము & శతక పద్యాలు", "గద్య భాగము & కథానికలు", "ఇతిహాసాలు & కావ్యాలు"] }
  ],
  "English": [
    { name: "Grammar & Vocabulary", concepts: ["Tenses & Subject-Verb Agreement", "Direct & Indirect Speech", "Active & Passive Voice", "Prepositions & Phrasal Verbs"] },
    { name: "Literature & Poetry", concepts: ["Prose & Short Stories Analysis", "Poetic Devices & Metaphors", "Character Sketch & Themes", "Drama & Play Context"] },
    { name: "Writing Skills", concepts: ["Formal & Informal Letter Writing", "Analytical Paragraph Writing", "Article & Essay Drafting", "Reading Comprehension"] }
  ]
}

// ─── Dynamic Helper Functions ───────────────────────────────────────────────
export function getDynamicSubjects(profile, syllabusData) {
  // 1. If user uploaded a custom syllabus document or text, return extracted subjects
  if (syllabusData && Array.isArray(syllabusData.extracted_subjects) && syllabusData.extracted_subjects.length > 0) {
    return syllabusData.extracted_subjects
  }

  // 2. If student profile has custom subjects array set during onboarding/registration
  if (profile?.subjects && Array.isArray(profile.subjects) && profile.subjects.length > 0) {
    return profile.subjects
  }

  // 3. If college student with semester and domain credentials
  if (profile?.level === 'college') {
    const sem = parseInt(profile?.semester || 5)
    const domain = profile?.domain || profile?.stream || "Computer Science & AI"
    
    // Find matching domain from COLLEGE_SEMESTER_DATA
    const domainKey = Object.keys(COLLEGE_SEMESTER_DATA).find(k => 
      k.toLowerCase() === domain.toLowerCase() || 
      k.toLowerCase().includes(domain.toLowerCase()) || 
      domain.toLowerCase().includes(k.toLowerCase())
    ) || "Computer Science & AI"
    
    const domainData = COLLEGE_SEMESTER_DATA[domainKey]
    if (domainData) {
      const semSubjects = domainData[sem] || domainData[5] || domainData[3] || domainData[1]
      if (semSubjects) {
        return Object.keys(semSubjects)
      }
    }
  }

  // 4. If school student with stream credentials
  if (profile?.level === 'school' && profile?.stream && STREAMS[profile.stream]) {
    return STREAMS[profile.stream]
  }

  // 5. If no syllabus uploaded and no profile credentials set, return empty array
  return []
}

export function getDynamicChapters(subject, profile, syllabusData) {
  // Check if syllabusData has custom extracted chapters for this subject
  if (syllabusData && syllabusData.chapters && syllabusData.chapters[subject]) {
    return syllabusData.chapters[subject]
  }

  // Check if subject is native language
  if (SCHOOL_LANGUAGES_DATA[subject]) {
    return SCHOOL_LANGUAGES_DATA[subject]
  }

  // If college student
  if (profile?.level === 'college') {
    const sem = parseInt(profile?.semester || 5)
    const domain = profile?.domain || "Computer Science & AI"
    const domainData = COLLEGE_SEMESTER_DATA[domain] || COLLEGE_SEMESTER_DATA["Computer Science & AI"]
    const semSubjects = domainData[sem] || domainData[5] || domainData[3] || domainData[1]
    if (semSubjects && semSubjects[subject]) {
      return semSubjects[subject]
    }
  }

  // School board chapters
  const board = profile?.board || 'CBSE'
  const classLvl = profile?.classLevel || 12
  const syllabus = getSyllabus(board, classLvl)
  if (syllabus && syllabus[subject]) {
    return syllabus[subject]
  }

  // Generic fallback chapters if subject custom
  return [
    { name: `${subject} Core Fundamentals`, concepts: ["Key Principles", "Fundamental Formulas", "Core Theories", "Definitions & Terminology"] },
    { name: `${subject} Advanced Applications`, concepts: ["Problem Solving Techniques", "Exam Analysis & Scenarios", "Case Studies", "Scoring Strategies"] }
  ]
}

const DAY_TO_DAY_SCENARIOS_TEMPLATES = [
  { context: "Smartphone & Streaming Apps", diff: "Easy", title: "Why does your smartphone application use '{concept}' from {module} when streaming HD video or playing music?", answer: "Smartphones use {concept} from {module} to optimize data payload over wireless links, preventing buffering while maintaining clear audio/video playback." },
  { context: "Electric & Smart Vehicles", diff: "Medium", title: "How do modern electric vehicles (like Tesla or EV scooters) apply '{concept}' from {module} to maximize battery range?", answer: "EVs implement {concept} within battery management and motor controllers to minimize resistive heating losses and recapture kinetic energy." },
  { context: "Online Banking & Payments", diff: "Hard", title: "How does online banking (like GPay, UPI, or Credit Cards) leverage '{concept}' from {module} to prevent fraud in real time?", answer: "Banking systems use {concept} to calculate transaction velocity, verify digital signatures, and isolate anomalous spending patterns in real time." },
  { context: "Home Wi-Fi & Smart Devices", diff: "Easy", title: "Why does your home Wi-Fi router or IoT device utilize '{concept}' from {module} to prevent connection drops?", answer: "Routers utilize {concept} to allocate frequency channels dynamically and manage packet queues across multiple connected household devices." },
  { context: "Smart Fitness Wearables", diff: "Medium", title: "How do smart fitness bands (like Apple Watch or Fitbit) track real-time heart rate using '{concept}' from {module}?", answer: "Wearables use optical sensors to capture pulse waveforms, applying {concept} to filter out arm movement noise and isolate true heart rates." },
  { context: "Food Delivery & Urban Logistics", diff: "Medium", title: "Why do food delivery apps (like Zomato or Swiggy) rely on '{concept}' from {module} to assign drivers in seconds?", answer: "Delivery platforms use {concept} to solve geospatial assignment problems, matching driver coordinates to restaurant orders for minimal wait times." },
  { context: "Digital Photography & Camera Tech", diff: "Easy", title: "How does smartphone camera software use '{concept}' from {module} to process low-light night mode photos?", answer: "Camera ISPs combine multiple burst exposures, applying {concept} to align images, reduce sensor grain noise, and enhance dynamic range." },
  { context: "Aviation & Flight Safety", diff: "Hard", title: "Why do commercial airplane autopilot computers depend on '{concept}' from {module} during severe turbulence?", answer: "Autopilot controllers apply {concept} to compute closed-loop aerodynamic corrections, stabilizing wing flaps against sudden wind gusts." },
  { context: "Live Video Calls & Conferencing", diff: "Medium", title: "How do video calling apps (like Zoom or WhatsApp) use '{concept}' from {module} when cell signal drops?", answer: "Video encoders evaluate available link bandwidth, using {concept} to compress frame bitrates dynamically and preserve audio clarity." },
  { context: "Kitchen & Home Appliances", diff: "Easy", title: "Why does a modern microwave, induction cooktop, or inverter AC depend on '{concept}' from {module}?", answer: "Appliance microcontrollers use {concept} to regulate power modulation, matching energy draw precisely to heating or cooling demands." },
  { context: "Healthcare & Diagnostic Scanning", diff: "Hard", title: "How do hospital MRI machines or CT scanners apply '{concept}' from {module} to generate 3D tissue scans?", answer: "Medical scanners record spatial signals, applying {concept} to transform frequency measurements into precise 3D anatomical images." },
  { context: "Console & Mobile Gaming Engine", diff: "Medium", title: "Why do 3D game engines (like Unreal or Unity) use '{concept}' from {module} to render 60 FPS graphics?", answer: "Game engines use {concept} to perform rapid matrix vector transformations and spatial culling, maintaining smooth frame rates." },
  { context: "Weather Supercomputers", diff: "Hard", title: "How do meteorological supercomputers apply '{concept}' from {module} to predict storm paths days ahead?", answer: "Weather models run numerical differential equations over geographic grids, using {concept} to simulate atmospheric pressure transitions." },
  { context: "Automobile Anti-Lock Brakes (ABS)", diff: "Easy", title: "Why does a modern car's anti-lock braking system (ABS) utilize '{concept}' from {module} on wet roads?", answer: "ABS wheel speed sensors detect impending wheel lockup, applying {concept} to pulse hydraulic brake pressure 15 times per second." },
  { context: "Social Media Recommendation", diff: "Medium", title: "How do social media algorithms (like Instagram or TikTok) apply '{concept}' from {module} to curate your feed?", answer: "Recommendation engines map user interactions into feature vectors, using {concept} to compute similarity scores for tailored content." },
  { context: "Active Noise-Canceling Audio", diff: "Medium", title: "Why do noise-canceling headphones apply '{concept}' from {module} to silence loud cafe background noise?", answer: "Headphone micro-DSPs sample ambient acoustic waves, applying {concept} to emit an inverted 180° anti-phase wave that cancels background sound." },
  { context: "Renewable Solar Power Grids", diff: "Easy", title: "How do solar panel micro-inverters use '{concept}' from {module} to convert sunlight into AC electricity?", answer: "Solar inverters sample DC voltage, using {concept} to track maximum power point (MPPT) and invert current smoothly to 230V household AC." },
  { context: "Cloud Storage & Backup", diff: "Medium", title: "Why does cloud storage (like Google Drive) utilize '{concept}' from {module} to back up photos rapidly?", answer: "Cloud backends evaluate file redundancies, applying {concept} to compress payloads and deduplicate identical blocks across user storage." },
  { context: "Smart Thermostats & Climate Control", diff: "Easy", title: "How do smart inverter ACs use '{concept}' from {module} to maintain room temperature while saving power?", answer: "Inverter ACs vary compressor motor speed smoothly using {concept}, avoiding energy spikes caused by frequent on/off cycling." },
  { context: "High-Speed Railway & Bullet Trains", diff: "Hard", title: "Why do high-speed bullet train propulsion systems apply '{concept}' from {module} for 300 km/h travel?", answer: "Train traction inverters use {concept} to regulate linear induction motor frequencies, achieving smooth acceleration without mechanical wear." }
]

export function getDynamicScenarios(subject, profile, syllabusData, difficultyFilter = 'All', moduleFilter = 'All') {
  let list = []
  const chaps = getDynamicChapters(subject, profile, syllabusData)
  
  if (realityLabBySubject[subject] && realityLabBySubject[subject].length >= 10 && moduleFilter === 'All') {
    list = realityLabBySubject[subject]
  } else {
    const generated = []
    chaps.forEach((ch, chIdx) => {
      const concepts = (ch.concepts && ch.concepts.length > 0) ? ch.concepts : ["Core Principle", "System Optimization", "Performance Analysis"]
      
      // Generate 20 questions for this module
      DAY_TO_DAY_SCENARIOS_TEMPLATES.forEach((tmpl, tIdx) => {
        const concept = concepts[tIdx % concepts.length]
        const formattedTitle = tmpl.title.replace('{concept}', concept).replace('{module}', ch.name)
        const formattedAnswer = tmpl.answer.replace(/{concept}/g, concept).replace(/{module}/g, ch.name)

        generated.push({
          id: `dyn-lab-${subject.toLowerCase().replace(/\s+/g, '-')}-m${chIdx + 1}-q${tIdx + 1}`,
          title: formattedTitle,
          context: tmpl.context,
          difficulty: tmpl.diff,
          chapter: ch.name,
          expectedConcepts: [
            { concept: concept, required: true },
            { concept: "Day-to-day Life Application", required: true },
            { concept: tmpl.context, required: false }
          ],
          modelAnswer: formattedAnswer
        })
      })
    })

    list = generated
  }

  if (moduleFilter && moduleFilter !== 'All') {
    const filteredByModule = list.filter((item) => item.chapter === moduleFilter)
    if (filteredByModule.length > 0) list = filteredByModule
  }

  if (difficultyFilter && difficultyFilter !== 'All') {
    const filteredByDiff = list.filter((item) => item.difficulty === difficultyFilter)
    if (filteredByDiff.length > 0) list = filteredByDiff
  }

  return list
}

export function getDynamicTransferQuestions(subject, profile, syllabusData, difficultyFilter = 'All', moduleFilter = 'All') {
  let list = []
  const chaps = getDynamicChapters(subject, profile, syllabusData)

  if (transferBySubject[subject] && transferBySubject[subject].length >= 10 && moduleFilter === 'All') {
    list = transferBySubject[subject]
  } else {
    const generated = []
    let roundNum = 1

    chaps.forEach((ch, chIdx) => {
      const concepts = (ch.concepts && ch.concepts.length > 0) ? ch.concepts : ["Core Principle", "System Optimization"]
      
      DAY_TO_DAY_SCENARIOS_TEMPLATES.forEach((tmpl, tIdx) => {
        const concept = concepts[tIdx % concepts.length]
        const formattedTitle = tmpl.title.replace('{concept}', concept).replace('{module}', ch.name)
        const formattedAnswer = tmpl.answer.replace(/{concept}/g, concept).replace(/{module}/g, ch.name)

        generated.push({
          round: roundNum++,
          difficulty: tmpl.diff,
          concept: concept,
          chapter: ch.name,
          scenario: formattedTitle,
          hint: `Recall how ${concept} governs operational rules in ${ch.name}.`,
          modelAnswer: formattedAnswer,
          conceptsApplied: [concept, tmpl.context, "Day-to-day Life Transfer"],
          transferScore: tmpl.diff === "Easy" ? 92 : tmpl.diff === "Medium" ? 84 : 76
        })
      })
    })

    list = generated
  }

  if (moduleFilter && moduleFilter !== 'All') {
    const filteredByModule = list.filter((item) => item.chapter === moduleFilter)
    if (filteredByModule.length > 0) list = filteredByModule
  }

  if (difficultyFilter && difficultyFilter !== 'All') {
    const filteredByDiff = list.filter((item) => item.difficulty === difficultyFilter)
    if (filteredByDiff.length > 0) list = filteredByDiff
  }

  return list
}





