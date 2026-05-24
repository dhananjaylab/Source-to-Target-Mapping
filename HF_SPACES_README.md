# 🗄️ Oracle Source-to-Target Schema Mapping

[![HF Spaces](https://img.shields.io/badge/HF%20Spaces-blue?logo=huggingface)](https://huggingface.co/spaces)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38.0-red)](https://streamlit.io)

> **AI-assisted Oracle source-to-target column mapping** using **Gemini 2.0 Flash**, **FastAPI**, and **Streamlit**.

Automatically maps source Oracle schema columns to target columns using four signals:
- 🔤 Name similarity & abbreviation expansion
- 🔬 Sample data pattern detection  
- 📐 Type compatibility analysis
- 🧠 Semantic reasoning with Gemini LLM

---

## 🚀 Quick Deploy to HF Spaces

### 1. Fork this repo to your GitHub account

### 2. Create a Hugging Face Space

Go to [huggingface.co/spaces/new](https://huggingface.co/new-space) and:
- Choose **Docker** SDK
- Connect your GitHub repository
- Click **"Create Space"**

### 3. Add Secrets

In your HF Space **Settings → Repository secrets**, add:

| Secret | Value |
|--------|-------|
| `GEMINI_API_KEY` | [Get from makersuite.google.com](https://makersuite.google.com/app/apikey) |

That's it! 🎉 HF Spaces will auto-deploy.

---

## 🏃 Run Locally

### Requirements
- Python 3.12+
- Gemini API key

### Setup

```bash
# Clone repository
git clone <repo-url>
cd oracle-mapping-copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Start Application

```bash
# Option 1: Run startup script (runs both FastAPI + Streamlit)
bash run.sh

# Option 2: Run separately
# Terminal 1 - Backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
streamlit run app.py
```

Visit **http://localhost:8501** (Streamlit UI)

---

## 📋 System Architecture

```
┌──────────────────────────────────────┐
│    Streamlit Frontend (Port 7860)    │
│  Setup → Generate → Review → Export  │
└────────────────┬─────────────────────┘
                 │ HTTP REST
┌────────────────▼─────────────────────┐
│    FastAPI Backend (Port 8000)       │
│  /projects /schemas /mappings /etc   │
└────────┬──────────────────────────────┘
         │
    ┌────▼─────────┐      ┌──────────────┐
    │ Mapping      │      │ Gemini 2.0   │
    │ Engine       │──────│ Flash LLM    │
    │ (inference)  │      │              │
    └──────────────┘      └──────────────┘
```

---

## 📚 Documentation

- **[Deployment Guide](DEPLOYMENT.md)** — Detailed HF Spaces setup
- **[API Documentation](API.md)** — FastAPI endpoints
- **[Architecture](README.md)** — System design & signals

---

## 🔐 Environment Variables

```env
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.0 | REST API backend |
| `streamlit` | 1.38.0 | Web UI |
| `google-genai` | 2.6.0 | Gemini LLM |
| `pydantic` | 2.9.2 | Data validation |
| `pandas` | 2.2.3 | Data processing |

See [requirements.txt](requirements.txt) for full list.

---

## 🎯 Features

✅ **4-Signal Mapping Algorithm**
- Name similarity with abbreviation expansion
- Pattern-based sample analysis
- Type compatibility checking
- Gemini semantic reasoning

✅ **Full Review Workflow**
- Confidence-scored suggestions
- Bulk accept/reject
- Override capabilities
- Audit logging

✅ **Export Options**
- CSV format
- JSON format
- Comprehensive reports

✅ **Performance**
- Parallel schema profiling
- Optimized Gemini prompts
- Streaming results

---

## 🐛 Troubleshooting

### Backend not starting
```bash
# Check logs
tail -f logs/backend.log

# Verify Gemini API key
echo $GEMINI_API_KEY
```

### Streamlit can't connect to backend
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check network in app.py
API_BASE = "http://localhost:8000"
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📝 License

[Add your license here]

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📞 Support

- **HF Spaces**: [Documentation](https://huggingface.co/docs/hub/spaces)
- **Gemini API**: [ai.google.dev](https://ai.google.dev)
- **FastAPI**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Streamlit**: [streamlit.io](https://streamlit.io)

---

**Made with ❤️ for Oracle DBAs and Data Engineers**
