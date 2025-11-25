from SetAnubis.core.DataBase.ports.ICardGetter import ICardGetter
from SetAnubis.core.DataBase.domain.MadGraphCard import CardType, CardTemplateManager

class CardGetter(ICardGetter):
    """Class to retrieve MadGraph card templates based on their type."""
    
    @staticmethod
    def get(type : CardType):
        """Retrieves the card template based on the specified type.

        Args:
            type (CardType): Type of MadGraph card.

        Returns:
            Any: The requested card template.
        """
        return CardTemplateManager().get(type)