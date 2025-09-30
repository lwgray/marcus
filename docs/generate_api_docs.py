#!/usr/bin/env python3
"""
Generate comprehensive Sphinx API documentation from Marcus codebase.

This script scans all Python modules and generates RST files for complete API coverage.
"""
import os
from pathlib import Path
from collections import defaultdict

def find_python_modules(src_dir):
    """Find all Python modules in the source directory."""
    modules = []
    src_path = Path(src_dir)

    for py_file in src_path.rglob("*.py"):
        # Skip __pycache__, __init__.py (unless it has code), and test files
        if "__pycache__" in str(py_file):
            continue
        if py_file.name.startswith("test_"):
            continue

        # Convert file path to module path
        rel_path = py_file.relative_to(src_path.parent)
        module_path = str(rel_path.with_suffix("")).replace(os.sep, ".")

        modules.append({
            'path': module_path,
            'file': py_file,
            'name': py_file.stem,
            'package': module_path.rsplit('.', 1)[0] if '.' in module_path else module_path
        })

    return modules

def organize_by_package(modules):
    """Organize modules by their top-level package."""
    packages = defaultdict(list)

    for module in modules:
        # Get top-level package
        top_level = module['path'].split('.')[0]
        packages[top_level].append(module)

    return packages

def generate_api_rst(output_file, modules_by_package):
    """Generate comprehensive API RST file."""

    content = """Python API Reference
====================

Complete Python API documentation for all Marcus modules.

**Auto-generated from {total_files} Python files (~65,000 lines of code).**

.. contents:: Table of Contents
   :local:
   :depth: 2

""".format(total_files=sum(len(mods) for mods in modules_by_package.values()))

    # Package organization with nice names
    package_titles = {
        'marcus_mcp': ('MCP Server', 'Marcus MCP server implementation and tools.'),
        'src': ('Source Code', 'Core Marcus implementation.'),
        'ai': ('AI & Intelligence', 'Artificial intelligence and machine learning systems.'),
        'core': ('Core Systems', 'Core Marcus functionality and models.'),
        'intelligence': ('Intelligence Systems', 'Memory, learning, and decision-making.'),
        'integrations': ('Integrations', 'External service integrations.'),
        'orchestration': ('Orchestration', 'Task and agent orchestration.'),
        'worker': ('Worker Management', 'Worker lifecycle and support.'),
        'communication': ('Communication', 'Inter-agent and system communication.'),
        'monitoring': ('Monitoring', 'Health monitoring and metrics.'),
        'quality': ('Quality Assurance', 'Testing, validation, and QA.'),
        'analysis': ('Analysis & Reporting', 'Analytics and report generation.'),
        'recommendations': ('Recommendations', 'Task and optimization recommendations.'),
        'workflow': ('Workflow', 'Workflow management and state machines.'),
        'modes': ('Operational Modes', 'Different operational modes (adaptive, creator, enricher).'),
        'config': ('Configuration', 'Configuration management and settings.'),
        'infrastructure': ('Infrastructure', 'Event bus, service registry, persistence.'),
        'logging': ('Logging', 'Event logging and conversation tracking.'),
        'visualization': ('Visualization', 'Dashboards, charts, and timelines.'),
        'cost_tracking': ('Cost Tracking', 'Budget management and cost analysis.'),
        'performance': ('Performance', 'Profiling and optimization.'),
        'security': ('Security', 'Authentication, authorization, permissions.'),
        'operations': ('Operations', 'Deployment and pipeline operations.'),
        'utils': ('Utilities', 'Helper functions and data structures.'),
        'enhancements': ('Enhancements', 'Task and project enhancement systems.'),
        'organization': ('Organization', 'Project and task organization tools.'),
        'detection': ('Detection', 'Blocker and orphan detection.'),
        'learning': ('Learning', 'Pattern recognition and knowledge base.'),
        'reports': ('Reporting', 'Report generation and dashboards.'),
        'templates': ('Templates', 'Project and task templates.'),
        'marketplace': ('Marketplace', 'Extension marketplace (future).'),
        'enterprise': ('Enterprise', 'Enterprise features (future).'),
    }

    # Sort packages by importance
    package_order = [
        'marcus_mcp', 'core', 'ai', 'intelligence', 'integrations',
        'orchestration', 'worker', 'communication', 'monitoring', 'quality',
        'analysis', 'recommendations', 'workflow', 'modes', 'config',
        'infrastructure', 'logging', 'visualization', 'cost_tracking',
        'performance', 'security', 'operations', 'utils', 'enhancements',
        'organization', 'detection', 'learning', 'reports'
    ]

    # Add packages in order
    for package_name in package_order:
        if package_name == 'src':
            continue  # Skip src wrapper

        modules = modules_by_package.get(package_name, [])
        if not modules:
            modules = modules_by_package.get(f'src.{package_name}', [])

        if not modules:
            continue

        title, description = package_titles.get(package_name, (package_name.title(), ''))

        content += f"\n{title}\n"
        content += "-" * len(title) + "\n\n"
        if description:
            content += f"{description}\n\n"

        # Group by subpackage
        subpackages = defaultdict(list)
        standalone = []

        for module in modules:
            parts = module['path'].split('.')
            if len(parts) > 2:  # Has subpackage
                sub = parts[1] if parts[0] == 'src' else parts[0]
                subpackages[sub].append(module)
            else:
                standalone.append(module)

        # Add standalone modules first
        for module in sorted(standalone, key=lambda x: x['name']):
            content += generate_module_section(module)

        # Add subpackages
        for sub_name, sub_modules in sorted(subpackages.items()):
            if sub_name == package_name:
                continue

            content += f"\n{sub_name.title()}\n"
            content += "~" * len(sub_name) + "\n\n"

            for module in sorted(sub_modules, key=lambda x: x['name']):
                content += generate_module_section(module, is_sub=True)

    with open(output_file, 'w') as f:
        f.write(content)

    print(f"Generated API documentation: {output_file}")
    print(f"Total modules documented: {sum(len(mods) for mods in modules_by_package.values())}")

def generate_module_section(module, is_sub=False):
    """Generate RST section for a single module."""
    header_char = "^" if is_sub else "~"

    section = f"\n{module['name'].replace('_', ' ').title()}\n"
    section += header_char * len(section.strip()) + "\n\n"
    section += f".. automodule:: {module['path']}\n"
    section += "   :members:\n"
    section += "   :undoc-members:\n"
    section += "   :show-inheritance:\n\n"

    return section

if __name__ == '__main__':
    src_dir = Path(__file__).parent.parent / 'src'
    output_file = Path(__file__).parent / 'source' / 'api' / 'python_api.rst'

    print(f"Scanning {src_dir}...")
    modules = find_python_modules(src_dir)
    print(f"Found {len(modules)} Python modules")

    modules_by_package = organize_by_package(modules)
    print(f"Organized into {len(modules_by_package)} top-level packages")

    generate_api_rst(output_file, modules_by_package)
    print("\n✅ API documentation generated successfully!")
    print(f"\nNext step: cd docs_sphinx && sphinx-build -b html source build/html")
