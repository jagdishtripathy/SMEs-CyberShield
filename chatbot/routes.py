from flask import Blueprint, request, jsonify, session
import os
from .gemini_api import GeminiChatbot
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Initialize chatbot with environment variable (no hardcoded fallback for security)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

chatbot = GeminiChatbot(api_key=GEMINI_API_KEY)

@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']
    logger.info(f"Received chatbot message: {user_message[:50]}...")

    try:
        response = chatbot.send_message(user_message)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error getting chatbot response: {str(e)}")
        return jsonify({"error": f"Failed to get response: {str(e)}"}), 500


@chatbot_bp.route('/reset', methods=['POST'])
def reset_chat():
    """
    Endpoint to reset the chat conversation.
    Authentication is optional - works with or without logged-in session.
    """
    try:
        # Check if user is logged in (optional - for tracking purposes)
        is_authenticated = 'logged_in' in session and session['logged_in']
        
        if is_authenticated:
            logger.info(f"Authenticated user reset conversation")
        else:
            logger.info(f"Anonymous user reset conversation")
        
        chatbot.reset_conversation()
        return jsonify({"success": True, "message": "Conversation reset successfully"})
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        return jsonify({"error": f"Failed to reset conversation: {str(e)}"}), 500

def init_app(app):
    """
    Initialize the blueprint with the Flask app.
    """
    app.register_blueprint(chatbot_bp)
    logger.info("Chatbot blueprint registered")