"""Tests for PDF parsing tool."""

import asyncio
from pathlib import Path

from stratagem.tools.pdf import parse_pdf as _parse_pdf_tool, _parse_page_range, _table_to_markdown

# @tool decorator wraps functions as SdkMcpTool; access handler for testing
parse_pdf = _parse_pdf_tool.handler


class TestPageRange:
    def test_all(self):
        assert _parse_page_range("all", 10) == list(range(10))

    def test_single_page(self):
        assert _parse_page_range("3", 10) == [2]

    def test_range(self):
        assert _parse_page_range("2-4", 10) == [1, 2, 3]

    def test_out_of_range(self):
        assert _parse_page_range("15", 10) == []

    def test_comma_separated(self):
        assert _parse_page_range("1,3,5", 10) == [0, 2, 4]


class TestTableToMarkdown:
    def test_basic_table(self):
        table = [["Name", "Value"], ["Revenue", "$100M"], ["Profit", "$20M"]]
        result = _table_to_markdown(table)
        assert "| Name | Value |" in result
        assert "| --- | --- |" in result
        assert "| Revenue | $100M |" in result

    def test_empty_table(self):
        assert _table_to_markdown([]) == ""


class TestParsePdf:
    async def test_missing_file(self):
        result = await parse_pdf({"file_path": "/nonexistent/file.pdf"})
        assert result.get("isError")
        assert "not found" in result["content"][0]["text"].lower()
