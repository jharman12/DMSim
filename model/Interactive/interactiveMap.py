import sys
import pathlib

dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
from model.Simulation.map import Map

class interactiveMap(Map):
    """
    Deprecated: Use Map class directly with graphicsViewer parameter.
    
    This class now inherits from Map for backward compatibility.
    Example: Map(numHex, partyList, enemyList, graphicsViewer=viewer)
    """
    
    def __init__(self, numHex, partyList, enemyList, graphicsViewer):
        super().__init__(numHex, partyList, enemyList, graphicsViewer=graphicsViewer)
