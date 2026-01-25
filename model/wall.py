"""
Wall class for D&D combat simulation.
Walls are destructible objects that block movement and can be attacked.
"""

import sys
import pathlib

dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
sys.path.insert(1, dmSimPath)

class Wall:
    """
    Represents a destructible wall in combat.
    Compatible with Player and Monster classes for combat methods.
    """
    
    def __init__(self, name="Wall", health=20, ac=15, Image=None):
        """
        Initialize a Wall object.
        
        Args:
            name: Name/description of the wall (default: "Wall")
            health: Hit points of the wall (default: 20)
            ac: Armor class of the wall (default: 15)
            Image: Optional image path for the wall
        """
        self.name = name
        self.health = health
        self.maxHealth = health
        self.ac = ac
        self.Image = Image
        
        # Combat-related attributes to match Player/Monster interface
        self.alive = 1  # Walls are "alive" until destroyed
        self.size = 25  # Standard hex size
        self.speed = 0  # Walls don't move
        
        # Walls don't have these, but some methods may check for them
        self.modDict = {
            'Strength': 10,
            'Dexterity': 0,  # Walls auto-fail dex saves
            'Constitution': 10,
            'Intelligence': 0,
            'Wisdom': 0,
            'Charisma': 0
        }
        
        # Walls don't have weapons, spells, or reactions
        self.weaponList = []
        self.spells = {}
        self.reaction = 0
        
        # Walls are immune to most conditions
        self.status = []
        self.cc = []  # No crowd control on walls
        
        # Walls don't belong to party or enemy
        self.isWall = True  # Flag to identify as wall
    
    def __repr__(self):
        return f"Wall('{self.name}', HP: {self.health}/{self.maxHealth}, AC: {self.ac})"
    
    def __str__(self):
        return self.name
    
    def takeDamage(self, damage):
        """
        Apply damage to the wall.
        
        Args:
            damage: Amount of damage to deal
            
        Returns:
            bool: True if wall was destroyed, False otherwise
        """
        self.health -= damage
        print(f"{self.name} took {damage} damage. HP: {self.health}/{self.maxHealth}")
        
        if self.health <= 0:
            self.alive = 0
            print(f"{self.name} destroyed!")
            return True
        return False


def createWall(name="Wall", health=20, ac=15, image=None):
    """
    Factory function to create a Wall object.
    
    Args:
        name: Name/description of the wall
        health: Hit points
        ac: Armor class
        image: Optional image path
        
    Returns:
        Wall: A new Wall object
    """
    return Wall(name=name, health=health, ac=ac, Image=image)
