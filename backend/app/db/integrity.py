from sqlalchemy.exc import IntegrityError


def violates_constraint(error: IntegrityError, constraint_name: str) -> bool:
    """Return whether PostgreSQL identified the expected constraint."""
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == constraint_name
