from flask import Flask, render_template, request, jsonify
import ollama
import datetime
import os
from ddgs import DDGS

app = app = Flask(__name__, template_folder="lucci_templates")

conversation_history = []

def get_current_time():
    now = datetime.datetime.now()
    return now.strftime("%A, %B %d %Y - %I:%M %p")

def save_note(note):
    with open("notes.txt", "a") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"[{timestamp}] {note}\n")
    return "Note saved successfully."

def load_documents():
    docs = []
    folder = r"C:\Users\seths\lucci_docs"
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            with open(os.path.join(folder, filename), "r") as f:
                content = f.read()
                docs.append("Document: " + filename + "\n" + content)
    return "\n\n".join(docs)

def web_search(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(r["title"] + ": " + r["body"])
    return "\n\n".join(results)

documents = load_documents()

system_prompt = "You are Lucci, a sharp and intelligent personal AI assistant built for Seth. You are direct, confident, and get straight to the point. You help with business ideas, automation, AI tools, and anything Seth needs. You never give long unnecessary responses unless asked. You speak like a smart advisor, not a corporate robot. You have access to the following documents: " + documents

conversation_history.append({"role": "system", "content": system_prompt})

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    user_input_lower = user_input.lower()

    if any(word in user_input_lower for word in ["time", "date", "day", "today"]):
        current_time = get_current_time()
        return jsonify({"response": "Right now it's " + current_time})

    elif any(word in user_input_lower for word in ["search", "research", "find out", "investigate"]):
        search_results = web_search(user_input)
        execute_prompt = "Using these real web search results: " + search_results + "\n\nAnswer this: " + user_input
        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": execute_prompt}]
        )
        reply = response["message"]["content"]
        save_note("Search: " + user_input + "\n" + reply)
        return jsonify({"response": reply})

    elif any(word in user_input_lower for word in ["save", "note", "remember"]):
        save_note(user_input)
        return jsonify({"response": "Got it, note saved."})

    else:
        conversation_history.append({"role": "user", "content": user_input})
        response = ollama.chat(model="llama3.2", messages=conversation_history)
        reply = response["message"]["content"]
        conversation_history.append({"role": "assistant", "content": reply})
        return jsonify({"response": reply})

if __name__ == "__main__":
    app.run(debug=True)