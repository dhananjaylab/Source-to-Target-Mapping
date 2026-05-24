# 🚀 HF Spaces Deployment Quick Start

## What We've Set Up For You

✅ **Dockerfile** — Containerizes your app  
✅ **run.sh** — Starts FastAPI + Streamlit together  
✅ **.streamlit/config.toml** — Optimized Streamlit config for HF Spaces  
✅ **.hf/app-config.yaml** — HF Spaces metadata  
✅ **DEPLOYMENT.md** — Full deployment guide  
✅ **health_check.py** — Verify everything is working  

---

## 3-Minute Deployment

### Step 1: Push to GitHub

```bash
cd a:\Source-to-Target-Mapping
git init
git add .
git commit -m "Add HF Spaces deployment files"
git remote add origin https://github.com/YOUR_USERNAME/oracle-mapping-copilot.git
git push -u origin main
```

### Step 2: Create HF Space

1. Go to **[huggingface.co/spaces/new](https://huggingface.co/new-space)**
2. Select **Docker** SDK
3. Fill in your space name: `oracle-mapping-copilot`
4. Click **"Create Space"**

### Step 3: Connect Repository

1. In your new HF Space, go to **Settings → Repository**
2. Connect your GitHub repo
3. HF Spaces will auto-deploy (takes 2-5 minutes)

### Step 4: Add Secrets

1. Go to **Settings → Repository secrets**
2. Click **"Add new secret"**
3. Add: 
   - **Name:** `GEMINI_API_KEY`
   - **Value:** Your API key from [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
4. Click **"Restart space"** in Settings

### Step 5: Done! 🎉

Your app is now live at:
```
https://huggingface.co/spaces/YOUR_USERNAME/oracle-mapping-copilot
```

---

## Testing Locally First

Test your deployment locally before pushing to HF Spaces:

```bash
# Terminal 1 - Start backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Start frontend
streamlit run app.py

# Terminal 3 - Health check
python health_check.py
```

Visit **http://localhost:8501** to see the UI.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"No module named 'google.genai'"** | Dependencies building - wait 2-3 minutes for Dockerfile build |
| **"401 Unauthorized Gemini API"** | Add `GEMINI_API_KEY` secret and restart space |
| **App won't load** | Check logs: **Settings → Logs** in HF Space |
| **Backend timeout** | Increase Docker build timeout or simplify requirements.txt |

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `run.sh` | Startup script (runs backend + frontend) |
| `.streamlit/config.toml` | Streamlit UI configuration |
| `app.py` | Streamlit frontend |
| `main.py` | FastAPI backend |
| `requirements.txt` | Python dependencies |
| `health_check.py` | System verification script |

---

## Next Steps

After deployment:

1. ✅ Test all mapping features
2. ✅ Monitor HF Spaces logs for errors
3. ✅ Gather user feedback
4. ✅ Update Gemini prompts as needed
5. ✅ Consider adding database persistence

---

## Support

- **HF Spaces Help**: [huggingface.co/docs/hub/spaces](https://huggingface.co/docs/hub/spaces)
- **Docker Issues**: Check `Dockerfile` in your repo
- **API Issues**: Verify `GEMINI_API_KEY` is set in secrets
- **Full Guide**: See `DEPLOYMENT.md`

---

**Questions?** Check the logs in HF Space Settings → Logs first!
