from dataclasses import dataclass
import random as r
import numpy as np
#import matplotlib.pyplot as plt
import time
#import pandas as pd
import numpy as np
import time
from map import Map
import sys

import pathlib
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)
print(dmSimPath)
from modelMethods import takeTurn, removeDeadActors, rollSave