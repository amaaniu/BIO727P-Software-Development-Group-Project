from flask import Flask, render_template
app = Flask(__name__)

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')