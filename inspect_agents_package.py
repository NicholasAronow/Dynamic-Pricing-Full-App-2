import sys
print(f"Python version: {sys.version}")

try:
    import agents
    print(f"Agents version: {agents.__version__ if hasattr(agents, '__version__') else 'unknown'}")
    print(f"Agents dir: {dir(agents)}")
    
    # Check if these specific imports exist
    try:
        from agents import Tool
        print("Successfully imported Tool")
    except ImportError as e:
        print(f"Failed to import Tool: {e}")
    
    try:
        from agents import ToolType
        print("Successfully imported ToolType")
    except ImportError as e:
        print(f"Failed to import ToolType: {e}")
        
    try:
        from agents import FunctionTool
        print("Successfully imported FunctionTool")
    except ImportError as e:
        print(f"Failed to import FunctionTool: {e}")
        
    try:
        from agents.tools import ToolType
        print("Successfully imported ToolType from agents.tools")
    except ImportError as e:
        print(f"Failed to import ToolType from agents.tools: {e}")

except ImportError as e:
    print(f"Failed to import agents: {e}")
