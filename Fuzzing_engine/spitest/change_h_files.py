import os
import re

def read_file_with_encoding(file_path):
    encodings = ['utf-8', 'gbk', 'latin-1']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue
    print(f"Warning: Unable to read file {file_path}, skipping this file.")
    return None

def convert_includes(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.c', '.h')):
                file_path = os.path.join(root, file)
                convert_file(file_path)

def convert_file(file_path):
    content = read_file_with_encoding(file_path)
    if content is None:
        return

    # Update the regular expression to match more cases
    pattern = r'(^|\n)\s*#\s*include\s*<([^>]+)>'
    replacement = r'\1#include "\2"'

    modified_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if content != modified_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(modified_content)
            print(f"File modified: {file_path}")
        except Exception as e:
            print(f"Fail to write the file {file_path}: {str(e)}")
    else:
        print(f"No modifications needed for file: {file_path}")

def print_unmodified_includes(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.c', '.h')):
                file_path = os.path.join(root, file)
                content = read_file_with_encoding(file_path)
                if content is None:
                    continue
                includes = re.findall(r'^\s*#\s*include\s*<[^>]+>', content, re.MULTILINE)
                if includes:
                    print(f"Unmodified #include statements in file {file_path} :")
                    for include in includes:
                        print(f"  {include}")

if __name__ == "__main__":
    directory = r"C:\SandBox\Chery\T003\Views\DevelopmentView"
    convert_includes(directory)
    print("\nCheck unmodified #include statements:")
    print_unmodified_includes(directory)
    print("\nProcessing finish.")