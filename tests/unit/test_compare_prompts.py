from scripts.compare_prompts import print_confusion


def test_print_confusion_counts_each_true_label_against_each_answered_label(capsys):
    results = [
        {"label": "personal", "got": "docs"},
        {"label": "personal", "got": "personal"},
        {"label": "docs", "got": "invalid"},
        {"label": "off_topic", "got": "off_topic"},
    ]

    print_confusion("classify_v2", results)

    output = capsys.readouterr().out
    assert "| true \\ predicted | docs | personal | off_topic | invalid |" in output
    assert "| personal | 1 | 1 | 0 | 0 |" in output
    assert "| docs | 0 | 0 | 0 | 1 |" in output
    assert "| off_topic | 0 | 0 | 1 | 0 |" in output
