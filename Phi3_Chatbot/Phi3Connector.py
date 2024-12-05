import requests
import json

class Phi3Connector:
    def __init__(self, base_url="http://localhost:11434", model="phi3"):
        """
        Initialize the connection to the Phi3 model via Ollama's REST API.
        """
        self.base_url = base_url
        self.model = model

    def send_prompt(self, prompt):
        """
        Send a prompt to the Phi3 model and get the response.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            # Make the API request
            response = requests.post(url, json=payload)
            
            # Raise an error if the request failed
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Phi3: {e}")
            return None
        except KeyError:
            print("Unexpected response format. Check the API output.")
            return None

def main():
    phi3 = Phi3Connector()
    
    # Example prompts
    prompts = [
        "Explain quantum computing in simple terms.",
        "Write a short poem about technology.",
        "What is the capital of France?"
    ]
    
    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        response = phi3.send_prompt(prompt)
        if response:
            print(f"Response: {response}")
        else:
            print("Failed to get a response.")

if __name__ == "__main__":
    main()
