# ollama_helper.py
import requests

def get_ollama_response(prompt):
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "llama3:latest",
                "prompt": prompt,
                "stream": False
            }
        )
        if response.status_code == 200:
            return response.json().get('response', "Sorry, I couldn't understand your question.")
        else:
            return f"Ollama error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error contacting Ollama: {str(e)}"
