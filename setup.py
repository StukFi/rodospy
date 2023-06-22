import setuptools

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "rodospy",
    version = "2.0",
    author = "Tuomas Peltonen",
    author_email = "tuomas.peltonen@stuk.fi",
    description = "Python interface for JRODOS WPS and REST services",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/StukFi/rodospy",
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where="src"),
    python_requires = ">=3.5"
)
