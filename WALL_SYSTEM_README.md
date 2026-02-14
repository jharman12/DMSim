# Wall System Documentation

## Overview

The wall system adds destructible obstacles to your D&D hex-based combat simulation. Walls occupy hexes, block movement, and can be destroyed by dealing damage to them.

## Features

- **Hex Blocking**: Walls occupy hex coordinates and prevent actors from moving through them
- **Pathfinding**: All movement calculations automatically route around walls
- **Destructible**: Walls have HP and can be damaged or destroyed
- **Visual Feedback**: Walls appear as gray hexes in the GUI and '#' in console output
- **Flexible Placement**: Place walls anywhere on the map before or during combat

## Core Functionality

### Map Class Methods

#### `addWall(coord, hp=20, name="Wall")`
Add a wall at the specified coordinate.

**Parameters:**
- `coord` (tuple): (x, y) coordinate for the wall
- `hp` (int, optional): Hit points of the wall (default: 20)
- `name` (str, optional): Name/description of the wall (default: "Wall")

**Example:**
```python
myMap.addWall((4, 2))  # Basic wall with 20 HP
myMap.addWall((6, 4), hp=40, name="Stone Wall")  # Stronger wall
```

#### `removeWall(coord)`
Remove a wall at the specified coordinate.

**Parameters:**
- `coord` (tuple): (x, y) coordinate of the wall to remove

**Example:**
```python
myMap.removeWall((4, 2))
```

#### `damageWall(coord, damage)`
Deal damage to a wall. Automatically removes the wall if HP drops to 0 or below.

**Parameters:**
- `coord` (tuple): (x, y) coordinate of the wall
- `damage` (int): Amount of damage to deal

**Returns:**
- `bool`: True if wall was destroyed, False otherwise

**Example:**
```python
destroyed = myMap.damageWall((4, 2), 15)
if destroyed:
    print("Wall destroyed!")
```

#### `isWall(coord)`
Check if a coordinate contains a wall.

**Parameters:**
- `coord` (tuple): (x, y) coordinate to check

**Returns:**
- `bool`: True if coordinate has a wall, False otherwise

**Example:**
```python
if myMap.isWall((4, 2)):
    print("There's a wall here!")
```

#### `getWallInfo(coord)`
Get detailed information about a wall.

**Parameters:**
- `coord` (tuple): (x, y) coordinate of the wall

**Returns:**
- `dict` or `None`: Dictionary with keys 'hp', 'maxHp', 'name', or None if no wall exists

**Example:**
```python
info = myMap.getWallInfo((4, 2))
if info:
    print(f"{info['name']}: {info['hp']}/{info['maxHp']} HP")
```

## Automatic Movement Integration

The following functions automatically respect walls:

### In `map.py`:
- `moveActor()` - Won't move actors into wall hexes
- `nearestFreeHex()` - Excludes walls when finding free hexes
- `populateMap()` - Won't spawn actors on walls

### In `modelMethods.py`:
- `drawLine()` - Filters out wall hexes from paths
- `calcMoveHexes()` - Excludes walls from valid movement
- `bestSquare()` - Avoids walls in spell area calculations
- `bestLine()` / `bestLine2()` - Avoids walls in line spell calculations
- `bestCone()` - Excludes walls from cone spell calculations

## Graphics Viewer Integration

The `CustomGraphicsView` class handles wall visualization:

- **Color**: Walls are displayed as gray hexes with darker outlines
- **Auto-loading**: Walls are automatically displayed when loading an encounter
- **Real-time updates**: Adding/removing walls updates the display immediately

### Methods:
- `addWall(hexIndex)` - Visualize a wall
- `removeWall(hexIndex)` - Remove wall visualization
- `clearWalls()` - Clear all wall visualizations

## Common Use Cases

### 1. Creating Barriers

```python
# Horizontal wall
for x in range(2, 10, 2):
    myMap.addWall((x, 6), hp=15, name="Wooden Fence")

# Vertical wall
for y in range(2, 10, 2):
    myMap.addWall((8, y), hp=20, name="Stone Barrier")
```

### 2. Creating Rooms

