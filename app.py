from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from groq import Groq
import datetime
import os
import base64
import urllib.parse
import json
from ddgs import DDGS

app = Flask(__name__, template_folder="lucci_templates")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

conversation_history = []

def get_current_time():
    now = datetime.datetime.now()
    return now.strftime("%A, %B %d %Y - %I:%M %p")

def save_note(note):
    with open("notes.txt", "a") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"[{timestamp}] {note}\n")
    return "Note saved successfully."

def web_search(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(r["title"] + ": " + r["body"])
    return "\n\n".join(results)

system_prompt = "You are Lucci, a sharp and intelligent personal AI assistant. You are direct, confident, and get straight to the point. You help with business ideas, automation, AI tools, research, and programming. You never give long unnecessary responses unless asked. You speak like a smart advisor, not a corporate robot."

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    user_input_lower = user_input.lower()

    # ── BLOCK GROQ FROM HANDLING IMAGE GENERATION ──
    generate_triggers = ["generate image", "create image", "draw", "imagine", "make an image", "paint", "generate an image"]
    if any(trigger in user_input_lower for trigger in generate_triggers):
        return jsonify({"skip": True})

    if any(word in user_input_lower for word in ["time", "date", "day", "today"]):
        current_time = get_current_time()
        return jsonify({"response": "Right now it's " + current_time})

    elif any(word in user_input_lower for word in ["search", "research", "find out", "investigate"]):
        search_results = web_search(user_input)
        execute_prompt = "Using these real web search results: " + search_results + "\n\nAnswer this: " + user_input
        conversation_history.append({"role": "user", "content": execute_prompt})

    elif any(word in user_input_lower for word in ["save", "note", "remember"]):
        save_note(user_input)
        return jsonify({"response": "Got it, note saved."})

    else:
        conversation_history.append({"role": "user", "content": user_input})

    def generate():
        full_reply = ""
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + conversation_history,
            max_tokens=1024,
            stream=True
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            full_reply += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        conversation_history.append({"role": "assistant", "content": full_reply})
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ── PHASE 1: AI VISION ──────────────────────────────────────────
@app.route("/vision", methods=["POST"])
def vision():
    if "image" not in request.files:
        return jsonify({"response": "No image received."})

    image_file = request.files["image"]
    prompt = request.form.get("prompt", "Describe this image in detail.")

    image_data = base64.b64encode(image_file.read()).decode("utf-8")
    mime_type = image_file.content_type

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=1024
    )

    reply = response.choices[0].message.content
    return jsonify({"response": reply})


# ── PHASE 2: IMAGE GENERATION ───────────────────────────────────
@app.route("/imagine", methods=["POST"])
def imagine():
    prompt = request.json.get("prompt", "")
    if not prompt:
        return jsonify({"response": "No prompt given."})

    encoded = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true&enhance=true&seed={int(datetime.datetime.now().timestamp())}"
    return jsonify({"image_url": image_url})


if __name__ == "__main__":
    app.run(debug=True)
