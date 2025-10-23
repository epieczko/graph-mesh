"""
Setup configuration for Graph-Mesh project.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
README = Path(__file__).parent / "README.md"
long_description = README.read_text() if README.exists() else ""

# Read requirements
REQUIREMENTS = Path(__file__).parent / "requirements.txt"
requirements = []
if REQUIREMENTS.exists():
    with open(REQUIREMENTS) as f:
        requirements = [
            line.strip() for line in f
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="graph-mesh",
    version="0.1.0",
    description="Multi-source ontology alignment and knowledge graph fusion platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Graph-Mesh Team",
    author_email="",
    url="https://github.com/epieczko/graph-mesh",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
            "isort>=5.12.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.24.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "graph-mesh=graph_mesh_orchestrator.pipeline:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="ontology alignment knowledge-graph semantic-web owl rdf",
)
