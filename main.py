from flask import Flask, render_template, request, session, redirect, url_for, abort, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import json, math, os
from datetime import datetime
from werkzeug.utils import secure_filename
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

with open('Python\Flask\IdeaSpace\config.json', 'r') as c:
    params = json.load(c)["params"]

isLocalServer = True

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['imgLocation']

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['emailUser'],
    MAIL_PASSWORD=params['emailPassword']
)
mail = Mail(app)

if isLocalServer:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['localURI']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['productionURI']

db = SQLAlchemy(app)

class Posts(db.Model):
    p_no = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    img_file = db.Column(db.String(20), nullable=True)
    date = db.Column(db.String(12), nullable=True)
    slug = db.Column(db.String(25), nullable=True)

class Contact(db.Model):
    m_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for('login.html'))
        return func(*args, **kwargs)
    return decorated_function


@app.route("/login")
def login_page():
    if "user" in session and session['user'] == params['username']:
        return redirect('/')
    else:
        if request.method == 'POST':
            username = request.form.get('uname')
            password = request.form.get('password')
            if params['username'] == username and params['password'] == password:
                session['user'] = username
                posts = Posts.query.all()
                return render_template('index.html', params=params, posts=posts)
            else:
                flash("Invalid username or password.", "danger")
                return render_template('error.html', error_message="Invalid username or password.")
        return render_template('login.html', params=params)



@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/login')


@app.route("/dashboard" , methods=['GET','POST'])
def dashboard():
    if "user" in session and session['user']==params['username']:
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    if request.method=='POST':
        username = request.form.get('uname')
        password = request.form.get('password')
        if(params['username']==username and params['password']==password):
            session['user'] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            return render_template("login.html", params=params)
        
    return render_template("login.html", params=params)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['noOfPosts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['noOfPosts']):(page-1)*int(params['noOfPosts'])+ int(params['noOfPosts'])]
    if page==1:
        prev = "#"
        next = "/?page="+ str(page+1)
    elif page==last:
        prev = "/?page="+ str(page-1)
        next = "#"
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)
    
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/post/<string:post_slug>", methods=['GET'])
@login_required
def postRoute(post_slug):
    try:
        post = Posts.query.filter_by(slug=post_slug).first()
        if not post:
            abort(404)
        return render_template('post.html', params=params, post=post)
    except SQLAlchemyError as e:
        return render_template('error.html', error_message="An error occurred while fetching the post."), 500



@app.route("/edit/<string:p_no>", methods=['GET', 'POST'])
@login_required
def edit(p_no):
    if "user" in session and session['user'] == params['username']:
        try:
            post = None
            if p_no != '0':
                post = Posts.query.filter_by(p_no=p_no).first()
                if not post:
                    abort(404)

            if request.method == "POST":
                title = request.form.get('title')
                slug = request.form.get('slug')
                content = request.form.get('content')
                img_file = request.files.get('img_file')
                date = datetime.now()

                if p_no == '0':
                    post = Posts(title=title, slug=slug, content=content, date=date)
                else:
                    post.title = title
                    post.slug = slug
                    post.content = content
                    post.date = date

                if img_file:
                    filename = secure_filename(img_file.filename)
                    img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    post.img_file = filename

                db.session.add(post)
                db.session.commit()

                flash("Post Edited Successfully", "success")
                return redirect('/edit/' + str(post.p_no))

        except SQLAlchemyError as e:
            flash("An error occurred while editing the post.", "danger")

    return render_template('edit.html', params=params, post=post, p_no=p_no)


@app.route("/delete/<string:p_no>", methods=['POST'])
def delete_post(p_no):
    if "user" in session and session['user'] == params['username']:
        post = Posts.query.filter_by(p_no=p_no).first()

        if post:
                db.session.delete(post)
                db.session.commit()
        else:
            abort(404)

    return redirect('/dashboard')


@app.route("/about")
def about():
    return render_template('about.html', params=params)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        msg = request.form.get('msg')
        
        if not name or not email or not phone or not msg:
            flash("All fields are required.", "danger")
            return render_template('contact.html', params=params)

        entry = Contact(name=name, phone=phone, msg=msg, date=datetime.now(), email=email)
        db.session.add(entry)
        db.session.commit()

        subject = 'New message from ' + params['websiteName'] + ' by ' + name
        body = msg + "\n" + phone
        message = Message(subject=subject, sender=email, recipients=[params['emailUser']], body=body)
        mail.send(message)

        flash("Message Sent Successfully", "success")
    return render_template('contact.html', params=params)



@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    return render_template('error.html', error_message="An unexpected error occurred!"), 500


if __name__ == '__main__':
    app.run(debug=True)
