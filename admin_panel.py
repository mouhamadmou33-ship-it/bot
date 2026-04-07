from flask import Flask, render_template_string, request, redirect, url_for, session
import json

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # غيّرها في الإنتاج

ADMIN_PASSWORD = "admin123"  # غيّر كلمة المرور لاحقًا

TEMPLATE = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>لوحة تحكم البوت</title>
    <style>
        body { font-family: Tahoma, Arial; direction: rtl; background: #f9f9f9; }
        table { border-collapse: collapse; width: 100%; background: #fff; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
        th { background: #eee; }
        .container { max-width: 900px; margin: 40px auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px #0001; }
        .logout { float: left; }
    </style>
</head>
<body>
<div class="container">
    <h2>لوحة تحكم البوت</h2>
    <form method="post" action="/logout" class="logout"><button type="submit">تسجيل خروج</button></form>
    <table>
        <tr>
            <th>معرف المستخدم</th>
            <th>الرسالة</th>
            <th>الوقت</th>
        </tr>
        {% for log in logs %}
        <tr>
            <td>{{ log.user_id }}</td>
            <td>{{ log.message }}</td>
            <td>{{ log.timestamp }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تسجيل دخول الأدمن</title>
    <style>
        body { font-family: Tahoma, Arial; direction: rtl; background: #f9f9f9; }
        .login-box { max-width: 350px; margin: 100px auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px #0001; }
        input { width: 100%; padding: 8px; margin: 10px 0; }
        button { width: 100%; padding: 8px; }
        .error { color: red; }
    </style>
</head>
<body>
<div class="login-box">
    <h2>تسجيل دخول الأدمن</h2>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="post">
        <input type="password" name="password" placeholder="كلمة المرور" required>
        <button type="submit">دخول</button>
    </form>
</div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="كلمة المرور غير صحيحة")
    return render_template_string(LOGIN_TEMPLATE, error=None)


@app.route("/panel")
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("login"))
    logs = []
    try:
        with open("logs.jsonl", encoding="utf-8") as f:
            for line in f:
                log = json.loads(line.strip())
                logs.append(log)
    except FileNotFoundError:
        pass
    logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
    return render_template_string(TEMPLATE, logs=logs)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
