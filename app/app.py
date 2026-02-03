from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/features')
def features():
    return 'soon rendering template features'

@app.route('/documentation')
def documentation():
    return 'soon rendering template documentation'

@app.route('/casestudy_tutorial')
def casestudy_tutorial():
    return 'soon rendering template casestudy tutorial'

if __name__ == '__main__':
    app.run(debug=True)
