import requests
import os

def test_health():
    response = requests.get('http://localhost:8080/health')
    print("Health Check Response:", response.json())

def process_video(video_path):
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return

    # Prepare the file for upload
    with open(video_path, 'rb') as video_file:
        files = {
            'video': (os.path.basename(video_path), video_file, 'video/mp4')
        }
        
        # Make the request
        response = requests.post('http://localhost:8080/process-video', files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("Extracted Text Prompt:", result['prompt'])
            print("Generated Image Paths:", result['image_paths'])
            
            # Download the generated images
            for image_name in result['image_paths']:
                download_image(image_name)
        else:
            print("Error:", response.json())

def download_image(image_name):
    response = requests.get(f'http://localhost:8080/get-image/{image_name}', stream=True)
    if response.status_code == 200:
        # Save the image
        output_path = f'downloaded_{image_name}'
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Image downloaded successfully: {output_path}")
    else:
        print(f"Error downloading image: {response.json()}")

if __name__ == "__main__":
    # Test health endpoint
    test_health()
    
    # Test video processing
    # Replace with your video file path
    video_path = "path/to/your/video.mp4"
    process_video(video_path) 