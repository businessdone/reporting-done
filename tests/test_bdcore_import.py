# tests/test_bdcore_import.py
def test_bdcore_imports():
    from bd_core.database import PGSQLClient, Repository
    from bd_core.enums import Roles, Permissions
    from bd_core.auth import hash_password
    assert PGSQLClient is not None
    assert Repository is not None
    assert Roles.OWNER.value == 4
