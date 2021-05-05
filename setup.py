import codecs

from setuptools import find_packages, setup

VERSION_FILE = "pytest_never_sleep/_version.py"


with codecs.open("README.md", "r", "utf-8") as fh:
    long_description = fh.read()


setup(
    name="pytest-never-sleep",
    use_scm_version={
        "write_to": VERSION_FILE,
        "local_scheme": "dirty-tag",
    },
    setup_requires=["setuptools_scm==5.0.2"],
    author="Denis Korytkin",
    author_email="DKorytkin@gmail.com",
    description="pytest plugin helps to avoid adding tests without mock `time.sleep`",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DKorytkin/pytest-never-sleep",
    keywords=["py.test", "pytest", "without sleep", "mock time.sleep"],
    py_modules=[
        "pytest_never_sleep.plugin",
        "pytest_never_sleep.hooks",
        "pytest_never_sleep.never_sleep",
    ],
    packages=find_packages(exclude=["tests*"]),
    install_requires=["pytest>=3.5.1"],
    entry_points={"pytest11": ["never_sleep = pytest_never_sleep.plugin"]},
    license="MIT license",
    python_requires=">=2.7",
    classifiers=[
        "Framework :: Pytest",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities",
    ],
)
