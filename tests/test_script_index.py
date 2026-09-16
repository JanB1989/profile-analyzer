import pytest

from profile_analyzer.script_index import index_entries


def test_nested_blocks_comments_strings_and_optional_operator():
    entries = index_entries('root = {\n # fake = {\n target ?= {\n text = "a # { escaped \\"quote\\" }"\n n >= 4\n }\n}\n')
    assert [entry["key"] for entry in entries] == ["root", "target", "text", "n"]
    assert [entry["parent"] for entry in entries] == [None, 0, 1, 1]
    assert [entry["line"] for entry in entries] == [1, 3, 4, 5]


def test_typed_and_anonymous_blocks():
    entries = index_entries('root = { color = hsv { 1 0.5 0 } list = { { x = yes } } }')
    assert [entry["key"] for entry in entries] == ["root", "color", "list", "x"]
    assert entries[-1]["parent"] == 2
    assert entries[-1]["symbol"] == "root"


@pytest.mark.parametrize("source", ['x = {', '}', 'x =', 'x = }', 'x = "unfinished', 'x ! yes'])
def test_malformed_sources_fail_without_fabricated_ancestry(source):
    with pytest.raises(ValueError):
        index_entries(source)


def test_deep_blocks_do_not_require_python_recursion():
    entries = index_entries('x = { ' * 1500 + 'v = yes ' + '} ' * 1500)
    assert len(entries) == 1501
    assert entries[-1]["parent"] == 1499
