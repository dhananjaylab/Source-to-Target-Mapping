#!/usr/bin/env python3
"""
Health check script for Oracle Mapping Copilot
Verifies both FastAPI backend and Gemini API are accessible
"""

import requests
import os
import sys
from time import sleep

def check_backend():
    """Check if FastAPI backend is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI backend is running")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ FastAPI backend is not running on localhost:8000")
        return False
    except Exception as e:
        print(f"⚠️  Backend check failed: {e}")
        return False

def check_gemini_api():
    """Check if Gemini API key is configured"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        return False
    
    if len(api_key) < 20:
        print("❌ GEMINI_API_KEY appears invalid (too short)")
        return False
    
    print("✅ GEMINI_API_KEY is configured")
    return True

def check_streamlit():
    """Check if Streamlit is accessible"""
    try:
        response = requests.get("http://localhost:7860", timeout=5)
        if response.status_code == 200:
            print("✅ Streamlit frontend is running")
            return True
    except requests.exceptions.ConnectionError:
        print("⚠️  Streamlit not yet running (this is normal on startup)")
        return None
    except Exception as e:
        print(f"⚠️  Streamlit check failed: {e}")
        return None

def main():
    print("🔍 Performing health checks...\n")
    
    backend_ok = check_backend()
    gemini_ok = check_gemini_api()
    streamlit_ok = check_streamlit()
    
    print("\n" + "="*50)
    
    if backend_ok and gemini_ok:
        print("✅ All critical systems operational!")
        return 0
    else:
        print("❌ Some critical systems are not operational")
        return 1

if __name__ == "__main__":
    sys.exit(main())
