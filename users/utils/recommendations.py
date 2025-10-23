"""
Quiz-Based Video Recommendation System for Cybersecurity Learning
Uses Gemini AI to suggest targeted videos based on quiz performance and topic
"""

import google.generativeai as genai
import json
import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Gemini API key from environment variable
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

genai.configure(api_key=GEMINI_API_KEY)


def get_performance_level(score: float) -> str:
    """
    Determine recommendation level based on quiz score.
    
    Args:
        score: Quiz score percentage (0-100)
    
    Returns:
        Recommendation level: 'basic', 'medium', or 'advanced'
    """
    if score < 40:
        return "basic"
    elif score < 70:
        return "medium"
    else:
        return "advanced"


def get_ai_recommendations_for_quiz(quiz_title: str, quiz_category: str, score: float) -> Dict:
    """
    Generate AI-powered video recommendations based on quiz performance.
    
    Args:
        quiz_title: Title of the quiz (e.g., "Phishing Awareness")
        quiz_category: Category of the quiz (e.g., "Threat Detection")
        score: Quiz score percentage (0-100)
    
    Returns:
        Dictionary containing recommendations and metadata
    """
    performance_level = get_performance_level(score)
    
    # Build performance-specific prompts for non-technical users
    prompts = {
        "basic": f"""
You are a cybersecurity educator for non-technical users. A user scored {score}% on a "{quiz_title}" quiz.
They need BASIC, beginner-friendly video recommendations to understand this topic better.

Generate a JSON response with EXACTLY 3 video recommendations for BASIC/BEGINNER level on "{quiz_title}".

Each video should be:
- Very beginner-friendly (no technical jargon)
- Practical and relevant to daily life
- Around 10-20 minutes long
- From reputable sources (YouTube searches)

For each video, provide ONLY this JSON structure (no other text):
{{
  "recommendations": [
    {{
      "title": "Clear, simple video title",
      "topic": "{quiz_title}",
      "description": "1-2 sentences for non-technical users",
      "youtube_search": "Search term to find on YouTube",
      "duration": "10-15 minutes",
      "why_important": "Why this matters for you",
      "difficulty": "Beginner"
    }},
    ...3 videos total...
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text or explanation.
""",
        "medium": f"""
You are a cybersecurity educator. A user scored {score}% on a "{quiz_title}" quiz.
They need INTERMEDIATE video recommendations to deepen their understanding.

Generate a JSON response with EXACTLY 3 video recommendations for INTERMEDIATE level on "{quiz_title}".

Each video should be:
- Intermediate difficulty (some technical concepts allowed)
- Builds on basics with practical applications
- Around 20-30 minutes long
- From reputable sources (YouTube searches)

For each video, provide ONLY this JSON structure (no other text):
{{
  "recommendations": [
    {{
      "title": "Clear video title",
      "topic": "{quiz_title}",
      "description": "1-2 sentences for users building skills",
      "youtube_search": "Search term to find on YouTube",
      "duration": "20-30 minutes",
      "why_important": "Why this matters for your skills",
      "difficulty": "Intermediate"
    }},
    ...3 videos total...
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text or explanation.
""",
        "advanced": f"""
You are a cybersecurity educator. A user scored {score}% on a "{quiz_title}" quiz.
They want ADVANCED video recommendations to master this topic.

Generate a JSON response with EXACTLY 3 video recommendations for ADVANCED level on "{quiz_title}".

Each video should be:
- Advanced difficulty (technical concepts expected)
- Deep-dive into practical implementations
- Around 30-40 minutes long
- From reputable sources (YouTube searches)

For each video, provide ONLY this JSON structure (no other text):
{{
  "recommendations": [
    {{
      "title": "Advanced technical video title",
      "topic": "{quiz_title}",
      "description": "1-2 sentences for advanced learners",
      "youtube_search": "Search term to find on YouTube",
      "duration": "30-40 minutes",
      "why_important": "Why this matters for advanced practitioners",
      "difficulty": "Advanced"
    }},
    ...3 videos total...
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text or explanation.
"""
    }
    
    prompt = prompts.get(performance_level, prompts["basic"])
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        
        # Try to extract JSON from the response
        try:
            recommendations_data = json.loads(response_text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                recommendations_data = json.loads(response_text[start_idx:end_idx])
            else:
                # Fallback recommendations if parsing fails
                recommendations_data = generate_fallback_recommendations(quiz_title, performance_level)
        
        return {
            "success": True,
            "performance_level": performance_level,
            "score": score,
            "quiz_title": quiz_title,
            "recommendations": recommendations_data.get("recommendations", []),
            "generated_at": __import__('datetime').datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        # Return fallback recommendations on error
        return {
            "success": False,
            "performance_level": performance_level,
            "score": score,
            "quiz_title": quiz_title,
            "recommendations": generate_fallback_recommendations(quiz_title, performance_level),
            "error": str(e),
            "generated_at": __import__('datetime').datetime.now().isoformat()
        }


def generate_fallback_recommendations(quiz_title: str, performance_level: str) -> List[Dict]:
    """
    Generate fallback recommendations if AI fails.
    """
    fallback_data = {
        ("Phishing Awareness", "basic"): [
            {
                "title": "What is Phishing? Simple Explanation for Everyone",
                "topic": "Phishing Awareness",
                "description": "Learn how phishing emails trick people and simple ways to spot them.",
                "youtube_search": "phishing email what is phishing explained",
                "duration": "10-12 minutes",
                "why_important": "Phishing is the #1 cause of data breaches",
                "difficulty": "Beginner"
            },
            {
                "title": "How to Identify Suspicious Emails",
                "topic": "Phishing Awareness",
                "description": "Simple techniques to recognize when an email is not what it seems.",
                "youtube_search": "how to identify suspicious emails phishing red flags",
                "duration": "8-10 minutes",
                "why_important": "First defense against email-based attacks",
                "difficulty": "Beginner"
            },
            {
                "title": "Email Safety: Protect Yourself from Scams",
                "topic": "Phishing Awareness",
                "description": "Practical daily habits to stay safe from email scams and phishing.",
                "youtube_search": "email safety phishing protection tips",
                "duration": "12-15 minutes",
                "why_important": "Essential personal cybersecurity hygiene",
                "difficulty": "Beginner"
            }
        ],
        ("Password Security", "basic"): [
            {
                "title": "How to Create a Strong Password",
                "topic": "Password Security",
                "description": "Easy steps to make passwords that are hard to hack.",
                "youtube_search": "how to create strong password cybersecurity",
                "duration": "10-12 minutes",
                "why_important": "Passwords are your first line of defense",
                "difficulty": "Beginner"
            },
            {
                "title": "Password Management Basics",
                "topic": "Password Security",
                "description": "How to manage multiple passwords safely and securely.",
                "youtube_search": "password manager how to use password management",
                "duration": "12-15 minutes",
                "why_important": "Practical way to keep passwords secure",
                "difficulty": "Beginner"
            },
            {
                "title": "Why Unique Passwords Matter",
                "topic": "Password Security",
                "description": "Understand why using the same password everywhere is dangerous.",
                "youtube_search": "unique passwords why important password security",
                "duration": "8-10 minutes",
                "why_important": "Prevents account takeover across multiple sites",
                "difficulty": "Beginner"
            }
        ],
        ("Malware Awareness", "basic"): [
            {
                "title": "What is Malware? Types Explained Simply",
                "topic": "Malware Awareness",
                "description": "Learn about viruses, trojans, and ransomware in simple terms.",
                "youtube_search": "what is malware types viruses trojans explained",
                "duration": "12-15 minutes",
                "why_important": "Understand common threats to your devices",
                "difficulty": "Beginner"
            },
            {
                "title": "How to Protect Your Computer from Malware",
                "topic": "Malware Awareness",
                "description": "Practical steps to keep your computer safe from malware.",
                "youtube_search": "protect computer from malware antivirus tips",
                "duration": "10-12 minutes",
                "why_important": "Essential computer protection practices",
                "difficulty": "Beginner"
            },
            {
                "title": "Recognizing Malware: Signs Your Computer is Infected",
                "topic": "Malware Awareness",
                "description": "How to tell if your computer has been infected with malware.",
                "youtube_search": "signs computer infected malware slow performance",
                "duration": "8-10 minutes",
                "why_important": "Early detection prevents data loss",
                "difficulty": "Beginner"
            }
        ]
    }
    
    # Return specific fallback or generic basic recommendation
    key = (quiz_title, performance_level)
    if key in fallback_data:
        return fallback_data[key]
    
    # Generic fallback for any quiz
    return [
        {
            "title": f"Introduction to {quiz_title}",
            "topic": quiz_title,
            "description": f"Learn the basics of {quiz_title} to improve your understanding.",
            "youtube_search": f"{quiz_title} explained for beginners",
            "duration": "15-20 minutes",
            "why_important": f"Strengthens your knowledge of {quiz_title}",
            "difficulty": performance_level.capitalize()
        },
        {
            "title": f"{quiz_title} Best Practices",
            "topic": quiz_title,
            "description": f"Practical tips and best practices for {quiz_title}.",
            "youtube_search": f"{quiz_title} best practices tutorial",
            "duration": "15-20 minutes",
            "why_important": f"Apply {quiz_title} knowledge in real situations",
            "difficulty": performance_level.capitalize()
        },
        {
            "title": f"Common Mistakes in {quiz_title}",
            "topic": quiz_title,
            "description": f"Learn what most people get wrong about {quiz_title}.",
            "youtube_search": f"common mistakes {quiz_title} what to avoid",
            "duration": "10-15 minutes",
            "why_important": f"Avoid pitfalls in {quiz_title} awareness",
            "difficulty": performance_level.capitalize()
        }
    ]


def get_recommendation_message(score: float) -> str:
    """Get a personalized message based on quiz score."""
    if score < 40:
        return f"📚 Score: {score:.1f}% - Let's strengthen your knowledge! Check out these beginner-friendly videos."
    elif score < 70:
        return f"✏️ Score: {score:.1f}% - Good effort! Here are some intermediate videos to deepen your understanding."
    else:
        return f"🎉 Score: {score:.1f}% - Excellent work! Here are advanced videos to master this topic."
