from SetAnubis.core.DataBase.adapters.CardGetter import CardGetter, CardType
from SetAnubis.core.Madgraph.ports.output.ICardAdapter import ICardAdapter

class CardAdapter(ICardAdapter):
    
    @staticmethod
    def get(type : CardType):
        return CardGetter.get(type)