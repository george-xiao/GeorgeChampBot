class Movie:
    def __init__(self, name: str, genre: str, picking_reason: str):
        self.name = name
        self.genre = genre
        self.picking_reason = picking_reason

    def __eq__(self, __value: object) -> bool:
        assert isinstance(__value, Movie)
        return self.name == __value.name and self.genre == __value.genre and self.picking_reason == __value.picking_reason

    def get(self):
        return {
            "name": self.name,
            "genre": self.genre,
            "picking_reason": self.picking_reason
        }
