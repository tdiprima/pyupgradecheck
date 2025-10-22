from pyupgradecheck import check_environment


def test_import_and_run():
    r = check_environment("3.13")
    assert isinstance(r, dict)
