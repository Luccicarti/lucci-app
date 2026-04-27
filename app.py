from flask import Flask, render_template, request, jsonify
from groq import Groq
import datetime
import os
import json
from ddgs import DDGS

app = Flask(__name__, template_folder='lucci_templates')
client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

MEMORY_FILE = 'memory.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_memory(history):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(history[-50:], f)

conversation_history = load_memory()

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

def get_weather(city):
    with DDGS() as ddgs:
        results = list(ddgs.text(f'current weather in {city} today', max_results=3))
    if results:
        return '\n'.join([r['body'] for r in results])
    return 'Could not fetch weather data.'

system_prompt = '''You are Lucci, a sharp and intelligent personal AI assistant.
You are direct, confident, and get straight to the point.
You help with business ideas, automation, AI tools, research, and programming.
You never give long unnecessary responses unless asked.
You speak like a smart advisor, not a corporate robot.
You have memory of past conversations and reference them when relevant.
You can search the web, check weather, do calculations, and save notes.
When asked to calculate or solve math, always show the working and final answer clearly.'''

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    global conversation_history
    user_input = request.json.get('message')
    user_input_lower = user_input.lower()

    if any(word in user_input_lower for word in ['time', 'date', 'day', 'today']):
        current_time = get_current_time()
        return jsonify({'response': 'Right now it is ' + current_time})

    elif any(word in user_input_lower for word in ['weather', 'temperature', 'forecast', 'raining']):
        weather_data = get_weather(user_input)
        execute_prompt = f'Using this weather data: {weather_data}\n\nAnswer this: {user_input}'
        conversation_history.append({'role': 'user', 'content': execute_prompt})

    elif any(word in user_input_lower for word in ['calculate', 'compute', 'math', 'solve', 'multiply', 'divide', 'add', 'subtract', '%', 'percent']):
        conversation_history.append({'role': 'user', 'content': user_input + ' (solve this mathematically and show the result clearly)'})

    elif any(word in user_input_lower for word in ['search', 'research', 'find out', 'investigate', 'look up']):
        search_results = web_search(user_input)
        execute_prompt = f'Using these real web search results: {search_results}\n\nAnswer this: {user_input}'
        conversation_history.append({'role': 'user', 'content': execute_prompt})

    elif any(word in user_input_lower for word in ['save', 'note', 'remember this']):
        save_note(user_input)
        return jsonify({'response': 'Got it, note saved.'})

    elif 'forget' in user_input_lower or 'clear memory' in user_input_lower:
        conversation_history = []
        save_memory([])
        return jsonify({'response': 'Memory cleared. Starting fresh.'})

    else:
        conversation_history.append({'role': 'user', 'content': user_input})

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'system', 'content': system_prompt}] + conversation_history,
        max_tokens=1024
    )
    reply = response.choices[0].message.content
    conversation_history.append({'role': 'assistant', 'content': reply})
    save_memory(conversation_history)
    return jsonify({'response': reply})

if __name__ == '__main__':
    app.run(debug=True)
