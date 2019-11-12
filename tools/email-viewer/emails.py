from flask import Flask, render_template
import datetime
import os

tmpl_dir = '../../emails'

app = Flask(__name__, template_folder=tmpl_dir)

@app.template_filter()
def user_reference_filter(value):
    return value

@app.template_filter()
def admin_reference(value):
    return value

@app.template_filter()
def repository_reference(value):
    return value

@app.template_filter()
def team_reference(value):
    return value

app.jinja_env.filters['user_reference'] = user_reference_filter
app.jinja_env.filters['admin_reference'] = admin_reference
app.jinja_env.filters['repository_reference'] = repository_reference
app.jinja_env.filters['team_reference'] = team_reference

app_title = 'Quay.io (local)'

def app_link_handler(url=None, title=None):
    """ Just because it is in the original email tempaltes """
    return 'http://example.com/example'

def render_with_options(template=None):
    """ Pass a bunch of common variables when rendering templates """
    return render_template(template, username="exampleuser", user_reference="testing",
        app_logo="https://quay.io/static/img/quay-horizontal-color.svg", token="sdf8SdfKGRME9dse_dfdf",
        app_link=app_link_handler, namespace="booboo", repository="foobar", organization="buynlarge",
        admin_usernames=["lazercat", "booboocoreos"], teamname="creators", inviter="devtable",
        hosted=False, app_title=app_title, app_url="https://quay.io")

def get_templates():
    """ Return a list of the available templates """
    return [t.replace('.html', '') for t in os.listdir('../../emails')]

@app.route("/")
def template_test():
    return render_template('email-template-viewer.html', templates=get_templates())

@app.route("/changeemail")
def changeemail():
    return render_with_options('changeemail.html');

@app.route("/confirmemail")
def confirmemail():
    return render_with_options('confirmemail.html');

@app.route("/emailchanged")
def emailchanged():
    return render_with_options('emailchanged.html');

@app.route("/orgrecovery")
def orgrecovery():
    return render_with_options('orgrecovery.html');

@app.route("/passwordchanged")
def passwordchanged():
    return render_with_options('passwordchanged.html');

@app.route("/paymentfailure")
def paymentfailure():
    return render_with_options('paymentfailure.html');

@app.route("/recovery")
def recovery():
    return render_with_options('recovery.html');

@app.route("/repoauthorizeemail")
def repoauthorizeemail():
    return render_with_options('repoauthorizeemail.html');

@app.route("/teaminvite")
def teaminvite():
    return render_with_options('teaminvite.html');

if __name__ == '__main__':
    app.run(debug=True)
