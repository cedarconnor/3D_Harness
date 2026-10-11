"""Owner questions on stage submissions, answered at completion with defaults."""
from coordination_helpers import Fixture

QUESTIONS = [{'id': 'pace', 'text': 'Calm or busy garden?', 'choices': ['Calm', 'Busy'], 'default': 'Calm'},
             {'id': 'path', 'text': 'Gravel or flagstone path?', 'choices': ['Gravel', 'Flagstone']},
             {'id': 'note', 'text': 'Anything else for the next stage?', 'default': 'No'}]


class QuestionTests(Fixture):
    def setUp(self):
        super().setUp()
        self.bind()

    def test_questions_are_frozen_with_the_submission(self):
        submitted = self.submit(questions=QUESTIONS)
        self.assertEqual(submitted['result']['submission']['questions'], QUESTIONS)

    def test_invalid_questions_are_refused(self):
        cases = {
            'duplicate id': [QUESTIONS[0], QUESTIONS[0]],
            'default outside choices': [{**QUESTIONS[0], 'default': 'Loud'}],
            'one choice': [{**QUESTIONS[0], 'choices': ['Calm'], 'default': 'Calm'}],
            'empty text': [{**QUESTIONS[0], 'text': ' '}],
            'bad id': [{**QUESTIONS[0], 'id': 'Pace!'}],
            'unknown key': [{**QUESTIONS[0], 'help': 'x'}],
            'too many': [{'id': f'q{i}', 'text': 'Why?'} for i in range(13)],
        }
        for name, questions in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                self.submit(questions=questions)

    def test_defaults_fill_unanswered_questions_and_answers_are_recorded(self):
        submitted = self.submit(questions=QUESTIONS)
        completed = self.complete(submitted, answers={'path': 'Flagstone'})
        answers = {a['id']: (a['answer'], a['used_default']) for a in completed['result']['answers']}
        self.assertEqual(answers, {'pace': ('Calm', True), 'path': ('Flagstone', False), 'note': ('No', True)})

    def test_a_question_without_a_default_must_be_answered(self):
        submitted = self.submit(questions=QUESTIONS)
        with self.assertRaisesRegex(ValueError, 'needs an answer'):
            self.complete(submitted)

    def test_unknown_or_empty_answers_are_refused(self):
        submitted = self.submit(questions=QUESTIONS)
        with self.assertRaisesRegex(ValueError, 'Unknown question'):
            self.complete(submitted, answers={'path': 'Gravel', 'colour': 'Red'})
        with self.assertRaisesRegex(ValueError, 'answer'):
            self.complete(submitted, answers={'path': ' '})

    def test_free_answers_beside_choices_are_allowed(self):
        submitted = self.submit(questions=QUESTIONS)
        completed = self.complete(submitted, answers={'path': 'Neither: mown grass'})
        self.assertIn(('path', 'Neither: mown grass'), [(a['id'], a['answer']) for a in completed['result']['answers']])

    def test_submissions_and_reviews_without_questions_are_unchanged(self):
        completed = self.complete(self.submit())
        self.assertEqual(completed['result']['answers'], [])
