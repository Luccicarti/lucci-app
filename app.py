from flask import Flask, render_template, request, jsonify
from groq import Groq
import datetime
import os
from ddgs import DDGS

app = Flask(__name__, template_folder='lucci_templates')
client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
conversation_history = []

def get_current_time():
    now = datetime.datetime.now()
    return now.strftime('%A, %B %d %Y - %I:%M %p')

def save_note(note):
    with open('notes.txt', 'a') as f:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        f.write(f'[{timestamp}] {note}\n')
    return 'Note saved successfully.'

def web_search(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(r['title'] + ': ' + r['body'])
    return '\n\n'.join(results)

system_prompt = 'You are Lucci, a sharp and intelligent personal AI assistant. You are direct, confident, and get straight to the point. You help with business ideas, automation, AI tools, research, and programming. You never give long unnecessary responses unless asked. You speak like a smart advisor, not a corporate robot.'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    user_input_lower = user_input.lower()
    if any(word in user_input_lower for word in ['time', 'date', 'day', 'today']):
        current_time = get_current_time()
        return jsonify({'response': 'Right now it is ' + current_time})
    elif any(word in user_input_lower for word in ['search', 'research', 'find out', 'investigate']):
        search_results = web_search(user_input)
        execute_prompt = 'Using these real web search results: ' + search_results + '\n\nAnswer this: ' + user_input
        conversation_history.append({'role': 'user', 'content': execute_prompt})
    elif any(word in user_input_lower for word in ['save', 'note', 'remember']):
        save_note(user_input)
        return jsonify({'response': 'Got it, note saved.'})
    else:
        conversation_history.append({'role': 'user', 'content': user_input})
    response = client.chat.completions.create(model='llama3-70b-8192', messages=[{'role': 'system', 'content': system_prompt}] + conversation_history, max_tokens=1024)
    reply = response.choices[0].message.content
    conversation_history.append({'role': 'assistant', 'content': reply})
    return jsonify({'response': reply})

if __name__ == '__main__':
    app.run(debug=True)