```python
def create_room(map, top_left, width, height, hp=30, door_coord=None):
    """Create a rectangular room with optional door."""
    x_start, y_start = top_left
    
    # Top and bottom walls
    for x in range(x_start, x_start + width * 2, 2):
        if (x, y_start) != door_coord:
            map.addWall((x, y_start), hp=hp)
        if (x, y_start + height * 2) != door_coord:
            map.addWall((x, y_start + height * 2), hp=hp)
    
    # Left and right walls
    for y in range(y_start, y_start + height * 2, 2):
        if (x_start, y) != door_coord:
            map.addWall((x_start, y), hp=hp)
        if (x_start + width * 2, y) != door_coord:
            map.addWall((x_start + width * 2, y), hp=hp)

# Usage
create_room(myMap, (2, 2), 4, 3, door_coord=(6, 2))
```

### 3. Attacking Walls

```python
def attack_hex(attacker, target_coord, damage, map):
    """Attack either a wall or a character at the target hex."""
    
    # Check if it's a wall
    if map.isWall(target_coord):
        destroyed = map.damageWall(target_coord, damage)
        if destroyed:
            print(f"{attacker.name} destroyed the wall at {target_coord}!")
        else:
            wall_info = map.getWallInfo(target_coord)
            print(f"{attacker.name} damaged the wall! ({wall_info['hp']} HP remaining)")
        return True
    
    # Handle character attack
    target = map.arrayCenters.get(target_coord)
    if target and hasattr(target, 'health'):
        target.health -= damage
        return True
    
    return False
```

### 4. Checking Line of Sight

```python
def has_line_of_sight(actor_coord, target_coord, map):
    """Check if there's an unobstructed line of sight between two hexes."""
    from modelMethods import drawLine
    
    path = drawLine(actor_coord, target_coord, map)
    
    # If path is empty or doesn't reach target, there's a wall in the way
    return len(path) > 0 and target_coord in path
```

## Data Structure

Walls are stored in the `Map.walls` dictionary:

```python
{
    (4, 2): {'hp': 20, 'maxHp': 20, 'name': 'Wall'},
    (6, 4): {'hp': 35, 'maxHp': 40, 'name': 'Stone Wall'},
    ...
}
```

The `Map.arrayCenters` dictionary marks wall hexes with the string `'wall'`:

```python
{
    (4, 2): 'wall',
    (6, 4): 'wall',
    ...
}
```

## Console Display

In console map output, walls are displayed as `#`:

```
.       .       .       .       
    .       #       #       .       
.       .       #       .       
    P       .       E       .       
```

Where:
- `.` = empty hex
- `#` = wall
- `P` = party member (first letter of name)
- `E` = enemy (first letter of name)

## Best Practices

1. **Add walls before combat starts** - Easier to set up the battlefield
2. **Use descriptive names** - Helps identify different wall types
3. **Vary HP values** - Makes combat more interesting (wood = 15, stone = 30, iron = 50)
4. **Leave paths** - Don't completely block off areas unless intentional
5. **Test pathfinding** - Ensure actors can still reach objectives
6. **Consider spell areas** - Walls can protect or hinder spell casters

## Troubleshooting

**Problem**: Actors are stuck and can't move
- **Solution**: Check if walls are completely surrounding them. Remove some walls or increase actor speed.

**Problem**: Walls not appearing in GUI
- **Solution**: Ensure `loadFromEncounter()` is called after adding walls.

**Problem**: Movement seems to ignore walls
- **Solution**: Verify walls are added before movement calculations. Check that `isWall()` returns True for wall coordinates.

**Problem**: Can't attack walls
- **Solution**: Implement custom attack logic using `damageWall()` method (see examples above).

## Future Enhancements

Potential improvements you could add:

1. **Wall materials** - Different types with resistances/vulnerabilities
2. **Cover system** - Walls provide AC bonuses to adjacent actors
3. **Partial walls** - Half-height walls that block movement but not sight
4. **Magical walls** - Temporary walls created by spells
5. **Doors** - Walls that can be opened/closed
6. **Destructible terrain** - Extend to other environmental features

## See Also

- `wall_system_examples.py` - More code examples
- `map.py` - Core Map class implementation
- `modelMethods.py` - Movement and pathfinding functions
- `TestingMap.py` - GUI visualization
