import re

def parse_sql(content):
    sql = content.strip()
    match = re.search(r"```\w*(.*?)```", sql, re.DOTALL)
    if match:
        sql = match.group(1)
    return sql.strip()

def test_parsing():
    # Test case 1: sqlite block
    content1 = "Here is the query:\n```sqlite\nSELECT * FROM table;\n```"
    parsed1 = parse_sql(content1)
    assert parsed1 == "SELECT * FROM table;", f"Failed sqlite: {parsed1}"
    print("PASS: sqlite block")

    # Test case 2: sql block
    content2 = "```sql\nSELECT * FROM table;\n```"
    parsed2 = parse_sql(content2)
    assert parsed2 == "SELECT * FROM table;", f"Failed sql: {parsed2}"
    print("PASS: sql block")

    # Test case 3: no block
    content3 = "SELECT * FROM table;"
    parsed3 = parse_sql(content3)
    assert parsed3 == "SELECT * FROM table;", f"Failed no block: {parsed3}"
    print("PASS: no block")
    
    # Test case 4: generic block
    content4 = "```\nSELECT * FROM table;\n```"
    parsed4 = parse_sql(content4)
    assert parsed4 == "SELECT * FROM table;", f"Failed generic block: {parsed4}"
    print("PASS: generic block")

if __name__ == "__main__":
    test_parsing()
