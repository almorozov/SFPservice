from flask import Flask, render_template, url_for, request, has_request_context, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from datetime import datetime, date
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import logging
from flask.logging import default_handler
from logging.handlers import RotatingFileHandler
import time
import os

#For logs
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None
        return super().format(record)

formatter = RequestFormatter('[%(asctime)s] [%(levelname)s] from %(remote_addr)s req: %(url)s > %(message)s')

#>Base config
app = Flask(__name__)
DATABASE_NAME = "SFP_DB.sqlite"
file_path = os.path.abspath(os.getcwd())+"/data/"+DATABASE_NAME
file_log = os.path.abspath(os.getcwd()) + "/data/SFP_Events.log"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'CTFsecretKeySaltHash'
db = SQLAlchemy(app)
manager = LoginManager(app)
tstatus = ["In progress","Pass", "Rejected"]
saccount = ["admin","Z@rya-2023"]
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
handler = RotatingFileHandler(file_log, maxBytes=1048576, backupCount=10)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

#DB Models
class SFP_Users(db.Model, UserMixin):
    __tablename__ = 'SFP_Users'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    login = db.Column(db.String(128), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    SFP_FlightPass = db.relationship("SFP_FlightPass")

    def __repr__(self):
        return "<{}:{}>".format(self.id, self.login)

class SFP_FlightPass(db.Model):
    __tablename__ = 'SFP_FlightPass'
    tid = db.Column(db.Integer, primary_key=True)
    fpid = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    destination = db.Column(db.String(100), nullable=False)
    depdate = db.Column(db.Date, nullable=False)
    starship_name = db.Column(db.String(100), nullable=False)
    starship_reg = db.Column(db.String(100), nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('SFP_Users.id'))
    rem = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    SFP_Users = db.relationship("SFP_Users")

    def __repr__(self):
        return '<SFP_FlightPass %r>' % self.tid


#DB create if not exist db-file
db_is_created = os.path.exists(f'data/{DATABASE_NAME}')
if not db_is_created:
    with app.app_context():
        db.create_all()
        app.logger.info('[INIT] [DB] [Succeess] DB create <%s>', app.config['SQLALCHEMY_DATABASE_URI'])
        time.sleep(5)
        user = SFP_Users.query.filter_by(login=saccount[0]).first()
    if not(user):
            with app.app_context():
                user = SFP_Users(login=saccount[0], password=generate_password_hash(saccount[1]))
                try:
                    db.session.add(user)
                    db.session.commit()
                    app.logger.info('[INIT] [DB] [Succeess] User create:<%s>', saccount[0])
                except:
                    app.logger.error('[INIT] [DB] [Failed] User create:<%s>. Error DB insert', saccount[0])


#Base function
@manager.user_loader
def load_user(user_id):
    return SFP_Users.query.get(user_id)


def f_genfpid(uid, uname):
#Format FlightPassID: fp<username>-#
    if uid and uname:
        ticket = SFP_FlightPass.query.filter_by(uid=uid).order_by(SFP_FlightPass.date.desc()).first()
        if ticket:
            sfpid = ticket.fpid
            sfpid.split("-")
            try:
                tnum = int(sfpid[len(sfpid)-1])
                tnum +=1
            except:
                tnum = 0
        else:
            tnum = 0
            if not uname:
                uname = "<uname>"
    fpid = "fp" + uname + "-" + str(tnum)
    return fpid


def f_apprules(uname):
    now = datetime.now()
    cmd = "echo \"" + now.strftime("%m/%d/%Y") + " " + uname +  "\" >> data/SFP_approve.txt"
    res = os.system(cmd)
    return res


#Flask function
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/MyProfile')
@login_required
def MyProfile():
    user = SFP_Users.query.get(current_user.id)
    app.logger.info('[FUNC] [/MyProfile] [Succeess] User:<%s>',current_user.login)
    return render_template("myprofile.html", user=user)


@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == "POST":
        ulogin = request.form['login']
        upassword = request.form['password']
        user = SFP_Users.query.filter_by(login=ulogin).first()
        if user and check_password_hash(user.password, upassword):
            login_user(user)
            app.logger.info('[AUTH] [LOGIN] [Succeess] User:<%s>', current_user.login)
            return redirect('/MyProfile')
        else:
            flash('Login or password incorrect')
            app.logger.warning('[AUTH] [LOGIN] [Failed] User:<%s> Password:<%s>', ulogin, upassword)
            return redirect('/login')
    else:
        return render_template("login.html")


@app.route('/logout', methods=['POST','GET'])
@login_required
def logout():
    app.logger.info('[AUTH] [LOGOUT] [Succeess] User:<%s>', current_user.login)
    logout_user()
    return redirect('/')


@app.route('/reg', methods=['POST','GET'])
def reg():
    if request.method == "POST":
        ulogin=request.form['login']
        upassword=request.form['password']
        if not(ulogin or upassword):
            flash('Please, fill all fileds')
            return redirect('/reg')
        elif not(SFP_Users.query.filter_by(login=ulogin).first()) and ulogin and upassword:
            user = SFP_Users(login=ulogin, password=generate_password_hash(upassword))
            try:
                db.session.add(user)
                db.session.commit()
                app.logger.info('[AUTH] [REG] [Succeess] User:<%s>', ulogin)
                return redirect('/login')
            except:
                app.logger.error('[AUTH] [REG] [Failed] User:<%s>. Error DB insert.', ulogin)
                flash('Error DB insert')
                return redirect('/reg')
        else:
            app.logger.warning('[AUTH] [REG] [Failed] Please, enter other login or not null login or not null password')
            flash('Please, enter other login or not null login or not null password')
            return redirect('/reg')
    else:
        return render_template("reg.html")


@app.after_request
def redirect_to_login(response):
    if response.status_code == 401:
        return redirect('/login')
    return response


@app.route('/ApproveRules', methods=['GET'])
@login_required
def ApproveRules():
    uname = request.args.get('uname')
    if uname:
        app.logger.info('[FUNC] [/ApproveRules] [Succeess] Data:<%s>', uname)
        f_apprules(uname)
    return redirect('/MyProfile')


@app.route('/CreateTicket', methods=['POST','GET'])
@login_required
def CreateTicket():
    if request.method == "POST":
        if (len(request.form['destination']) > 2) and (len(request.form['depdate']) > 0) and date.fromisoformat(request.form['depdate']) and (len(request.form['starship_name']) > 2) and (len(request.form['starship_reg']) > 2):
            ticket = SFP_FlightPass(destination=request.form['destination'], depdate=date.fromisoformat(request.form['depdate']), starship_name=request.form['starship_name'], starship_reg=request.form['starship_reg'], rem=request.form['rem'], fpid=f_genfpid(current_user.id, current_user.login), uid=current_user.id)
            try:
                db.session.add(ticket)
                db.session.commit()
                app.logger.info('[FUNC] [/CreateTicket] [Succeess] User:<%s> Data:<%s>',current_user.login, ticket)
                return redirect('/MyTicketList')
            except:
                app.logger.error('[FUNC] [/CreateTicket] [Failed] User:<%s> Error DB insert',current_user.login)
                flash('Error DB insert')
                return redirect('/CreateTicket')
        else:
            flash('Please, enter all rewuired data!')
            return redirect('/CreateTicket')
    else:
        return render_template("create-ticket.html")


@app.route('/search', methods=['GET'])
@login_required
def search():
    tsearch = request.args.get('search')
    if tsearch:
        e = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        with e.connect() as conn:
            sql = text("SELECT * FROM SFP_FlightPass WHERE starship_name == \""+ tsearch +"\" and uid == "+ str(current_user.id))
            app.logger.info('[FUNC] [/search] [Succeess] User:<%s> Data:<%s>',current_user.login, tsearch)
            tickets = conn.execute(sql).all()
        return render_template("searchlist-2.html", tickets=tickets, tstatus=tstatus)
    else:
        return redirect('/')


@app.route('/ticket/<string:fpid>')
@login_required
def ticket_detail(fpid):
    ticket = SFP_FlightPass.query.filter_by(fpid=fpid).order_by(SFP_FlightPass.date.desc()).first()
    app.logger.info('[FUNC] [/ticket] [Succeess] User:<%s> Read ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
    return render_template("myticket_detail.html", ticket=ticket, tstatus=tstatus)


@app.route('/ticket/<int:id>/del')
@login_required
def ticket_del(id):
    ticket = SFP_FlightPass.query.get_or_404(id)
    if ticket.SFP_Users.id == current_user.id:
        try:
            db.session.delete(ticket)
            db.session.commit()
            app.logger.info('[FUNC] [/ticket/del] [Succeess] User:<%s> Del ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
            return redirect('/MyTicketList')
        except:
            app.logger.error('[FUNC] [/ticket/del] [Failed] User:<%s> Del ticket: <%s> <%s> pilot: <%s>. Error DB delete!', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
            return "Error DB delete!"
    else:
        app.logger.warning('[FUNC] [/ticket/del] [Failed] User:<%s> Del ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
        return redirect('/')


@app.route('/ticket/<int:id>/edit', methods=['POST','GET'])
@login_required
def ticket_edit(id):
    ticket = SFP_FlightPass.query.get_or_404(id)
    if ticket.SFP_Users.id == current_user.id:
        if request.method == "POST":
            if (len(request.form['destination']) > 2) and (len(request.form['depdate']) > 0) and date.fromisoformat(request.form['depdate']) and (len(request.form['starship_name']) > 2) and (len(request.form['starship_reg']) > 2):
                ticket.destination = request.form['destination']
                ticket.depdate = date.fromisoformat(request.form['depdate'])
                ticket.starship_name = request.form['starship_name']
                ticket.starship_reg = request.form['starship_reg']
                ticket.rem = request.form['rem']
                ticket.status = 0
                try:
                    db.session.commit()
                    app.logger.info('[FUNC] [/ticket/edit] [Succeess] User:<%s> Edit ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
                    return redirect('/MyTicketList')
                except:
                    app.logger.error('[FUNC] [/ticket/del] [Failed] User:<%s> Del ticket: <%s> <%s> pilot: <%s>. Error DB insert/', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
                    flash('Error DB insert')
                    return redirect('/ticket/' + id + '/edit')
            else:
                flash('Please, enter all rewuired data!')
                return redirect('/ticket/' + id + '/edit')
        else:
            return render_template("myticket_edit.html", ticket=ticket)
    else:
        app.logger.warning('[FUNC] [/ticket/edit] [Failed] User:<%s> Edit ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
        return redirect('/')

@app.route('/MyTicketList')
@login_required
def MyTicketList():
    tickets = SFP_FlightPass.query.filter_by(uid=current_user.id).order_by(SFP_FlightPass.date.desc()).all()
    app.logger.info('[FUNC] [/MyTicketList] [Succeess] User:<%s> Read count(tickets): <%d>', current_user.login, len(tickets))
    return render_template("myticketlist.html", tickets=tickets, tstatus=tstatus)


@app.route('/StatusPilotList')
def StatusPilotList():
    i = 0
    pilot = SFP_Users.query.order_by(SFP_Users.login.asc()).all()
    while pilot[i].login != saccount[0] and i < len(pilot):
        i += 1
    if pilot[i].login == saccount[0]:
        pilot.pop(i)
    return render_template("statuspilotlist.html", pilot=pilot)


@app.route('/adminpanel')
@login_required
def adminpanel():
    if current_user.login == saccount[0]:
        tickets = SFP_FlightPass.query.order_by(SFP_FlightPass.date.desc()).all()
        app.logger.info('[FUNC] [/adminpanel] [Succeess] User:<%s> Read count(tickets): <%d>', current_user.login, len(tickets))
        return render_template("adminpanel.html", tickets=tickets, tstatus=tstatus)
    else:
        app.logger.warning('[FUNC] [/adminpanel] [Failed] User:<%s> ', current_user.login)
        return redirect('/')


@app.route('/adminpanel/<int:id>/approve')
@login_required
def adminpanel_appr(id):
    if current_user.login == saccount[0]:
        ticket = SFP_FlightPass.query.get_or_404(id)
        ticket.status = 1
        try:
            db.session.commit()
            app.logger.info('[FUNC] [/adminpanel/approve] [Succeess] User:<%s> Approve ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
        except:
            app.logger.error('[FUNC] [/adminpanel/approve] [Failed] User:<%s> Reject ticket: <%s> <%s> pilot: <%s>. Error DB', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
            flash("Error DB approve!")
        return redirect('/adminpanel')
    else:
        return redirect('/')


@app.route('/adminpanel/<int:id>/rejected')
@login_required
def adminpanel_rej(id):
    if current_user.login == saccount[0]:
        ticket = SFP_FlightPass.query.get_or_404(id)
        ticket.status = 2
        try:
            db.session.commit()
            app.logger.info('[FUNC] [/adminpanel/rejected] [Succeess] User:<%s> Reject ticket: <%s> <%s> pilot: <%s>', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
        except:
            app.logger.error('[FUNC] [/adminpanel/rejected] [Failed] User:<%s> Reject ticket: <%s> <%s> pilot: <%s>. Error DB', current_user.login, ticket.tid, ticket.fpid, ticket.SFP_Users.login)
            flash("Error DB reject!")
        return redirect('/adminpanel')
    else:
        return redirect('/')


#Flask start...
if __name__ == "__main__":
    app.run()