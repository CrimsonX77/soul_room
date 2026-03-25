from setuptools import setup, find_packages

setup(
    name="soul-room",
    version="0.1.0",
    description="Multi-model AI collaboration framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Crimson Valentine",
    url="https://github.com/CrimsonDragonX7/soul-room",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PyYAML>=6.0",
        "aiohttp>=3.9.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "ollama": ["ollama>=0.2.0"],
        "gui": ["PyQt6>=6.6.0"],
        "voice": ["edge-tts>=6.1.0", "SpeechRecognition>=3.10.0"],
        "all": [
            "ollama>=0.2.0",
            "PyQt6>=6.6.0",
            "edge-tts>=6.1.0",
            "SpeechRecognition>=3.10.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
