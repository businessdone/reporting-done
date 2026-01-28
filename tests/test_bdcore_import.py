# tests/test_bdcore_import.py
def test_bdcore_imports():
    from businessdone_core.database import PGSQLClient, Repository
    from businessdone_core.enums import Roles, Permissions
    from businessdone_core.auth import hash_password
    assert PGSQLClient is not None
    assert Repository is not None
    assert Roles.OWNER.value == 4
