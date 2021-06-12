import emoji
import shelve
import operator
import math

async def check_meme(message, guild, channel):
    try:
        if len(message.attachments) == 0:
            return
        formatList = ["jpg", "jpeg", "JPG", "JPEG", "png", "PNG", "gif", "gifv", "webm", "mp4", "wav"]
        fileFormat = message.attachments[0].filename.split(".")[-1]
        if fileFormat not in formatList:
            return
        # Structure of list is: GoodMemeCount, isNotMeme, [memeAuthorName, memeAuthorId], memeLink
        memeDatabase = shelve.open('./database/meme_review.db')
        memeDatabase[str(message.id)] = [0, True, [message.author.display_name, '<@' + str(message.author.id) + '>'], message.attachments[0].url]
        memeDatabase.close()
        await add_reactions(message)
    except Exception as e:
        await message.channel.send('Error Checking Meme: ' + str(e))

async def add_reactions(message):
    try:
        await message.add_reaction(emoji.emojize(":no_entry_sign:", use_aliases=True))
        await message.add_reaction(emoji.emojize(":thumbs_down:", use_aliases=True))
        await message.add_reaction(emoji.emojize(":one:", use_aliases=True))
        await message.add_reaction(emoji.emojize(":two:", use_aliases=True))
        await message.add_reaction(emoji.emojize(":three:", use_aliases=True))
        await message.add_reaction(emoji.emojize(":four:", use_aliases=True))
        await message.add_reaction(emoji.emojize(":five:", use_aliases=True))
    except Exception as e:
        await message.channel.send('Error Adding Review Reactions: ' + str(e))

async def add_meme_reactions(payload, channel, adminRole, client):
    try:
        message = await channel.fetch_message(payload.message_id)
        payloadUser = await client.fetch_user(payload.user_id)
        author = await message.guild.fetch_member(payloadUser.id)
        payloadEmoji = payload.emoji
        if type(payload.emoji) != str:
            payloadEmoji = payload.emoji.name
        
        # If the message is not a meme or the bot added the reaction or the reaction is not valid, leave
        isValidEmote = isNotMemeReaction(payloadEmoji) or isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji)
        if len(message.attachments) == 0 or payloadUser.bot or not isValidEmote:
            return

        # check if reactor is Admin
        isAdmin = False
        for role in author.roles:
            tempAdminRole = adminRole
            if role.name[0] != "@":
                tempAdminRole = adminRole[1:]
            if role.name == tempAdminRole:
                isAdmin = True
                
        memeDatabase = shelve.open('./database/meme_review.db')
        if(memeDatabase.get(str(message.id)) is None):
            memeDatabase[str(message.id)] = [0, True, [message.author.display_name, '<@' + str(message.author.id) + '>'], message.attachments[0].url]
        memeDatabase.close()
                
        #check whether the message is a considered a meme
        for reaction in message.reactions:
            reactionEmoji = reaction.emoji
            if type(reactionEmoji) != str:
                reactionEmoji = reaction.emoji.name
            if isNotMemeReaction(reactionEmoji):
                # If the Admin is reacting "Not A Meme", leave
                if reactionEmoji == payloadEmoji and isAdmin:
                    memeDatabase = shelve.open('./database/meme_review.db')
                    memeDatabase[str(message.id)] = addToDatabase(memeDatabase[str(message.id)], 1, False)
                    memeDatabase.close()
                    return
                # If the  message is considered "Not A Meme", remove payloadReaction
                elif reaction.count > 1:
                    await message.remove_reaction(payload.emoji, payloadUser)
                    return
        
        if isGoodMemeReaction(payloadEmoji):
            memeDatabase = shelve.open('./database/meme_review.db')
            memeDatabase[str(message.id)] = addToDatabase(memeDatabase[str(message.id)], 0, memeDatabase[str(message.id)][0]+getScore(payloadEmoji))
            print(memeDatabase[str(message.id)])
            memeDatabase.close()
        elif not isBadMemeReaction(payloadEmoji):
            await channel.send('Error adding meme reaction (1)')
            
        userId = str(payloadUser.display_name)

        # Adding points for reacting
        if isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji):
            memeLeaderboard = shelve.open('./database/meme_leaderboard.db')
            if memeLeaderboard.get(userId) is None:
                memeLeaderboard[userId] = 1
            else:
                memeLeaderboard[userId] += 1
            memeLeaderboard.close()
        
        for reaction in message.reactions:
            reactionEmoji = reaction.emoji
            if type(reactionEmoji) != str:
                reactionEmoji = reaction.emoji.name
            if isGoodMemeReaction(reactionEmoji) or isBadMemeReaction(reactionEmoji):
                sameUser = False
                for user in await reaction.users().flatten():
                    if user.id == payload.user_id:
                        sameUser = True
                # if user alredy voted before, replace the previous emote with current one
                if reactionEmoji != payloadEmoji and sameUser:
                    await message.remove_reaction(reaction.emoji, payloadUser)
    except Exception as e:
        await channel.send('Error adding meme reactions: ' + str(e))

