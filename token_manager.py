from flask import Flask, request, render_template_string
import os
import subprocess
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Basic Auth (Hardcoded or Env Var)
AUTH_PIN = os.environ.get("TOKEN_PIN", "123456") 

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot Token Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f0f2f5; }
        .container { max_width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .success { color: green; margin-top: 10px; font-weight: bold; }
        .error { color: red; margin-top: 10px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔑 Update Zerodha Token</h2>
        <form method="POST">
            <label>Security PIN:</label>
            <input type="password" name="pin" placeholder="Enter PIN" required>
            
            <label>New Access Token:</label>
            <input type="text" name="token" placeholder="Paste new token here" required>
            
            <button type="submit">Update & Restart Bot</button>
        </form>
        {% if message %}
            <div class="{{ status }}">{{ message }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

def write_token_file(new_token):
    try:
        with open("zerodha_hot_token.txt", "w") as f:
            f.write(new_token.strip())
        os.chmod("zerodha_hot_token.txt", 0o666)
        return True
    except Exception as e:
        logging.error(f"Error writing token file: {e}")
        return False

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        pin = request.form.get("pin")
        token = request.form.get("token")
        
        if pin != AUTH_PIN:
             return render_template_string(HTML_TEMPLATE, message="❌ Invalid PIN!", status="error")
             
        if not token:
             return render_template_string(HTML_TEMPLATE, message="❌ Token cannot be empty!", status="error")
        
        # Hot Reload Write
        if write_token_file(token):
             return render_template_string(HTML_TEMPLATE, message="✅ Token Saved! Brain will update in ~60s.", status="success")
        else:
            return render_template_string(HTML_TEMPLATE, message="❌ Failed to write token file.", status="error")

    return render_template_string(HTML_TEMPLATE, message="", status="")

    return render_template_string(HTML_TEMPLATE, message="", status="")

if __name__ == "__main__":
    # Host 0.0.0.0 to be accessible externally (GCP)
    app.run(host="0.0.0.0", port=5000)
