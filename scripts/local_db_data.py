"""Local database seeding script.

NOTE: This script needs to be updated to use async patterns.
It previously used the sync SQLAlchemySession which has been removed.
Use bd_core.database.PGSQLClient with async patterns instead.

Example usage with async:

    import asyncio
    from bd_core.database import PGSQLClient

    async def seed_database():
        client = PGSQLClient(
            db_user="...",
            db_password="...",
            db_host="...",
            db_port=5432,
            db_name="...",
        )

        session = await client.session()
        try:
            async with session.begin():
                # Add your seed data here
                session.add(entity)
        finally:
            await session.close()
            await client.close()

    if __name__ == "__main__":
        asyncio.run(seed_database())
"""

raise NotImplementedError(
    "This script needs to be updated to use async database patterns. "
    "See the module docstring for migration guidance."
)
