"""
Test script to verify takeDmg works with Wall objects
"""

import sys
import pathlib

# Setup paths
dmSimPath = str(pathlib.Path(__file__).parent.resolve())
sys.path.insert(1, dmSimPath + '\\model')
sys.path.insert(1, dmSimPath + '\\model\\Simulation')

from map import Map
from player import Player, WeaponNew
from monster import Monster
from modelMethods import takeDmg

print("=" * 60)
print("TESTING TAKEDMG WITH WALL OBJECTS")
print("=" * 60)

# Create a simple weapon for the player
test_weapon = WeaponNew(
    name="Longsword",
    attackType="Melee",
    range=5,
    attackMod=5,
    diceType="d8",
    diceCount=1,
    dmgMod=3
)

# Create player
player1 = Player(
    name="TestHero",
    lvl=5,
    ac=16,
    health=40,
    modDict={
        'Strength': 14,
        'Dexterity': 12,
        'Constitution': 14,
        'Intelligence': 10,
        'Wisdom': 10,
        'Charisma': 10
    },
    turnFactors={'Melee': 1.0, 'Ranged': 1.0, 'Ranged Spell': 1.0, 'Spell CC': 1.0},
    weaponList=[test_weapon],
    type="Fighter",
    Image=False
)

# Create monster
monster_weapon = WeaponNew(
    name="Claws",
    attackType="Melee",
    range=5,
    attackMod=4,
    diceType=[6],
    diceCount=[1],
    dmgMod=2
)

enemy1 = Monster(
    name="TestMonster",
    ac=12,
    health=30,
    speed=30,
    modDict={
        'Strength': 12,
        'Dexterity': 10,
        'Constitution': 12,
        'Intelligence': 8,
        'Wisdom': 8,
        'Charisma': 8
    },
    weaponList=[monster_weapon],
    size=25,
    spells={},
    spellMod=0,
    multiAttack={'Claws': 1},
    Image=None
)

# Create map
testMap = Map(numHex=5, partyList=[player1], enemyList=[enemy1], graphicsViewer=None)

# Add a wall
valid_coords = [coord for coord in testMap.arrayCenters.keys() if testMap.arrayCenters[coord] == '']
wall_coord = valid_coords[0]
testMap.addWall(wall_coord, hp=25, name="Stone Wall", ac=17)

print(f"\n1. Created wall at {wall_coord}")
wall = testMap.getWallInfo(wall_coord)
print(f"   Wall: {wall.name}, HP: {wall.health}/{wall.maxHealth}, AC: {wall.ac}")

# Test takeDmg on the wall
print(f"\n2. Player attacks the wall with 10 damage...")
takeDmg(player1, wall, 10, testMap)
print(f"   Wall HP after attack: {wall.health}/{wall.maxHealth}")
assert wall.health == 15, f"Expected wall HP=15, got {wall.health}"
assert wall.alive == 1, "Wall should still be alive"
print("   ✓ Wall damaged correctly")

# Deal more damage
print(f"\n3. Player attacks the wall with 20 damage...")
takeDmg(player1, wall, 20, testMap)
print(f"   Wall HP after attack: {wall.health}/{wall.maxHealth}")
print(f"   Wall alive status: {wall.alive}")
assert wall.health <= 0, f"Expected wall HP<=0, got {wall.health}"
assert wall.alive == 0, "Wall should be destroyed"
assert not testMap.isWall(wall_coord), "Wall should be removed from map"
assert testMap.arrayCenters[wall_coord] == '', "Hex should be freed"
print("   ✓ Wall destroyed and removed from map")

# Test takeDmg still works with Player
print(f"\n4. Testing takeDmg with Player...")
print(f"   Monster attacks Player with 8 damage...")
player_initial_hp = player1.health
takeDmg(enemy1, player1, 8, testMap)
assert player1.health == player_initial_hp - 8, "Player should take damage"
print(f"   Player HP: {player1.health}/{player1.maxHealth}")
print("   ✓ takeDmg works with Player")

# Test takeDmg still works with Monster
print(f"\n5. Testing takeDmg with Monster...")
print(f"   Player attacks Monster with 12 damage...")
monster_initial_hp = enemy1.health
takeDmg(player1, enemy1, 12, testMap)
assert enemy1.health == monster_initial_hp - 12, "Monster should take damage"
print(f"   Monster HP: {enemy1.health}/{enemy1.maxHealth}")
print("   ✓ takeDmg works with Monster")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
print("\nThe takeDmg function now works correctly with:")
print("  • Wall objects")
print("  • Player objects")
print("  • Monster objects")
print("\nWalls are fully integrated into the combat system!")
print("=" * 60)
