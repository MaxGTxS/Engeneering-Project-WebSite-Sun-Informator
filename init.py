from main import app, db

# Załaduj kontekst aplikacji
app.app_context().push()

# Teraz możesz wywołać operacje na bazie danych
db.create_all()