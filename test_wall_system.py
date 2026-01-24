"""
Test script to verify the wall system functionality.
Run this to ensure walls are working correctly.
"""

import sys
import pathlib

# Setup paths
dmSimPath = str(pathlib.Path(__file__).parent.resolve())
sys.path.insert(1, dmSimPath + '\\model')
sys.path.insert(1, dmSimPath + '\\model\\Simulation')

from map import Map
from player import Player
from monster import Monster

print("=" * 60)
print("WALL SYSTEM TEST")
print("=" * 60)

# Create some test actors
print("\n1. Creating test actors...")
player1 = Player()
player1.name = "TestHero"
player1.speed = 30
player1.size = 1

enemy1 = Monster()
enemy1.name = "TestMonster"
enemy1.speed = 30
enemy1.size = 1

partyList = [player1]
enemyList = [enemy1]
print("✓ Actors created")

# Create map without graphics viewer (for testing)
print("\n2. Creating map...")
testMap = Map(numHex=5, partyList=partyList, enemyList=enemyList, graphicsViewer=None)
print("✓ Map created")

# Test 1: Add walls
print("\n3. Testing wall addition...")
testMap.addWall((2, 2), hp=20, name="Test Wall 1")
testMap.addWall((4, 4), hp=30, name="Test Wall 2")
testMap.addWall((6, 6), hp=15, name="Weak Wall")
assert (2, 2) in testMap.walls, "Wall 1 not added!"
assert (4, 4) in testMap.walls, "Wall 2 not added!"
assert (6, 6) in testMap.walls, "Wall 3 not added!"
print("✓ Walls added successfully")

# Test 2: Check wall info
print("\n4. Testing wall info retrieval...")
wall_info = testMap.getWallInfo((2, 2))
assert wall_info is not None, "Wall info not found!"
assert wall_info['hp'] == 20, f"Expected hp=20, got {wall_info['hp']}"
assert wall_info['maxHp'] == 20, f"Expected maxHp=20, got {wall_info['maxHp']}"
assert wall_info['name'] == "Test Wall 1", f"Expected name='Test Wall 1', got {wall_info['name']}"
print(f"✓ Wall info correct: {wall_info}")

# Test 3: Check isWall
print("\n5. Testing isWall() method...")
assert testMap.isWall((2, 2)) == True, "isWall failed to detect wall!"
assert testMap.isWall((0, 0)) == False, "isWall detected wall where none exists!"
print("✓ isWall() working correctly")

# Test 4: Damage wall
print("\n6. Testing wall damage...")
destroyed = testMap.damageWall((6, 6), 10)
assert destroyed == False, "Wall destroyed prematurely!"
wall_info = testMap.getWallInfo((6, 6))
assert wall_info['hp'] == 5, f"Expected hp=5 after damage, got {wall_info['hp']}"
print(f"✓ Wall damaged correctly (HP: {wall_info['hp']}/{wall_info['maxHp']})")

# Test 5: Destroy wall
print("\n7. Testing wall destruction...")
destroyed = testMap.damageWall((6, 6), 10)
assert destroyed == True, "Wall should have been destroyed!"
assert (6, 6) not in testMap.walls, "Wall still in walls dict after destruction!"
assert testMap.arrayCenters[(6, 6)] == '', "Hex not freed after wall destruction!"
print("✓ Wall destroyed and hex freed")

# Test 6: Remove wall manually
print("\n8. Testing manual wall removal...")
testMap.removeWall((4, 4))
assert (4, 4) not in testMap.walls, "Wall not removed!"
assert testMap.arrayCenters[(4, 4)] == '', "Hex not freed after removal!"
print("✓ Wall removed manually")

# Test 7: Create a wall barrier and test pathfinding
print("\n9. Testing pathfinding around walls...")
# Add a vertical wall barrier
for y in range(2, 10, 2):
    testMap.addWall((8, y), hp=20, name="Barrier")

# Test that movement functions exclude walls
from modelMethods import calcMoveHexes

if player1 in [testMap.arrayCenters[coord] for coord in testMap.arrayCenters if testMap.arrayCenters[coord] != '']:
    moveHexes = calcMoveHexes(player1, testMap)
    # Check that no wall hexes are in the movement list
    for hexIndex in moveHexes:
        coord = list(testMap.arrayCenters)[hexIndex]
        assert not testMap.isWall(coord), f"Movement includes wall hex at {coord}!"
    print(f"✓ Movement calculation excludes {len(testMap.walls)} walls")
else:
    print("⚠ Player not on map, skipping movement test")

# Test 8: Print map with walls
print("\n10. Displaying map with walls (walls shown as #)...")
print("-" * 40)
testMap.printCurrMap()
print("-" * 40)
print("✓ Map displayed")

# Summary
print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
print(f"\nWall Summary:")
print(f"  Total walls: {len(testMap.walls)}")
for coord, info in testMap.walls.items():
    print(f"  {coord}: {info['name']} - {info['hp']}/{info['maxHp']} HP")

print("\n" + "=" * 60)
print("Wall system is working correctly!")
print("See wall_system_examples.py for usage examples.")
print("See WALL_SYSTEM_README.md for full documentation.")
print("=" * 60)
