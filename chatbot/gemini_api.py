import google.generativeai as genai
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class GeminiChatbot:
    """
    A chatbot class that uses Google's Gemini API for cybersecurity assistance.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini chatbot with the provided API key.
        
        Args:
            api_key: Optional API key, will use environment variable if not provided
        """
        # Use provided API key, or get from environment variable, or raise error
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('GEMINI_API_KEY')
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
        
        genai.configure(api_key=self.api_key)
        
        # Configure the model
        self.model = genai.GenerativeModel(
            model_name="models/gemini-flash-latest",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ],
        )
        
        # Initialize chat history
        self.chat_history = []
        
        # Set the cybersecurity system prompt as the first message
        cybersecurity_prompt = self._get_cybersecurity_system_prompt()
        self.chat = self.model.start_chat(history=[])
    
    def _get_cybersecurity_system_prompt(self) -> str:
        """
        Returns the system prompt that instructs the model to focus on cybersecurity assistance.
        """
        return """
        You are a cybersecurity assistant for a SIEM (Security Information and Event Management) system and your name is CyberShield.
        Your primary role is to help security analysts and IT staff with cybersecurity-related questions and issues.
        
        You can:
        1. Explain security concepts, threats, and best practices
        2. Help interpret log data and security alerts
        3. Provide guidance on incident response procedures
        4. Recommend security tools and configurations
        5. Assist with compliance and security policy questions
        
        You should:
        - Provide accurate, up-to-date information about cybersecurity
        - Be concise but thorough in your explanations
        - Prioritize security best practices in your recommendations
        - Acknowledge when a question is outside your expertise
        - Avoid providing guidance that could enable malicious activities
        
        When discussing potential security issues:
        - Emphasize the importance of proper investigation before taking action
        - Recommend involving appropriate security personnel for critical issues
        - Suggest documentation and evidence collection procedures
        
        Your goal is to enhance the security posture of the organization by providing helpful, 
        educational guidance to security staff using the SIEM system.
        """
    
    def send_message(self, message: str) -> str:
        """
        Send a message to the Gemini model and get a response.
        
        Args:
            message: The user's message
            
        Returns:
            The model's response
        """
        try:
            # For the first message, prepend the cybersecurity system prompt
            if not self.chat_history:
                system_prompt = self._get_cybersecurity_system_prompt()
                prompt_message = f"{system_prompt}\n\nUser query: {message}"
                response = self.chat.send_message(prompt_message)
            else:
                response = self.chat.send_message(message)
            
            # Add to chat history
            self.chat_history.append({"role": "user", "content": message})
            self.chat_history.append({"role": "assistant", "content": response.text})
            
            return response.text
        except Exception as e:
            return f"Error communicating with Gemini API: {str(e)}"
    
    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.chat_history = []
        self.chat = self.model.start_chat(history=[])