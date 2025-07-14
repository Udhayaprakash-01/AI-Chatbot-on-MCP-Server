import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def crawl_website(url, tag='p', limit=5):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Text content
        elements = soup.find_all(tag)
        text_content = "\n".join([elem.get_text(strip=True) for elem in elements[:limit]])

        # Image URLs
        images = soup.find_all('img')
        image_urls = []
        for img in images:
            src = img.get('src')
            if src:
                if not src.startswith("http"):
                    src = requests.compat.urljoin(url, src)
                image_urls.append(src)

        return {
            "text": text_content or "⚠️ No text content found.",
            "images": image_urls
        }

    except Exception as e:
        return {
            "text": f"❌ Crawling error: {str(e)}",
            "images": []
        }


def crawl_form_fields(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        form = soup.find("form")
        if not form:
            return {"error": "No form found"}

        # ✅ Convert form action to absolute URL
        raw_action = form.get("action") or ""
        full_action_url = urljoin(res.url, raw_action)

        fields = []
        for input_tag in form.find_all("input"):
            name = input_tag.get("name")
            if not name:
                continue  # Skip inputs without a name

            field = {
                "name": name,
                "type": input_tag.get("type", "text"),
                "required": input_tag.has_attr("required"),
                "placeholder": input_tag.get("placeholder"),
                "maxlength": input_tag.get("maxlength"),
                "pattern": input_tag.get("pattern"),
                "label": input_tag.get("aria-label") or name
            }
            fields.append(field)

        return {
            "action": full_action_url,
            "method": form.get("method", "post").lower(),
            "fields": fields
        }

    except Exception as e:
        return {"error": f"❌ Form crawling error: {str(e)}"}
