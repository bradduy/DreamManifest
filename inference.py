import pathlib
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool
from moviepy import *
import speech_recognition as sr
import os
import yaml
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import uuid

def load_config():
    """Load configuration from YAML file"""
    config_path = "config.yaml"
    template_path = "config.template.yaml"
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            f"Please copy {template_path} to {config_path} and update with your settings."
        )
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Load configuration
config = load_config()

app = Flask(__name__)

# Configure upload settings from config
UPLOAD_FOLDER = config['directories']['uploads']
ALLOWED_EXTENSIONS = set(config['upload_settings']['allowed_extensions'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config['upload_settings']['max_content_length']

# Create necessary directories from config
for directory in config['directories'].values():
    os.makedirs(directory, exist_ok=True)

# Setup the Gemini Client with API key from config
GOOGLE_API_KEY = config['api_keys']['google_gemini']
genai.configure(api_key=GOOGLE_API_KEY)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 2. Function to extract audio from video
def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video file and save it as WAV"""
    try:
        # Generate output audio path
        audio_path = os.path.join('temp', f'{uuid.uuid4()}.wav')
        
        # Load video and extract audio
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path)
        video.close()
        
        return audio_path
    except Exception as e:
        raise Exception(f"Error extracting audio from video: {str(e)}")

# 3. Function to convert speech to text
def speech_to_text(audio_path: str) -> str:
    """Convert speech from audio file to text"""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)  # Using Google's speech recognition
            return text
    except Exception as e:
        raise Exception(f"Error converting speech to text: {str(e)}")

# 4. Define function to call the Gemini Image Generation API
def call_gemini_image(prompt: str):
    try:
        # Use text-to-text model to enhance the prompt
        text_model = genai.GenerativeModel('gemini-pro')
        enhanced_prompt = text_model.generate_content(
            f"Create a detailed image generation prompt based on this description: {prompt}. "
            "Make it more descriptive and artistic."
        ).text

        # Generate image using the enhanced prompt
        image_model = genai.GenerativeModel('gemini-pro-vision')
        response = image_model.generate_content(
            enhanced_prompt,
            generation_config={
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32,
                "max_output_tokens": 1024,
            },
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
            ]
        )

        # Save generated image
        image_name = f'{uuid.uuid4()}.png'
        image_path = os.path.join('output', image_name)
        with open(image_path, 'wb') as f:
            f.write(response.image.image_bytes)
        return [image_name]
    except Exception as e:
        print(f"Error in image generation: {str(e)}")
        return []

# 5. Define LangChain tools
generate_image_tool = Tool(
    name="GeminiImageGenerator",
    func=call_gemini_image,
    description="Use this tool to generate an image based on a text prompt using the Google Gemini API."
)

# 6. Set up LangChain agent with Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.7,
)

tools = [generate_image_tool]
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 7. Main function to process video and generate image
def generate_image_from_video(video_path: str):
    """Process video to extract speech and generate image based on the speech content"""
    try:
        # Step 1: Extract audio from video
        audio_path = extract_audio_from_video(video_path)
        
        # Step 2: Convert speech to text
        text_prompt = speech_to_text(audio_path)
        
        # Step 3: Generate image from text
        result = agent.run(text_prompt)
        
        # Clean up temporary files
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return {"prompt": text_prompt, "image_paths": result}
    except Exception as e:
        raise Exception(f"Error in video processing pipeline: {str(e)}")

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/process-video', methods=['POST'])
def process_video():
    """Endpoint to process video and generate image"""
    try:
        # Check if video file is present in request
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
        
        file = request.files['video']
        
        # Check if a file was selected
        if file.filename == '':
            return jsonify({"error": "No video file selected"}), 400
        
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
        file.save(video_path)
        
        try:
            # Process the video
            result = generate_image_from_video(video_path)
            
            # Clean up the uploaded video
            if os.path.exists(video_path):
                os.remove(video_path)
            
            return jsonify(result), 200
            
        except Exception as e:
            # Clean up the uploaded video in case of error
            if os.path.exists(video_path):
                os.remove(video_path)
            raise e
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-image/<image_name>', methods=['GET'])
def get_image(image_name):
    """Endpoint to retrieve generated images"""
    try:
        image_path = os.path.join('output', image_name)
        if not os.path.exists(image_path):
            return jsonify({"error": "Image not found"}), 404
        return send_file(image_path, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(
        host=config['server']['host'],
        port=config['server']['port'],
        debug=config['server']['debug']
    )
