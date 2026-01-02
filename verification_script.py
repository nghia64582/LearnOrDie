
try:
    from Code.Sql.mysql_connetor import MysqlConnector
    print("Successfully imported MysqlConnector")
except ImportError as e:
    print(f"Failed to import MysqlConnector: {e}")
    exit(1)

# Basic instantiation test (no connection validation without credentials)
try:
    db = MysqlConnector("localhost", "root", "password", "test_db")
    print("Successfully instantiated MysqlConnector")
except Exception as e:
    print(f"Failed to instantiate MysqlConnector: {e}")
