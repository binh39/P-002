from calculator import classify_number


def test_classify_number_paths():
    assert classify_number(-1) == "negative"
    assert classify_number(0) == "zero"
    assert classify_number(1) == "positive"
