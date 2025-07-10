from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import json
import os

# Get the absolute path of the directory where this file is located (/api)
# This is crucial for Vercel's serverless environment.
base_dir = os.path.dirname(os.path.abspath(__file__))

# --- CHANGE 1: Point Flask to the correct template and static folders ---
# The folders are one level up (../) from the /api directory.
app = Flask(__name__,
            template_folder=os.path.join(base_dir, '../templates'))

# --- CHANGE 2: Update CORS for deployment ---
# After you deploy, replace "YOUR_VERCEL_URL_HERE" with your actual Vercel URL.
# For example: "https://your-project-name.vercel.app"
CORS(app, resources={r"/chat": {"origins": ["https://YOUR_VERCEL_URL_HERE", "http://127.0.0.1:5000"]}})

# --- CHANGE 3: Securely get API key from Vercel Environment Variables ---
# Never hardcode your API key in the source code.
API_KEY = os.environ.get('GEMINI_API_KEY')

API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}'

SYSTEM_PROMPT = """You are a compassionate and thoughtful AI chatbot named 'Aura'. 
You are trained to provide mental and emotional support. 
You must speak in a warm, relatable, and non-judgmental tone. 
Your goal is to help users express their feelings and provide grounded, realistic advice or reflections based on what they say. 
You do not diagnose, but you support users emotionally and suggest small, meaningful actions they can take.
Always try to ask a follow-up question to encourage reflection and conversation.
When a user expresses sadness, anxiety, fear, or self-doubt, respond with empathy and give a practical and gentle suggestion.
Use relatable language (like a wise, kind friend) and AVOID clichés or toxic positivity (e.g., "just be positive!", "everything happens for a reason").
Keep your responses concise, around 2-4 sentences.
You can suggest quick replies by ending your message with bracketed options, like: That sounds tough. Would you like to talk more about it? [Yes] [Tell me more]
You can display an image by using the format [image: URL_OF_IMAGE].
"""

@app.route('/chat', methods=['POST'])
def chat():
    # Check if the API key is missing
    if not API_KEY:
        return jsonify({'error': 'API key is not configured on the server.'}), 500
        
    user_message = request.json.get('message')
    history = request.json.get('history', [])

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    formatted_history = "\n".join(history)
    
    prompt_with_context = f"{SYSTEM_PROMPT}\n\n--- Start of Chat History ---\n{formatted_history}\n--- End of Chat History ---\n\nUser: {user_message}\nAura:"

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"text": prompt_with_context}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 200,
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(data), timeout=20)
        response.raise_for_status()
        response_data = response.json()
        
        if 'candidates' not in response_data or not response_data['candidates']:
             raise KeyError("Missing 'candidates' in response")
        if 'content' not in response_data['candidates'][0] or 'parts' not in response_data['candidates'][0]['content']:
             raise KeyError("Missing 'content' or 'parts' in candidate")

        bot_text = response_data['candidates'][0]['content']['parts'][0].get('text', 'Sorry, I couldn’t process that.')
        return jsonify({'reply': bot_text.strip()})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to connect to the AI service: {str(e)}'}), 500
    except (KeyError, IndexError) as e:
        print(f"API Response Error: {e}\nResponse Data: {response.text}")
        return jsonify({'error': 'The AI service returned an unexpected response format.'}), 500

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/messenger')
def serve_messenger():
    return render_template('messenger.html')

# --- CHANGE 4: The app.run() block is removed ---
# Vercel handles the server execution, so this is no longer needed.
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)
