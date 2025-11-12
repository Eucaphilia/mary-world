from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import secrets
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration
ADMIN_PASSWORD = "Manglem12"
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Production: Use PostgreSQL
    import psycopg2
    import psycopg2.extras
    DATABASE_TYPE = 'postgresql'
else:
    # Development: Use SQLite
    DATABASE = 'blog.db'
    DATABASE_TYPE = 'sqlite'

def init_db():
    """Initialize the database"""
    if DATABASE_TYPE == 'postgresql':
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

def get_db_connection():
    """Get database connection"""
    if DATABASE_TYPE == 'postgresql':
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

def get_all_posts():
    """Get all posts from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts ORDER BY id DESC')
    posts = cursor.fetchall()
    conn.close()
    return [dict(post) for post in posts]

def add_post(title, content):
    """Add a new post to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    date = datetime.now().strftime('%B %d, %Y')
    cursor.execute('INSERT INTO posts (title, content, date) VALUES (%s, %s, %s)' if DATABASE_TYPE == 'postgresql' 
                  else 'INSERT INTO posts (title, content, date) VALUES (?, ?, ?)',
                  (title, content, date))
    conn.commit()
    conn.close()

def delete_post_by_id(post_id):
    """Delete a post from database"""
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

# Initialize database when app starts
init_db()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Admin access required!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    posts = get_all_posts()
    return render_template('index.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Welcome back!', 'success')
            return redirect(url_for('admin'))
        flash('Invalid password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    posts = get_all_posts()
    return render_template('admin.html', posts=posts)

@app.route('/admin/new', methods=['POST'])
@admin_required
def new_post():
    title = request.form.get('title')
    content = request.form.get('content')
    if title and content:
        add_post(title, content)
        flash('Post created! ✨', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:post_id>')
@admin_required
def delete_post(post_id):
    delete_post_by_id(post_id)
    flash('Post deleted! 🗑️', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)