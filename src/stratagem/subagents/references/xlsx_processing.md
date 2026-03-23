# Spreadsheet Processing Reference

## Reading Spreadsheets

Use `read_spreadsheet` tool:
- Supports `.xlsx`, `.xls`, and `.csv`
- `sheets: "all"` or `sheets: "Sheet1,Sheet2"` for specific sheets
- `max_rows: 500` — increase for large datasets

### Reading Best Practices
- Check sheet names first to target the right data
- For financial models: look for sheets named "Summary", "P&L", "BS", "CF"
- For data exports: check if first row is actually headers or metadata
- CSV files: auto-detects delimiter (comma, tab, semicolon)

## Creating Spreadsheets

Use `create_spreadsheet` tool for structured data output.

### Financial Model Standards

#### Color Coding (Industry Standard)
- **Blue text** (`0000FF`): Hardcoded inputs, scenario-changeable values
- **Black text** (`000000`): All formulas and calculations
- **Green text** (`008000`): Links from other worksheets
- **Red text** (`FF0000`): External links to other files
- **Yellow background** (`FFFF00`): Key assumptions needing attention

#### Number Formatting
| Data Type | Format | Example |
|-----------|--------|---------|
| Currency | `$#,##0` | $1,234 |
| Currency (millions) | `$#,##0` + header "(in $M)" | $1,234 |
| Percentages | `0.0%` | 15.3% |
| Multiples | `0.0x` | 12.5x |
| Years | Text format | "2024" not "2,024" |
| Negatives | Parentheses | (123) not -123 |
| Zeros | Dash | — not 0 |

#### Formula Rules
- Place ALL assumptions in separate cells, never hardcode in formulas
- Use `=B5*(1+$B$6)` not `=B5*1.05`
- Document hardcoded values: "Source: [Document], [Date], [Reference]"

### Data Export Standards
- First row: column headers (bold)
- No merged cells
- No blank rows between data
- Consistent date format throughout
- Numbers as numbers, not text

### Comparison Tables
For competitive analysis, financial comparisons, feature matrices:
```
Column A: Category/Metric labels
Columns B-N: One entity per column
Last column: Notes/Source
```

### When to Use Spreadsheet vs Other Formats
| Data Type | Use Spreadsheet | Use Report |
|-----------|----------------|------------|
| Raw financial data | Yes | No |
| Calculated metrics with formulas | Yes | No |
| Narrative analysis | No | Yes |
| Data + narrative combo | Spreadsheet for data, report for analysis |
| Comparison matrix (3+ items) | Yes | Only if small |
