import logging
import os
from jsonschema import validate
import yaml
from os import listdir
from os.path import isfile, join
import argparse
from rasa_core import utils
from rasa_core.domain import Domain
import sys


logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument(
    '--domain', '-d',
    type=str, default='domain.yml',
    help='Path for the domain file'
)

parser.add_argument(
    '--stories', '-s',
    type=str, default='data/stories.md',
    help='Path for the stories file or directory'
)

parser.add_argument(
    '--intents', '-i',
    type=str, default='data/intents.md',
    help='Path for the intents file or directory'
)

parser.add_argument(
    '--warnings', '-w',
    action='store_true',
    default=False,
    help='Run script with warings'
)

parser.add_argument(
    '--no_validate_intents', action='store_true', default=False,
    help='Skips validations to intents'
)

parser.add_argument(
    '--no_validate_utters', action='store_true', default=False,
    help='Skips validations to utters'
)


class Validator:

    def __init__(self, domain="domain.yml", intents="data/nlu.md",
                 stories="data/stories.md"):
        self.domain = domain
        self.intents = intents
        self.stories = stories
        self.valid_intents = []
        self.valid_utters = []

    @classmethod
    def validate_paths(cls, domain_path, intents_path, stories_path, warnings=True):
        paths = [domain_path, intents_path, stories_path]
        all_paths_verified = True
        domain = ""
        stories = []
        intents =[]

        for path in paths:
            if os.path.isfile(path):
                if paths.index(path) == 0:
                    domain = path
                elif paths.index(path) == 1:
                    intents.append(path)
                elif paths.index(path) == 2:
                    stories.append(path)

            elif os.path.isdir(path) and (paths.index(path) != 0):
                if not path.endswith('/'):
                    path += '/'

                path_files = [f for f in listdir(path)
                              if isfile(join(path, f))]

                for file in path_files:
                    if paths.index(path) == 1:
                        intents.append(path + file)
                    elif paths.index(path) == 2:
                        stories.append(path + file)

            else:
                logger.error("{} is not a valid path".format(path))
                all_paths_verified = False

        if cls.verify_domain(domain, warnings) and all_paths_verified:
            return cls(domain=domain,
                        stories=stories,
                        intents=intents)
        else:
            sys.exit("There was an error while loading files")


    @classmethod
    def verify_domain(cls, domain, warnings=True):
        if domain != '':
            schema = """
            type: object
            """
            with open(domain, 'r') as file:
                domain_file = file.read()            
            try:
                validate(yaml.load(domain_file), yaml.load(schema))
                if warnings:
                    cls._check_spaces_between_utters(domain)
                logger.info('Domain verified')
                return 1
            except Exception as e:
                logger.error("Verification of domain file from {} failed with "
                             "the following exception:".format(domain))
                logger.error(str(e))
                return 0
        else:
            logger.error('The domain could not be verified')
            return 0

    @classmethod
    def _check_spaces_between_utters(cls, domain):
        if domain != '':
            with open (domain, 'r') as file:
                domain_lines = file.readlines()

            for line in domain_lines:
                line_s = line.strip().split('_')
                if len(line_s) >= 2 and line_s[0] == 'utter':
                    index = domain_lines.index(line) - 1

                    previous_line = domain_lines[index]

                    if previous_line != '\n' and previous_line != 'templates:\n':
                        logger.warning("There should be a space between lines"
                                        " {} and {} in the domain file"
                                        .format((index + 1), (index + 2)))
        else:
            logger.error('The domain could not be verified')


    def _search(self, vector, searched_value):
        vector.append(searched_value)
        count = 0
        while(searched_value != vector[count]):
            count += 1
        if(count == len(vector)-1):
            return False
        else:
            return True

    def verify_intents(self):
        if self.intents != [] and self.domain != '':
            # Adds intents in domain to the list
            with open(self.domain, 'r') as file:
                domain_lines = file.readlines()

            intents_in_domain = []
            intents_in_files = []

            start = domain_lines.index('intents:\n') + 1

            for i in range(start, len(domain_lines)):
                line = domain_lines[i]
                s_line = line.split()
                if len(s_line) >= 2 and s_line[0] == '-':
                    intents_in_domain.append(s_line[1])
                elif line.strip().endswith(':'):
                    break

            # Adds intents in intent files to another list
            for intent in self.intents:
                with open(intent, 'r') as f:
                    intent_lines = f.readlines()

                for line in intent_lines:
                    s_line = line.split(':')
                    if len(s_line) >= 2 and s_line[0] == '## intent':
                        intents_in_files.append(s_line[1].strip())

            # Checks if the intents in domain are the same as the ones
            # in the intent files
            for intent in intents_in_domain:
                found = self._search(intents_in_files, intent)
                if not found:
                    logger.error("The intent {} is in the domain file but "
                                 "was not found in the intent files"
                                 .format(intent))
                else:
                    self.valid_intents.append(intent)

            for intent in intents_in_files:
                found = self._search(intents_in_domain, intent)
                if not found:
                    logger.error("The intent {} is in the intents files but "
                                 "was not found in the domain file"
                                 .format(intent))

        else:
            logger.error('The intents could not be verified')

    def verify_intents_in_stories(self):

        if self.intents != [] and self.domain != '' and self.stories != []:

            if self.valid_intents == []:
                self.verify_intents()

            for file in self.stories:
                with open(file, 'r') as f:
                    stories_lines = f.readlines()

                for line in stories_lines:
                    s_line = line.split()
                    if len(s_line) >= 2 and s_line[0] == '*':
                        intent = s_line[1]
                        if '{' in intent:
                            intent = intent[:intent.find('{')]

                        found = self._search(self.valid_intents, intent)
                        if not found:
                            logger.error("The intent {} is used in the "
                                         "stories story file {} (line: {}) "
                                         "but it's not a valid intent"
                                         .format(intent, file,
                                         (stories_lines.index(line)+1)))

        else:
            logger.error('The intents could not be verified')

    def verify_intents_being_used(self):
        if self.intents != [] and self.domain != '' and self.stories != []:
            if self.valid_intents == []:
                self.verify_intents()

            stories_intents = []
            for file in self.stories:
                with open(file, 'r') as f:
                    stories_lines = f.readlines()

                for line in stories_lines:
                    s_line = line.split()
                    if len(s_line) >= 2 and s_line[0] == '*':
                        intent = s_line[1]
                        if '{' in intent:
                            intent = intent[:intent.find('{')]
                        stories_intents.append(intent)

            for intent in self.valid_intents:
                found = self._search(stories_intents, intent)
                if not found:
                    logger.warning("The intent {} is not being used in any "
                                   "story".format(intent))

        else:
            logger.error('The intents could not be verified')

    def verify_utters(self):
        if self.domain != '':
            with open(self.domain, 'r') as file:
                domain_lines = file.readlines()

            utter_actions = []
            utter_templates = []

            start = domain_lines.index('templates:\n') + 1
            for i in range(start, len(domain_lines)):
                line = domain_lines[i]
                s_line = line.strip()
                v_line = s_line.split()

                if s_line.split('_')[0] == 'utter':
                    utter = s_line
                    if utter.endswith(':'):
                        utter = utter[:utter.find(':')]
                    utter_templates.append(utter)
                elif ((len(v_line) >= 1 and v_line[0] != '-') and
                      (s_line.endswith(':') and not line.startswith(' '))):
                    break

            start = domain_lines.index('actions:\n') + 1
            for i in range(start, len(domain_lines)):
                line = domain_lines[i]
                s_line = line.split()
                if len(s_line) == 2 and s_line[0] == '-':
                    ss_line = s_line[1].split('_')
                    if ss_line[0] == 'utter':
                        utter_actions.append(s_line[1])
                elif line.strip().endswith(':'):
                    break

            for utter in utter_actions:
                found = self._search(utter_templates, utter)
                if not found:
                    logger.error("There is no template for utter {}"
                                 .format(utter))
                else:
                    self.valid_utters.append(utter)

            for utter in utter_templates:
                found = self._search(utter_actions, utter)
                if not found:
                    logger.error("The utter {} is not listed in actions"
                                 .format(utter))
        else:
            logger.error('The utters could not be verified')

    def verify_utters_in_stories(self):
        if self.domain != '' and self.stories != []:

            if self.valid_utters == []:
                self.verify_utters()

            for file in self.stories:
                with open(file, 'r') as f:
                    stories_lines = f.readlines()

                for line in stories_lines:
                    s_line = line.split()

                    if(len(s_line) == 2 and s_line[0] == '-' and
                       s_line[1][:5] == 'utter'):
                        utter = s_line[1]
                        found = self._search(self.valid_utters, utter)
                        if not found:
                            logger.error("The utter {} is used in the stories "
                                         "story file {} (line: {}) but it's "
                                         "not a valid utter".format(utter,
                                         file,(stories_lines.index(line)+1)))
        else:
            logger.error('The utters could not be verified')

    def verify_utters_being_used(self):
        if self.domain != '' and self.stories != []:
            if self.valid_utters == []:
                self.verify_utters()

            stories_utters = []
            for file in self.stories:
                with open(file, 'r') as f:
                    stories_lines = f.readlines()

                for line in stories_lines:
                    s_line = line.split()
                    if len(s_line) == 2 and s_line[0] == '-':
                        utter = s_line[1]
                        stories_utters.append(utter)

            for utter in self.valid_utters:
                found = self._search(stories_utters, utter)
                if not found:
                    logger.warning("The utter {} is not being used in any "
                                   "story".format(utter))

        else:
            logger.error('The utters could not be verified')

    def run_verifications(self):
        self.verify_intents_in_stories()
        self.verify_intents_being_used()
        self.verify_utters_in_stories()
        self.verify_utters_being_used()


if __name__ == '__main__':
    domain = parser.parse_args().domain
    stories = parser.parse_args().stories
    intents = parser.parse_args().intents
    warning = parser.parse_args().warnings
    no_validate_intents = parser.parse_args().no_validate_intents
    no_validate_utters = parser.parse_args().no_validate_utters

    utils.configure_colored_logging(loglevel='DEBUG')

    validator = Validator.validate_paths(domain, intents, stories, warning)

    if not no_validate_intents:
        validator.verify_intents()
        validator.verify_intents_in_stories()
        if warning:
            validator.verify_intents_being_used()

    if not no_validate_utters:
        validator.verify_utters()
        validator.verify_utters_in_stories()
        if warning:
            validator.verify_utters_being_used()
