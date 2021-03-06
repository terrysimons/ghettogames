import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ghettogames",
    version="0.0.1",
    author="Terry Simons",
    author_email="terry.simons@gmail.com",
    description="Ghetto Games and Tools for Pygame and Python 3",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/terrysimons/ghettogames",
    packages=setuptools.find_packages(),
    scripts=['scripts/bitmappy'],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
)
