"""
Wall System Example for DMSim

This demonstrates how to use the wall system in your D&D simulation.
Walls block movement and can be damaged/destroyed.
"""

# Example 1: Adding walls to a map
# ---------------------------------
# In your encounter setup code, after creating the map:

# Add a basic wall at coordinate (4, 2) with default 20 HP
myMap.addWall((4, 2))

# Add a stronger wall with custom HP and name
myMap.addWall((6, 4), hp=40, name="Stone Wall")

# Add multiple walls to create a barrier
for x in range(2, 8, 2):
    myMap.addWall((x, 6), hp=15, name="Wooden Barrier")


# Example 2: Checking for walls
# ------------------------------
coord = (4, 2)
if myMap.isWall(coord):
    print(f"There is a wall at {coord}")
    wall = myMap.getWallInfo(coord)
    print(f"Wall: {wall.name}")
    print(f"Wall HP: {wall.health}/{wall.maxHealth}")
    print(f"Wall AC: {wall.ac}")


# Example 3: Damaging and destroying walls
# -----------------------------------------
# Deal 10 damage to a wall
coord = (4, 2)
destroyed = myMap.damageWall(coord, 10)
if destroyed:
    print(f"Wall at {coord} was destroyed!")
else:
    print(f"Wall damaged but still standing")


# Example 4: Removing walls manually
# -----------------------------------
# Remove a wall without dealing damage
myMap.removeWall((6, 4))


# Example 5: Integrating with attack actions
# -------------------------------------------
# In your combat code, you can now attack walls using takeDmg:

from modelMethods import takeDmg

def attack_target(attacker, target_coord, damage, map):
    """
    Attack a hex - either a character or a wall.
    """
    target = map.arrayCenters[target_coord]
    
    # Check if target is a wall or character and use takeDmg
    if target and target != '':
        if hasattr(target, 'isWall') and target.isWall:
            print(f"{attacker.name} attacks the wall!")
            takeDmg(attacker, target, damage, map)
            if target.alive == 0:
                print(f"{attacker.name} destroyed the wall!")
        elif hasattr(target, 'health'):
            takeDmg(attacker, target, damage, map)
            print(f"{attacker.name} deals {damage} damage to {target.name}")
        return True
    
    return False


# Example 6: Creating a room with walls
# --------------------------------------
def create_room(map, top_left, width, height, door_coord=None):
    """
    Create a rectangular room made of walls with an optional door.
    
    Args:
        map: The Map object
        top_left: Tuple (x, y) for top-left corner
        width: Width in hexes
        height: Height in hexes
        door_coord: Optional tuple for door location (no wall there)
    """
    x_start, y_start = top_left
    
    # Top and bottom walls
    for x in range(x_start, x_start + width * 2, 2):
        if (x, y_start) != door_coord:
            map.addWall((x, y_start), hp=30, name="Room Wall")
        if (x, y_start + height * 2) != door_coord:
            map.addWall((x, y_start + height * 2), hp=30, name="Room Wall")
    
    # Left and right walls
    for y in range(y_start, y_start + height * 2, 2):
        if (x_start, y) != door_coord:
            map.addWall((x_start, y), hp=30, name="Room Wall")
        if (x_start + width * 2, y) != door_coord:
            map.addWall((x_start + width * 2, y), hp=30, name="Room Wall")

# Usage:
# create_room(myMap, (2, 2), 4, 3, door_coord=(6, 2))


# Example 7: Checking wall info before encounter starts
# ------------------------------------------------------
# Print all walls on the map
print("\n=== Current Walls ===")
walls = [(coord, obj) for coord, obj in myMap.arrayCenters.items() if myMap.isWall(coord)]
for coord, wall in walls:
    print(f"{coord}: {wall.name} - HP: {wall.health}/{wall.maxHealth}, AC: {wall.ac}")


# Example 8: Movement will automatically avoid walls
# ---------------------------------------------------
# The system already handles this! Movement functions like:
# - moveActor()
# - dashActor()
# - calcMoveHexes()
# - nearestFreeHex()
# - drawLine()
# All automatically avoid wall hexes.

# Example: This will path around walls automatically
# myMap.moveToNearest(attacker, defender)


# Notes:
# ------
# 1. Walls are displayed as gray hexes with '#' in console output
# 2. Actors cannot move through walls
# 3. Walls block line-of-sight for spell area calculations
# 4. Walls are saved with the map state
# 5. When a wall is destroyed, the hex becomes passable again
