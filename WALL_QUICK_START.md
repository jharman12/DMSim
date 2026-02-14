# Wall System - Quick Start Guide

## Installation Complete ✓

The wall system has been successfully added to your DMSim project. Here's how to start using it.

## 1. Basic Testing

First, verify the system works by running the test script:

```bash
cd C:\Users\jackh\Code\Python\GitRepo\DMSim
python test_wall_system.py
```

You should see output like:
```
============================================================
WALL SYSTEM TEST
============================================================
...
ALL TESTS PASSED! ✓
```

## 2. Simple Example

Here's a minimal working example to add walls to an existing encounter:

```python
# In your encounter setup code:
from model.Simulation.map import Map
from model.player import createPartyList
from model.monster import createMonsterList

# Create your map as usual
partyList = createPartyList()
enemyList = createMonsterList()
myMap = Map(numHex=10, partyList=partyList, enemyList=enemyList)

# Add walls before combat starts
myMap.addWall((4, 2), hp=20, name="Stone Wall")
myMap.addWall((6, 4), hp=30, name="Iron Gate")
myMap.addWall((8, 6), hp=15, name="Wooden Fence")

# Walls are now active - they block movement automatically!
```

## 3. Creating a Simple Barrier

```python
# Create a horizontal barrier across the middle of the map
barrier_y = 10
for x in range(2, 16, 2):  # Every other x coordinate (hex grid)
    myMap.addWall((x, barrier_y), hp=20, name="Barrier")

# Leave a gap for a doorway
myMap.removeWall((8, barrier_y))  # Creates opening at x=8
```

## 4. Damaging Walls During Combat

Add this to your combat action handler:

```python
def handle_attack(attacker, target_hex, damage, map):
    """Handle attacks that might target walls."""
    
    # Check if target is a wall
    if map.isWall(target_hex):
        print(f"{attacker.name} attacks the wall!")
        destroyed = map.damageWall(target_hex, damage)
        
        if destroyed:
            print(f"The wall crumbles!")
        else:
            info = map.getWallInfo(target_hex)
            print(f"Wall damaged! {info['hp']}/{info['maxHp']} HP remaining")
        return
    
    # Normal character attack logic
    target = map.arrayCenters.get(target_hex)
    if target and hasattr(target, 'health'):
        target.health -= damage
        print(f"{attacker.name} hits {target.name} for {damage} damage!")
```

## 5. Check What the Player Sees

Walls appear differently in different contexts:

**Console Output** (when calling `printCurrMap()`):
```
.       .       .       .       
    .       #       #       .       
.       .       #       .       
    P       .       E       .       
```
- `#` = wall
- `.` = empty hex
- `P` = party member
- `E` = enemy

**GUI Display**:
- Walls appear as **gray hexes** with darker borders
- They're automatically displayed when you load an encounter

## 6. Common Wall Patterns

### Room with Door
```python
# 4x3 room with door at top
myMap.addWall((2, 2), hp=30)  # Top-left
myMap.addWall((4, 2), hp=30)  # Top
# Skip (6, 2) for door
myMap.addWall((8, 2), hp=30)  # Top-right
myMap.addWall((2, 4), hp=30)  # Left side
myMap.addWall((2, 6), hp=30)  # Left side
myMap.addWall((8, 4), hp=30)  # Right side
myMap.addWall((8, 6), hp=30)  # Right side
myMap.addWall((2, 8), hp=30)  # Bottom-left
myMap.addWall((4, 8), hp=30)  # Bottom
myMap.addWall((6, 8), hp=30)  # Bottom
myMap.addWall((8, 8), hp=30)  # Bottom-right
```

### Fortification
```python
# Strong walls on one side of the map
for y in range(0, 20, 2):
    myMap.addWall((10, y), hp=50, name="Fort Wall")
```

### Maze-like Structure
```python
# Create some corridors
walls = [
    (4, 4), (4, 6), (4, 8),   # Vertical wall
    (8, 4), (8, 6), (8, 8),   # Another vertical wall
    (6, 6), (10, 6),          # Horizontal connectors
]

for coord in walls:
    myMap.addWall(coord, hp=25, name="Maze Wall")
```

## 7. Helpful Utilities

### Check All Walls on Map
```python
print("\n=== Current Walls ===")
for coord, info in myMap.walls.items():
    print(f"{coord}: {info['name']} - {info['hp']}/{info['maxHp']} HP")
```

### Find Weak Walls
```python
weak_walls = [coord for coord, info in myMap.walls.items() 
              if info['hp'] < info['maxHp'] * 0.5]
print(f"Weak walls: {weak_walls}")
```

### Clear All Walls
```python
# Remove all walls from the map
for coord in list(myMap.walls.keys()):
    myMap.removeWall(coord)
```

## 8. Integration with Existing Code

Walls automatically integrate with:
- ✓ `moveActor()` - Can't move into walls
- ✓ `moveToNearest()` - Paths around walls
- ✓ `dashActor()` - Respects walls
- ✓ `calcMoveHexes()` - Excludes walls from movement
- ✓ Spell targeting - Walls block area effects

**No changes needed** to your existing movement code!

## 9. Tips & Tricks

1. **Balance HP**: 
   - Wood/Weak: 10-15 HP
   - Stone/Normal: 20-30 HP
   - Metal/Strong: 40-50 HP
   - Magical: 60+ HP

2. **Strategic Placement**:
   - Force tactical positioning
   - Create choke points
   - Protect objectives
   - Separate enemy groups

3. **Dynamic Terrain**:
   - Start with many walls, destroy during combat
   - Create collapsing structures
   - Breakable cover

4. **Testing**:
   - Always test pathfinding after adding walls
   - Ensure actors aren't trapped
   - Verify spell targeting works as expected

## 10. Documentation

For more details:
- **Examples**: `wall_system_examples.py` - Copy-paste code snippets
- **API Reference**: `WALL_SYSTEM_README.md` - Complete method documentation
- **Implementation**: `WALL_IMPLEMENTATION_SUMMARY.md` - Technical details

## Troubleshooting

**Issue**: Walls not showing in GUI
- **Fix**: Call `graphicsViewer.loadFromEncounter(encounter)` after adding walls

**Issue**: Movement calculation errors
- **Fix**: Ensure map.walls is initialized (should happen automatically)

**Issue**: Actors stuck
- **Fix**: Use `myMap.removeWall(coord)` to create escape route

## Next Steps

1. ✓ Run `test_wall_system.py` to verify installation
2. Add walls to your favorite encounter
3. Test movement and combat with walls
4. Create custom wall patterns for your maps
5. Implement wall-attacking in your combat system

---

**Ready to use!** Start adding walls to your encounters now. 🧱
