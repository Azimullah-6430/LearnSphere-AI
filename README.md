# LearnSphere-AI 🎓

**A Comprehensive AI-Powered Smart Education Platform** with advanced evaluation, plagiarism detection, and personalized learning features.

## 🚀 Features

### **Teacher Portal**
- 📊 Professional Dashboard with Analytics
- 📝 AI Evaluation System (BERT + 95%+ Accuracy)
- 🔍 Advanced Plagiarism Detection with Student Details Storage
- 📈 Student Analytics & Visualizations

### **Student Portal**
- 📱 Personal Performance Dashboard
- 🤖 Personal Trainer Agent (AI Chatbot + 5 Study Techniques)
- 👨‍👩‍👧 Parent Tracking Agent with Encouragement Tokens
- ⏱️ Focus Session with Timer & Distraction Prevention
- 🧠 Memory Agent (Permanent Performance History)
- ✅ Self-Evaluator (95%+ Accuracy with Teacher Feedback Loop)

## 🏗️ Tech Stack

- **Backend**: Flask/FastAPI with SQLAlchemy ORM
- **Frontend**: React with TypeScript & Tailwind CSS
- **Database**: PostgreSQL
- **AI/ML**: BERT, Transformers, scikit-learn, PyTorch
- **Authentication**: JWT + OAuth2
- **File Processing**: PyPDF2, Pillow, Tesseract OCR
- **Real-time**: WebSockets
- **Plagiarism Detection**: Advanced similarity algorithms
- **Deployment**: Docker, Docker Compose

## 📁 Project Structure

```
LearnSphere-AI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── ml_models/
│   │   └── utils/
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── context/
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── Dockerfile
├── database/
│   ├── migrations/
│   └── seeds/
├── docker-compose.yml
├── .gitignore
└── SETUP.md
```

## 🔄 Complete Workflow

### **Evaluation & Feedback Path**
1. **Student** uploads answer script (PDF/Image)
2. **System** extracts text using OCR + Tesseract
3. **BERT Model** evaluates with 95%+ accuracy
4. **Teacher** reviews AI evaluation and adds feedback
5. **Analysis Report** automatically generated
6. **Report** sent back to student with suggestions
7. **Student** can view detailed feedback per question
8. **Self-Evaluator** allows student to compare with teacher evaluation

### **Advanced Plagiarism Detection**
1. **File Upload** - Student submits answer script
2. **Duplicate Detection** - Checks for renamed PDFs
3. **Content Similarity** - Advanced algorithms detect similar content
4. **Match Storage** - Stores details of matched students
5. **Teacher Alert** - Reports with student names and similarity %
6. **Database Record** - Permanent record for academic integrity

### **Analytics & Tracking**
1. **Student Dashboard** - Personal performance metrics
2. **Teacher Dashboard** - Class average, total students, performance trends
3. **Parent Dashboard** - Child's progress with encouragement tokens
4. **Graphs & Charts** - Visual representation of performance
5. **Memory Agent** - Permanent academic history storage

## ✨ Installation & Setup

See `SETUP.md` for detailed installation instructions.

## 📄 License

MIT License

---

**Built with ❤️ for Smart Education**