#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Armin Chat Bot - Server
چت بات پیشرفته با اتصال به اینترنت و OpenAI
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

# ===== تنظیمات =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def has_web_intent(message: str) -> bool:
    """بررسی اینکه پیام نیاز به جستجوی وب دارد"""
    text = message.lower()
    triggers = [
        "latest", "news", "today", "weather", "price", "current", "who is", "what is",
        "when", "where", "how to", "status", "trend", "market", "recent",
        "امروز", "اخبار", "قیمت", "آب و هوا", "کیست", "چیست", "چطور", "کجا", "چرا"
    ]
    return any(t in text for t in triggers)

def duckduckgo_search(query: str):
    """جستجو در اینترنت با DuckDuckGo"""
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        results = []
        abstract = data.get("AbstractText", "").strip()
        abstract_url = data.get("AbstractURL", "").strip()
        heading = data.get("Heading", "نتیجه").strip()
        
        if abstract:
            results.append({
                "title": heading,
                "url": abstract_url or "https://duckduckgo.com/",
                "snippet": abstract
            })

        for item in data.get("RelatedTopics", [])[:5]:
            if isinstance(item, dict):
                title = (item.get("Text") or "").strip()
                url = (item.get("FirstURL") or "").strip()
                if title:
                    results.append({
                        "title": title[:120],
                        "url": url or "https://duckduckgo.com/",
                        "snippet": title
                    })

        return results[:5]
    except Exception as e:
        print(f"❌ خطا در جستجو: {e}")
        return []

def call_openai(messages):
    """فراخوانی OpenAI API"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800
    }
    response = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def fallback_response(user_message, search_results):
    """پاسخ پیشفرض اگر OpenAI موجود نباشد"""
    msg = user_message.lower()
    
    if any(word in msg for word in ["سلام", "hello", "hi", "درود"]):
        return "سلام! خوش اومدی. چطور می‌توانم کمکت کنم؟"
    
    if any(word in msg for word in ["ساعت", "time", "clock"]):
        return f"الان ساعت {datetime.now().strftime('%H:%M:%S')} است."
    
    if any(word in msg for word in ["تاریخ", "date", "امروز", "today"]):
        return f"امروز {datetime.now().strftime('%Y/%m/%d')} است."
    
    if search_results:
        context = "\n".join(f"- {r['title']}: {r['snippet']}" for r in search_results[:3])
        return "من از نتایج جست‌وجو استفاده می‌کنم:\n\n" + context
    
    if any(word in msg for word in ["خوبی", "حال", "status"]):
        return "مرسی، من خوبم و آماده‌ام."
    
    return "من در حالت بدون API کار می‌کنم. اگر کلید OpenAI را تنظیم کنی، پاسخ‌های دقیق‌تر می‌گیرم."

@app.route("/")
def index():
    """رابط کاربری اصلی"""
    return render_template_string("""
    <!doctype html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>چت بات Armin</title>
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                background: linear-gradient(135deg, #0f172a, #111827);
                font-family: Tahoma, Arial, sans-serif;
                color: #e2e8f0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .chat-box {
                width: min(900px, 95vw);
                height: 88vh;
                background: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 20px;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            }
            .header {
                background: linear-gradient(135deg, #1e293b, #334155);
                padding: 18px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(148, 163, 184, 0.2);
            }
            .title {
                font-weight: bold;
                font-size: 1.2rem;
                color: #f1f5f9;
            }
            .status {
                color: #86efac;
                font-size: 0.8rem;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .status::before {
                content: "●";
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 12px;
                background: rgba(15, 23, 42, 0.85);
            }
            .msg {
                max-width: 75%;
                padding: 12px 16px;
                border-radius: 16px;
                line-height: 1.7;
                white-space: pre-wrap;
                word-wrap: break-word;
                animation: slideIn 0.3s ease-out;
            }
            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .user {
                align-self: flex-end;
                background: linear-gradient(135deg, #2563eb, #3b82f6);
                color: white;
            }
            .bot {
                align-self: flex-start;
                background: rgba(51, 65, 85, 0.95);
                color: #e2e8f0;
                border: 1px solid rgba(148, 163, 184, 0.15);
            }
            .input-area {
                display: flex;
                gap: 10px;
                padding: 14px 16px 18px;
                background: rgba(15, 23, 42, 0.95);
                border-top: 1px solid rgba(148, 163, 184, 0.2);
            }
            textarea {
                flex: 1;
                resize: none;
                border: none;
                border-radius: 12px;
                background: rgba(30, 41, 59, 0.9);
                color: white;
                padding: 14px 16px;
                font-size: 1rem;
                outline: none;
                font-family: inherit;
                min-height: 50px;
                max-height: 160px;
            }
            button {
                border: none;
                border-radius: 12px;
                background: linear-gradient(135deg, #22c55e, #16a34a);
                color: white;
                font-weight: bold;
                padding: 0 22px;
                cursor: pointer;
                transition: filter 0.2s;
            }
            button:hover { filter: brightness(1.08); }
            button:active { filter: brightness(0.95); }
            .search-box {
                display: none;
                margin: 0 16px 12px;
                padding: 12px;
                border-radius: 12px;
                background: rgba(13, 148, 136, 0.12);
                border: 1px solid rgba(45, 212, 191, 0.2);
                color: #d1fae5;
                font-size: 0.9rem;
            }
            .search-box a {
                color: #a7f3d0;
                text-decoration: none;
            }
            .search-box a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="chat-box">
            <div class="header">
                <div class="title">🤖 چت بات Armin</div>
                <div class="status">آنلاین</div>
            </div>

            <div id="messages" class="messages">
                <div class="msg bot">سلام! من Armin هستم. هر سوالی داری بپرس! 😊</div>
            </div>

            <div id="searchBox" class="search-box"></div>

            <div class="input-area">
                <textarea id="messageInput" placeholder="پیام خود را بنویسید..."></textarea>
                <button id="sendBtn">ارسال</button>
            </div>
        </div>

        <script src="/static/app.js"></script>
    </body>
    </html>
    """)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """API برای پردازش پیام"""
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "پیام خالی است"}), 400

    search_results = []
    try:
        if has_web_intent(user_message):
            search_results = duckduckgo_search(user_message)
    except Exception:
        pass

    try:
        if OPENAI_API_KEY:
            system_prompt = "You are a helpful Persian assistant named Armin. Answer in Persian. Use web results when relevant."
            messages = [{"role": "system", "content": system_prompt}]
            
            for item in history[-12:]:
                if "role" in item and "content" in item:
                    messages.append({"role": item["role"], "content": item["content"]})
            
            if search_results:
                context = "\n".join(f"[{i+1}] {r['title']} ({r['url']})" for i, r in enumerate(search_results[:3]))
                messages.append({"role": "user", "content": user_message + f"\n\nWeb context:\n{context}"})
            else:
                messages.append({"role": "user", "content": user_message})
            
            reply = call_openai(messages)
        else:
            reply = fallback_response(user_message, search_results)
    except Exception as e:
        reply = f"خطا: {str(e)}"

    return jsonify({
        "reply": reply,
        "search": search_results[:3]
    })

@app.route("/api/health")
def health():
    """بررسی وضعیت سرور"""
    return jsonify({
        "status": "ok",
        "time": now_str(),
        "openai_configured": bool(OPENAI_API_KEY)
    })

if __name__ == "__main__":
    print("🚀 سرور در حال اجرا... http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
