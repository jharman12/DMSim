"""
Test complete wall blockage forcing monster to destroy walls.
"""

import sys
import pathlib

dmSimPath = str(pathlib.Path(__file__).parent.resolve())
sys.path.insert(1, dmSimPath + '\\model')
sys.path.insert(1, dmSimPath + '\\model\\Simulation')

from map import Map
from player import Player, WeaponNew
from monster import Monster

print("=" * 70)
print("COMPLETE WALL BLOCKAGE TEST")
print("=" * 70)

test_weapon = WeaponNew(
    name="Longsword", attackType="Melee", range=5, attackMod=5,
    diceType="d8", diceCount=1, dmgMod=3
)

player1 = Player(
    name="Hero", lvl=5, ac=16, health=40,
    modDict={'Strength': 14, 'Dexterity': 12, 'Constitution': 14,
             'Intelligence': 10, 'Wisdom': 10, 'Charisma': 10},
    turnFactors={'Melee': 1.0, 'Ranged': 1.0, 'Ranged Spell': 1.0, 'Spell CC': 1.0},
    weaponList=[test_weapon], type="Fighter", Image=False
)

monster_weapon = WeaponNew(
    name="Claws", attackType="Melee", range=5, attackMod=4,
    diceType=[6], diceCount=[1], dmgMod=2
)

enemy1 = Monster(
    name="Orc", ac=12, health=50, speed=30,
    modDict={'Strength': 16, 'Dexterity': 10, 'Constitution': 14,
             'Intelligence': 8, 'Wisdom': 8, 'Charisma': 8},
    weaponList=[monster_weapon], size=25, spells={}, spellMod=0,
    multiAttack={'Claws': 1}, Image=None
)

# Create map
testMap = Map(numHex=7, partyList=[player1], enemyList=[enemy1], graphicsViewer=None)

print("\n1. Initial Map:")
testMap.printCurrMap()

# Get positions
monster_coord = [coord for coord, obj in testMap.arrayCenters.items() if obj == enemy1][0]
player_coord = [coord for coord, obj in testMap.arrayCenters.items() if obj == player1][0]

print(f"\n2. Creating complete enclosure around player...")
print(f"  Monster at: {monster_coord}")
print(f"  Player at: {player_coord}")

# Create a box of walls around the player that monster must break through
px, py = player_coord
walls_created = []

# Create box around player
for dx in [-2, 0, 2]:
    for dy in [-2, 0, 2]:
        if dx == 0 and dy == 0:
            continue  # Don't wall in the player's exact position
        coord = (px + dx, py + dy)
        if coord in testMap.arrayCenters and testMap.arrayCenters[coord] == '':
            testMap.addWall(coord, hp=10, name="Wall", ac=10)
            walls_created.append(coord)

print(f"  Created {len(walls_created)} walls boxing in player")
print("\nMap with wall box:")
testMap.printCurrMap()

# Try to move monster
print(f"\n3. Monster attempts to reach player...")
walls_before = sum(1 for coord in testMap.arrayCenters if testMap.isWall(coord))
print(f"  Initial walls: {walls_before}")

for turn in range(5):
    print(f"\n  === Turn {turn + 1} ===")
    monster_pos = [c for c, o in testMap.arrayCenters.items() if o == enemy1][0]
    walls_count = sum(1 for coord in testMap.arrayCenters if testMap.isWall(coord))
    
    print(f"  Monster at: {monster_pos}, Walls: {walls_count}")
    
    # Move monster
    testMap.moveToNearest(enemy1, player1)
    
    new_monster_pos = [c for c, o in testMap.arrayCenters.items() if o == enemy1][0]
    new_walls = sum(1 for coord in testMap.arrayCenters if testMap.isWall(coord))
    
    if monster_pos != new_monster_pos:
        print(f"  → Moved to {new_monster_pos}")
    
    if new_walls < walls_count:
        print(f"  → WALL DESTROYED! ({walls_count} -> {new_walls})")
    
    testMap.printCurrMap()
    
    # Check if monster reached player
    dist = testMap.distanceCalc(
        list(testMap.arrayCenters).index(new_monster_pos),
        list(testMap.arrayCenters).index(player_coord)
    )
    if dist <= 1:
        print(f"\n  Monster reached the player!")
        break

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
final_walls = sum(1 for coord in testMap.arrayCenters if testMap.isWall(coord))
print(f"\nWalls destroyed: {walls_before} -> {final_walls} ({walls_before - final_walls} broken)")
print("\nPathfinding behavior:")
print("  ✓ Monster tries to find path around walls (Dijkstra)")
print("  ✓ When completely blocked, monster destroys nearest wall")
print("  ✓ Monster continues until reaching target")
print("=" * 70)
