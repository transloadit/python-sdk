import copy


class OptionBuilder(object):
    def __init__(self, options=None):
        super(OptionBuilder, self).__init__()
        self.options = options or {}
        self.steps = {}

    def add_step(self, name, robot, options):
        options['robot'] = robot
        self.steps[name] = options

    def remove_step(self, name):
        self.steps.pop(name)

    def get_options(self):
        options = copy.deepcopy(self.options)
        options['steps'] = self.steps
        return options