async def remove_meme_reactions(payload, channel, client):
    try:
        message = await channel.fetch_message(payload.message_id)
        payloadUser = await client.fetch_user(payload.user_id)
        payloadEmoji = payload.emoji
        if type(payload.emoji) != str:
            payloadEmoji = payload.emoji.name
        notMemeReaction = None
        for reaction in message.reactions:
            notMemeReaction = reaction.emoji
            if type(notMemeReaction) != str:
                notMemeReaction = reaction.emoji.name
            if isNotMemeReaction(notMemeReaction):
                notMemeReaction = reaction
                break
        
        userId = str(payloadUser.display_name)
        if isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji):
            memeLeaderboard = shelve.open('./database/meme_leaderboard.db')
            if memeLeaderboard.get(userId) is None:
                memeLeaderboard[userId] = -1
            else:
                memeLeaderboard[userId] -= 1
            memeLeaderboard.close()
            
        memeDatabase = shelve.open('./database/meme_review.db')
        if(memeDatabase.get(str(message.id)) is None):
            memeDatabase[str(message.id)] = [0, True, [message.author.display_name, '<@' + str(message.author.id) + '>'], message.attachments[0].url]
        if isGoodMemeReaction(payloadEmoji):
            memeDatabase[str(message.id)] = addToDatabase(memeDatabase[str(message.id)], 0, memeDatabase[str(message.id)][0]-getScore(payloadEmoji))
        elif isNotMemeReaction(payloadEmoji) and notMemeReaction is not None and notMemeReaction.count <= 1:
            memeDatabase[str(message.id)] = addToDatabase(memeDatabase[str(message.id)], 1, False)
        print(memeDatabase[str(message.id)])
        memeDatabase.close()
        
    except Exception as e:
        await channel.send('Error removing meme reactions: ' + str(e))

def isNotMemeReaction(inputEmoji):
    return inputEmoji == emoji.emojize(":no_entry_sign:", use_aliases=True)
def isBadMemeReaction(inputEmoji):
    return inputEmoji == emoji.emojize(":thumbs_down:", use_aliases=True)
def isGoodMemeReaction(inputEmoji):
    memeList = [
        emoji.emojize(":one:", use_aliases=True),
        emoji.emojize(":two:", use_aliases=True),
        emoji.emojize(":three:", use_aliases=True),
        emoji.emojize(":four:", use_aliases=True),
        emoji.emojize(":five:", use_aliases=True)
    ]
    return inputEmoji in memeList

def addToDatabase(memeDatabase, index, value):
    tempDatabase = memeDatabase[:index]
    tempDatabase.append(value)
    tempDatabase += memeDatabase[(index+1):]
    return tempDatabase

def getScore(inputEmoji):
    if inputEmoji == emoji.emojize(":one:", use_aliases=True):
        return 1
    if inputEmoji == emoji.emojize(":two:", use_aliases=True):
        return 2
    if inputEmoji == emoji.emojize(":three:", use_aliases=True):
        return 3
    if inputEmoji == emoji.emojize(":four:", use_aliases=True):
        return 4
    if inputEmoji == emoji.emojize(":five:", use_aliases=True):
        return 5

async def best_announcement_task(channel):
    try:
        memeDatabase = shelve.open('./database/meme_review.db')
        memeLeaderboard = shelve.open('./database/meme_leaderboard.db')
        shelf_as_dict = dict(memeDatabase)
        print(shelf_as_dict)
        
        if len(shelf_as_dict) == 0:
            await channel.send("No memes this week. :sadkek:")
            return
        
        sorted_database = sorted(shelf_as_dict.items(), key=lambda item: item[1][0], reverse=True)
        print(sorted_database)
        points = [25,20,15,10,5]
        i = 0
        for meme1 in sorted_database:
            meme = meme1[1]
            if meme[1] == True:
                if i < 5:
                    if memeLeaderboard.get(meme[2][0]) is None:
                        memeLeaderboard[meme[2][0]] = points[i]
                    else:
                        memeLeaderboard[meme[2][0]] += points[i]
                i += 1

        bestMeme = sorted_database[0][1]                
        partyEmotes = emoji.emojize(":partying_face:") + " " + emoji.emojize(":partying_face:") + " " + emoji.emojize(":partying_face:")
        await channel.send("The Meme of the Week Award goes to " + bestMeme[2][1] + "!! " + partyEmotes + "\n" + bestMeme[3])
        
        memeDatabase.clear()
        memeDatabase.close()
        memeLeaderboard.close()
    except Exception as e:
        await channel.send('Error Printing Best Emote: ' + str(e))
      
        
async def print_memerboard(message):
    try:
        memeLeaderboard = shelve.open('./database/meme_leaderboard.db')
        shelf_as_dict = dict(memeLeaderboard)
        sorted_memers = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)
        memeReview = shelve.open('./database/meme_review.db')
        start = 0
        end = 10
        if len(message.content) != len('!memerboard') and (message.content[len('!memerboard') + 1:].strip().lower() != "last"):
                increment = int(message.content[len('!memerboard') + 1:])
                # page size = 10
                start += (increment - 1) * 10
                end += (increment - 1) * 10
        curr_page_num = (start / 10) + 1

        if len(message.content) != len('!memerboard') and (message.content[len('!memerboard') + 1:].strip().lower() == "last"):
            end = total_page_num
            start = total_page_num - 10
            curr_page_num = math.ceil(total_page_num/10)
        total_page_num = math.ceil(len(memeLeaderboard)/10)
        sorted_memers = sorted_memers[start:end]

        if len(sorted_memers) == 0:
            await message.channel.send("Doesn't look like there are memers here :( Try another page.")
        else:
            leaderboard_msg = "Meme Leaderboard\nMemer - Points \n"
            for i in range(10):
                if (i < len(sorted_memers)):
                    placement = start + i + 1
                    leaderboard_msg = leaderboard_msg + str(placement) + ". " + sorted_memers[i][0] + " - " + str(sorted_memers[i][1]) + "\n"
            leaderboard_msg += "Page " + str(int(curr_page_num)) + "/" + str(int(total_page_num))
            await message.channel.send(leaderboard_msg)

        memeLeaderboard.close()

    except Exception as e:
        await message.channel.send('Error Printing Leaderboard: ' + str(e))