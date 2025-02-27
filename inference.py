import requests
from langchain.agents import initialize_agent, Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.agents import AgentExecutor

# 1. Setup Gemini Image API details (Example)
GEMINI_API_KEY = "your_api_key_here"
GEMINI_API_URL = "https://api.gemini-image.com/generate"

# 2. Define the function to call the Gemini Image API
def call_gemini_image(prompt: str):
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "size": "1024x1024",  # or whatever size the API supports
    }
    response = requests.post(GEMINI_API_URL, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()['image_url']  # assuming the response contains the image URL
    else:
        return f"Error: {response.status_code} - {response.text}"

# 3. Define LangChain tools
generate_image_tool = Tool(
    name="GeminiImageGenerator",
    func=call_gemini_image,
    description="Use this tool to generate an image based on a text prompt."
)

# 4. Set up LangChain agent with OpenAI model (or any LLM of your choice)
llm = OpenAI(temperature=0.7)  # You can change the model and temperature based on your needs
tools = [generate_image_tool]

# 5. Initialize LangChain agent
agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description", verbose=True)

# 6. Example usage with LangChain agent
def generate_image_from_prompt(prompt: str):
    result = agent.run(prompt)
    return result

# Test with a prompt
if __name__ == "__main__":
    user_prompt = "A futuristic city skyline at sunset"
    image_url = generate_image_from_prompt(user_prompt)
    print(f"Generated image URL: {image_url}")
