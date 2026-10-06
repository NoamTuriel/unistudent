"""Plugin recommendations (ticket 12): setup tells the student which plugins fit their university (ADR 0011: no subject plugins)."""
import unittest

from helpers import CourseTestCase, run_json


def names(result):
    return [p["name"] for p in result["plugins"]]


class PluginRecommendations(CourseTestCase):
    def test_a_known_university_gets_its_plugin_with_the_exact_command(self):
        result = run_json("plugins", "recommend", "--university", "Open University of Israel")
        self.assertEqual(names(result), ["openu"])
        self.assertEqual(result["plugins"][0]["install"], "/plugin install openu@unistudent")
        self.assertIn("openu", result["summary"])

    def test_an_unknown_university_recommends_nothing(self):
        result = run_json("plugins", "recommend", "--university", "Bar-Ilan")
        self.assertEqual(result["plugins"], [])
        self.assertIn("generic", result["summary"].lower())

    def test_spelling_case_punctuation_and_hebrew_still_match(self):
        for university in ("open-university-of-israel", "OPEN UNIVERSITY OF ISRAEL", "האוניברסיטה הפתוחה"):
            self.assertEqual(names(run_json("plugins", "recommend", "--university", university)), ["openu"], university)

    def test_another_open_university_is_not_the_israeli_one(self):
        self.assertEqual(names(run_json("plugins", "recommend", "--university", "Open University UK")), [])

    def test_spelling_variants_of_the_israeli_open_university_match(self):
        for university in ("OUI", "OpenU Israel", "openu.ac.il", "Open University of Israel (OUI)", "האוניברסיטה הפתוחה של ישראל"):
            self.assertEqual(names(run_json("plugins", "recommend", "--university", university)), ["openu"], university)
        self.assertEqual(names(run_json("plugins", "recommend", "--university", "The Open University")), [])

    def test_other_apps_get_a_harness_neutral_line(self):
        result = run_json("plugins", "recommend", "--university", "OpenU")
        self.assertIn("skills", result["other_apps"])


if __name__ == "__main__":
    unittest.main()
