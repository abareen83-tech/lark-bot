from flask import Flask, request, jsonify
import requests
import json
import re

app = Flask(__name__)

APP_ID = "cli_a90fa4a689f89ed3"
APP_SECRET = "WuSCjMiT9nJAm0bGVnHgChbmq87YIoDV"   # 🔴 حط السكرت هنا
SPREADSHEET_TOKEN = "FZx9wxhtBiAcxDkisJDl9CPigif"
SHEET_ID = "0qGYgP"


# 🔐 الحصول على التوكن
def get_tenant_access_token():
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    response = requests.post(url, json=payload)
    result = response.json()
    return result.get("tenant_access_token")


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
    fat  = numbers[3] if len(numbers) > 3 else "."

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
                "埃及公司",      # A
                "埃及片区",      # B
                sample,          # C
                "",              # D
                "",              # E
                "",              # F
                date,            # G
                formula,         # H
                "",              # I
                batch_number,    # J
                mois,            # K
                cp,              # L
                ash,             # M
                fat,             # N
                "Bareen"         # O
            ]]
        }
    }

    response = requests.post(url, headers=headers, json=body)
    print("📝 Sheet Response:", response.json())


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

    requests.post(url, headers=headers, params=params, json=body)


# 🤖 Webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    try:
        if data.get("schema") == "2.0":
            content = data["event"]["message"]["content"]
            content_dict = json.loads(content)
            message_text = content_dict.get("text", "")

            open_id = data["event"]["sender"]["sender_id"]["open_id"]

            token = get_tenant_access_token()
            if not token:
                return "fail"

            sample, date, formula, batch_number, mois, cp, ash, fat = parse_message(message_text)

            add_row(token, sample, date, formula, batch_number, mois, cp, ash, fat)

            reply_to_user(token, open_id)

    except Exception as e:
        print("❌ Error:", e)

    return "ok"


if __name__ == "__main__":
    app.run(port=5000, debug=True)
