from eval.reference_annotation_v2 import match_quote

def test_pdf_physical_line_hyphens_and_ligatures():
    assert match_quote('simultaneously learn high-order features','simulta-\nneously learn high-\norder features')
    assert match_quote('efficient features','efﬁcient features')
    assert not match_quote('highorder features','high-order features')
    assert not match_quote('95% accuracy','85% accuracy')
    assert not match_quote('','anything')
