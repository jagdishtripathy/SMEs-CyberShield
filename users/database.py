import sqlite3
import json
from datetime import datetime
import os

# Get the correct database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users', 'cybersecurity.db')

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            badges TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Quizzes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            questions TEXT NOT NULL,  -- JSON string of questions
            category TEXT NOT NULL
        )
    ''')
    
    # User progress table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quiz_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
        )
    ''')
    
    # URL checks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS url_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            virustotal_result TEXT,
            gemini_analysis TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Activity logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT NOT NULL,
            points_earned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Video recommendations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_level TEXT NOT NULL,
            recommendations_json TEXT NOT NULL,
            topic_category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_activity(user_id, activity_type, description, points_earned=0):
    """Log user activity"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO activity_logs (user_id, activity_type, description, points_earned)
        VALUES (?, ?, ?, ?)
    ''', (user_id, activity_type, description, points_earned))
    conn.commit()
    conn.close()

def get_user_activities(user_id, limit=10):
    """Get recent activities for a user"""
    conn = get_db_connection()
    activities = conn.execute('''
        SELECT * FROM activity_logs 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return activities

def get_leaderboard(limit=10):
    """Get top users by score"""
    conn = get_db_connection()
    users = conn.execute('''
        SELECT username, score, badges 
        FROM users 
        ORDER BY score DESC 
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return users

def update_user_score(user_id, points):
    """Update user score and return new total"""
    conn = get_db_connection()
    conn.execute('UPDATE users SET score = score + ? WHERE id = ?', (points, user_id))
    conn.commit()
    
    # Get updated score
    user = conn.execute('SELECT score FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    return user['score'] if user else 0

def get_user_stats(user_id):
    """Get comprehensive user statistics"""
    conn = get_db_connection()
    
    # User basic info
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # Training stats
    training_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_quizzes,
            AVG(score) as average_score,
            MAX(score) as best_score
        FROM user_progress 
        WHERE user_id = ?
    ''', (user_id,)).fetchone()
    
    # URL check stats
    url_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_checks,
            SUM(CASE WHEN json_extract(virustotal_result, '$.malicious') > 0 THEN 1 ELSE 0 END) as malicious_found
        FROM url_checks 
        WHERE user_id = ?
    ''', (user_id,)).fetchone()
    
    # Recent activities
    recent_activities = conn.execute('''
        SELECT * FROM activity_logs 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 5
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return {
        'user': user,
        'training_stats': training_stats,
        'url_stats': url_stats,
        'recent_activities': recent_activities
    }

def get_quiz_progress(user_id):
    """Get user's quiz progress"""
    conn = get_db_connection()
    progress = conn.execute('''
        SELECT 
            q.title,
            q.category,
            up.score,
            up.completed_at,
            (SELECT COUNT(*) FROM user_progress up2 
             WHERE up2.quiz_id = up.quiz_id AND up2.user_id = ?) as attempts
        FROM user_progress up
        JOIN quizzes q ON up.quiz_id = q.id
        WHERE up.user_id = ?
        ORDER BY up.completed_at DESC
    ''', (user_id, user_id)).fetchall()
    conn.close()
    return progress

