from cpe.text_parser import clean_transcript, calculate_metrics

def test_clean_transcript_disfluencies():
    input_text = "I, um, feel like so stressed, you know, and uh, er, I might fail."
    expected = "i feel stressed and i might fail."
    assert clean_transcript(input_text) == expected

def test_clean_transcript_speaker_tags():
    input_text = "Student: I am feeling tired.\nSpeaker 1: Why is that?\n[Therapist]: Let's talk about it."
    expected = "i am feeling tired. why is that? let's talk about it."
    assert clean_transcript(input_text) == expected

def test_calculate_metrics():
    # Text with 1 positive word ("happy") and 2 negative words ("sad", "depressed")
    text = "i am happy but also sad and depressed"
    metrics = calculate_metrics(text)
    
    assert metrics["word_count"] == 8
    assert metrics["linguistic_markers"]["positive_count"] == 1
    assert metrics["linguistic_markers"]["negative_count"] == 2
    assert metrics["linguistic_markers"]["neg_to_pos_ratio"] == 2.0
    assert metrics["semantic_density"] > 0.0
