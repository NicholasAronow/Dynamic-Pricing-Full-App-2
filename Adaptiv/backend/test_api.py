import requests
import json

def test_agent_capabilities():
    """Test the agent capabilities endpoint to check if OpenAI agent is included"""
    url = "http://localhost:5000/api/agents/dynamic-pricing/agent-capabilities"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("Available agents:")
            for agent_key, agent_details in data["agents"].items():
                print(f"- {agent_key}: {agent_details['name']}")
            
            # Check specifically for OpenAI agent
            if "openai_agent" in data["agents"]:
                print("\nOpenAI agent found with details:")
                print(json.dumps(data["agents"]["openai_agent"], indent=2))
                return True
            else:
                print("\nOpenAI agent not found in capabilities!")
                return False
        else:
            print(f"Error: API returned status code {response.status_code}")
            return False
    except Exception as e:
        print(f"Error connecting to API: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing agent capabilities endpoint...")
    test_agent_capabilities()
