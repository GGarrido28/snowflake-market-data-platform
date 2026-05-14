__all__ = ["SnowflakeManager", "S3JsonLinesWriter"]


def __getattr__(name: str):
    if name == "SnowflakeManager":
        from market_data_platform.warehouse.snowflake import SnowflakeManager

        return SnowflakeManager
    if name == "S3JsonLinesWriter":
        from market_data_platform.warehouse.s3 import S3JsonLinesWriter

        return S3JsonLinesWriter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
