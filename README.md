# DreamManifest: Make Dream Come True by Video to Image Generator API

This API service converts speech from video files into text and then generates images based on the extracted text using Google's Gemini AI. The service provides a complete pipeline that handles video upload, audio extraction, speech recognition, and image generation.

![Description of GIF](doc/demo.gif)

## Features

- Extract audio from video files
- Convert speech to text using **Google's Speech Recognition**
- Understand speech using generative model with **Langchain**.
- Generate images from text using **Gemini 2.0 Flash**
- RESTful API endpoints for processing and retrieving results
- Support for multiple video formats (MP4, AVI, MOV, WMV, FLV)
- Automatic cleanup of temporary files
- YAML-based configuration for easy setup

## Prerequisites

- Python 3.10 or higher
- Google Gemini API key
- FFmpeg (for video processing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/bradduy/DreamManifest.git
cd DreamManifest
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg (if not already installed):
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)

5. Set up configuration:
   - Copy the template configuration file:
     ```bash
     cp config.template.yaml config.yaml
     ```
   - Edit `config.yaml` and update with your settings:
     ```yaml
     api_keys:
       google_gemini: "your-api-key-here"  # Get from Google AI Studio
     ```
   - The config.yaml file is gitignored to prevent committing sensitive data

## Configuration

The `config.yaml` file contains all the configuration settings:

```yaml
api_keys:
  google_gemini: "your-api-key-here"

server:
  host: "0.0.0.0"
  port: 8080
  debug: true

upload_settings:
  max_content_length: 16777216  # 16MB in bytes
  allowed_extensions:
    - mp4
    - avi
    - mov
    - wmv
    - flv

directories:
  uploads: "uploads"
  temp: "temp"
  output: "output"
```

You can customize:
- API keys
- Server settings (host, port, debug mode)
- Upload limitations
- File type restrictions
- Directory locations

## Usage

### Starting the Server

Run the Flask server:
```bash
python inference.py
```

The server will start using the settings from your `config.yaml` file.

### API Endpoints

1. **Health Check**
   - Endpoint: `GET /health`
   - Response:
     ```json
     {
       "status": "healthy"
     }
     ```

2. **Process Video**
   - Endpoint: `POST /process-video`
   - Request: Form data with video file
   - Key: `video`
   - Supported formats: MP4, AVI, MOV, WMV, FLV
   - Max file size: 16MB
   - Response:
     ```json
     {
       "prompt": "extracted text from speech",
       "image_paths": ["generated_image_uuid.png"]
     }
     ```

3. **Get Generated Image**
   - Endpoint: `GET /get-image/<image_name>`
   - Response: PNG image file

### Testing the API

1. Using the provided test script:
```bash
# Install requests if not already installed
pip install requests

# Update video path in test_api.py
python test_api.py
```

2. Using cURL:
```bash
# Health check
curl http://localhost:8080/health

# Process video
curl -X POST -F "video=@path/to/your/video.mp4" http://localhost:8080/process-video

# Get generated image
curl http://localhost:8080/get-image/image_name.png --output downloaded_image.png
```

3. Using Postman:
   - Import the following endpoints:
     - GET `http://localhost:8080/health`
     - POST `http://localhost:8080/process-video` (with form-data: key=video, type=file)
     - GET `http://localhost:8080/get-image/<image_name>`

## Project Structure

```
.
├── inference.py          # Main server implementation
├── test_api.py          # API test script
├── requirements.txt     # Python dependencies
├── uploads/            # Temporary video storage
├── temp/              # Temporary audio files
└── output/            # Generated images
```

## Error Handling

The API includes comprehensive error handling for:
- Missing or invalid video files
- Unsupported file types
- File size limits
- Processing errors
- Missing images

## Cleanup

The service automatically cleans up:
- Temporary video files after processing
- Temporary audio files after text extraction
- Failed uploads in case of errors

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

[MIT License](LICENSE)