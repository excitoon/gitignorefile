"""Setup script."""

import os
import setuptools


with open(f"{os.path.dirname(os.path.abspath(__file__))}/requirements.txt") as requirements:
    with open(f"{os.path.dirname(os.path.abspath(__file__))}/README.md") as readme:
        setuptools.setup(
            name="gitignorefile",
            version="1.1.2",
            description="A spec-compliant `.gitignore` parser for Python",
            long_description=readme.read(),
            long_description_content_type="text/markdown",
            author="Vladimir Chebotarev",
            author_email="vladimir.chebotarev@gmail.com",
            license="MIT",
            classifiers=[
                "Development Status :: 5 - Production/Stable",
                "Intended Audience :: Developers",
                "License :: OSI Approved :: MIT License",
                "Operating System :: OS Independent",
                "Programming Language :: Python :: 3 :: Only",
                "Programming Language :: Python :: 3.6",
                "Programming Language :: Python :: 3.7",
                "Programming Language :: Python :: 3.8",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
                "Topic :: Software Development :: Libraries :: Python Modules",
                "Topic :: Software Development :: Version Control :: Git",
                "Topic :: Text Processing :: Filters",
            ],
            keywords=["git", "gitignore"],
            project_urls={
                "Documentation": "https://github.com/excitoon/gitignorefile/blob/master/README.md",
                "Source": "https://github.com/excitoon/gitignorefile",
                "Tracker": "https://github.com/excitoon/gitignorefile/issues",
            },
            url="https://github.com/excitoon/gitignorefile",
            packages=["gitignorefile"],
            scripts=[],
            install_requires=requirements.read().splitlines(),
        )
