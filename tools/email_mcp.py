import sys
from datetime import datetime
from typing import Literal

from mcp.server import FastMCP


mcp = FastMCP("Email MCP Service")

@mcp.tool(description="Schedule a calendar meeting.")
def schedule_meeting(
    attendees: list[str], subject: str, duration_minutes: int, preferred_day: datetime, start_time: int
) -> str:
    """Schedule a calendar meeting."""
    # Placeholder response - in real app would check calendar and schedule
    date_str = preferred_day.strftime("%A, %B %d, %Y")
    return f"Meeting '{subject}' scheduled on {date_str} at {start_time} for {duration_minutes} minutes with {len(attendees)} attendees"

@mcp.tool(description="Check calendar availability for a given day.")
def check_calendar_availability(day: str) -> str:
    """Check calendar availability for a given day."""
    # Placeholder response - in real app would check actual calendar
    return f"Available times on {day}: 9:00 AM, 2:00 PM, 4:00 PM"


@mcp.tool(description="Write and send an email.")
def write_email(to: str, subject: str, content: str) -> str:
    """Write and send an email."""
    # Placeholder response - in real app would send email
    return f"Email sent to {to} with subject '{subject}' and content: {content}"

@mcp.tool(description="Triage an email into one of three categories: ignore, notify, respond.")
def triage_email(category: Literal["ignore", "notify", "respond"]) -> str:
    """Triage an email into one of three categories: ignore, notify, respond."""
    return f"Classification Decision: {category}"

@mcp.tool(description="Email has been sent.")
def Done() -> str:
    """E-mail has been sent. Call this when the email response task is complete."""
    return f"Done: email task completed"

def main():
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        # Write errors to stderr to avoid polluting stdout (which is used for MCP protocol)
        print(f"MCP Server Error: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
