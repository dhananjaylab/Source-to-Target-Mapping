# 🚀 Deploying Oracle Mapping Copilot on Hugging Face Spaces

This guide walks you through deploying the Oracle Mapping Copilot on **Hugging Face Spaces**.

---

## Prerequisites

- ✅ Hugging Face account (free at [huggingface.co](https://huggingface.co))
- ✅ Gemini API key (get it at [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey))
- ✅ GitHub account (to fork/push the repository)

---

## Step 1: Prepare Your Repository

### 1a. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Oracle Mapping Copilot"
git remote add origin https://github.com/YOUR_USERNAME/oracle-mapping-copilot.git
git push -u origin main
```

### 1b. Verify Required Files

Ensure these files are in your repository root:

- `app.py` — Streamlit frontend
- `main.py` — FastAPI backend
- `requirements.txt` — Python dependencies
- `run.sh` — Startup script (provided)
- `.streamlit/config.toml` — Streamlit config (provided)

---

## Step 2: Create Hugging Face Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in:
   - **Space name:** `oracle-mapping-copilot`
   - **License:** Choose your preferred license
   - **Space SDK:** Select **"Docker"** (for full control) or **"Python"** (simpler)
4. Click **"Create Space"**

---

## Step 3: Connect Repository

### Option A: Use Docker (Recommended)

1. Create `Dockerfile` in your repo root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make startup script executable
RUN chmod +x run.sh

# Expose ports
EXPOSE 7860 8000

# Run both Streamlit and FastAPI
CMD ["bash", "run.sh"]
```

2. Push Dockerfile to your repo
3. In HF Space settings, connect your GitHub repository
4. HF Spaces will automatically deploy using the Dockerfile

### Option B: Use Python SDK (Simpler)

1. In HF Space, go to **Settings** → **Linked Repositories**
2. Choose your GitHub repo
3. Create `app.py` at root (already exists!)
4. HF Spaces will automatically deploy

---

## Step 4: Add Secrets (API Keys)

1. In your HF Space, go to **Settings** → **Repository secrets**
2. Click **"Add a new secret"**
3. Add these secrets:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | Your Gemini API key from [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) |
| `API_BASE_URL` | `http://localhost:8000` (default, HF Spaces will proxy) |

---

## Step 5: Configure HF Spaces Runtime (Python SDK Method)

Create `.hf/app-config.yaml` in your repo:

```yaml
title: Oracle Mapping Copilot
description: AI-assisted Oracle source-to-target schema mapping
sdk: docker
sdk_version: latest
app_file: app.py
models:
  - text-generation
  - text2text-generation
tags:
  - oracle
  - database
  - mapping
  - ai
```

---

## Step 6: Deploy

### For Docker Method:
1. Commit and push all files:
```bash
git add .
git commit -m "Add deployment files"
git push origin main
```
2. HF Spaces will automatically build and deploy the Dockerfile

### For Python SDK Method:
1. In HF Space settings, select your repo as the space repository
2. HF Spaces will auto-deploy on push

**Status will change from "Building" → "Running"** (takes 2-5 minutes)

---

## Step 7: Access Your Space

Once deployed, your app will be live at:
```
https://huggingface.co/spaces/YOUR_USERNAME/oracle-mapping-copilot
```

The Streamlit UI will be automatically accessible!

---

## Troubleshooting

### App shows "No space specified"
- Verify `app.py` is in repo root
- Check that `requirements.txt` has all dependencies

### Backend (FastAPI) not starting
- Check **Space Logs** in Settings → Logs
- Verify `run.sh` is executable: `chmod +x run.sh`
- Confirm `GEMINI_API_KEY` secret is set

### Streamlit can't connect to backend
- This is handled automatically in HF Spaces (localhost:8000)
- Check logs: `API_BASE_URL=http://localhost:8000` in `app.py`

### API Key not recognized
1. Verify you set the secret in HF Space settings
2. Restart the space: Settings → Restart space
3. Get a new key from [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

### Space times out during build
- HF Spaces has a 1-hour build limit
- Check that all dependencies in `requirements.txt` are available

---

## Environment Variables in HF Spaces

Your secrets automatically become environment variables:

```python
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

---

## Production Considerations

For production on HF Spaces, consider:

1. **Database**: Configure Oracle connection via secrets
2. **Logging**: Enable structured logging to track usage
3. **Rate Limiting**: Add to FastAPI if needed
4. **Monitoring**: Use HF Spaces' built-in logging

---

## Useful Links

- 📖 [HF Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- 🐳 [Docker on HF Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- 🔐 [Managing Secrets in Spaces](https://huggingface.co/docs/hub/spaces-secrets)
- 🧠 [Gemini API Docs](https://ai.google.dev)

---

## Need Help?

- Check HF Spaces logs: **Settings** → **Logs**
- Review requirements.txt compatibility
- Test locally first: `bash run.sh`

Happy deploying! 🚀
