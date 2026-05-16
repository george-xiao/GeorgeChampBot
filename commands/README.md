# Slash Commands

This directory contains all slash command definitions for the bot. These commands are dynamically loaded and updated during runtime to help standardize a way to add commands to this bot.

Discord supports [nesting one level deep](https://docs.discord.com/developers/interactions/application-commands#slash-commands). In addition, only top-level commands can be hidden from users. The slash commands are structured with these restrictions in mind:
- Non-admin commands: `commands/<feature>/` maps to command → subcommand (e.g., `/movie pick-movie`)
- Admin commands: `commands/admin/<feature>/` maps to command → subcommand-group → subcommand (e.g., `/admin movie pick-host`)

## Structure

Since discord.py uses `app_commands.Group` for both nesting levels, this codebase refers to the hierarchy as group → subgroup → subcommand (rather than Discord's command → subcommand-group → subcommand). From now on, the terminology stated above will be used for the rest of this document.

```
commands/
├── __init__.py                       # Entry point. Discovers and registers all groups
├── movie/                            # movie group (e.g. /movie <subcommand>)
│   ├── __init__.py                   # Defines movie group, registers subcommands
│   ├── <subcommand1>.py
│   ├── ...
│   └── <subcommandN>.py
├── <new_feature>/                    # <new_feature> group (e.g. /<new_feature> <subcommand>)
│   ├── __init__.py                   # Should define <new_feature> group, register subcommands
│   ├── <subcommand1>.py
│   ├── ...
│   └── <subcommandN>.py
└── admin/                            # admin group, hidden from non-ADMIN_ROLE users (e.g. /admin <subgroup> <subcommand>)
    ├── __init__.py                   # Defines admin group with permissions, registers subgroups
    ├── movie/                        # movie subgroup (e.g. /admin movie <subcommand>)
    │   ├── __init__.py               # Defines movie subgroup, registers subcommands
    │   ├── <subcommand1>.py
    │   ├── ...
    │   └── <subcommandN>.py
    └── <new_feature>/                # <new_feature> subgroup (e.g. /admin <new_feature> <subcommand>)
        ├── __init__.py               # Should define <new_feature> subgroup, register subcommands
        ├── <subcommand1>.py
        ├── ...
        └── <subcommandN>.py
```

## How Auto-Discovery Works

Subcommands are auto-discovered at runtime — just drop files in the right folder.

- `commands/__init__.py` — Scans for subdirectories and calls `register_group(tree)` on each one.
- `commands/<feature>/__init__.py` — Defines an `app_commands.Group`, scans for `.py` files, and calls `register_subcommand(group)` on each one. Then adds the group to the command tree.
- `commands/admin/__init__.py` — Defines an `app_commands.Group` with admin permissions, scans for subdirectories, and calls `register_subgroup(admin_group)` on each one. Then adds the group to the command tree.
- `commands/admin/<feature>/__init__.py` — Defines an `app_commands.Group` as a subgroup, scans for `.py` files, and calls `register_subcommand(group)` on each one. Then adds the subgroup to the admin group.

## Adding a New Feature

Create the following, using the reference files below as templates:
- A folder under `commands/` with an `__init__.py` that defines a group and exports `register_group(tree)`
- (Optional) A folder under `commands/admin/` with an `__init__.py` that defines a subgroup and exports `register_subgroup(admin_group)`
- Individual `.py` files for each subcommand, each exporting `register_subcommand(group)`

## Reference Files

- `commands/movie/__init__.py` - Defining a new group and registering subcommands
- `commands/movie/pick_movie.py` - Sample subcommand with autocomplete
- `commands/admin/movie/__init__.py` - Defining a new subgroup and registering admin subcommands
- `commands/admin/movie/pick_host.py` - Sample admin subcommand with error handling
