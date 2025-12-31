import os

def list_files():
    # 1. Get the directory where this script is living (tests folder)
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Go up one level to find the Project Root
    project_root = os.path.dirname(current_script_dir)
    
    print(f"Project Root: {project_root}\n")
    
    # 3. Walk through the project root
    for root, dirs, files in os.walk(project_root):
        # Filter out clutter
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', 'node_modules', '.git', '.idea', '.vscode']]
        
        # Calculate depth for pretty printing
        level = root.replace(project_root, '').count(os.sep)
        indent = '│   ' * level
        print(f'{indent}├── {os.path.basename(root)}/')
        
        subindent = '│   ' * (level + 1)
        for f in files:
            if not f.startswith('.') and not f.endswith('.pyc') and not f.endswith('.DS_Store'):
                print(f'{subindent}├── {f}')

if __name__ == "__main__":
    list_files()