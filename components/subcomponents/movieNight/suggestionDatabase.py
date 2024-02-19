'''
A class to allow adding, removing and listing movie suggestions persistent using shelve library
Each entry in the database consists of:
    - Discord Member Name (str) as its key
    - List of Movies (list[Movies]) as its value
'''
import discord
import common.utils as ut
from common.orderedShelve import OrderedShelve
from .movie import Movie

MAX_SUGGESTIONS = 10

class Suggestions:
    def __init__(self, database_path):
        self.shelve = OrderedShelve(database_path)

    def has_space(self, member: str) -> bool:
        db = self.shelve.open()
        has_space = False

        if db.get(member) is None or len(db[member]) < MAX_SUGGESTIONS:
            has_space = True
        self.shelve.close()

        return has_space

    def get_members(self) -> [str]:
        db = self.shelve.open()
        members = list(db.keys())
        self.shelve.close()

        return members

    def get_movie(self, member: str, movie_name: str) -> Movie | None:
        db = self.shelve.open()
        movie = None

        movies = db.get(member)
        if movies:
            movie = next((movie for movie in movies if movie.name == movie_name), None)
        self.shelve.close()

        return movie

    # Allows up to MAX_SUGGESTIONS suggestions to be stored per user
    def add_suggestion(self, member:str, suggested_movie: Movie) -> discord.Embed:
        reply = self.__embed_movie(suggested_movie)

        if self.has_space(member):
            # Update Database if there is space
            db = self.shelve.open()
            if db.get(member) is None:
                db[member] = [suggested_movie]
            else:
                db[member] = db[member] + [suggested_movie]
            self.shelve.close(modified_dict=db)

            reply.title="Movie successfully added to " + member + "'s list !"
        else:
            # Send error if suggestion list is full
            reply.color = ut.embed_colour["ERROR"]
            reply.title="Suggestion List at Capacity!"
            reply.description = "Please remove some suggestions before adding new ones."

        return reply

    def remove_suggestion(self, member:str, movie_name: str) -> discord.Embed:
        reply = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])

        movie = self.get_movie(member, movie_name)
        if movie:
            db = self.shelve.open()
            new_suggestion_list = db.get(member)
            new_suggestion_list.remove(movie)
            db[member] = new_suggestion_list
            self.shelve.close(modified_dict=db)

            reply = self.__embed_movie(movie)
            reply.title="Movie Successfully Removed from " + member + "'s list !"
        else:
            reply.colour = ut.embed_colour["ERROR"]
            reply.title="Removal Unsuccessful!"
            reply.description = "The movie `" + movie_name + "` was not found in " + member + "'s suggestion list."

        return reply

    def get_suggestion_names(self, member:str) -> [str]:
        db = self.shelve.open()

        suggested_movies_names = []
        suggested_movies = db.get(member)
        if suggested_movies:
            suggested_movies_names = [movie.name for movie in suggested_movies]
        self.shelve.close()

        return suggested_movies_names

    def get_list_embed(self) -> discord.Embed:
        reply = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])

        members = self.get_members()
        if members:
            reply.title = "Suggestion List"
            reply.description = ""
            for member in members:
                # Format list
                suggested_names_str = ", ".join(self.get_suggestion_names(member))
                reply.description += "**" + member + "**: " + suggested_names_str + "\n"
        else:
            reply.colour = ut.embed_colour["ERROR"]
            reply.title = "Movies not found!"
            reply.description = "Everyone's suggestion list is empty."

        return reply

    def get_suggestion_embed(self, member:str, movie_name: str) -> discord.Embed:
        reply = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])

        movie = self.get_movie(member, movie_name)
        if movie:
            reply = self.__embed_movie(movie)
            reply.title = member + "'s Suggestion"
        else:
            reply.colour = ut.embed_colour["ERROR"]
            reply.title = "Movie not found!"
            reply.description = "The movie `" + movie_name + "` was not found in " + member + "'s suggestion list."

        return reply

    # Bumps member to the end of the shelve
    def bump_member(self, member: str) -> bool:
        successful = False
        db = self.shelve.open()
        movies = db.get(member)

        if movies:
            del db[member]
            db[member] = movies
            successful = True
        self.shelve.close(modified_dict=db)

        return successful

    # Bumps previous_host to the end of the list
    # Returns embed only if unsuccessful
    def bump_prev_host(self, previous_host: discord.User) -> discord.Embed | None:
        if previous_host:
            if not self.bump_member(previous_host.name):
                embed = discord.Embed(colour= ut.embed_colour["ERROR"])
                embed.title = "Command Unsuccessful!"
                embed.description = "`prev_host` does not exist in suggestion list!"
                embed.description += "\nPlease pick a valid member."
                return embed
        return None

    # Embedded message has a generic title; change it after
    def __embed_movie(self, movie: Movie) -> discord.Embed:
        embed = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])
        embed.title = "Movie Suggestion"
        embed.description = "**Name:** " + movie.name
        embed.description += "\n**Genre:** " + movie.genre
        embed.description += "\n**Reason for Picking:** " + movie.picking_reason
        return embed
