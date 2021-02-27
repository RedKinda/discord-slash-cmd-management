# Discord Slash Command Management

This is a simple, command line like tool to quickly view and edit your registered slash commands.
The commands are intended to be intuitive, although the editing may get a little confusing. 

### What you may need to know
* You can specify your secrets like client id and bot token in a config file. Look at `example_config.json`
to get you started. Add this file as an argument like this `-c config.json` when running `manage.py`

* This command line works in a guild context. Context can either be a guild ID or 'global'. 
When viewing the commands in the context of a guild, you will see commands specific to that guild, 
in addition to the global ones. When the context is global, you will only see global commands. 

* If you find any bugs or improvements dont hesitate to make a PR or something idk