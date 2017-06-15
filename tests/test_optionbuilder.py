import unittest

from transloadit.optionbuilder import OptionBuilder


class OptionBuilderTest(unittest.TestCase):
    def setUp(self):
        self.option_builder = OptionBuilder()

    def test_add_step(self):
        self.option_builder.add_step(
            'resize', '/image/resize', {'width': 70, 'height': 70})

        self.assertEqual(self.option_builder.steps, {'resize': {
            'robot': '/image/resize',
            'width': 70,
            'height': 70
        }})

    def test_remove_step(self):
        self.option_builder.add_step(
            'resize', '/image/resize', {'width': 70, 'height': 70})
        self.assertTrue('resize' in self.option_builder.steps)

        self.option_builder.remove_step('resize')
        self.assertFalse('resize' in self.option_builder.steps)

    def test_get_options(self):
        self.option_builder.add_step(
            'resize', '/image/resize', {'width': 70, 'height': 70})
        self.option_builder.options['template_id'] = 'foo'

        self.assertEqual(self.option_builder.get_options(), {'steps': {'resize': {
            'robot': '/image/resize',
            'width': 70,
            'height': 70
        }}, 'template_id': 'foo'})
