import sys
print(f"Python version: {sys.version}")

try:
    import agents
    print(f"Agents version: {agents.__version__ if hasattr(agents, '__version__') else 'unknown'}")
    
    # Import FunctionTool and function_tool
    try:
        from agents import FunctionTool, function_tool
        print("Successfully imported FunctionTool and function_tool")
        
        # Define a sample function with the decorator
        @function_tool
        def sample_tool(query: str) -> dict:
            """Sample tool function"""
            return {"result": f"Processed: {query}"}
        
        # Print information about the tool
        print(f"Type of sample_tool: {type(sample_tool)}")
        print(f"Dir of sample_tool: {dir(sample_tool)}")
        
        # Check attributes
        if hasattr(sample_tool, 'function'):
            print(f"sample_tool.function: {sample_tool.function}")
        
        if hasattr(sample_tool, 'type'):
            print(f"sample_tool.type: {sample_tool.type}")
        else:
            print("FunctionTool doesn't have 'type' attribute")
            
        # Check if this is how tools are used in the API
        print("\nInspecting how tools should be passed to API:")
        
        # Check available attributes and methods
        if hasattr(sample_tool, 'to_dict'):
            print(f"sample_tool.to_dict(): {sample_tool.to_dict()}")
        else:
            print("FunctionTool doesn't have 'to_dict' method")
            
        # Check the schema of the function
        if hasattr(sample_tool, 'schema'):
            print(f"sample_tool.schema: {sample_tool.schema}")
        else:
            print("FunctionTool doesn't have 'schema' attribute")
            
        # Check the function definition
        if hasattr(sample_tool, 'function'):
            print(f"Function name: {sample_tool.function.__name__ if hasattr(sample_tool.function, '__name__') else 'Unknown'}")
        
    except ImportError as e:
        print(f"Failed to import FunctionTool or function_tool: {e}")

except ImportError as e:
    print(f"Failed to import agents module: {e}")