def save_url_check(user_id, url, virustotal_result, gemini_analysis):
    """Save URL check result"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO url_checks (user_id, url, virustotal_result, gemini_analysis)
        VALUES (?, ?, ?, ?)
    ''', (user_id, url, 
          json.dumps(virustotal_result) if isinstance(virustotal_result, dict) else virustotal_result,
          gemini_analysis))
    conn.commit()
    conn.close()

def get_recent_url_checks(user_id, limit=5):
    """Get recent URL checks for a user"""
    conn = get_db_connection()
    checks = conn.execute('''
        SELECT * FROM url_checks 
        WHERE user_id = ? 
        ORDER BY checked_at DESC 
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return checks

def get_quiz_by_id(quiz_id):
    """Get quiz by ID"""
    conn = get_db_connection()
    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    conn.close()
    return quiz

def save_quiz_progress(user_id, quiz_id, score):
    """Save quiz progress and update user score safely"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calculate points (10 points per correct answer percentage)
        points_earned = int(score / 10)

        # Save progress
        cursor.execute('''
            INSERT INTO user_progress (user_id, quiz_id, score)
            VALUES (?, ?, ?)
        ''', (user_id, quiz_id, score))

        # Update user score
        cursor.execute('UPDATE users SET score = score + ? WHERE id = ?', (points_earned, user_id))

        # Fetch quiz title safely
        cursor.execute('SELECT title FROM quizzes WHERE id = ?', (quiz_id,))
        quiz = cursor.fetchone()
        quiz_title = quiz['title'] if quiz else f"Quiz #{quiz_id}"

        # Log activity
        cursor.execute('''
            INSERT INTO activity_logs (user_id, activity_type, description, points_earned)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'quiz_completed', f"Completed quiz: {quiz_title} ({score:.1f}%)", points_earned))

        conn.commit()
        conn.close()
        return points_earned

    except Exception as e:
        print("🔥 Error in save_quiz_progress:", str(e))
        try:
            conn.close()
        except:
            pass
        return 0


def update_user_badges(user_id):
    """Update user badges based on score"""
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT score FROM users WHERE id = ?', (user_id,)).fetchone()
        
        badges = []
        score = user['score'] if user else 0
        
        # Badge thresholds
        if score >= 1000:
            badges.append("Security Champion")
        if score >= 500:
            badges.append("Security Driver")
        if score >= 100:
            badges.append("Security Enthusiast")
        if score >= 10:
            badges.append("Getting Started")
        
        # Special badges
        try:
            stats = get_user_stats(user_id)
            training_stats = stats.get('training_stats', {})
            url_stats = stats.get('url_stats', {})
            
            total_quizzes = training_stats.get('total_quizzes', 0) if training_stats else 0
            total_checks = url_stats.get('total_checks', 0) if url_stats else 0
            malicious_found = url_stats.get('malicious_found', 0) if url_stats else 0
            
            if total_quizzes and total_quizzes >= 5:
                badges.append("Dedicated Learner")
            if total_checks and total_checks >= 10:
                badges.append("Vigilant Protector")
            if malicious_found and malicious_found >= 3:
                badges.append("Threat Hunter")
        except Exception as e:
            print(f"Warning: Could not update special badges: {e}")
        
        # Update badges
        conn.execute('UPDATE users SET badges = ? WHERE id = ?', (json.dumps(badges), user_id))
        conn.commit()
        conn.close()
        
        return badges
    except Exception as e:
        print(f"Error in update_user_badges: {e}")
        return []

def get_all_quizzes():
    """Get all available quizzes"""
    conn = get_db_connection()
    quizzes = conn.execute('SELECT * FROM quizzes').fetchall()
    conn.close()
    return quizzes

def user_exists(username, email):
    """Check if user exists"""
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                       (username, email)).fetchone()
    conn.close()
    return user is not None

def create_user(username, email, password_hash):
    """Create new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                  (username, email, password_hash))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Log registration activity
    log_activity(user_id, 'registration', 'New user registered', 0)
    
    return user_id

def get_user_by_username(username):
    """Get user by username"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user




def add_extra_quizzes():
    """Add 3 more quizzes manually if fewer than 6 exist"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check how many quizzes exist
    existing_count = cursor.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0]

    if existing_count >= 6:
        print("✅ Already have 6 or more quizzes.")
        conn.close()
        return

    print(f"📘 Found only {existing_count} quizzes. Adding more...")

    extra_quizzes = [
        {
            "title": "Safe Browsing Habits",
            "category": "Internet Safety",
            "questions": [
                {
                    "question": "Which of the following URLs is most likely safe to click?",
                    "options": [
                        "http://bank-login.com",
                        "https://mybank.com/login",
                        "http://secure-mybank.com",
                        "https://bank-verification.net"
                    ],
                    "correct_answer": 1,
                    "explanation": "Always use HTTPS and the official domain name of your bank."
                },
                {
                    "question": "What should you do when a browser shows a 'Not Secure' warning?",
                    "options": [
                        "Ignore it and continue",
                        "Proceed only if it's your bank site",
                        "Avoid entering sensitive data",
                        "Refresh the page multiple times"
                    ],
                    "correct_answer": 2,
                    "explanation": "Never enter passwords or payment info on 'Not Secure' sites."
                },
                {
                    "question": "What is a common sign of a malicious website?",
                    "options": [
                        "Spelling errors and pop-ups",
                        "Clean design",
                        "HTTPS padlock",
                        "Official domain name"
                    ],
                    "correct_answer": 0,
                    "explanation": "Phishing and scam sites often have poor grammar and many pop-ups."
                }
            ]
        },
        {
            "title": "Social Media Security",
            "category": "Privacy",
            "questions": [
                {
                    "question": "Which of these is a bad security practice on social media?",
                    "options": [
                        "Sharing personal details like address",
                        "Using two-factor authentication",
                        "Keeping profile private",
                        "Strong passwords"
                    ],
                    "correct_answer": 0,
                    "explanation": "Never share personal details publicly on social media."
                },
                {
                    "question": "If you receive a suspicious friend request, you should:",
                    "options": [
                        "Accept to see who it is",
                        "Report or ignore it",
                        "Send a message first",
                        "Block immediately"
                    ],
                    "correct_answer": 1,
                    "explanation": "Avoid engaging with unknown users and report suspicious accounts."
                },
                {
                    "question": "Why should you review app permissions on social media platforms?",
                    "options": [
                        "To remove apps that collect unnecessary data",
                        "To make your feed more colorful",
                        "It boosts followers",
                        "To get rewards"
                    ],
                    "correct_answer": 0,
                    "explanation": "Third-party apps can collect your private info if permissions are not reviewed."
                }
            ]
        },
        {
            "title": "Email Security Essentials",
            "category": "Email Protection",
            "questions": [
                {
                    "question": "What is the best way to verify a suspicious email sender?",
                    "options": [
                        "Click the link to confirm",
                        "Reply asking for details",
                        "Check sender domain and contact via official website",
                        "Forward to all colleagues"
                    ],
                    "correct_answer": 2,
                    "explanation": "Always check the sender’s official domain or call the company directly."
                },
                {
                    "question": "Attachments ending in which extension are most risky?",
                    "options": [".jpg", ".pdf", ".exe", ".txt"],
                    "correct_answer": 2,
                    "explanation": ".exe files can contain executable malware or trojans."
                },
                {
                    "question": "What should you do before clicking an email link?",
                    "options": [
                        "Hover over it to preview the URL",
                        "Click fast before it disappears",
                        "Trust if it looks professional",
                        "Disable antivirus"
                    ],
                    "correct_answer": 0,
                    "explanation": "Always hover to verify the real destination before clicking any link."
                }
            ]
        }
    ]

    # Insert new quizzes
    for quiz in extra_quizzes:
        cursor.execute(
            "INSERT INTO quizzes (title, questions, category) VALUES (?, ?, ?)",
            (quiz["title"], json.dumps(quiz["questions"]), quiz["category"])
        )

    conn.commit()
    conn.close()
    print("✅ Added 3 extra quizzes successfully.")


# =============================================================================
# VIDEO RECOMMENDATIONS FUNCTIONS
# =============================================================================
def save_recommendations(user_id, skill_level, topic_category, recommendations_json):
    """Save AI-generated video recommendations for a user"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO video_recommendations (user_id, skill_level, topic_category, recommendations_json)
        VALUES (?, ?, ?, ?)
    ''', (user_id, skill_level, topic_category, recommendations_json))
    conn.commit()
    conn.close()

def get_latest_recommendations(user_id):
    """Get the most recent video recommendations for a user"""
    conn = get_db_connection()
    recommendation = conn.execute('''
        SELECT * FROM video_recommendations 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1
    ''', (user_id,)).fetchone()
    conn.close()
    return recommendation

def get_user_score(user_id):
    """Get user's current score"""
    conn = get_db_connection()
    user = conn.execute('SELECT score FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user['score'] if user else 0

def determine_skill_level(score):
    """Determine skill level based on user's points"""
    if score == 0:
        return "beginner"
    elif score < 300:
        return "intermediate"
    elif score < 600:
        return "advanced"
    else:
        return "expert"

