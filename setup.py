import setuptools

version = "0.0.11"

setuptools.setup(
    name="shpyx",
    version=version,
    author="https://github.com/Apakottur",
    description="Configurable shell command execution in Python",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Apakottur/shpyx",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={"shpyx": ["py.typed"]},
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
)
