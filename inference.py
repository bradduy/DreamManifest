import pathlib
from google import genai
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from langchain.agents import AgentExecutor
from langchain.agents import AgentType

# 1. Setup the Gemini Client
client = genai.Client()

# 2. Define a function to call the Gemini Image Generation API
def call_gemini_image(prompt: str):
    # Configure image generation settings
    gen_images = client.models.generate_image(
        model='imagen-3.0-generate-001',  # Model ID for Gemini Image
        prompt=prompt,
        config=genai.types.GenerateImageConfig(
            number_of_images=1,  # You can adjust the number of images to generate
            safety_filter_level="BLOCK_ONLY_HIGH",  # Adjust the safety filter
            person_generation="ALLOW_ADULT",  # You can control whether to allow adult content
            aspect_ratio="3:4",  # Aspect ratio for the image
            negative_prompt="Outside"  # What to avoid in the generated image
        )
    )

    # Save generated image(s)
    image_urls = []
    for n, image in enumerate(gen_images.generated_images):
        image_path = pathlib.Path(f'{n}.png')
        image_path.write_bytes(image.image.image_bytes)  # Save as PNG
        image_urls.append(str(image_path))  # Collect the image path (could be a URL if the API provided one)
    return image_urls

# 3. Define LangChain tools
generate_image_tool = Tool(
    name="GeminiImageGenerator",
    func=call_gemini_image,
    description="Use this tool to generate an image based on a text prompt using the Google Gemini API."
)

# 4. Set up LangChain agent with OpenAI model (or any LLM of your choice)
llm = OpenAI(temperature=0.7)  # You can change the model and temperature based on your needs
tools = [generate_image_tool]

# 5. Initialize LangChain agent
agent = initialize_agent(tools, llm, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

# 6. Example usage with LangChain agent
def generate_image_from_prompt(prompt: str):
    result = agent.run(prompt)
    return result

# Test with a prompt
if __name__ == "__main__":
    user_prompt = "Robot holding a red skateboard"
    image_paths = generate_image_from_prompt(user_prompt)
    print(f"Generated image paths: {image_paths}")
