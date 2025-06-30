#!/usr/bin/env python3
"""
Find all dictionary iterations in the codebase
"""

import os
import re

def find_dict_iterations(directory):
    """Find all dictionary iterations in Python files"""
    patterns = [
        r'for\s+\w+\s+in\s+\w+\.items\(\)',
        r'for\s+\w+\s*,\s*\w+\s+in\s+\w+\.items\(\)',
        r'for\s+\w+\s+in\s+\w+\.values\(\)',
        r'for\s+\w+\s+in\s+\w+\.keys\(\)',
        r'\{.*for.*in.*\.items\(\).*\}',
        r'\{.*for.*in.*\.values\(\).*\}',
        r'\{.*for.*in.*\.keys\(\).*\}',
    ]
    
    results = []
    
    for root, dirs, files in os.walk(directory):
        # Skip test directories and __pycache__
        if '__pycache__' in root or 'test' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    for i, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if re.search(pattern, line):
                                # Check if it's already using list()
                                if 'list(' not in line:
                                    results.append((filepath, i, line.strip()))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results

if __name__ == "__main__":
    # Search in key directories
    directories = [
        'src/integrations',
        'src/ai',
        'src/intelligence',
        'src/detection',
        'src/modes',
        'src/core',
        'src/monitoring'
    ]
    
    all_results = []
    for directory in directories:
        if os.path.exists(directory):
            results = find_dict_iterations(directory)
            all_results.extend(results)
    
    if all_results:
        print("Found dictionary iterations without list():")
        print("=" * 80)
        for filepath, line_num, line in all_results:
            print(f"{filepath}:{line_num}")
            print(f"  {line}")
            print()
    else:
        print("No unsafe dictionary iterations found!")