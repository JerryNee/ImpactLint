from dataclasses import dataclass

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from impactlint.models import ChangeOperation


class ChangeParseError(ValueError):
    pass


@dataclass(frozen=True)
class _Names:
    table: str | None
    identifiers: list[str]


def _extract_names(expression: exp.Expression) -> _Names:
    table = next(expression.find_all(exp.Table), None)
    identifiers = [node.name for node in expression.find_all(exp.Identifier) if node.name]
    table_name = table.sql() if table is not None else None
    if table is not None:
        table_parts = {part.name for part in table.find_all(exp.Identifier)}
        identifiers = [name for name in identifiers if name not in table_parts]
    return _Names(table=table_name, identifiers=list(dict.fromkeys(identifiers)))


def _operation_kind(action: exp.Expression) -> str:
    name = type(action).__name__.lower()
    rendered = action.sql().lower()
    if "rename" in name or rendered.startswith("rename column"):
        return "rename_column"
    if isinstance(action, exp.Drop) or rendered.startswith("drop column"):
        return "drop_column"
    if "add" in name or rendered.startswith("add column"):
        return "add_column"
    if "alter" in name or rendered.startswith(("modify column", "alter column")):
        return "alter_column"
    return "unknown"


def parse_change(sql: str, dialect: str) -> list[ChangeOperation]:
    try:
        expression = parse_one(sql, read=dialect)
    except (ParseError, ValueError) as exc:
        raise ChangeParseError(f"Unable to parse the proposed {dialect} change") from exc

    names = _extract_names(expression)
    actions = list(expression.args.get("actions") or [])
    if not actions:
        actions = [expression]

    operations: list[ChangeOperation] = []
    for action in actions:
        action_names = _extract_names(action).identifiers
        identifiers = action_names or names.identifiers
        kind = _operation_kind(action)
        field = identifiers[0] if identifiers else None
        replacement = identifiers[1] if kind == "rename_column" and len(identifiers) > 1 else None
        operations.append(
            ChangeOperation(
                kind=kind,
                table=names.table,
                field=field,
                replacement=replacement,
                rendered_sql=action.sql(dialect=dialect),
            )
        )
    return operations
