import copy


class OptionBuilder(object):
    """
    Object representation of a new Assembly to be created.

    :Attributes:
        - transloadit (<transloadit.client.Transloadit>):
            An instance of the Transloadit class.
        - files (dict):
            storage of files to be uploaded. Each file is stored with a key corresponding
            to its field name when it is being uploaded.

    :Constructor Args:
        - options (Optional[dict]):
            params to send along with the assembly. Please see
            https://transloadit.com/docs/api-docs/#21-create-a-new-assembly for available options.
    """
    def __init__(self, options=None):
        super(OptionBuilder, self).__init__()
        self.options = options or {}
        self.steps = {}

    def add_step(self, name, robot, options):
        """
        Add a step to the Assembly/Template

        :Args:
            - name (str): The name of the step.
            - robot (str): The name of the robot for the step
            - options (dict): The options to apply to the step
        """
        options['robot'] = robot
        self.steps[name] = options

    def remove_step(self, name):
        """
        Remove the step specified by the given name.abs

        :Args:
            - name (str): The name of the step to remove.
        """
        self.steps.pop(name)

    def get_options(self):
        """
        Return the Assembly/Template options in Transloadit, ready format. 
        """
        options = copy.deepcopy(self.options)
        options['steps'] = self.steps
        return options
