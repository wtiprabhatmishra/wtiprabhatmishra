from flask import Flask, render_template, request, redirect, url_for, flash
import os # For generating a secret key
import uuid # For generating API keys
from . import database # Use a relative import for database.py

app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for flashing messages

# Initialize the database
# This should ideally be robust, e.g. only if not already initialized or via a CLI command
# For this task, calling it directly is fine.
database.init_db()

@app.route('/')
def hello_bharatpath():
    return render_template('index.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('register'))

        # Attempt to add user
        success, message = database.add_user(email, password)
        
        if success:
            flash(message, 'success')
            # In a real app, you might redirect to a login page or dashboard
            # For now, just re-render the registration page with the success message
            return redirect(url_for('register')) 
        else:
            flash(message, 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/api_key')
def api_key_page():
    # Placeholder: Generate a new key each time.
    # Later, this would be retrieved for the logged-in user.
    generated_key = uuid.uuid4().hex
    return render_template('api_key.html', api_key=generated_key)

@app.route('/api/docs')
def api_docs_page():
    return render_template('api_docs.html')

@app.route('/payment-methods')
def payment_methods_page():
    return render_template('payment_methods.html')

if __name__ == '__main__':
    # Ensure the app context is available for database operations if they were to happen here
    # with app.app_context():
    #     database.init_db() # Alternative placement if not at module level
    app.run(debug=True)
