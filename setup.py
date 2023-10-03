from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="devtale",
    version="0.1.2",
    author="Mystral AI",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "devtale=devtale.cli:main",
        ],
    },
    include_package_data=True,
)
