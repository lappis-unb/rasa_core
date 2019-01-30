import logging
import os
from jsonschema import validate
import yaml
from os import listdir
from os.path import isfile, join
import argparse
from rasa_core import utils


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

parser.add_argument(
    '--no_validate_domain', action='store_true', default=False,
    help='Skips validations to domain'
)


class Validator:
    domain = ''
    intents = []
    stories = []
    valid_intents = []
    valid_utters = []

    def __init__(self, domain="domain.yml", intents="data/nlu.md",
                 stories="data/stories.md"):

        # Saving domain file
        if os.path.exists(domain):
            self.domain = domain
        else:
            logger.error("The domain file was not found")

        # Saving intents files
        if os.path.isfile(intents) and os.path.exists(intents):
            self.intents.append(intents)

        elif os.path.isdir(intents):
            if not intents.endswith('/'):
                intents += '/'

            intent_files = [f for f in listdir(intents)
                            if isfile(join(intents, f))]
            for file in intent_files:
                self.intents.append(intents + file)

        else:
            logger.error("The intents file was not found")

        # Saving stories files
        if os.path.isfile(stories) and os.path.exists(stories):
            self.stories.append(stories)

        elif os.path.isdir(stories):
            if not stories.endswith('/'):
                stories += '/'

            stories_files = [f for f in listdir(stories)
                             if isfile(join(stories, f))]
            for file in stories_files:
                self.stories.append(stories + file)

        else:
            logger.error("The stories file was not found")

    def verify_domain(self, warnings):
        if self.domain != '':
            schema = """
            type: object
            """
            file = open(self.domain, 'r')
            domain_file = file.read()
            file.close()
            try:
                validate(yaml.load(domain_file), yaml.load(schema))
                if warnings:
                    self._check_spaces_between_utters()
                logger.info('Domain verified')
            except Exception as e:
                logger.error('There is an error in ' + self.domain +
                             ' ' + str(e))
        else:
            logger.error('The domain could not be verified')

    def _check_spaces_between_utters(self):
        file = open(self.domain, 'r')
        domain_lines = file.readlines()
        file.close()
        for line in domain_lines:
            line_s = line.strip().split('_')
            if len(line_s) >= 2 and line_s[0] == 'utter':
                index = domain_lines.index(line) - 1

                previous_line = domain_lines[index]

                if previous_line != '\n' and previous_line != 'templates:\n':
                    logger.warning('There should be a space between lines ' +
                                   str(index+1) + ' and ' + str(index+2) +
                                   ' in the domain file')

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
            file = open(self.domain, 'r')
            domain_lines = file.readlines()
            file.close()
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
                f = open(intent, 'r')
                intent_lines = f.readlines()
                f.close()

                for line in intent_lines:
                    s_line = line.split(':')
                    if len(s_line) >= 2 and s_line[0] == '## intent':
                        intents_in_files.append(s_line[1].strip())

            # Checks if the intents in domain are the same as the ones
            # in the intent files
            for intent in intents_in_domain:
                found = self._search(intents_in_files, intent)
                if not found:
                    logger.error('The intent ' + intent +
                                 ' is in the domain file but was' +
                                 ' not found in the intent files')
                else:
                    self.valid_intents.append(intent)

            for intent in intents_in_files:
                found = self._search(intents_in_domain, intent)
                if not found:
                    logger.error('The intent ' + intent +
                                 ' is in the intent files but was' +
                                 ' not found in the domain file')

        else:
            logger.error('The intents could not be verified')

    def verify_intents_in_stories(self):

        if self.intents != [] and self.domain != '' and self.stories != []:

            if self.valid_intents == []:
                self.verify_intents()

            for file in self.stories:
                f = open(file, 'r')
                stories_lines = f.readlines()
                f.close()

                for line in stories_lines:
                    s_line = line.split()
                    if len(s_line) >= 2 and s_line[0] == '*':
                        intent = s_line[1]
                        if '{' in intent:
                            intent = intent[:intent.find('{')]

                        found = self._search(self.valid_intents, intent)
                        if not found:
                            logger.error('The intent ' + intent +
                                         ' is used in the stories' +
                                         ' story ile ' + file + ' (line: ' +
                                         str(stories_lines.index(line)+1) +
                                         ') but it\'s not a valid intent.')

        else:
            logger.error('The intents could not be verified')

    def verify_intents_being_used(self):
        if self.intents != [] and self.domain != '' and self.stories != []:
            if self.valid_intents == []:
                self.verify_intents()

            stories_intents = []
            for file in self.stories:
                f = open(file, 'r')
                stories_lines = f.readlines()
                f.close()

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
                    logger.warning('The intent ' + intent +
                                   ' is not being used in any story')

        else:
            logger.error('The intents could not be verified')

    def verify_utters(self):
        if self.domain != '':
            file = open(self.domain, 'r')
            domain_lines = file.readlines()
            file.close()
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
                    logger.error('There is no template for utter ' + utter)
                else:
                    self.valid_utters.append(utter)

            for utter in utter_templates:
                found = self._search(utter_actions, utter)
                if not found:
                    logger.error('The utter ' + utter +
                                 ' is not listed in actions')
        else:
            logger.error('The utters could not be verified')

    def verify_utters_in_stories(self):
        if self.domain != '' and self.stories != []:

            if self.valid_utters == []:
                self.verify_utters()

            for file in self.stories:
                f = open(file, 'r')
                stories_lines = f.readlines()
                f.close()

                for line in stories_lines:
                    s_line = line.split()

                    if(len(s_line) == 2 and s_line[0] == '-' and
                       s_line[1][:5] == 'utter'):
                        utter = s_line[1]
                        found = self._search(self.valid_utters, utter)
                        if not found:
                            logger.error('The utter ' + utter +
                                         ' is used in the stories' +
                                         ' story file ' + file + ' (line: ' +
                                         str(stories_lines.index(line)+1) +
                                         ') but it\'s not a valid utter.')
        else:
            logger.error('The utters could not be verified')

    def verify_utters_being_used(self):
        if self.domain != '' and self.stories != []:
            if self.valid_utters == []:
                self.verify_utters()

            stories_utters = []
            for file in self.stories:
                f = open(file, 'r')
                stories_lines = f.readlines()
                f.close()

                for line in stories_lines:
                    s_line = line.split()
                    if len(s_line) == 2 and s_line[0] == '-':
                        utter = s_line[1]
                        stories_utters.append(utter)

            for utter in self.valid_utters:
                found = self._search(stories_utters, utter)
                if not found:
                    logger.warning('The utter ' + utter +
                                   ' is not being used in any story')

        else:
            logger.error('The utters could not be verified')

    def run_verifications(self):
        self.verify_domain(True)
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
    no_validate_domain = parser.parse_args().no_validate_domain

    utils.configure_colored_logging(loglevel='DEBUG')

    validator = Validator(domain, intents, stories)

    if not no_validate_domain:
        validator.verify_domain(warning)

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
