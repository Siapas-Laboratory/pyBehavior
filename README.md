# pyBehavior

## Installation
Before installing be sure to have the [Anaconda distribution of Python](https://www.anaconda.com/download) installed on your device. Once you've done this, follow the below steps for instalation:

1. Clone this repository
2. Navigate to the cloned repository from a conda-enabled shell and run the following command to create an environment with all dependicies:
```
conda env create -f environment.yml
conda activate pyBehavior
```
3. Run the following commands to build and install pyBehavior
```
python setup.py bdist_wheel sdist
python -m pip install .
```
If you intend to use pyBehavior to interface with a ratBerryPi, follow the installation instructions for a client device [here](https://github.com/nathanielnyema/ratBerryPi#readme) while the pyBehavior environment is activated.

Once you've completed these steps, you can launch the pyBehavior GUI from anywhere on your device by running `python -m pyBehavior.main --setup_dir <setup_dir>`, where `<setup_dir>` is the path to a directory with subdirectories containing code for monitoring and controlling a specific setup. This directory can be empty at first -- within the GUI you can populate this directory with subdirectories with the appropriate files and template code. **NOTE: for the above command to work from anywhere you must activate the pyBehavior environment first.** For an example setup directory see this [repository](https://github.com/nathanielnyema/siapas-b150-chronic-setups)

## Usage
When launching the GUI, the user has the option to either select a pre-configured setup to load and use to run behavioral tasks, or create/edit setup configurations. For first time users, if you do not already have a pre-configured setup we recommend following the instructions in the gui to generate the template code. This will create a subfolder in the provided setup directory with some config files, a folder called `protocols`, and a file called `gui.py` which you will need to customize by adding code to flesh out the user interface with PyQt5. **Do not change any of the automatically generated code for defining the class.** pyBehavior assumes that the class as the same name as the folder containing the file and that the class is a subclass of the class `SetupGUI` defined in `pyBehavior/gui.py`. When filling in the rest of the class definition, you will need to update the field `reward_modules` which is inherited from the `SetupGUI` class. `reward_modules` should be a dictionary mapping names to all widgets to be used for reward control. These widgets must be instances of a subclass of the `RewardWidget` class defined in `pyBehavior/gui.py`. The provided widgets that meet this criterion include one for controlling the national instruments based reward modules we have in lab (`pyBehavior.interfaces.ni.NIRewardControl`) and another for controlling the modules of a ratBerryPi (`pyBehavior.interfaces.rpi.RPIRewardControl`).

The `protocols` folder will be empty but should be populated by the user with files which each define state machines for behavioral tasks to be run on the setup. In a future version of the code there will be a GUI element to generate template code, but for now we note that the users will want to import the class `Protocol` from `pyBehavior.protocols` and create a subclass of it with the same name as the file name (which should be the desired name of the protocol). `Protocol` is an abstract subclass of the `StateMachine` from the python statemachine package. As a result, we direct users to the [documentation for this package](https://python-statemachine.readthedocs.io/en/latest/) for further information on setting up the statemachine. The important caveat however, is that users must be sure to define a method called `handle_input` which will be used to signal transitions in the statemachine given an input. This input can be anything from an event detected by a sensor in the setup to the position of the animal depending on how the function itself is written. This function should then be called from the class defined in gui.py in response to an event (TODO: should maybe define an abstract register_event method in SetupGUI function which calls handle_input).