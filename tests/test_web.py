"""Tests for web scraping tool."""

from stratagem.tools.web import _extract_title, _html_table_to_markdown


class TestHtmlTableToMarkdown:
    def test_basic_conversion(self):
        from bs4 import BeautifulSoup
        html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        result = _html_table_to_markdown(table)
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result


class TestExtractTitle:
    def test_og_title(self):
        from bs4 import BeautifulSoup
        html = '<html><head><meta property="og:title" content="Test Title"></head></html>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_title(soup) == "Test Title"

    def test_html_title(self):
        from bs4 import BeautifulSoup
        html = "<html><head><title>Page Title</title></head></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_title(soup) == "Page Title"

    def test_h1_fallback(self):
        from bs4 import BeautifulSoup
        html = "<html><body><h1>Heading</h1></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_title(soup) == "Heading"
