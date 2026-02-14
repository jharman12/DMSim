# Pathfinding System with Wall Avoidance

## Overview
Implemented Dijkstra's shortest path algorithm to enable intelligent pathfinding around walls. Monsters now route around walls when possible and only destroy walls when no alternative path exists.

## Changes Made

### 1. Added Pathfinding Functions (`modelMethods.py`)

#### `findPathAroundWalls(start_coord, end_coord, map, max_distance=None)`
- **Algorithm**: Dijkstra's shortest path
- **Purpose**: Find optimal path avoiding walls
- **Features**:
  - Uses priority queue (heapq) for efficient pathfinding
  - Checks direct path first for quick optimization
  - Respects maximum distance constraints
  - Avoids walls and occupied hexes
  - Returns None if no path exists

#### `findBlockingWalls(start_coord, end_coord, map)`
- **Purpose**: Identify walls blocking direct path to target
- **Returns**: Coordinate of wall closest to target
- **Use case**: Determine which wall to destroy when blocked

#### `drawLineSimple(coord1, coord2, map)`
- **Purpose**: Internal helper for drawing straight lines
- **Note**: Does not filter walls (used by pathfinding internally)

#### Updated `drawLine(coord1, coord2, map)`
- **New behavior**: 
  - Attempts pathfinding first
  - Falls back to filtered direct line if no path
  - Returns best available route

### 2. Updated Map Movement Methods (`model/Simulation/map.py`)

#### Updated `dashActor(mover, targetCoord)`
```python
# New logic:
1. Try to find path around walls using pathfinding
2. If no path exists AND mover is a Monster:
   - Find blocking wall
   - Attack wall with takeDmg (10 damage)
   - Return without moving
3. Fallback to simple movement if needed
```

#### Updated `moveToNearest(mover, target)`
```python
# New logic:
1. Try pathfinding around walls
2. If path found:
   - Move to next coordinate in path
3. If no path AND mover is Monster:
   - Find blocking wall
   - Attack wall with takeDmg (10 damage)
4. Fallback to nearest free hex
```

### 3. Imports Updated
- Added `findPathAroundWalls` and `findBlockingWalls` to map.py imports
- Circular import avoided by importing `takeDmg` locally when needed

## How It Works

### Pathfinding Algorithm (Dijkstra's)

1. **Initialization**:
   - Priority queue with (distance, coordinate) tuples
   - Visited set to track explored hexes
   - came_from dictionary to reconstruct path
   - cost_so_far tracking shortest distance to each hex

2. **Search**:
   - Explore hexes in order of distance from start
   - Skip walls completely
   - Allow target hex even if occupied
   - Track parent hex for path reconstruction

3. **Path Reconstruction**:
   - Backtrack from target to start using came_from
   - Return reversed path (start → end)

### Monster Behavior

**Preferred**: Route around walls
- Monster tries pathfinding first
- Follows optimal path avoiding walls
- Moves toward target each turn

**Fallback**: Destroy blocking walls
- Only when NO path exists to target
- Identifies wall in direct path closest to target
- Attacks wall with 10 damage using `takeDmg()`
- Wall may be destroyed or damaged
- Next turn, path may open up

## API Usage

### Finding Paths
```python
from modelMethods import findPathAroundWalls

path = findPathAroundWalls(start_coord, end_coord, map, max_distance=6)
if path:
    print(f"Path found: {len(path)} hexes")
    # path is list of coordinates from start to end
else:
    print("No path exists")
```

### Finding Blocking Walls
```python
from modelMethods import findBlockingWalls

blocking_wall = findBlockingWalls(start_coord, end_coord, map)
if blocking_wall:
    print(f"Wall at {blocking_wall} is blocking the path")
    # Attack or destroy this wall
```

### Automatic Behavior
```python
# Movement methods now use pathfinding automatically
map.moveToNearest(monster, player)  # Routes around walls
map.dashActor(monster, target_coord)  # Uses pathfinding
```

## Testing

Created three test files:

### `test_pathfinding.py`
- Tests basic pathfinding functionality
- Demonstrates routing around wall barriers
- Verifies Dijkstra's algorithm works correctly

### `test_wall_breaking.py`
- Shows monster routing around walls
- Demonstrates intelligent path selection
- Verifies walls are avoided when possible

### `test_complete_blockage.py`
- Tests wall destruction when completely blocked
- Shows monster breaking through barriers
- Demonstrates fallback behavior

### Test Results
✅ All tests passing
✅ Pathfinding routes around walls efficiently
✅ Monsters only attack walls when necessary
✅ Falls back gracefully when no path exists

## Benefits

1. **Intelligent Movement**: Monsters route around obstacles like players would
2. **Realistic Behavior**: Only destroy walls when truly blocked
3. **Efficient**: Dijkstra's algorithm finds shortest path
4. **Flexible**: Works with any map size and wall configuration
5. **Backwards Compatible**: Existing movement code still works

## Performance

- **Best case**: O(1) when direct path is clear
- **Average case**: O(E log V) where E = edges, V = vertices (Dijkstra)
- **Optimization**: Quick check for direct path before full pathfinding
- **Memory**: O(V) for visited set and distances

## Future Enhancements

1. **A* Algorithm**: Use heuristic for even faster pathfinding
2. **Path Caching**: Store calculated paths for reuse
3. **Difficulty-Based Damage**: Adjust wall-breaking damage by monster strength
4. **Strategic Targeting**: Choose weakest wall to destroy
5. **Player Behavior**: Apply same pathfinding to player characters
6. **Flying Units**: Ignore walls for flying creatures
7. **Terrain Costs**: Different movement costs for different hex types

## Configuration

### Wall Breaking Damage
Currently hardcoded to 10 damage per attack. To modify:

```python
# In map.py, dashActor() and moveToNearest()
damage = 10  # Change this value
```

### Pathfinding Distance
```python
# Limited pathfinding range
path = findPathAroundWalls(start, end, map, max_distance=10)

# Unlimited range
path = findPathAroundWalls(start, end, map)
```

## Examples

### Example 1: Monster Routes Around Wall
```
Before:        After Turn 1:    After Turn 2:
.  .  #        .  .  #          .  .  #
M  .  #   →    .  M  #    →     .  .  M
.  P  #        .  P  #          .  P  #

Monster intelligently goes around instead of attacking wall.
```

### Example 2: Monster Destroys Blocking Wall
```
Before:        After Turn 1:    After Turn 2:
.  #  .        .  #  .          .  .  .
M  #  P   →    M  #  P    →     .  M  P
.  #  .        .  X  .          .  .  .
                (wall damaged)  (wall destroyed, monster moves)

Monster attacks wall when no other path exists.
```

## Files Modified

1. ✅ `modelMethods.py` - Added pathfinding functions
2. ✅ `model/Simulation/map.py` - Updated movement methods
3. ✅ Created `test_pathfinding.py` - Basic pathfinding tests
4. ✅ Created `test_wall_breaking.py` - Wall avoidance tests
5. ✅ Created `test_complete_blockage.py` - Wall destruction tests

## Summary

The pathfinding system successfully implements intelligent wall avoidance using Dijkstra's algorithm. Monsters now behave realistically by routing around walls when possible and only destroying them when absolutely necessary. The system is efficient, well-tested, and ready for use in combat scenarios.
