import requests
import os

def test_health():
    response = requests.get('http://localhost:8080/health')
    print("📢 Health check reponse:", response.json()['status'])

def process_video(video_path):
    
    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found at {video_path}")
        return

    with open(video_path, 'rb') as video_file:
        files = {
            'video': (os.path.basename(video_path), video_file, 'video/mp4')
        }
    
        response = requests.post('http://localhost:8080/process-video', files=files)
        
        if response.status_code == 200:
            result = response.json()
            requests.post('http://localhost:8080/save-prompt', json={"prompt": result['prompt']})
            
            upload_image(result['image_paths'])
            download_image(result['image_paths'])
            
        else:
            print("❌ Error:", response.json())
            
def upload_image(image_path):
    """Upload an image to the server."""
    
    url = f'http://localhost:8080/upload-image'
    
    with open(image_path, 'rb') as img_file:
        files = {'image': (os.path.basename(image_path), img_file, 'image/png')}
        response = requests.post(url, files=files)
    
    if response.status_code != 200:
        print(f"❌ Failed to upload image: {image_path}, Error: {response.json()}")

def download_image(image_name):
    
    image_name = os.path.basename(image_name)
    response = requests.get(f'http://localhost:8080/get-image/{image_name}', stream=True)
    if response.status_code == 200:
        # Save the image
        output_path = f'downloads/downloaded_{image_name}'
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        print(f"❌ Error downloading image: {response.json()}")
    
if __name__ == "__main__":
    
    test_health()
    video_path = "video_test.mp4"
    process_video(video_path) 