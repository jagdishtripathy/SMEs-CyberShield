# users/app.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
import os
import base64
import sqlite3
import logging
from datetime import datetime
import google.generativeai as genai
from users.database import (
    init_db,
    get_db_connection,
    create_user,
    user_exists,
    get_all_quizzes,
    get_quiz_by_id,
    save_quiz_progress,
    update_user_badges,
    save_url_check,
)
from utils.alert_notifier import send_discord_alert
from users.utils.recommendations import get_ai_recommendations_for_quiz, get_recommendation_message

# =============================================================================
# CONFIGURATION
# =============================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "cybersecurity.db")
VIRUSTOTAL_API_KEY = "b5064eb975fdd2c7168c7ef96d166002339589ed581d544dfb1c8bddc509f946"
GEMINI_API_KEY = "AIzaSyCVhoSCnZ8zXv2iVAuDWT01CHVMYU0a8NY"
genai.configure(api_key=GEMINI_API_KEY)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# =============================================================================
# BLUEPRINT
# =============================================================================
user_bp = Blueprint(
    "user_bp",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/users"
)

# =============================================================================
# DASHBOARD
# =============================================================================
@user_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect("/admin/dashboard")

    conn = get_db_connection()
    
    # Get fresh user data to ensure badges and score are up-to-date
    user_data = conn.execute('SELECT score, badges FROM users WHERE id = ?', (current_user.id,)).fetchone()
    if user_data:
        current_user.score = user_data['score']
        try:
            current_user.badges = json.loads(user_data['badges']) if user_data['badges'] else []
        except:
            current_user.badges = []
    
    progress = conn.execute('''
        SELECT q.title, up.score, up.completed_at 
        FROM user_progress up 
        JOIN quizzes q ON up.quiz_id = q.id 
        WHERE up.user_id = ? 
        ORDER BY up.completed_at DESC
        LIMIT 3
    ''', (current_user.id,)).fetchall()

    recent_checks = conn.execute('''
        SELECT url, virustotal_result, checked_at 
        FROM url_checks 
        WHERE user_id = ? 
        ORDER BY checked_at DESC 
        LIMIT 5
    ''', (current_user.id,)).fetchall()
    conn.close()

    return render_template("dashboard.html", progress=progress, recent_checks=recent_checks, badges=current_user.badges)

# =============================================================================
# REGISTER
# =============================================================================
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        if conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email)).fetchone():
            conn.close()
            return render_template('register.html', error='Username or email already exists')

        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                     (username, email, password_hash, 'user'))
        conn.commit()
        conn.close()

        return render_template('register.html', error='Registration successful! Please log in.', success=True)
    return render_template('register.html')

# =============================================================================
# LOGIN
# =============================================================================
@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            from flask_login import UserMixin, login_user

            class User(UserMixin):
                def __init__(self, id, username, email, role):
                    self.id = id
                    self.username = username
                    self.email = email
                    self.role = role

            user_obj = User(user['id'], user['username'], user['email'], user['role'])
            login_user(user_obj)

            if user_obj.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_bp.dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

# =============================================================================
# QUIZZES
# =============================================================================
@user_bp.route('/quiz')
@login_required
def quiz():
    quizzes_data = get_all_quizzes()
    quiz_list = []
    for q in quizzes_data:
        quiz_list.append({
            'id': q['id'],
            'title': q['title'],
            'category': q['category'],
            'questions': json.loads(q['questions'])
        })
    return render_template('quiz.html', quizzes=quiz_list)

@user_bp.route('/get_quiz/<int:quiz_id>')
@login_required
def get_quiz(quiz_id):
    quiz_data = get_quiz_by_id(quiz_id)
    if not quiz_data:
        return jsonify({'error': 'Quiz not found'}), 404

    quiz = {
        'id': quiz_data['id'],
        'title': quiz_data['title'],
        'category': quiz_data['category'],
        'questions': json.loads(quiz_data['questions'])
    }
    return jsonify(quiz)

