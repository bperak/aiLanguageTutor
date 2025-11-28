from __future__ import annotations

import json
from neo4j import GraphDatabase

from app.core.config import settings


def main() -> None:
    uri = settings.NEO4J_URI
    username = settings.NEO4J_USERNAME
    password = settings.NEO4J_PASSWORD
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session() as session:
            query = (
                "MATCH (c:CanDoDescriptor) "
                "WHERE toString(c.level) = 'A1' "
                "RETURN c.uid AS uid LIMIT 5"
            )
            result = session.run(query)
            ids = [record["uid"] for record in result if record.get("uid")]
    finally:
        driver.close()
    print(json.dumps(ids, ensure_ascii=False))


if __name__ == "__main__":
    main()


