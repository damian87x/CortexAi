import os
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")
    
print("Python path:")
for p in sys.path:
    print(f"  - {p}")

print("\nTrying imports...")

# Try imports to validate they work
try:
    from src.cortexai.tools.tool_collection import ToolCollection
    print("✅ Successfully imported ToolCollection")
except ImportError as e:
    print(f"❌ Failed to import ToolCollection: {e}")

try:
    from src.cortexai.tools.base_tool import BaseTool, ToolResult
    print("✅ Successfully imported BaseTool and ToolResult")
except ImportError as e:
    print(f"❌ Failed to import BaseTool and ToolResult: {e}")

print("\nFixing __init__.py files...")

# Check if there are any references to the legacy structure
import re

fixable_init_files = [
    os.path.join(project_root, 'tests', '__init__.py'),
    os.path.join(project_root, 'tests', 'src', '__init__.py') if os.path.exists(os.path.join(project_root, 'tests', 'src', '__init__.py')) else None,
    os.path.join(project_root, 'tests', 'src', 'cortexai', '__init__.py') if os.path.exists(os.path.join(project_root, 'tests', 'src', 'cortexai', '__init__.py')) else None,
    os.path.join(project_root, 'tests', 'src', 'cortexai', 'providers', '__init__.py') if os.path.exists(os.path.join(project_root, 'tests', 'src', 'cortexai', 'providers', '__init__.py')) else None,
    os.path.join(project_root, 'tests', 'src', 'cortexai', 'tools', '__init__.py') if os.path.exists(os.path.join(project_root, 'tests', 'src', 'cortexai', 'tools', '__init__.py')) else None,
]

fixable_init_files = [f for f in fixable_init_files if f and os.path.exists(f)]

for init_file in fixable_init_files:
    with open(init_file, 'r') as f:
        content = f.read()
    
    if 'CortexAi' in content:
        print(f"📝 Fixing {init_file}")
        # Create backup
        with open(f"{init_file}.bak", 'w') as f:
            f.write(content)
            
        # Remove problematic imports
        content = re.sub(r'from CortexAi.*', '# Legacy import removed', content)
        content = re.sub(r'import CortexAi.*', '# Legacy import removed', content)
        
        with open(init_file, 'w') as f:
            f.write(content)
        print(f"✅ Fixed {init_file}")
    else:
        print(f"✅ No issues in {init_file}")

print("\nDone fixing imports!")
