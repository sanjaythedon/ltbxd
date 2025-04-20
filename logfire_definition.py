import os
import logfire

logfire.configure(
    scrubbing=False,
    token=os.getenv("PYDANTIC_TOKEN")
)


