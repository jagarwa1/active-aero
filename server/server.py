import sys
sys.path.append('/home/benchh1/active-aero/lib/python3.11/site-packages')
from flask import Flask, render_template
from flaskwebgui import FlaskUI # import FlaskUI

app = Flask(__name__)

@app.route("/")
def hello():
    return render_template('index.html')

@app.route("/home", methods=['GET'])
def home():
    return render_template('some_page.html')


if __name__ == "__main__":
  # If you are debugging you can do that in the browser:
  # app.run()
  # If you want to view the flaskwebgui window:
  FlaskUI(app=app, server="flask").run()
