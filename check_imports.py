import sys
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

try:
    import openai
    print(f"OpenAI version: {openai.__version__}")
    print(f"OpenAI path: {openai.__path__}")
except ImportError as e:
    print(f"OpenAI import error: {e}")

try:
    import agents
    print(f"Agents module exists: {True}")
    print(f"Agents path: {agents.__path__}")
except ImportError as e:
    print(f"Agents import error: {e}")

try:
    from openai import agents
    print(f"OpenAI Agents submodule exists: {True}")
except ImportError as e:
    print(f"OpenAI Agents submodule error: {e}")
