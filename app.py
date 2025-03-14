from flask import Flask, request, jsonify, render_template_string
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
    </style>
</head>
<body>
    <div class="container">
        <h1>Enhanced LLM Application</h1>
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

    <script>
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
        
        return jsonify({"response": generated_text})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
