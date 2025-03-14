from flask import Flask, request, jsonify, render_template_string
import requests
import os
import sqlite3
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('llm_history.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS history
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     prompt TEXT,
     response TEXT,
     model TEXT,
     timestamp TEXT)
    ''')
    conn.commit()
    conn.close()

init_db()

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced LLM Application</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        textarea {
            width: 100%;
            height: 100px;
            margin-bottom: 10px;
            padding: 10px;
        }
        select, button {
            padding: 10px;
            margin-bottom: 10px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }
        .controls {
            display: flex;
            align-items: center;
        }
        .response {
            margin-top: 20px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
            white-space: pre-wrap;
        }
        .loading {
            display: none;
            margin-left: 10px;
        }
        .history-item {
            border-bottom: 1px solid #eee;
            padding: 10px 0;
        }
        .history-prompt {
            font-weight: bold;
        }
        .history-response {
            margin-top: 5px;
            white-space: pre-wrap;
        }
        .history-meta {
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid #ddd;
            background-color: #f9f9f9;
            margin-right: 5px;
            border-radius: 5px 5px 0 0;
        }
        .tab.active {
            background-color: #fff;
            border-bottom: 1px solid #fff;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <h1>Enhanced LLM Application</h1>
    
    <div class="tabs">
        <div class="tab active" data-tab="generate">Generate</div>
        <div class="tab" data-tab="history">History</div>
    </div>
    
    <div id="generate-tab" class="tab-content active">
        <div class="container">
            <form id="promptForm">
                <textarea id="prompt" placeholder="Enter your prompt here..."></textarea>
                <div class="controls">
                    <select id="model">
                        <option value="google/flan-t5-small">Flan-T5 Small (Fast)</option>
                        <option value="google/flan-t5-base">Flan-T5 Base (Better)</option>
                        <option value="facebook/bart-large-cnn">BART Large CNN (Summarization)</option>
                    </select>
                    <button type="submit">Submit</button>
                    <span id="loading" class="loading">Processing...</span>
                </div>
            </form>
            <div class="response" id="response"></div>
        </div>
    </div>
    
    <div id="history-tab" class="tab-content">
        <div class="container">
            <h2>Query History</h2>
            <div id="history-list">Loading history...</div>
        </div>
    </div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                // Remove active class from all tabs
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                this.classList.add('active');
                document.getElementById(this.dataset.tab + '-tab').classList.add('active');
                
                // Load history if history tab is clicked
                if (this.dataset.tab === 'history') {
                    loadHistory();
                }
            });
        });
        
        // Form submission
        document.getElementById('promptForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const prompt = document.getElementById('prompt').value;
            const model = document.getElementById('model').value;
            const responseElement = document.getElementById('response');
            const loadingElement = document.getElementById('loading');
            
            responseElement.textContent = "";
            loadingElement.style.display = "inline";
            
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        prompt: prompt,
                        model: model
                    })
                });
                
                const data = await response.json();
                if (data.error) {
                    responseElement.textContent = "Error: " + data.error;
                } else {
                    responseElement.textContent = data.response;
                }
            } catch (error) {
                responseElement.textContent = "Error: " + error.message;
            } finally {
                loadingElement.style.display = "none";
            }
        });
        
        // Load history
        async function loadHistory() {
            const historyList = document.getElementById('history-list');
            
            try {
                const response = await fetch('/api/history');
                const data = await response.json();
                
                if (data.history.length === 0) {
                    historyList.innerHTML = '<p>No history yet. Try generating some responses first!</p>';
                    return;
                }
                
                let historyHTML = '';
                data.history.forEach(item => {
                    historyHTML += `
                        <div class="history-item">
                            <div class="history-prompt">Prompt: ${item.prompt}</div>
                            <div class="history-response">Response: ${item.response}</div>
                            <div class="history-meta">Model: ${item.model} | Time: ${item.timestamp}</div>
                        </div>
                    `;
                });
                
                historyList.innerHTML = historyHTML;
            } catch (error) {
                historyList.innerHTML = `<p>Error loading history: ${error.message}</p>`;
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', 'google/flan-t5-small')
    
    # Use the Hugging Face Inference API (free tier)
    API_URL = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Extract the generated text from the response
        result = response.json()
        
        if model.startswith("facebook/bart"):
            # BART models return a different format
            generated_text = result[0]['summary_text'] if isinstance(result, list) else "No response generated"
        else:
            # T5 models
            generated_text = result[0]['generated_text'] if isinstance(result, list) else "No response generated"
        
        # Save to database
        conn = sqlite3.connect('llm_history.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO history (prompt, response, model, timestamp) VALUES (?, ?, ?, ?)",
            (prompt, generated_text, model, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        
        return jsonify({"response": generated_text})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history')
def history():
    conn = sqlite3.connect('llm_history.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM history ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    
    history_items = []
    for row in rows:
        history_items.append({
            "id": row['id'],
            "prompt": row['prompt'],
            "response": row['response'],
            "model": row['model'],
            "timestamp": row['timestamp']
        })
    
    return jsonify({"history": history_items})

if __name__ == '__main__':
    app.run(debug=True)