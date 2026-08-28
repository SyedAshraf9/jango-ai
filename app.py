from flask import Flask, request, jsonify, render_template
import requests
import json
import os
import re

app = Flask(__name__)

# ========== CONFIG ==========
HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
MEMORY_FILE = "memory.json"
MAX_MEMORY_TURNS = 10
MAX_MESSAGE_LENGTH = 500

SYSTEM_PROMPT = """You are Jango, a casual friend who talks in slang. STRICT RULES:
- Match the user's energy and slang exactly
- Simple questions = 1-2 short sentences max
- Complex questions = 3-4 simple sentences max
- NEVER formal. Never say 'certainly', 'indeed', 'how may I assist you', 'as an AI'
- Use casual words like 'bruh', 'ngl', 'bet', 'aight', 'fam', 'vibe', 'lowkey', 'cap', 'no cap'
- Talk like you're texting a close friend, not a robot
- Your name is Jango. Respond naturally when called.
- Be concise. Don't ramble."""

# ========== MEMORY ==========
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            pass
    return []

def save_memory(turns):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(turns[-MAX_MEMORY_TURNS:], f)
    except Exception as e:
        print(f"Memory save error: {e}")

# ========== HF API ==========
def format_qwen_prompt(messages):
    prompt = ""
    for m in messages:
        if m["role"] == "system":
            prompt += f"<|im_start|>system\n{m['content']}<|im_end|>\n"
        elif m["role"] == "user":
            prompt += f"<|im_start|>user\n{m['content']}<|im_end|>\n"
        elif m["role"] == "assistant":
            prompt += f"<|im_start|>assistant\n{m['content']}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    return prompt

def ask_ai(messages):
    if not HF_TOKEN:
        return "bruh, I need a brain token. Set HF_TOKEN in environment variables."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    
    # Try modern chat completions endpoint
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/v1/chat/completions",
            headers=headers,
            json={"model": MODEL, "messages": messages, "max_tokens": 120, "temperature": 0.85, "top_p": 0.9},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    
    # Fallback to legacy text generation
    try:
        prompt = format_qwen_prompt(messages)
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{MODEL}",
            headers=headers,
            json={"inputs": prompt, "parameters": {"max_new_tokens": 120, "temperature": 0.85, "top_p": 0.9, "return_full_text": False}},
            timeout=30
        )
        if r.status_code == 200:
            text = r.json()[0]["generated_text"].strip()
            return re.sub(r'<\|.*?\|>', '', text)
    except:
        pass
    
    return "bruh my brain glitched, try again in a sec."

# ========== ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_msg = data.get('message', '').strip()[:MAX_MESSAGE_LENGTH]
    
    if not user_msg:
        return jsonify({"reply": "Yo, I didn't catch that. Say something, fam."})
    
    memory = load_memory()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in memory:
        messages.append({"role": "user", "content": turn.get("user", "")})
        messages.append({"role": "assistant", "content": turn.get("assistant", "")})
    messages.append({"role": "user", "content": user_msg})
    
    reply = ask_ai(messages)
    reply = reply.replace('<|im_end|>', '').replace('<|endoftext|>', '').strip()
    
    memory.append({"user": user_msg, "assistant": reply})
    save_memory(memory)
    
    return jsonify({"reply": reply})

@app.route('/clear-memory', methods=['POST'])
def clear_memory():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    return jsonify({"status": "Memory cleared, fam. Fresh start."})

@app.route('/health')
def health():
    return jsonify({"status": "Jango is awake"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)