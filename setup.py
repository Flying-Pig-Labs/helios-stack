#!/usr/bin/env python3
"""
Setup script for Headless Research System
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="headless-research",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A headless multi-tier research system using Claude Code sub-agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/headless-research",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "aiofiles>=23.0.0",
        "asyncio-throttle>=1.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "diskcache>=5.6.0",
        "structlog>=24.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "parsing": [
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "headless-research=headless_research.cli:main",
            "check-research-setup=scripts.check_setup:main",
        ],
    },
    include_package_data=True,
    package_data={
        "headless_research": ["agents/definitions/*.md"],
    },
)
