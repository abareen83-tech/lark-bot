from flask import Flask, request, jsonify
import requests
import json
import re
import os

app = Flask(__name__)

# 🔐 Environment Variables
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
SPREADSHEET_TOKEN = os.environ.get("SPREADSHEET_TOKEN")
SHEET_ID = os.environ.get("SHEET_ID")


# 🔐 الحصول على التوكن
def get_tenant_access_token():
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    try:
        response = requests.post(url, json=payload)
        result = response.json()
        return result.get("tenant_access_token")
    except Exception as e:
        print("❌ Token Error:", e)
        return None


# 🧠 استخراج البيانات من الرسالة
def parse_message(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    sample = ""
    date = ""
    formula = ""
    batch_number = ""
    numbers = []

    for line in lines:

        if re.match(r"\d{4}/\d{1,2}/\d{1,2}", line):
            date = line

        elif re.match(r"^C\d+", line):
            batch_number = line

        elif re.match(r"^\d{8}$", line):
            formula = line

        elif re.match(r"^[A-Z]\d+$", line):
            sample = line

        elif "+/-" in line:
            value = line.split("+/-")[0].replace("%", "").strip()
            numbers.append(value)

    mois = numbers[0] if len(numbers) > 0 else ""
    cp   = numbers[1] if len(numbers) > 1 else ""
    ash  = numbers[2] if len(numbers) > 2 else ""
    fat  = numbers[3] if len(numbers) > 3 else ""

    return sample, date, formula, batch_number, mois, cp, ash, fat


# 📝 إضافة صف للشيت
def add_row(token, sample, date, formula, batch_number, mois, cp, ash, fat):
    url = f"https://open.larksuite.com/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values_append"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "valueRange": {
            "range": f"{SHEET_ID}!A:O",
            "values": [[
                "埃及公司",
                "埃及片区",
                sample,
                "",
                "",
                "",
                date,
                formula,
                "",
                batch_number,
                mois,
                cp,
                ash,
                fat,
                "Bareen"
            ]]
        }
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        print("📝 Sheet Response:", response.json())
    except Exception as e:
        print("❌ Sheet Error:", e)


# 📤 إرسال رد للمستخدم
def reply_to_user(token, open_id):
    url = "https://open.larksuite.com/open-apis/im/v1/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({
            "text": "تم تسجيل رسالتك ✅"
        })
    }

    params = {
        "receive_id_type": "open_id"
    }

    try:
        requests.post(url, headers=headers, params=params, json=body)
    except Exception as e:
        print("❌ Reply Error:", e)


# 🤖 Webhook
@app.route("/", methods=["GET", "POST"])
def webhook():

    # اختبار السيرفر من المتصفح
    if request.method == "GET":
        return "Server is running ✅"

    data = request.json

    if not data:
        return "no data"

    # Challenge verification
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    try:
        if data.get("schema") != "2.0":
            return "ignored"

        event = data.get("event", {})
        message = event.get("message")

        if not message:
            print("ℹ️ Not a message event")
            return "ignored"

        content = message.get("content", "{}")
        content_dict = json.loads(content)
        message_text = content_dict.get("text", "")

        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {})
        open_id = sender_id.get("open_id")

        if not open_id:
            print("ℹ️ No open_id found")
            return "ignored"

        token = get_tenant_access_token()
        if not token:
            return "token error"

        sample, date, formula, batch_number, mois, cp, ash, fat = parse_message(message_text)

        add_row(token, sample, date, formula, batch_number, mois, cp, ash, fat)

        reply_to_user(token, open_id)

    except Exception as e:
        print("❌ Webhook Error:", e)

    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
