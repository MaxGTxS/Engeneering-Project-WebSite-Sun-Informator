from flask import Flask, render_template, flash, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, ValidationError, SelectField
from wtforms.validators import DataRequired, EqualTo, Length
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, LoginManager, login_required, logout_user, UserMixin, current_user

import requests

import matplotlib, matplotlib.pyplot as plt
from flask_mail import Mail, Message
import json
import threading
matplotlib.use('Agg')
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()
scheduler.start()


#aplikacja
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = ""
#baza danych
db = SQLAlchemy(app)
migrate = Migrate(app,db)


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25),nullable=False, unique=True)
    name = db.Column(db.String(75), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    email_preference = db.Column(db.String(50), default='wykresy')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    #haslo w hashu
    password_hash = db.Column(db.String(128))

@property
def password(self):
    raise AttributeError('hasła nie można odczytać')
@password.setter
def password(self, password):
    self.password_hash = generate_password_hash(password)
def verify_password(self, password):
    return check_password_hash(self.password_hash, password)

def __repr__(self):
    return f'<Users {self.name}>'

#usuniecie z bazy danych kogos
@app.route('/delete/<int:id>')
def delete(id):
    user_to_delete = Users.query.get_or_404(id)
    name = None
    form = UserForm()
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("Użytkownik pomyślnie usunięty")
        our_users = Users.query.order_by(Users.date_added)
        return render_template("add_user.html", form=form, name=name, our_users=our_users)
    
    except:
        flash("Błąd z usunięciem użytkownika, spróbuj ponownie")
        return render_template("add_user.html", form=form, name=name, our_users=our_users)


#rejestracja
class UserForm(FlaskForm):
    name=StringField("Name", validators=[DataRequired()])
    username=StringField("Username", validators=[DataRequired()])
    email =StringField("Email", validators=[DataRequired()])
    password_hash=PasswordField("Password", validators=[DataRequired(), EqualTo('password_hash2', message='Hasła muszą być identyczne')])
    password_hash2=PasswordField("Confirm Password", validators=[DataRequired()])
    email_preference = SelectField(
        'Email Preference',
        choices=[('wykresy', 'Chcę otrzymywać powiadomienia drogą mailową'), ('wybuchy', 'Nie chcę otrzymywać żadnych powiadomień')],
        validators=[DataRequired()]
    )
    submit = SubmitField("Submit")
    def validate_username(self, field):
        user = Users.query.filter_by(username=field.data).first()
        if user:
            flash("Nazwa użytkownika jest już zajęta. Wybierz inną.")
            raise ValidationError('Nazwa użytkownika jest już zajęta. Wybierz inną.')
            
        

#zmienianie danych konta
@app.route('/update/<int:id>', methods = ['GET','POST'])
def update(id):
    form = UserForm()
    name_to_update = Users.query.get_or_404(id)

    if request.method == "POST":
        if form.username.data != name_to_update.username and Users.query.filter_by(username=form.username.data).first():
            flash("Nazwa użytkownika jest już zajęta. Wybierz inną.", 'error')
        if  form.email.data != name_to_update.email and Users.query.filter_by(email=form.email.data).first():
            flash("Email juz istnieje i widnieje u nas w bazie. Prawdopodobnie juz masz założone konto, zaloguj się.", 'error')   
        else:
            name_to_update.username = request.form['username']
            name_to_update.name = request.form['name']
            name_to_update.email = request.form['email']
            name_to_update.email_preference = form.email_preference.data
        #name_to_update.name = request.form['password']

            try:
                    db.session.commit()
                    flash("Profil pomyślnie zaktualizowany")
                    return render_template("update.html",
                                   form=form,
                                   name_to_update = name_to_update,
                                   id = id)
            except:
                    flash("Dane które próbujesz zmienić są juz zajęte")
                    return render_template("update.html",
                                   form=form,
                                   name_to_update = name_to_update,
                                   id = id
                                   )
    
        
    return render_template("update.html",
                                   form=form,
                                   name_to_update = name_to_update,
                                   id = id)
    
#haslo
class PasswordForm(FlaskForm):
    email=StringField("Podaj email", validators=[DataRequired()])
    password_hash = PasswordField("Podaj hasło", validators=[DataRequired()])
    submit = SubmitField("Submit")

#stworzenie klasy wtf
class NamerForm(FlaskForm):
    name=StringField("Whats your name", validators=[DataRequired()])
    submit = SubmitField("Submit")

#rejestracja z dodaniem do bazy danych
@app.route('/user/add', methods=['GET','POST'])
def add_user():
    name = None
    form = UserForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user is None:
            #hashing hasla
            hashed_pw = generate_password_hash(form.password_hash.data, 'pbkdf2:sha256')
            user = Users(username=form.username.data, name=form.name.data, email=form.email.data, password_hash=hashed_pw, email_preference=form.email_preference.data )
            db.session.add(user)
            db.session.commit()
            flash("Dodano użytkownika pomyślnie")
        else: 
            flash("Email juz istnieje i widnieje u nas w bazie. Prawdopodobnie juz masz założone konto, zaloguj się.", 'error')   
        name = form .name.data
        form.username.data=''
        form.name.data=''
        form.email.data= ''
        form.password_hash.data=''

    our_users = Users.query.order_by(Users.date_added)
    
    return render_template("add_user.html", form=form, name=name, our_users=our_users)

#stworzenie pierwszej strony url podstawowe z danymi API
@app.route('/')
def index():
    primary_url = 'https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json'
    secondary_url = 'https://services.swpc.noaa.gov/json/goes/secondary/xrays-1-day.json'

    primary_data = requests.get(primary_url).json()
    secondary_data = requests.get(secondary_url).json()

    primary_proton_url = 'https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json'
    secondary_proton_url = 'https://services.swpc.noaa.gov/json/goes/secondary/integral-protons-1-day.json'

    primary_proton_data = requests.get(primary_proton_url).json()
    secondary_proton_data = requests.get(secondary_proton_url).json()

    primary_electron_url = 'https://services.swpc.noaa.gov/json/goes/primary/integral-electrons-1-day.json'
    secondary_electron_url = 'https://services.swpc.noaa.gov/json/goes/secondary/integral-electrons-1-day.json'

    primary_electron_data = requests.get(primary_electron_url).json()
    secondary_electron_data = requests.get(secondary_electron_url).json()


    flare_url = 'https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json'
    flare_data = requests.get(flare_url).json()

    satellite_url = 'https://services.swpc.noaa.gov/json/goes/satellite-longitudes.json'
    satellite_data = requests.get(satellite_url).json()

    return render_template('index.html', primary_data=primary_data, 
                                        secondary_data=secondary_data, 
                                        primary_proton_data=primary_proton_data, 
                                        secondary_proton_data=secondary_proton_data, 
                                        primary_electron_data=primary_electron_data,
                                        secondary_electron_data=secondary_electron_data,
                                        flare_data=flare_data, 
                                        satellite_data=satellite_data)

# tworzymy Lock
plot_lock = threading.Lock()
#wykres protonow
def generate_and_save_plot_proton(data, filename):
    x_values = [item['time_tag'] for item in data]
    y_values = [item['flux'] for item in data]

    with plot_lock:

        plt.figure()
        plt.yscale('log')
        plt.ylim(0.01, 10000)
        plt.plot(x_values, y_values)
        plt.title("Wykres Proton Flux")
        plt.xlabel("Czas")
        plt.ylabel("Flux(Particles * cm^-2 * s^-1 * sr-1)")
        plt.xticks(x_values[::300], rotation=45, ha='right')
        plt.tight_layout()
        save_path = f'static/imagies/{filename}'
        plt.savefig(save_path)

#wykres elektronow
def generate_and_save_plot_electron(data, filename):
    x_values = [item['time_tag'] for item in data]
    y_values = [item['flux'] for item in data]

    with plot_lock:

        plt.figure()
        plt.yscale('log')
        plt.ylim(1, 10000000)
        plt.plot(x_values, y_values)
        plt.title("Wykres Flux Electron")
        plt.xlabel("Czas")
        plt.ylabel("Flux(Particles * cm^-2 * s^-1 * sr-1)")
        #plt.xticks(rotation=45, ha='right') 
        step = 30  
        plt.xticks(range(0, len(x_values), step), x_values[::step], rotation=45, ha='right')
        plt.tight_layout()
        #plt.xticks(range(0, len(x_values), step=10), x_values[::10])
        #plt.tight_layout()  # Aby etykiety nie były przycięte

        save_path = f'static/imagies/{filename}'
        plt.savefig(save_path)

#wykres flux
def generate_and_save_plot(data, filename):
    x_values = [item['time_tag'] for item in data]
    y_values = [item['flux'] for item in data]

    with plot_lock:

        plt.figure()
        plt.yscale('log')
        plt.ylim(0.000000001, 0.01)
        plt.plot(x_values, y_values)
        plt.title("Wykres Flux")
        plt.xlabel("Czas")
        plt.ylabel("Flux(Wats * m^-2)")
        #plt.xticks(rotation=45, ha='right')  # Obrót etykiet osi X
        plt.xticks(x_values[::300], rotation=45, ha='right')
        #plt.xticks(range(0, len(x_values), step=10), x_values[::10])
        plt.tight_layout()  # Aby etykiety nie były przycięte

        save_path = f'static/imagies/{filename}'
        plt.savefig(save_path)

#konfiguracja maila
app.config['MAIL_SERVER'] = ''
app.config['MAIL_PORT'] = 
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['MAIL_DEFAULT_SENDER'] = ''

mail = Mail(app)



#wysylanie maila
def send_email(flare_latest_data, satellite_data):
    with app.app_context():
        users = Users.query.filter(Users.email.isnot(None), Users.email_preference == 'wykresy').all()
        recipients = [user.email for user in users]


        msg = Message("Całodniowe podsumowanie aktywności Słonecznej", recipients=recipients)

    # tresc maila
        msg.body = f"""

    Dzienny raport danych:

Satellite logitudes (Dane o satelitach):

Satelita:   Długość geograficzna(stopnie):

{"".join([f"- {entry['satellite']}:                 {entry['longitude']}\n" for entry in satellite_data])}

Solar Flare Data (dane o ostatnim wybuchu słonecznym):

   
Data i czas rozpoczęcia wybuchu (Begin time):     {"".join([f"-{entry['begin_time']}       \n" for entry in flare_latest_data])}      
Klasa początkowa (Begin class):    {"".join([f"-{entry['begin_class']}      \n" for entry in flare_latest_data])}
Czas wystąpienia maksimum wybuchu (Max time):       {"".join([f"-{entry['max_time']}            \n" for entry in flare_latest_data])}    
Maksymalna klasa (Max class):      {"".join([f"-{entry['max_class']}      \n" for entry in flare_latest_data])}
Czas ukończenia zdarzenia (End time):       {"".join([f"-{entry['end_time']}    \n" for entry in flare_latest_data])}
Klasa końcowa (End class):      {"".join([f"-{entry['end_class']} \n" for entry in flare_latest_data])}
                                                                                              

Po więcej danych oraz wykresów należy udać sie na naszą stronę, serdecznie zapraszamy " tutaj znajdowałby się link do strony gdyby nie była zrobiona tylko lokalnie ".
    """


        with app.open_resource("static/imagies/primary_flux_plot.png") as fp:
            msg.attach("primary_flux_plot.png", "image/png", fp.read())
        with app.open_resource("static/imagies/secondary_flux_plot.png") as fp:
            msg.attach("secondary_flux_plot.png", "image/png", fp.read())
        with app.open_resource("static/imagies/primary_proton_flux_plot.png") as fp:
            msg.attach("primary_proton_flux_plot.png", "image/png", fp.read())
        with app.open_resource("static/imagies/secondary_proton_flux_plot.png") as fp:
            msg.attach("secondary_proton_flux_plot.png", "image/png", fp.read())
        with app.open_resource("static/imagies/primary_electron_flux_plot.png") as fp:
            msg.attach("primary_electron_flux_plot.png", "image/png", fp.read())
        with app.open_resource("static/imagies/secondary_electron_flux_plot.png") as fp:
            msg.attach("secondary_electron_flux_plot.png", "image/png", fp.read())

        msg.sender = ("Twoja codzienna dawka Słońca", "max.praca.work@gmail.com")
        mail.send(msg)

#generuje i wysyla maila
@app.route('/generate-plots')
def generate_plots():

    primary_url = 'https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json'
    primary_data = requests.get(primary_url).json()

    secondary_url = 'https://services.swpc.noaa.gov/json/goes/secondary/xrays-1-day.json'
    secondary_data = requests.get(secondary_url).json()

    primary_proton_url = 'https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json'
    secondary_proton_url = 'https://services.swpc.noaa.gov/json/goes/secondary/integral-protons-1-day.json'

    primary_proton_data = requests.get(primary_proton_url).json()
    secondary_proton_data = requests.get(secondary_proton_url).json()

    primary_electron_url = 'https://services.swpc.noaa.gov/json/goes/primary/integral-electrons-1-day.json'
    secondary_electron_url = 'https://services.swpc.noaa.gov/json/goes/secondary/integral-electrons-1-day.json'

    primary_electron_data = requests.get(primary_electron_url).json()
    secondary_electron_data = requests.get(secondary_electron_url).json()

    flare_latest_url = 'https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json'
    flare_latest_data = requests.get(flare_latest_url).json()

    satellite_url = 'https://services.swpc.noaa.gov/json/goes/satellite-longitudes.json'
    satellite_data = requests.get(satellite_url).json()

    

    generate_and_save_plot_electron(primary_electron_data, 'primary_electron_flux_plot.png')
    generate_and_save_plot_electron(secondary_electron_data, 'secondary_electron_flux_plot.png')
    generate_and_save_plot(primary_data, 'primary_flux_plot.png')
    generate_and_save_plot(secondary_data, 'secondary_flux_plot.png')
    generate_and_save_plot_proton(primary_proton_data, 'primary_proton_flux_plot.png')
    generate_and_save_plot_proton(secondary_proton_data, 'secondary_proton_flux_plot.png')


    send_email(flare_latest_data, satellite_data,)

    return "Wykresy zostały wygenerowane"


scheduler.add_job(generate_plots, trigger=IntervalTrigger(hours=24))




#stworzenie strony z url user na ktorej jest profil uzytkownika
@app.route('/user')
@login_required
def user():
    return render_template("user.html")
#if __name__ == "__main__":
 #   app.run(debug=True)

#stworzenie kolejnej strony odpowiedzialnej za wyswietlanie bledow
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500

#logowanie
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password =PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")

#strona logowania
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                #flash("Zalogowano pomyślnie")
                return redirect(url_for('user'))
            else:
                flash("Złe hasło")
        else:
            flash("Próba logowania nie udana, spróbuj jeszcze raz lub nie ma takiego użytkownika, zarejestruj się")
    return render_template('login.html', form=form)

#wylogowanie
@app.route('/logout', methods=['GET', 'POST'])    
@login_required
def logout():
    logout_user()
    flash("Użytkownik pomyślnie wylogowany")
    return redirect(url_for('login'))

# dzialanie strony do debuggowania 
if __name__ == "__main__":
    app.run(debug=True)