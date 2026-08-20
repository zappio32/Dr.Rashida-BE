import secrets
import time


def new_id(prefix: str = "c") -> str:
    """Generate a unique, URL-safe string id compatible with Prisma's String @id columns.

    Does not replicate Prisma's cuid() algorithm exactly, but produces a unique
    collision-resistant identifier of a similar shape (timestamp + random) that
    fits the existing TEXT id columns without any schema change.
    """
    timestamp = format(int(time.time() * 1000), "x")
    random_part = secrets.token_hex(8)
    return f"{prefix}{timestamp}{random_part}"
