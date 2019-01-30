from rasa_core.validator import Validator

domain_file = '../data/test_validator/domain.yml'
intents_file = '../data/test_validator/intents.md'
stories_file = '../data/test_validator/stories.md'

validator_test = Validator(domain=domain_file,
                           intents=intents_file,
                           stories=stories_file)


def test_validator_creation():
    assert validator_test.domain == domain_file
    assert validator_test.intents == [intents_file]
    assert validator_test.stories == [stories_file]


def test_search():
    vec = ['a', 'b', 'c', 'd', 'e']
    assert validator_test._search(vector=vec, searched_value='c')


def test_verify_intents():
    valid_intents = ['greet', 'goodbye', 'affirm', 'deny']

    validator_test.verify_intents()
    assert validator_test.valid_intents == valid_intents


def test_verify_utters():
    valid_utters = ['utter_greet', 'utter_goodbye', 'utter_question']

    validator_test.verify_utters()
    assert validator_test.valid_utters == valid_utters
