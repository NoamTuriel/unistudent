"""Plugin recommendations (ticket 12): setup tells the student which plugins fit their university and course."""
import unittest

from helpers import CourseTestCase, run, run_json


def names(result):
    return [p["name"] for p in result["plugins"]]


class PluginRecommendations(CourseTestCase):
    def test_a_known_university_gets_its_plugin_with_the_exact_command(self):
        result = run_json("plugins", "recommend", "--university", "Open University of Israel")
        self.assertEqual(names(result), ["openu"])
        self.assertEqual(result["plugins"][0]["install"], "/plugin install openu@unistudent")
        self.assertIn("openu", result["summary"])

    def test_a_known_field_gets_its_subject_plugin(self):
        result = run_json("plugins", "recommend", "--course-name", "Intro to Macroeconomics")
        self.assertEqual(names(result), ["economics"])

    def test_both_together_come_back_university_first(self):
        result = run_json("plugins", "recommend", "--university", "OpenU", "--field", "economics")
        self.assertEqual(names(result), ["openu", "economics"])

    def test_unknown_university_and_field_recommend_nothing(self):
        result = run_json("plugins", "recommend", "--university", "Bar-Ilan", "--field", "biology")
        self.assertEqual(result["plugins"], [])
        self.assertIn("generic", result["summary"].lower())

    def test_spelling_case_punctuation_and_hebrew_still_match(self):
        for university in ("open-university-of-israel", "OPEN UNIVERSITY OF ISRAEL", "האוניברסיטה הפתוחה"):
            self.assertEqual(names(run_json("plugins", "recommend", "--university", university)), ["openu"], university)
        self.assertEqual(names(run_json("plugins", "recommend", "--course-name", "מבוא למקרו כלכלה")), ["economics"])

    def test_a_university_never_brings_a_subject_plugin_and_the_reverse(self):
        self.assertEqual(names(run_json("plugins", "recommend", "--university", "OpenU")), ["openu"])
        self.assertEqual(names(run_json("plugins", "recommend", "--field", "economics")), ["economics"])

    def test_another_open_university_is_not_the_israeli_one(self):
        self.assertEqual(names(run_json("plugins", "recommend", "--university", "Open University UK")), [])

    def test_unrelated_words_and_the_field_course_join_do_not_match(self):
        self.assertEqual(run_json("plugins", "recommend", "--course-name", "מיקרוביולוגיה")["plugins"], [])
        self.assertEqual(run_json("plugins", "recommend", "--field", "econ", "--course-name", "omics")["plugins"], [])

    def test_spelling_variants_of_the_israeli_open_university_match(self):
        for university in ("OUI", "OpenU Israel", "openu.ac.il", "Open University of Israel (OUI)", "האוניברסיטה הפתוחה של ישראל"):
            self.assertEqual(names(run_json("plugins", "recommend", "--university", university)), ["openu"], university)
        self.assertEqual(names(run_json("plugins", "recommend", "--university", "The Open University")), [])

    def test_other_apps_get_a_harness_neutral_line(self):
        result = run_json("plugins", "recommend", "--university", "OpenU")
        self.assertIn("skills", result["other_apps"])

    def test_needs_something_to_go_on(self):
        code, _ = run("plugins", "recommend", "--json")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
