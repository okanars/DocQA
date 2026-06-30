from app.main import _is_summary_request
from app.retriever import _is_metadata_query, normalize_query
from app.generator import _evaluate_has_answer


def test_is_summary_request():
    assert _is_summary_request("can you summarize this document?") is True
    assert _is_summary_request("what is this document about?") is True
    assert _is_summary_request("who is the author?") is False
    assert _is_summary_request("tell me about this document") is True
    assert _is_summary_request("what's the overview?") is True
    assert _is_summary_request("explain quantum physics") is False


def test_is_metadata_query():
    assert _is_metadata_query("who is the author of this book?") is True
    assert _is_metadata_query("what is the title?") is True
    assert _is_metadata_query("when was it published?") is True
    assert _is_metadata_query("what is the topic of section 3?") is False
    assert _is_metadata_query("who wrote this article?") is True
    assert _is_metadata_query("explain the algorithm") is False


def test_evaluate_has_answer():
    assert _evaluate_has_answer("The author is John Doe.") is True
    assert _evaluate_has_answer("This information is not mentioned in the text.") is False
    assert _evaluate_has_answer("The document does not specify the publication date.") is False
    assert _evaluate_has_answer("I could not find the version number in the context.") is False
    assert _evaluate_has_answer("The system is currently offline.") is False


def test_normalize_query():
    assert normalize_query("author") == "who wrote this document and who are the authors?"
    assert normalize_query("who wrote this?") == "who wrote this document and who are the authors?"
    assert normalize_query("what is the title") == "what is the title of the document?"
    assert normalize_query("Custom Query String") == "Custom Query String"

