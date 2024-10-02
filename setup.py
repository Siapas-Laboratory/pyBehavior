from setuptools import setup, find_packages

setup(
    name = "pyBehavior",
    version = '0.0.0',
    author = "Nathaniel Nyema",
    author_email = "nnyema@caltech.edu",
    description = "A Python based system for controlling rodent behavior experiments", 
    packages = find_packages(),
    scripts = ['pyBehavior/main.py'],
    package_data = {"": ["*.csv", "*.mat"]},
    install_requires = [
        'numpy',
        'pyyaml',
        'python-statemachine',
        'paramiko',
        'scp'
    ],
    extras_require = {'ni': ['nidaqmx']}
)