from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from db_helper import handle_db_query
import requests
import os
import base64
from io import BytesIO
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image
from werkzeug.utils import secure_filename
from web_crawler import crawl_website, crawl_form_fields

app = Flask(__name__, template_folder='templates', static_folder='static')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CLAUDE_MCP_URL = "http://localhost:5005/v1/context"
LLAMA_MCP_URL = "http://localhost:11434/api/generate"
FORM_FILLER_API_URL = "http://localhost:9000/submit_form"

uploaded_file_content = ""
uploaded_file_name = ""
crawled_pages = {}

print("🛠️ Loading Stable Diffusion pipeline...")
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32
)
pipe = pipe.to("mps" if torch.backends.mps.is_available() else "cpu")
print("✅ Stable Diffusion pipeline loaded.")

LANGUAGE_HINTS = {
    "en": "Respond in English",
    "hi": "उत्तर हिंदी में दें",
    "ta": "தமிழில் பதிலளி",
    "fr": "Réponds en français",
    "es": "Responde en español",
    "de": "Antworte auf Deutsch"
}


def generate_image_base64(prompt):
    try:
        print(f"🎨 Generating image for: {prompt}")
        image = pipe(prompt).images[0]
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        base64_img = base64.b64encode(buffered.getvalue()).decode()
        print("✅ Image generated successfully.")
        return base64_img
    except Exception as e:
        print(f"❌ Image generation error: {e}")
        return None
def try_file_operations(prompt):
    prompt_lower = prompt.lower().strip()

    if prompt_lower.startswith("create file named"):
        try:
            filename = prompt_lower.replace("create file named", "").strip()
            with open(filename, "w") as f:
                f.write("")
            return f"✅ Created empty file: {filename}"
        except Exception as e:
            return f"❌ Error creating file: {str(e)}"

    elif "create file consist of" in prompt_lower:
        try:
            parts = prompt_lower.split("create file consist of", 1)
            filename = parts[1].strip()

            if not filename.endswith(".py") and "." not in filename:
                return "⚠️ Please specify a valid file format like `.py`, `.txt`, etc."

            code_prompt = f"Write a full working code for {filename}"
            code = get_claude_response(code_prompt) or get_llama_response(code_prompt)

            if not code:
                return "⚠️ Unable to generate code for the file."

            with open(filename, "w") as f:
                f.write(code.strip())

            return f"✅ Created file `{filename}` with AI-generated content."
        except Exception as e:
            return f"❌ Error creating file with content: {str(e)}"

    elif prompt_lower.startswith("update file"):
        try:
            parts = prompt_lower.replace("update file", "").strip().split(" with ")
            if len(parts) != 2:
                return "⚠️ Use: update file <filename> with <content>"
            filename, content = parts
            with open(filename.strip(), "w") as f:
                f.write(content.strip())
            return f"✏️ Updated file: {filename.strip()}"
        except Exception as e:
            return f"❌ Error updating file: {str(e)}"

    elif prompt_lower.startswith("delete file"):
        try:
            filename = prompt_lower.replace("delete file", "").strip()
            if os.path.exists(filename):
                os.remove(filename)
                return f"🗑️ Deleted file: {filename}"
            else:
                return f"⚠️ File not found: {filename}"
        except Exception as e:
            return f"❌ Error deleting file: {str(e)}"

    return None

def try_database(user_input):
    return handle_db_query(user_input)

