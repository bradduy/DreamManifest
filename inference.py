from google import genai
from google.genai import types
import google.generativeai as ggenai

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool

from moviepy import *
import speech_recognition as sr

from flask import Flask, request, jsonify, send_file, render_template

import os
import yaml
import uuid
from PIL import Image
from io import BytesIO

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

config = load_config()

app = Flask(__name__)

UPLOAD_FOLDER = config['directories']['uploads']
ALLOWED_EXTENSIONS = set(config['upload_settings']['allowed_extensions'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config['upload_settings']['max_content_length']

for directory in config['directories'].values():
    os.makedirs(directory, exist_ok=True)

GOOGLE_API_KEY = config['api_keys']['google_gemini']
ggenai.configure(api_key=GOOGLE_API_KEY)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video file and save it as WAV"""
    try:
        audio_path = os.path.join('temp', f'{uuid.uuid4()}.wav')
        
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path)
        video.close()
        
        return audio_path
    except Exception as e:
        raise Exception(f"Error extracting audio from video: {str(e)}")

def speech_to_text(audio_path: str) -> str:
    """Convert speech from audio file to text"""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)  
            return text
    except Exception as e:
        raise Exception(f"Error converting speech to text: {str(e)}")

def call_gemini(prompt: str):
    try:
        text_model = ggenai.GenerativeModel('gemini-pr')
        enhanced_prompt = text_model.generate_content(
            f"Create a detailed image generation prompt based on this description: {prompt}. "
            "Make it more descriptive and artistic."
        ).text

        image_model = ggenai.GenerativeModel('gemini-pro-vision')
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

        image_name = f'{uuid.uuid4()}.png'
        image_path = os.path.join('output', image_name)
        with open(image_path, 'wb') as f:
            f.write(response.image.image_bytes)
        return [image_name]
    
    except Exception as e:
        print(f"Error in image generation: {str(e)}")
        return []

generative_tool = Tool(
    name="GeminiImageGenerator",
    func=call_gemini,
    description="Use this tool to generate an insight prompt based on a text from the audio."
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.7,
)

tools = [generative_tool]
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def generate_image_from_video(video_path: str):
    """Process video to extract speech and generate image based on the speech content"""
    try:
        
        audio_path = extract_audio_from_video(video_path)
        
        text = speech_to_text(audio_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        insight_prompt = agent.run(f"Summarize the main idea of ​​the following paragraph in a sentence: {text}")
        
        client = genai.Client(api_key=GOOGLE_API_KEY)

        response = client.models.generate_content(
            model="models/gemini-2.0-flash-exp",
            contents= f"Generate a visual and interesting image with the following insight: {insight_prompt}",
            config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                image_path = f"output/generated_image.png"
                image.save(image_path)
                
        return {"prompt": insight_prompt, "image_paths": image_path}
            
    except Exception as e:
        raise Exception(f"error in video processing pipeline: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/process-video', methods=['POST'])
def process_video():
    """Endpoint to process video and generate image"""
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({"error": "No video file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400
        
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(video_path)
        
        try:
            result = generate_image_from_video(video_path)
            return jsonify(result), 200
            
        except Exception as e:
            if os.path.exists(video_path):
                os.remove(video_path)
            raise e
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-video/<video_name>', methods=['GET'])
def get_video(video_name):
    """Endpoint to serve an uploaded video."""
    try:
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_name)
        
        if not os.path.exists(video_path):
            return jsonify({"error": "Video not found"}), 404

        return send_file(video_path, mimetype='video/mp4', as_attachment=False)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/upload-image', methods=['POST'])
def upload_image():
    """Endpoint to upload an image and save it without extension."""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({"error": "No image file selected"}), 400

        image_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(image_path)
        
        return jsonify({"message": "Image uploaded successfully", "path": image_path}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-image/<image_name>', methods=['GET'])
def get_image(image_name):
    """Endpoint to retrieve uploaded images."""
    try:
        image_path = os.path.join(UPLOAD_FOLDER, image_name)
        
        if not os.path.exists(image_path):
            return jsonify({"error": "Image not found"}), 404
        
        return send_file(image_path, mimetype='image/png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

latest_insight_prompt = ""
@app.route('/save-prompt', methods=['POST'])
def save_prompt():
    """Save the latest insight prompt"""
    global latest_insight_prompt
    data = request.get_json()
    latest_insight_prompt = data.get("prompt", "")
    return jsonify({"message": "Insight prompt saved successfully!"}), 200

@app.route('/get-prompt', methods=['GET'])
def get_prompt():
    """Retrieve the latest saved insight prompt"""
    global latest_insight_prompt
    return jsonify({"insight_prompt": latest_insight_prompt}), 200

@app.route('/')
def home():
    """Home endpoint to display both image and video using an HTML template."""
    global latest_insight_prompt
    image_name = request.args.get('image', 'generated_image.png')
    video_name = request.args.get('video', 'video_test.mp4') 
    
    image_path = f"/get-image/{image_name}"
    video_path = f"/get-video/{video_name}"

    return render_template(
        'home.html', 
        prompt=latest_insight_prompt,
        image_path=image_path, 
        video_path=video_path
        )
    
if __name__ == "__main__":
    app.run(
        host=config['server']['host'],
        port=config['server']['port'],
        debug=config['server']['debug']
    )
