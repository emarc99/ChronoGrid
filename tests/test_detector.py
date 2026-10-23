from edge.detector import parse_vocab


def test_prompt_can_record_a_different_label():
    prompts, labels = parse_vocab(["person", "red pliers=pliers", " smartphone = phone "])
    assert prompts == ["person", "red pliers", "smartphone"]
    assert labels == ["person", "pliers", "phone"]