def get_claude_response(prompt):
    try:
        print(f"🔍 Sending to Claude: {prompt}")
        res = requests.post(CLAUDE_MCP_URL, json={"query": prompt})
        print(f"🔁 Claude response status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            return data.get("choices", [{}])[0].get("content", "").strip()
    except Exception as e:
        print(f"❌ Claude error: {e}")
    return None

def get_llama_response(prompt):
    try:
        print(f"🦙 Sending to LLaMA: {prompt}")
        res = requests.post(LLAMA_MCP_URL, json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        })
        print(f"🔁 LLaMA response status: {res.status_code}")
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception as e:
        print(f"❌ LLaMA error: {e}")
    return "🤖 Sorry, I'm unable to answer this at the moment."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    global uploaded_file_content, uploaded_file_name
    data = request.get_json()
    print("🟢 /ask received:", data)
    user_input = data.get("message", "")
    language_code = data.get("language", "en")
    lang_hint = LANGUAGE_HINTS.get(language_code, "Respond in English")

    if not user_input:
        return jsonify({"reply": "⚠️ Please enter a valid message."})

    if user_input.lower().startswith("crawl"):
        try:
            parts = user_input.split()
            if len(parts) < 2:
                return jsonify({"reply": "⚠️ Usage: crawl <url> [tag] [limit]"})
            url = parts[1]
            tag = parts[2] if len(parts) >= 3 else "p"
            limit = int(parts[3]) if len(parts) >= 4 else 5

            crawl_result = crawl_website(url, tag, limit)
            crawled_pages["last_url"] = url
            crawled_pages["last_url_content"] = crawl_result["text"]
            crawled_pages["last_url_images"] = crawl_result["images"]

            return jsonify({
                "reply": crawl_result["text"],
                "image_urls": crawl_result["images"]
            })
        except Exception as e:
            return jsonify({"reply": f"❌ Crawling error: {str(e)}"})

    if user_input.lower().startswith("register") or user_input.lower().startswith("fill"):
        try:
            parts = user_input.split()
            if len(parts) < 2:
                return jsonify({"reply": "⚠️ Please provide a valid registration link like: `register https://example.com/form`"})

            url = parts[1]
            form_info = crawl_form_fields(url)

            if not form_info or not form_info.get("fields"):
                return jsonify({"reply": "❌ No form fields were found on the provided link."})

            crawled_pages["last_form"] = form_info
            field_list = []
            for field in form_info["fields"]:
                field_list.append(f"- {field['name']} ({field.get('type', 'text')})" + 
                    (" [REQUIRED]" if field.get("required") else " [optional]") +
                    (f", pattern: {field.get('pattern')}" if field.get("pattern") else "") +
                    (f", placeholder: {field.get('placeholder')}" if field.get("placeholder") else "")
                )

            return jsonify({
                "reply": f"📝 Form detected at `{url}` with `{len(form_info['fields'])}` fields. Please reply with values.\n\n" +
                         "Example: `name=Udhay, email=abc@example.com, age=22`\n\n" +
                         "Expected fields:\n" + "\n".join(field_list)
            })
        except Exception as e:
            return jsonify({"reply": f"❌ Error fetching form: {str(e)}"})

    if "=" in user_input and crawled_pages.get("last_form"):
        form_data = {}
        try:
            entries = [x.strip() for x in user_input.split(",")]
            for entry in entries:
                if "=" in entry:
                    key, val = [s.strip() for s in entry.split("=", 1)]
                    form_data[key] = val

            form_info = crawled_pages["last_form"]
            missing = []
            invalid = []

            for field in form_info["fields"]:
                fname = field["name"]
                is_required = field.get("required")
                pattern = field.get("pattern")

                if is_required and fname not in form_data:
                    missing.append(fname)
                elif pattern and fname in form_data:
                    import re
                    if not re.fullmatch(pattern, form_data[fname]):
                        invalid.append((fname, pattern))

            if missing:
                return jsonify({"reply": f"⚠️ Missing required field(s): {', '.join(missing)}"})

            if invalid:
                return jsonify({"reply": "\n".join([
                    f"⚠️ `{name}` must match pattern: `{pat}`" for name, pat in invalid
                ])})

            form_url = form_info["action"]
            method = form_info["method"]

            response = requests.post(FORM_FILLER_API_URL, json={
                "form_url": form_url,
                "method": method,
                "fields": form_data
            })
            result = response.json()

            if result.get("success"):
                return jsonify({"reply": f"✅ Form submitted successfully! Status code: {result['status_code']}"})
            else:
                return jsonify({"reply": f"❌ Error from submission API: {result.get('error')}"})

        except Exception as e:
            return jsonify({"reply": f"❌ Error submitting form: {str(e)}"})

    # -- rest of the existing chatbot logic continues unchanged --


    webpage_content = crawled_pages.get("last_url_content", "")
    if webpage_content and "website" in user_input.lower():
        prompt = f"{lang_hint}\n\nThis is the content I got from a website:\n\n{webpage_content[:4000]}\n\nUser asks: {user_input}"
        llama_response = get_llama_response(prompt)
        return jsonify({"reply": llama_response or "🤖 Sorry, I couldn't answer your website question."})

    if uploaded_file_content and any(word in user_input.lower() for word in [
        "file", "code", "line", "function", "logic", "variable", "describe", "explain",
        "summarize", "output", "compile", "run", "does it work", "fix", "error"]):
        prompt = f"{lang_hint}\n\nThe user uploaded this file `{uploaded_file_name}`. Here is its content:\n\n{uploaded_file_content[:3500]}\n\nNow answer this: {user_input}"
    else:
        prompt = f"{lang_hint}.\n\nUser asked: {user_input}"

    if "read uploaded file" in user_input.lower():
        try:
            files = os.listdir(app.config['UPLOAD_FOLDER'])
            if not files:
                return jsonify({"reply": "⚠️ No uploaded files found."})
            latest_file = sorted(files, key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)))[-1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], latest_file)
            uploaded_file_name = latest_file
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                uploaded_file_content = f.read()
            return jsonify({"reply": uploaded_file_content[:4000]})
        except Exception as e:
            return jsonify({"reply": f"❌ Error reading file: {str(e)}"})

    if "download uploaded file" in user_input.lower():
        try:
            files = os.listdir(app.config['UPLOAD_FOLDER'])
            if not files:
                return jsonify({"reply": "⚠️ No uploaded files found to download."})
            latest_file = sorted(files, key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)))[-1]
            url = f"/download/{latest_file}"
            return jsonify({"reply": f"⬇️ Click here to download your file: {url}"})
        except Exception as e:
            return jsonify({"reply": f"❌ Error preparing download: {str(e)}"})

    if any(word in user_input.lower() for word in ["generate an image", "draw", "sketch", "create an image"]):
        base64_img = generate_image_base64(user_input)
        if base64_img:
            return jsonify({"image": base64_img})
        else:
            return jsonify({"reply": "❌ Failed to generate image."})

    file_response = try_file_operations(user_input)
    if file_response:
        return jsonify({"reply": file_response})

    db_response = try_database(user_input)
    if db_response:
        return jsonify({"reply": db_response})

    llama_response = get_llama_response(prompt)
    return jsonify({"reply": llama_response or "🤖 Sorry, I couldn't generate a response."})

