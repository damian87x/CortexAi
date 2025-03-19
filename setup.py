from setuptools import setup, find_packages
import os

with open(os.path.join("CortexAi", "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

setup(
    name="CortexAi",
    version=version,
    description="A modular, scalable framework for building autonomous AI agents",
    author="CortexAi Team",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/CortexAi",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "asyncio>=3.4.3",
        "python-dotenv>=1.0.0",
    ],
    # Optional dependencies
    extras_require={
        "yaml": ["PyYAML>=6.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=0.950",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
