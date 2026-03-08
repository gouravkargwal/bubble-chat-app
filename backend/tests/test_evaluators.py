"""Test rule-based evaluator."""

from app.testing.evaluators.rule_based import evaluate
from app.testing.scenarios.dataset import QualityCriteria


def test_perfect_replies_score_high():
    """Clean replies with forks should score well."""
    replies = [
        "your dog is clearly the star of your profile... whats their name tho",
        "okay a chef in training AND a farmers market regular... are you collecting hobbies or what",
        "ngl brunos probably more photogenic than me... but im funnier tho",
        "wait so you actually cook or is this a aspirational bio situation",
    ]
    criteria = QualityCriteria(
        must_reference=["dog", "chef", "farmers market"],
        forbidden_patterns=["Hey", "gorgeous"],
        max_length_chars=200,
        must_have_fork=True,
    )
    report = evaluate(replies, criteria)
    assert report.overall_score > 0.6
    assert report.ai_ism_count == 0
    assert report.fork_rate >= 0.75


def test_ai_ism_detection():
    """Replies with AI-isms should score poorly."""
    replies = [
        "That's so amazing! I'd love to hear more about your hiking adventures!",
        "Absolutely, that sounds incredible! What a journey!",
        "I totally get that. I appreciate you sharing!",
        "That sounds amazing! We should definitely hang out sometime!",
    ]
    criteria = QualityCriteria()
    report = evaluate(replies, criteria)
    assert report.ai_ism_count > 0
    assert report.overall_score < 0.7


def test_forbidden_pattern_detection():
    """Should catch forbidden patterns."""
    replies = [
        "Hey there! How are you doing?",
        "you seem cool lets chat",
        "gorgeous profile btw",
        "whats up beautiful",
    ]
    criteria = QualityCriteria(
        forbidden_patterns=["Hey", "gorgeous", "beautiful"],
    )
    report = evaluate(replies, criteria)
    # Should have failures for forbidden patterns
    forbidden_checks = [c for c in report.checks if c.name.startswith("forbidden")]
    assert len(forbidden_checks) > 0


def test_diversity_check():
    """Similar replies should score low on diversity."""
    replies = [
        "thats so cool tell me more about hiking",
        "thats really cool tell me more about your hiking",
        "wow thats cool tell me more about the hike",
        "okay thats cool tell me about hiking more",
    ]
    criteria = QualityCriteria()
    report = evaluate(replies, criteria)
    diversity_checks = [c for c in report.checks if c.name.startswith("diversity")]
    assert len(diversity_checks) > 0  # should flag similarity


def test_must_reference_check():
    """Should verify required references are present."""
    replies = [
        "hey whats up",
        "you seem cool",
        "nice profile",
        "lets chat",
    ]
    criteria = QualityCriteria(must_reference=["cooking", "dog", "hiking"])
    report = evaluate(replies, criteria)
    ref_checks = [c for c in report.checks if c.name == "must_reference"]
    assert len(ref_checks) == 1
    assert ref_checks[0].score < 0.5  # shouldn't find cooking/dog/hiking
