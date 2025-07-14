from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
import os
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)

def fill_form_with_selenium(form_url, fields):
    try:
        options = Options()
        # Comment this line to see the browser
        #options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        chromedriver_path = os.path.join(os.getcwd(), "chromedriver")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)

        print(f"🌐 Opening form URL: {form_url}")
        driver.get(form_url)
        time.sleep(5)

        # Screenshot before filling
        #driver.save_screenshot("form_loaded.png")
        #print("📸 Saved screenshot: form_loaded.png")

        filled_fields = set()

        for name, value in fields.items():
            print(f"\n🔍 Searching for field: {name} with value: {value}")
            element = None
            found = False

            selectors = [
                (By.NAME, name),
                (By.ID, name),
                (By.XPATH, f"//*[@placeholder='{name}']"),
                (By.XPATH, f"//*[contains(@placeholder, '{name}')]"),
                (By.XPATH, f"//*[contains(@name, '{name}')]"),
                (By.XPATH, f"//*[contains(@id, '{name}')]"),
            ]

            for by, query in selectors:
                try:
                    print(f"  Trying selector: {by} -> {query}")
                    element = driver.find_element(by, query)
                    print(f"  ✅ Found element using: {by}")
                    found = True
                    break
                except Exception as e:
                    print(f"  ❌ Not found using: {by}")

            if not found:
                print(f"❌ Could not find field: {name}")
                continue

            try:
                tag = element.tag_name
                input_type = element.get_attribute("type") or ""

                if tag == "input":
                    if input_type in ["checkbox", "radio"]:
                        if element.get_attribute("value") == value or value.lower() in ["true", "on", "yes"]:
                            element.click()
                    else:
                        element.clear()
                        element.send_keys(value)
                elif tag == "textarea":
                    element.clear()
                    element.send_keys(value)
                elif tag == "select":
                    Select(element).select_by_visible_text(value)

                filled_fields.add(name)
                print(f"✅ Filled field: {name}")

            except Exception as e:
                print(f"⚠️ Could not fill field '{name}': {e}")
        
        # Screenshot after filling
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"filled_form_{timestamp}.png"
        driver.save_screenshot(screenshot_filename)
        print(f"📸 Saved screenshot: {screenshot_filename}")

        print("📸 Saved screenshot: form_loaded.png")

        # Try submitting the form
        try:
            form = driver.find_element(By.TAG_NAME, "form")
            try:
                driver.find_element(By.XPATH, "//input[@type='submit' or @type='image' or @type='button']").click()
                print("✅ Clicked submit button")
            except Exception as e:
                print(f"⚠️ Could not click submit button: {e}")
            print("📤 Form submitted using <form>.submit()")
        except Exception:
            try:
                submit_button = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit'] | //button")
                submit_button.click()
                print("📤 Form submitted using submit button")
            except Exception as e:
                print(f"⚠️ Could not submit form: {e}")

        time.sleep(2)
        final_url = driver.current_url
        screenshot = driver.get_screenshot_as_base64()
        #driver.quit()

        return {
            "success": True,
            "final_url": final_url,
            "filled_fields": list(filled_fields),
            "screenshot_base64": screenshot
        }

    except Exception as e:
        print(f"❌ Exception in form filling: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received", "status_code": 400}), 400

        form_url = data.get('form_url')
        fields = data.get('fields', {})

        if not form_url or not fields:
            return jsonify({
                "success": False,
                "error": "Missing 'form_url' or 'fields' in request",
                "status_code": 400
            }), 400

        parsed_url = urlparse(form_url)
        if not parsed_url.scheme.startswith("http"):
            return jsonify({
                "success": False,
                "error": "Invalid form URL",
                "status_code": 400
            }), 400

        print(f"\n📤 Submitting form to: {form_url}")
        print(f"📝 Fields: {fields}")

        result = fill_form_with_selenium(form_url, fields)

        if result.get("success"):
            return jsonify({
                "success": True,
                "message": "✅ Form filled and submitted via browser",
                "final_url": result.get("final_url", ""),
                "filled_fields": result.get("filled_fields", []),
                "screenshot_base64": result.get("screenshot_base64", ""),
                "status_code": 200
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Unknown error"),
                "status_code": 500
            }), 500

    except Exception as e:
        print(f"❌ Submission Error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "status_code": 500
        }), 500

if __name__ == '__main__':
    print("🚀 REST API for form submission running at http://localhost:9000/submit_form")
    app.run(port=9000, debug=True)
