import os
from dotenv import load_dotenv
import logfire

# Load environment variables from .env file
load_dotenv()

logfire.configure(
    scrubbing=False,
    token=os.getenv("PYDANTIC_TOKEN")
)