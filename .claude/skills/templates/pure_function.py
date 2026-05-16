"""Template for a pure function inside components/<module>.py.

Pure functions are the testable layer beneath slash commands. They:
  - Take plain typed args (str, int, discord.Member, discord.Guild, etc.)
  - Return either a `str`, a `discord.Embed`, or a `list[str]`
  - MUST NOT take `discord.Interaction` or `discord.Message`
  - MUST NOT call `interaction.response.send_message(...)` or `channel.send(...)`

The body is wrapped in try/except so unexpected exceptions surface as
context-specific error messages instead of bubbling into the generic
`handle_slash_command_error` admin-ping. The error label should match what
a Discord user would expect to see if something blows up.

Replace the placeholders:
  <pure_function>    — function name (snake_case, descriptive of what it
                        produces; suffix with `_text` for str, `_embed` for
                        discord.Embed)
  <args>             — typed parameters
  <body>             — the actual logic that builds the response
  <action_label>     — short human label for the error message (e.g.
                        "Adding Player's Dotabuff", "Printing Leaderboard")
"""


async def <pure_function>(<args>) -> str:  # or -> discord.Embed, or -> list[str]
    try:
        <body>
        return "the response text or embed or list"
    except Exception as e:
        return f"Error <action_label>: {e}"
