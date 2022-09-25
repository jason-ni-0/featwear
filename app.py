from flask import Flask, render_template, request, redirect, url_for, session
import re
import requests
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import *
import sqlalchemy 
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import Session as sqlSess
from flask_cors import CORS, cross_origin
import os

app = Flask(__name__)
app.config.from_object(Config)

DB_URI = app.config['SQLALCHEMY_DATABASE_URI']
engine = create_engine(DB_URI)

CORS(app, support_credentials=True)
Base = automap_base()
Base.prepare(engine, reflect=True)
Accounts = Base.classes.account
sess = sqlSess(engine)
metadata = MetaData(engine)

app.secret_key = 'secret'

@app.route('/', methods=['GET', 'POST'])
def start():
    def getLoc():
        try:
            if session['weather']:
                return session['weather']
        except:
            return ''
    def getZod():
        try:
            if session['colors']:
                return session['colors']
        except:
            return ''
    account_details = ''
    if 'loggedin' in session:
        account_details = (session['id'],session['username'],session['email'])
    if 'location' in request.form:
        loc = session['location'] = request.form['location']
        URL = f'http://api.openweathermap.org/geo/1.0/direct?q={loc}&limit=5&appid=b417a914a5321e9318276a1bb6b2170f'
        try:
            res = requests.get(URL).json()[0]
        except:
            return render_template('start.html', weather=getLoc(), zodiac=getZod(), msg="Could not find city")
        lat=res['lat']
        long=res['lon']
        URL=f'https://feat-wear.herokuapp.com/weather?lat={lat}&long={long}'
        session['weather'] = requests.get(URL).json()

    if 'zodiacs' in request.form:
        zod = session['colors'] = request.form['zodiacs']
        URL=f'https://feat-wear.herokuapp.com/color?zodiac={zod}'
        session['colors'] = requests.get(URL).json()
    return render_template('start.html', weather=getLoc(), color=getZod(),account=account_details)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    try:
        if session['loggedin']:
            return redirect(url_for('start'))
    except:
        pass
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username_entered = request.form['username']
        password_entered = request.form['password']
        user = sess.query(Accounts).filter(or_(Accounts.username == username_entered, Accounts.email == username_entered)).first()
        if user is not None and check_password_hash(user.password, password_entered):
            session['loggedin'] = True
            session['id'] = user.user_id
            session['username'] = user.username
            session['email'] = user.email
            return redirect(url_for('start'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('index.html', msg=msg)

@app.route('/logout')
def logout():
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   session.pop('email', None)
   return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    try:
        if session['loggedin']:
            return redirect(url_for('home'))
    except:
        pass
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        password_hash = generate_password_hash(password)
        account = Table('account', metadata, autoload=True)
        try:
            engine.execute(account.insert(), username=username, email=email, password=password_hash)
            msg="Registration successful"
        except sqlalchemy.exc.IntegrityError as e:
            errorInfo = e.orig.args[0]
            if 'duplicate key value violates unique constraint "account_username_key"\nDETAIL' in errorInfo:
                msg = "The entered username is unavailable"
            elif 'duplicate key value violates unique constraint "account_email_key"\nDETAIL' in errorInfo:
                msg = "The entered email already has an account associated with it"
        except:
            msg="Error creating account"
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

@app.route('/home')
def home():
    if 'loggedin' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' in session:
        account_details = (session['id'],session['username'],session['email'])
        return render_template('profile.html', account=account_details)
    return redirect(url_for('login'))

