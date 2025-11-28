#!/usr/bin/env python3
"""Get A1 CanDo IDs"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j import AsyncGraphDatabase

async def main():
    driver = AsyncGraphDatabase.driver(
        'bolt://localhost:7687',
        auth=('neo4j', 'testpassword123')
    )
    
    async with driver.session() as session:
        result = await session.run(
            'MATCH (c:CanDoDescriptor) WHERE c.level = "A1" RETURN c.uid AS uid ORDER BY c.uid LIMIT 12'
        )
        
        ids = []
        async for record in result:
            ids.append(record['uid'])
        
        for uid in ids:
            print(uid)
    
    await driver.close()

asyncio.run(main())

