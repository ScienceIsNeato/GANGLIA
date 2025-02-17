import os
import re
import chardet

def collect_python_files(start_path):
    python_files = []
    for root, _, files in os.walk(start_path):
        if '.git' in root or '.venv' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def extract_imports(content):
    imports = []
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith(('import ', 'from ')):
            imports.append(line)
    return imports

def minify_content(content):
    # Remove docstrings
    content = re.sub(r'\"\"\"[\s\S]*?\"\"\"\n', '', content)
    content = re.sub(r'\'\'\'[\s\S]*?\'\'\'\n', '', content)

    # Remove comments
    content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)

    # Remove empty lines
    content = re.sub(r'\n\s*\n', '\n', content)

    return content.strip()

def process_files():
    files = collect_python_files('.')
    all_imports = set()
    minified_content = []

    for file_path in files:
        try:
            encoding = detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            # Extract and collect imports
            imports = extract_imports(content)
            all_imports.update(imports)

            # Remove imports from content
            content = re.sub(r'^(import|from).*$\n?', '', content, flags=re.MULTILINE)

            # Minify content
            minified = minify_content(content)

            if minified.strip():
                # Add file header comment
                header = f'\n# File: {file_path}\n'
                minified_content.append(header + minified)
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            continue

    # Combine everything
    final_content = '# GANGLIA - Minified Repository\n\n'
    final_content += '# Imports\n' + '\n'.join(sorted(all_imports)) + '\n'
    final_content += '\n'.join(minified_content)

    # Write to desktop
    desktop_path = os.path.expanduser('~/Desktop/ganglia_minified.py')
    with open(desktop_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f'Minified repository saved to: {desktop_path}')

if __name__ == '__main__':
    process_files()
