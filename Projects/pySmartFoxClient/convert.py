import os
import re

def convert_print_statements(directory="."):
    """
    Scans all Python files in the specified directory and its subdirectories
    to convert Python 2 'print' statements to Python 3 'print()' functions.

    It will replace lines like:
      - print "Hello, World!"
      - print a, b
    with:
      - print("Hello, World!")
      - print(a, b)
    
    It handles simple cases and avoids modifying lines that already use
    the print function syntax, or are commented out.
    """
    print(f"Starting conversion in directory: {os.path.abspath(directory)}")
    
    # Regular expression to match a print statement.
    # It looks for `print` followed by a space, but not an open parenthesis.
    # It also ignores lines that are commented out.
    print_regex = re.compile(r'^\s*print\s+(.*)$')
    
    # Counters for a summary at the end
    files_modified = 0
    statements_converted = 0

    # Walk through the directory tree
    for root, dirs, files in os.walk(directory):
        for filename in files:
            # Only process Python files
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                print(f"\nProcessing file: {filepath}")
                
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                new_lines = []
                file_changed = False
                
                for line in lines:
                    # Search for the pattern in each line
                    match = print_regex.match(line)
                    if match:
                        content_to_print = match.group(1).strip()
                        # If the content contains a comma, it's a tuple.
                        # We don't need to wrap it again.
                        if ',' in content_to_print:
                            new_line = line.replace(f'print {content_to_print}', f'print({content_to_print})')
                        else:
                            # For single arguments, we just wrap them.
                            new_line = line.replace(f'print {content_to_print}', f'print({content_to_print})')

                        new_lines.append(new_line)
                        statements_converted += 1
                        file_changed = True
                        print(f"  - Converted: '{line.strip()}' -> '{new_line.strip()}'")
                    else:
                        new_lines.append(line)

                # If any changes were made, write the new content back to the file
                if file_changed:
                    try:
                        with open(filepath, 'w') as f:
                            f.writelines(new_lines)
                        files_modified += 1
                        print(f"  - Changes saved to {filepath}")
                    except IOError as e:
                        print(f"Error writing to file {filepath}: {e}")
                else:
                    print(f"  - No changes needed.")

    print("\n" + "="*30)
    print("Conversion Complete!")
    print(f"Files modified: {files_modified}")
    print(f"Print statements converted: {statements_converted}")
    print("="*30 + "\n")

if __name__ == "__main__":
    convert_print_statements()
