from flask import Flask, request, render_template_string
import os

app = Flask(__name__)

# Page d'accueil avec formulaire HTML
@app.route("/", methods=["GET"])
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Outil de diagnostic réseau</title>
        </head>
        <body>
            <h1>Test de connectivité</h1>
            <form action="/ping" method="post">
                Adresse IP à ping : <input type="text" name="ip">
                <input type="submit" value="Envoyer">
            </form>
        </body>
        </html>
    ''')

# Route vulnérable à l'injection de commande
@app.route("/ping", methods=["POST"])
def ping():
    ip = request.form.get("ip")
    output = os.popen(f"ping -c 2 {ip}").read()
    return f"<pre>{output}</pre>"

# Lancement de l'app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
