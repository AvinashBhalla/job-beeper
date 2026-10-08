import unittest

from v2.radar import alertability_details, extract_experience, match_details


BASE_CONFIG = {
    "target_roles": ["software engineer", "ai engineer", "automation engineer"],
    "skills": ["python", "react", "ai"],
    "locations": ["Bengaluru, Karnataka, India", "Remote, India"],
    "title_exclude": ["senior", "lead", "staff", "principal", "manager"],
    "excluded_role_terms": [],
    "candidate_experience_years": 2,
    "min_experience_years": None,
    "max_experience_years": 3,
    "match_threshold": 55,
    "remote_only": False,
    "require_explicit_experience_for_alerts": True,
    "notifications_enabled": True,
}


def make_job(title, description="", location="Bengaluru, India"):
    return {
        "title": title,
        "description": description,
        "location": location,
    }


class MatcherTests(unittest.TestCase):
    def test_extracts_experience_range(self):
        self.assertEqual(extract_experience("0-2 years"), (0.0, 2.0))
        self.assertEqual(extract_experience("3 to 8 yrs"), (3.0, 8.0))

    def test_rejects_range_above_configured_maximum(self):
        result = match_details(
            make_job("Software Engineer", "Experience: 2-8 years"),
            BASE_CONFIG,
        )
        self.assertFalse(result["match"])
        self.assertEqual(result["experience_min_years"], 2.0)
        self.assertEqual(result["experience_max_years"], 8.0)

    def test_rejects_minimum_above_candidate(self):
        result = match_details(
            make_job("Software Engineer", "Experience: 3-5 years"),
            BASE_CONFIG,
        )
        self.assertFalse(result["match"])

    def test_skill_matching_is_phrase_aware(self):
        result = match_details(
            make_job("Software Engineer", "Maintain existing services."),
            {**BASE_CONFIG, "skills": ["ai"]},
        )
        self.assertNotIn("skills: ai", result["reasons"])

    def test_unknown_experience_can_match_but_is_not_alertable(self):
        result = match_details(
            make_job("AI Engineer", "Build AI systems with Python."),
            BASE_CONFIG,
        )
        self.assertTrue(result["match"])
        alert = alertability_details(make_job("AI Engineer", "Build AI systems with Python."), result, BASE_CONFIG)
        self.assertFalse(alert["alertable"])
        self.assertIn("explicit experience required for alerts", alert["reasons"])

    def test_excluded_role_category_is_configurable(self):
        config = {**BASE_CONFIG, "excluded_role_terms": ["quality assurance"]}
        result = match_details(
            make_job("Quality Assurance Automation Engineer", "2 years experience"),
            config,
        )
        self.assertFalse(result["match"])


if __name__ == "__main__":
    unittest.main()
