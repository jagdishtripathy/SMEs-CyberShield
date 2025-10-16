from flask import Blueprint, request, jsonify, session
import os
from .gemini_api import GeminiChatbot
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Initialize chatbot with environment variable or default key
# In production, use a secure method to store and retrieve API keys
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyAVM5fW5br_RIDNhmUJ1F5XaFiemVe9QuI')
chatbot = GeminiChatbot(api_key=GEMINI_API_KEY)

@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint to handle chat messages and return responses from the Gemini API.
    """
    # Check if user is logged in
    if 'logged_in' not in session or not session['logged_in']:
        logger.warning("Unauthorized attempt to access chatbot.")
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get message from request
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    user_message = data['message']
    logger.info(f"Received chatbot message: {user_message[:50]}...")
    
    # Get response from Gemini
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
    """
    # Check if user is logged in
    if 'logged_in' not in session or not session['logged_in']:
        logger.warning("Unauthorized attempt to reset chatbot.")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
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