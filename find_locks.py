#!/usr/bin/env python3
"""
Lock Detection Script for Marcus

This script finds all asyncio.Lock objects and similar synchronization
primitives in the Marcus codebase to help identify event loop binding issues.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Any


class LockDetector(ast.NodeVisitor):
    """AST visitor to find lock-related code patterns."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings = []
        self.current_class = None
        self.current_function = None
    
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Assign(self, node):
        """Find assignments like self._lock = asyncio.Lock()"""
        if isinstance(node.value, ast.Call):
            self._check_lock_call(node.value, node.lineno, "assignment")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Find direct calls to Lock constructors"""
        self._check_lock_call(node, node.lineno, "call")
        self.generic_visit(node)
    
    def _check_lock_call(self, node, lineno, context):
        """Check if a call creates a lock object"""
        lock_patterns = [
            ("asyncio", "Lock"),
            ("asyncio", "RLock"), 
            ("asyncio", "Semaphore"),
            ("asyncio", "BoundedSemaphore"),
            ("threading", "Lock"),
            ("threading", "RLock"),
            ("threading", "Semaphore"),
        ]
        
        for module, lock_type in lock_patterns:
            if self._is_lock_call(node, module, lock_type):
                self.findings.append({
                    'file': self.filepath,
                    'line': lineno,
                    'type': f"{module}.{lock_type}",
                    'context': context,
                    'class': self.current_class,
                    'function': self.current_function,
                })
    
    def _is_lock_call(self, node, module, lock_type):
        """Check if node is a call to module.lock_type()"""
        if not isinstance(node, ast.Call):
            return False
            
        # Check for asyncio.Lock() pattern
        if (isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == module and
            node.func.attr == lock_type):
            return True
            
        # Check for imported Lock pattern (from asyncio import Lock)
        if (isinstance(node.func, ast.Name) and
            node.func.id == lock_type):
            return True
            
        return False


def scan_file(filepath: Path) -> List[Dict[str, Any]]:
    """Scan a single Python file for locks."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        tree = ast.parse(content)
        detector = LockDetector(str(filepath))
        detector.visit(tree)
        
        # Also do regex search for patterns AST might miss
        regex_patterns = [
            r'asyncio\.Lock\(\)',
            r'threading\.Lock\(\)', 
            r'\.Lock\(\)',
            r'_lock\s*=',
            r'lock\s*=.*Lock',
        ]
        
        for i, line in enumerate(content.split('\n'), 1):
            for pattern in regex_patterns:
                if re.search(pattern, line):
                    detector.findings.append({
                        'file': str(filepath),
                        'line': i,
                        'type': 'regex_match',
                        'context': f'Pattern: {pattern}',
                        'class': None,
                        'function': None,
                        'code': line.strip()
                    })
        
        return detector.findings
    
    except Exception as e:
        return [{
            'file': str(filepath),
            'line': 0,
            'type': 'error',
            'context': f'Error parsing file: {e}',
            'class': None,
            'function': None,
        }]


def scan_directory(directory: Path) -> List[Dict[str, Any]]:
    """Scan all Python files in directory for locks."""
    all_findings = []
    
    for py_file in directory.rglob('*.py'):
        # Skip certain directories
        skip_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv'}
        if any(skip_dir in py_file.parts for skip_dir in skip_dirs):
            continue
            
        findings = scan_file(py_file)
        all_findings.extend(findings)
    
    return all_findings


def main():
    """Main entry point."""
    marcus_dir = Path(__file__).parent
    print(f"🔍 Scanning {marcus_dir} for asyncio locks...")
    
    findings = scan_directory(marcus_dir)
    
    # Group findings by file
    by_file = {}
    for finding in findings:
        file_path = finding['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(finding)
    
    # Report results
    print(f"\n📊 Found {len(findings)} potential lock-related items in {len(by_file)} files:\n")
    
    for file_path in sorted(by_file.keys()):
        rel_path = os.path.relpath(file_path, marcus_dir)
        print(f"📄 {rel_path}:")
        
        for finding in sorted(by_file[file_path], key=lambda x: x['line']):
            location = f"Line {finding['line']}"
            if finding['class']:
                location += f" in {finding['class']}"
            if finding['function']:
                location += f".{finding['function']}()"
            
            print(f"   {location}: {finding['type']}")
            if 'code' in finding:
                print(f"      Code: {finding['code']}")
        print()
    
    # Summary
    lock_types = {}
    for finding in findings:
        lock_type = finding['type']
        lock_types[lock_type] = lock_types.get(lock_type, 0) + 1
    
    print("📈 Summary by lock type:")
    for lock_type, count in sorted(lock_types.items()):
        print(f"   {lock_type}: {count}")


def check_for_problematic_locks():
    """Check for locks that could cause event loop binding issues."""
    marcus_dir = Path(__file__).parent
    findings = scan_directory(marcus_dir)
    
    # Look for problematic patterns
    problems = []
    for finding in findings:
        if finding['type'] in ['asyncio.Lock', 'threading.Lock']:
            if finding['context'] == 'assignment' and '__init__' in str(finding['function']):
                problems.append(f"⚠️  {finding['file']}:{finding['line']} - Lock created in __init__ (event loop binding risk)")
    
    if problems:
        print("🚨 Potential event loop binding issues found:")
        for problem in problems:
            print(f"   {problem}")
        return 1
    else:
        print("✅ No obvious lock binding issues detected")
        return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.exit(check_for_problematic_locks())
    else:
        main()