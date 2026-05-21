# Slash Commands

Slash command definitions, loaded dynamically at runtime.

Discord supports [nesting one level deep](https://docs.discord.com/developers/interactions/application-commands#slash-commands) and only top-level commands can be hidden from users. This gives us:
- Public commands: `commands/<feature>/<subcommand>.py/` -> `/feature subcommand`
- Admin commands: `commands/admin/<feature>/<subcommand>.py/` → `/admin feature subcommand`

## Structure

```
commands/
├── __init__.py                       # Entry point. Discovers and registers all groups
├── <new_feature>/                    # <new_feature> group (e.g. /<new_feature> <subcommand>)
│   ├── __init__.py                   # Defines <new_feature> group, registers subcommands
│   ├── <subcommand1>.py              # Defines subcommand
│   ├── ...
│   └── <subcommandN>.py              # Defines subcommand
└── admin/                            # admin group, hidden from non-ADMIN_ROLE users (e.g. /admin <subgroup> <subcommand>)
    ├── __init__.py                   # Defines admin group with permissions, registers subgroups
    └── <new_feature>/                # <new_feature> subgroup (e.g. /admin <new_feature> <subcommand>)
        ├── __init__.py               # Defines <new_feature> subgroup, registers subcommands
        ├── <subcommand1>.py          # Defines subcommand
        ├── ...
        └── <subcommandN>.py          # Defines subcommand
```

### Auto-discovery

Drop a `.py` file in the right folder and export the right function. The `__init__.py` files scan their directory and call `register_group` / `register_subgroup` /`register_subcommand` automatically.

### Example

The feature `movie` maps its public and admin commands in the following manner:

```
commands/
├── movie/
│   ├── __init__.py
│   ├── add_suggestion.py             # /movie add-suggestion
│   ├── ...
│   └── view_upcoming.py              # /movie view-upcoming
└── admin/
    └── movie/
        ├── __init__.py
        └── pick_host.py              # /admin movie pick-host
```

## Adding a Command

### To an existing feature group

Create `command/<existing_feature>/<subcommand>.py` or `command/admin/<existing_feature>/<subcommand>`, exporting `register_subcommand(group)`.

### To a new feature group
Create the following, using `#reference-files` as templates:
- A new directory under `commands/` with a new `__init__.py` to define the `<new_feature>` public group and export `register_group(tree)`
- (Optional) A new directory under `commands/admin/` with a new `__init__.py` to define the `<new_feature>` admin subgroup and export `register_subgroup(admin_group)`
- Individual `.py` files for each public (and optionally admin) commands, each exporting `register_subcommand(group)`

### Error handling

Every command must wire `cmd.error(ut.handle_command_error)` after its definition.

## Reference Files

| Pattern | Copy from |
|---|---|
| `__init__.py` to define a new public group and register subcommands | `commands/movie/__init__.py` |
| Subcommand with autocomplete | `commands/movie/pick_movie.py` |
| `__init__.py` to define a new admin subgroup and register subcommands | `commands/admin/movie/__init__.py` |
| Admin subcommand with custom error handling | `commands/admin/movie/pick_host.py` |