@user_bp.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    try:
        data = request.get_json()
        quiz_id = data.get('quiz_id')
        answers = data.get('answers', [])

        quiz_data = get_quiz_by_id(quiz_id)
        if not quiz_data:
            return jsonify({'error': 'Quiz not found'}), 404

        questions = json.loads(quiz_data['questions'])
        correct_answers = sum(
            int(answers[i]) == int(questions[i]['correct'])
            for i in range(min(len(answers), len(questions)))
        )
        score = (correct_answers / len(questions)) * 100 if questions else 0

        save_quiz_progress(current_user.id, quiz_id, score)
        badges = update_user_badges(current_user.id)

        # Get updated user score
        conn = get_db_connection()
        user_data = conn.execute('SELECT score FROM users WHERE id = ?', (current_user.id,)).fetchone()
        conn.close()
        updated_score = user_data['score'] if user_data else 0

        # Generate video recommendations based on quiz performance
        quiz_title = quiz_data['title']
        quiz_category = quiz_data['category']
        recommendations = None
        recommendation_message = None
        
        try:
            rec_result = get_ai_recommendations_for_quiz(quiz_title, quiz_category, score)
            if rec_result['success'] or rec_result.get('recommendations'):
                recommendations = rec_result.get('recommendations', [])
                recommendation_message = get_recommendation_message(score)
        except Exception as rec_error:
            logging.warning(f"Could not generate recommendations: {rec_error}")

        return jsonify({
            'score': score,
            'correct_answers': correct_answers,
            'total_questions': len(questions),
            'user_score': updated_score,
            'badges': badges,
            'recommendations': recommendations,
            'recommendation_message': recommendation_message
        })
    except Exception as e:
        print(f"Error in submit_quiz: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error submitting quiz: {str(e)}'}), 500

# =============================================================================
# LEADERBOARD
# =============================================================================
@user_bp.route('/leaderboard')
@login_required
def leaderboard():
    conn = get_db_connection()
    top_users = conn.execute('SELECT username, score, badges FROM users ORDER BY score DESC LIMIT 10').fetchall()
    conn.close()

    leaderboard_data = [{
        'username': user['username'],
        'score': user['score'],
        'badges': json.loads(user['badges']) if user['badges'] else []
    } for user in top_users]

    return render_template('leaderboard.html', leaderboard=leaderboard_data)

# =============================================================================
# URL CHECKER
# =============================================================================
@user_bp.route('/url_checker', methods=['GET'])
@login_required
def url_checker_page():
    """Render the URL checker page"""
    return render_template('url_checker.html')

@user_bp.route('/url_checker', methods=['POST'])
@login_required
def url_checker():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    vt_result = check_virustotal(url)
    gemini_analysis = analyze_with_gemini(url, vt_result)
    risk_level = determine_risk(vt_result, gemini_analysis)

    save_url_check(current_user.id, url, vt_result, gemini_analysis)

    return jsonify({
        'virustotal': vt_result,
        'gemini_analysis': gemini_analysis,
        'risk_level': risk_level
    })


# =============================================================================
# DISCORD ALERT (from UI)
# =============================================================================
@user_bp.route('/alert/discord', methods=['POST'])
@login_required
def alert_discord():
    """Endpoint to send a user-triggered alert to Discord via webhook.

    Expected JSON: { url: <string>, message: <optional string> }
    """
    try:
        data = request.get_json() or {}
        url = data.get('url')
        custom = data.get('message')

        # Build a concise alert payload
        user_label = getattr(current_user, 'username', 'unknown')
        message = custom or (f"User {user_label} reported a suspicious URL: {url}" if url else f"User {user_label} requested assistance from the URL Checker")

        alert = {
            'title': 'User Dashboard Alert',
            'message': message,
            'severity': 'high',
            'timestamp': datetime.utcnow().isoformat(),
            'source_ip': request.remote_addr
        }

        success = send_discord_alert(alert)
        status = 200 if success else 500
        return jsonify({'success': bool(success)}), status
    except Exception as e:
        logging.exception('Failed to send discord alert')
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def check_virustotal(url):
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    get_response = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)

    if get_response.status_code == 200:
        return get_response.json()["data"]["attributes"]["last_analysis_stats"]

    if get_response.status_code == 404:
        post_response = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
        analysis_id = post_response.json()["data"]["id"]
        analysis_response = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers)
        return analysis_response.json()["data"]["attributes"]["stats"]

    raise Exception(f"VirusTotal API error: {get_response.status_code}")

def analyze_with_gemini(url, vt_stats):
    prompt = f"""
    URL Analysis Report:
    URL: {url}
    VirusTotal Stats: {vt_stats}
    Provide a security summary and recommendation.
    """
    model = genai.GenerativeModel("gemini-flash-latest")
    response = model.generate_content(prompt)
    return response.text

def determine_risk(vt_stats, gemini_text):
    malicious = vt_stats.get('malicious', 0)
    suspicious = vt_stats.get('suspicious', 0)
    text = gemini_text.lower()

    if malicious >= 2 or suspicious >= 1 or 'high risk' in text:
        return 'high'
    elif malicious > 0 or suspicious > 0 or 'moderate' in text:
        return 'medium'
    else:
        return 'low'

# =============================================================================
# USER DATA API (for frontend to get fresh user info)
# =============================================================================
@user_bp.route('/api/user_info', methods=['GET'])
@login_required
def api_user_info():
    """Get fresh user data including score and badges"""
    conn = get_db_connection()
    user_data = conn.execute('SELECT score, badges FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()
    
    if user_data:
        try:
            badges = json.loads(user_data['badges']) if user_data['badges'] else []
        except:
            badges = []
        
        return jsonify({
            'username': current_user.username,
            'score': user_data['score'],
            'badges': badges
        })
    else:
        return jsonify({'error': 'User not found'}), 404


def init_user_routes(app):
    """Register user blueprint with the main Flask app."""
    init_db()
    app.register_blueprint(user_bp)
