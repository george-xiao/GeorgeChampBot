import shelve
import common.utils as ut

class MemberDatabase:
    '''
    DEPRECATED!
    Please use slash commands which includes input validation by default.
    https://discordpy.readthedocs.io/en/stable/interactions/api.html#application-commands

    A class to allow adding, removing and listing presistent group of members using shelve library
    Each entry in the database consists of:
    - Unique Identifier (Twitch Userid/DotaBuff Id) as its key
    - Discord Member Name as its value
    This application uses MemberDatabase in the following manner:
    - twitchAnnouncements: <Twitch UserId, Discord Member Name>
    - TODO: dotaReplay: <DotaBuff Id, Discord Member Name>
    '''

    def __init__(self, database_path):
        self.database_path = database_path

    async def add_item(self, message, admin_role, validate_value_lamda):
        '''
        Adds Item to the database if it is valid (Needs admin access)
        Returns a confirmation string if it succeeds
        Throws an exception otherwise

        Parameters
        ----------
        message: Discord Message Object
        admin_role: string
        validate_value_lamda: async lamda function that takes userid as its input
                              signature: (userid) -> boolean 
                              the function is used to validate userid against an external API
                              this prevents the database from being filled with erronious entries
                              example: lamda userid: validate_function(userid)
        '''

        # Step 1: Validate whether user has admin privilege
        if not ut.author_is_admin(message.author, admin_role):
            raise Exception("Sorry, you need to be a dictator to use this command.")

        # Step 2: Validate the number of arguments
        arg_list = ut.get_arg_list(message, 2, True)
        if not arg_list:
            raise Exception("Only two arguments expected.")

        # shelf: {key = Unique Identifier, value = Discord Member Name}
        userid = arg_list[1]
        member_name = arg_list[0]

        # Step 3: Validate value (must be existing Discord Member)
        if ut.get_member(member_name) is None:
            raise Exception(member_name + " is not our Discord Member.")

        # Step 4: Validate key (must be validated using validate_value_lamda)
        if not await validate_value_lamda(userid):
            raise Exception(userid + " is not a valid argument.")

        # Step 5: Add key-value pair if it does not already exist
        db = shelve.open(self.database_path)
        try:
            if db.get(userid) is None:
                db[userid] = member_name
                return "Successfully added " + member_name
            else:
                raise Exception("This entry already exists.")
        finally:
            db.close()

    def remove_item(self, message, admin_role):
        '''
        Removes Item from the database if it is valid (Needs Admin Access)
        Returns a confirmation string if it succeeds
        Throws an exception otherwise

        Parameters
        ----------
        message: Discord Message Object
        admin_role: string
        '''

        # Step 1: Validate whether user has admin privilege
        if not ut.author_is_admin(message.author, admin_role):
            raise Exception("Sorry, you need to be a dictator to use this command.")

        # Step 2: Validate the number of arguments
        arg_list = ut.get_arg_list(message, 1, True)
        if not arg_list:
            raise Exception("Only one argument expected.")

        first_arg = arg_list[0]

        # Step 3: Check if argument is value (Discord Member Name)
        member = ut.get_member(first_arg)
        successfully_removed = False

        db = shelve.open(self.database_path)
        if member:
            for id, name in db.items():
                if name.lower() == first_arg.lower():
                    del db[id]
                    successfully_removed = True

        # Step 4: Check if argument is key (Unique Identifier)
        if not successfully_removed:
            if db.get(first_arg):
                del db[first_arg]
                successfully_removed = True
        db.close()

        # Step 5: Let application know if deletion failed
        if not successfully_removed:
            raise Exception("Invalid argument content. Check list to ensure entry exists.")
        else:
            return "Successfully removed " + str(first_arg)

    def list_items(self):
        '''
        Returns list of items as string
        Returns empty string if list is empty
        '''
        db = shelve.open(self.database_path)
        if db:
            msg = "Here's everyone we're tracking:\n"
            for streamer_userid in db:
                msg += db[streamer_userid] + ": " + streamer_userid + "\n"
        else:
            msg = "We are not tracking anyone currently."
        db.close()

        return msg