@app.route('/upload', methods=['POST'])
def upload():
    global uploaded_file_content, uploaded_file_name
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"})
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        uploaded_file_name = filename
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            uploaded_file_content = f.read()
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/convert_download', methods=['POST'])
def convert_download():
    data = request.get_json()
    original_filename = data.get('filename')
    new_extension = data.get('extension', 'txt').lstrip('.')

    if not original_filename or not new_extension:
        return jsonify({"error": "Filename and new extension are required."}), 400

    original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    if not os.path.exists(original_path):
        return jsonify({"error": "File not found."}), 404

    try:
        with open(original_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        new_filename = f"{os.path.splitext(original_filename)[0]}.{new_extension}"
        new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({
            "message": f"✅ File converted to {new_extension} successfully.",
            "download_url": f"/download/{new_filename}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Add this proxy route to enable image downloads directly
@app.route('/proxy_image')
def proxy_image():
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400
    try:
        res = requests.get(url, stream=True)
        res.raise_for_status()
        return send_file(BytesIO(res.content), download_name='image.jpg', mimetype='image/jpeg')
    except Exception as e:
        return f"Error fetching image: {str(e)}", 500

if __name__ == '__main__':
    print("✅ MCP Smart Router: Image → File → DB → Claude → LLaMA → WebCrawler (Multilingual + File Uploads Ready)")
    app.run(port=8000, debug=True, use_reloader=False)
