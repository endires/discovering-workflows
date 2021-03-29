from wtforms import Form, StringField, SelectField
from flask import Flask, render_template, request
from flask_script import Manager
import sys
import shell_workflow_autocomplete

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    errors = []
    results = {}
    if request.method == "POST":
        # get url that the user has entered
        try:
            x= request.form
            name = x['q']
            results  = shell_workflow_autocomplete.getargums(name)
            return render_template('index.html', errors=errors, results=results,name=name) 
        except:
            errors.append(
                "Unable to get URL. Please make sure it's valid and try again."
            )
        
    return render_template('index.html', errors=errors, results=results)       
    
manager = Manager(app)

if __name__ == '__main__':
    app.run()
    
   