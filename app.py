from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

contacts = []


@app.route("/")
def home():
    return render_template("index_reeya.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/submit", methods=["POST"])
def submit():

    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if not name or not email or not message:
        return "All fields are required", 400

    contacts.append({
        "name": name,
        "email": email,
        "message": message
    })

    return redirect(url_for("success"))


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/contacts")
def get_contacts():
    return contacts


if __name__ == "__main__":
    app.run(debug=True)