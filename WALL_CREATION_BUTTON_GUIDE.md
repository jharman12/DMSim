# Wall Creation Button - User Guide

## Feature Overview

A new **"Create Walls"** button has been added to the MapWidget, located next to the "Spell Area" button. This allows you to interactively create walls on the hex grid by clicking and dragging.

## How to Use

### 1. Enable Wall Creation Mode

Click the **"Create Walls"** button at the top of the map view. The button will appear pressed/highlighted when active.

### 2. Create Walls

- **Click** on any empty hex to create a single wall
- **Click and drag** across multiple hexes to create a line of walls
- Hexes will turn **gray** as you drag over them
- Only empty hexes can be turned into walls (hexes with characters are skipped)

### 3. Finalize Walls

- **Release the mouse button** to finalize the walls
- The console will display how many walls were created
- Walls are immediately active in the encounter

### 4. Disable Wall Creation Mode

Click the **"Create Walls"** button again to exit wall creation mode and return to normal map interaction.

## Wall Properties

Walls created with this tool have the following default properties:
- **HP**: 10
- **Name**: "wall"

These walls:
- ✓ Block actor movement
- ✓ Are avoided in pathfinding
- ✓ Can be damaged/destroyed (implement attack logic)
- ✓ Appear as gray hexes in the GUI
- ✓ Appear as '#' in console output

## Tips

1. **Plan Before Creating**: Think about your wall placement strategy before enabling the mode
2. **Single Walls**: Quick click for individual walls
3. **Wall Lines**: Click and drag for continuous barriers
4. **Undo**: If you make a mistake, you'll need to manually remove walls (currently no undo for wall creation)
5. **Spell Area Mode**: The "Create Walls" mode automatically disables "Spell Area" mode when activated

## Technical Details

### Integration
- Walls are stored in `encounter.map.walls` dictionary
- Visual representation managed by `CustomGraphicsView.wall_items`
- Automatically integrated with existing movement/pathfinding system

### Mode Switching
- Enabling "Create Walls" automatically disables "Spell Area" mode
- Vice versa when enabling "Spell Area"
- Prevents conflicting mouse interactions

### Hex Selection
- Uses existing hex grid KD-tree for efficient hex detection
- Only processes hexes within the map boundaries
- Skips hexes that already contain actors or walls

## Future Enhancements

Possible improvements:
- **Custom HP**: Allow setting wall HP before creation
- **Wall Types**: Different wall materials (wood, stone, iron)
- **Eraser Mode**: Right-click to remove walls
- **Undo Stack**: Add wall creation to undo system
- **Brush Size**: Create thicker walls with one stroke
- **Wall Inspector**: Click walls to see/edit their properties

## Keyboard Shortcuts (Future)

Suggested shortcuts:
- `W` - Toggle wall creation mode
- `Shift + Drag` - Create thick walls (2 hex width)
- `Ctrl + Z` - Undo last wall placement

## Troubleshooting

**Issue**: Walls not appearing
- **Solution**: Make sure you're dragging over empty hexes (no characters)

**Issue**: Can't create walls
- **Solution**: Ensure "Create Walls" button is pressed/highlighted

**Issue**: Walls not blocking movement
- **Solution**: Walls are immediately active - check that movement calculation is running

**Issue**: Characters stuck after creating walls
- **Solution**: Use the same tool to remove walls or manually call `map.removeWall(coord)`

## Code Example: Removing Walls Programmatically

```python
# Remove a specific wall
coord = (4, 2)
myEncounter.map.removeWall(coord)

# Clear all walls
for coord in list(myEncounter.map.walls.keys()):
    myEncounter.map.removeWall(coord)
```

---

**Enjoy building your tactical encounters with walls!** 🧱
