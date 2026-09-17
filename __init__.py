import os
import importlib
import glob

# Tell ComfyUI to look for the web directory containing the JS file
WEB_DIRECTORY = "./web"

# Initialize the master mappings that ComfyUI looks for
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Get the absolute path of the 'nodes' subfolder
NODE_DIR = os.path.join(os.path.dirname(__file__), "nodes")

# Find all .py files inside the 'nodes' subfolder, excluding __init__.py files
py_files = glob.glob(os.path.join(NODE_DIR, "*.py"))
module_names = [
    os.path.basename(f)[:-3] 
    for f in py_files 
    if not f.endswith("__init__.py")
]

# Dynamically import each file from the subfolder and extract mappings
for module_name in module_names:
    try:
        # Relative import syntax pointing inside the 'nodes' directory
        # e.g., converts "auto_break" into ".nodes.auto_break"
        module = importlib.import_module(f".nodes.{module_name}", package=__name__)
        
        # Check and merge NODE_CLASS_MAPPINGS
        if hasattr(module, "NODE_CLASS_MAPPINGS"):
            NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)
            
        # Check and merge NODE_DISPLAY_NAME_MAPPINGS
        if hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS"):
            NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)
            
    except Exception as e:
        print(f"[AGI Nodes Error] Failed to load module '{module_name}' from nodes subfolder: {e}")

# Expose the merged dictionaries and web directory to ComfyUI's global loader
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]