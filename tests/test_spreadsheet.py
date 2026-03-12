"""Tests for spreadsheet parsing tool."""

import pytest
from stratagem.tools.spreadsheet import read_spreadsheet as _read_spreadsheet_tool, _rows_to_markdown

read_spreadsheet = _read_spreadsheet_tool.handler


class TestRowsToMarkdown:
    def test_basic(self):
        rows = [["Name", "Value"], ["A", "1"], ["B", "2"]]
        result = _rows_to_markdown(rows)
        assert "| Name | Value |" in result
        assert "| A | 1 |" in result

    def test_empty(self):
        assert _rows_to_markdown([]) == ""

    def test_uneven_rows(self):
        rows = [["A", "B", "C"], ["1"]]
        result = _rows_to_markdown(rows)
        assert "| 1 |  |  |" in result


class TestReadSpreadsheet:
    @pytest.mark.asyncio
    async def test_missing_file(self):
        result = await read_spreadsheet({"file_path": "/nonexistent/file.xlsx"})
        assert result.get("isError")

    @pytest.mark.asyncio
    async def test_unsupported_format(self, tmp_path):
        # Create a real file with unsupported extension
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        result = await read_spreadsheet({"file_path": str(txt_file)})
        assert result.get("isError")
        assert "unsupported" in result["content"][0]["text"].lower()
