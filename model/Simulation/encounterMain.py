from model.Simulation.encounterSim import Encounter
#from playersModel import Player

import sys
import json
import pathlib

# Get to DMSim root directory (up from Simulation to model to DMSim)
_root = pathlib.Path(__file__).parent.parent.parent

sys.path.insert(0, str(_root / 'actors' / 'statReader'))
sys.path.insert(0, str(_root))
from actors.statReader.textReader import buildMonsterFromString
from model.player import createPartyList, Player
import random as r 
from model.map import Map
from engine.combat import takeTurn, removeDeadActors, myAction
from model.monster import Monster, MonsterDump, createMonsterList


if __name__ == "__main__":

    
    path = dmSimPath + '\\actors\\savedObjs\\'
    
    print("=" * 60)
    print("TESTING ENCOUNTER SIMULATIONS")
    print("=" * 60)
    
    # Test 1: Party vs Small Group of Dryads
    print("\n\nTEST 1: Party vs 3 Dryads")
    print("-" * 60)
    enemy = createMonsterList(["Merrow" for i in range(20)], path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus','Aldric', 'Adrel'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 2: Party vs Mixed Monster Group
    print("\n\nTEST 2: Party vs Mixed Monsters (Goblins + Hobgoblin)")
    print("-" * 60)
    enemy = createMonsterList(["Medusa"] * 4 + ["Hobgoblin"], path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 3: Smaller party vs tougher enemy
    print("\n\nTEST 3: Small Party vs Ogre")
    print("-" * 60)
    enemy = createMonsterList(["Ogre"], path=path)
    party = createPartyList(['Cobo', 'VV'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 4: Party vs Spellcaster
    print("\n\nTEST 4: Party vs Cult Fanatic (Spellcaster)")
    print("-" * 60)
    enemy = createMonsterList(["Cult Fanatic"], path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 5: Party vs Many Weak Enemies
    print("\n\nTEST 5: Party vs 8 Kobolds")
    print("-" * 60)
    enemy = createMonsterList(["Kobold"] * 8, path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus','Aldric'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 6: Difficult - Multiple High-CR Enemies (potential party loss)
    print("\n\nTEST 6: DIFFICULT - Party vs 2 Trolls (party might lose)")
    print("-" * 60)
    enemy = createMonsterList(["Troll"] * 2, path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus','Aldric'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 7: Difficult - Dragons (very high CR)
    print("\n\nTEST 7: VERY DIFFICULT - Small Party vs Young Silver Dragon")
    print("-" * 60)
    enemy = createMonsterList(["Young Silver Dragon"], path=path)
    party = createPartyList(['Cobo', 'VV'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 8: Difficult - Many Medium Enemies
    print("\n\nTEST 8: DIFFICULT - Party vs 4 Duergar (melee heavy)")
    print("-" * 60)
    enemy = createMonsterList(["Duergar"] * 4, path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 9: Moderate-Difficult - Multiple Spellcasters
    print("\n\nTEST 9: Challenging - Party vs 3 Mages (spellcaster heavy)")
    print("-" * 60)
    enemy = createMonsterList(["Mage"] * 3, path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus','Aldric'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    # Test 10: Boss Fight - Single Powerful Enemy
    print("\n\nTEST 10: Boss Fight - Full Party vs Lich")
    print("-" * 60)
    enemy = createMonsterList(["Lich"], path=path)
    party = createPartyList(['Cobo', 'VV', 'Galleus','Aldric', 'Adrel'], path=path)
    if enemy and party:
        states = Encounter(party, [], enemyList=enemy, n=10)
    else:
        print("Failed to load party or enemies")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    
