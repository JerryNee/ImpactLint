import pytest

from impactlint.change_parser import ChangeParseError, parse_change


def test_parse_rename_column() -> None:
    operations = parse_change(
        "ALTER TABLE analytics.customer_360 RENAME COLUMN customer_id TO customer_key;",
        "snowflake",
    )

    assert len(operations) == 1
    assert operations[0].kind == "rename_column"
    assert operations[0].table == "analytics.customer_360"
    assert operations[0].field == "customer_id"
    assert operations[0].replacement == "customer_key"


def test_parse_drop_column() -> None:
    operations = parse_change(
        "ALTER TABLE analytics.customer_360 DROP COLUMN lifetime_value;",
        "snowflake",
    )

    assert operations[0].kind == "drop_column"
    assert operations[0].field == "lifetime_value"
    assert operations[0].replacement is None


def test_parse_rejects_invalid_sql() -> None:
    with pytest.raises(ChangeParseError):
        parse_change("ALTER TABLE [", "snowflake")
