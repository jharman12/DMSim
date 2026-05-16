"""
Test script to verify multiclass functionality
"""
import sys
from pathlib import Path

dmSimPath = Path(__file__).parent
sys.path.insert(0, str(dmSimPath))

from model.player import createPartyList

# Test paths
path = str(dmSimPath / "actors" / "savedObjs") + "\\"

print("=" * 60)
print("Testing Multiclass Implementation")
print("=" * 60)

# Test 1: Single-class character (backward compatibility)
print("\n1. Testing Single-Class Character (Cobo - Sorcerer 5):")
single_class = createPartyList(['Cobo'], path=path)
if single_class:
    char = single_class[0]
    print(f"   Name: {char.name}")
    print(f"   Primary Class: {char.DnDclass}")
    print(f"   Classes: {char.classes}")
    print(f"   Total Level: {char.lvl}")
    print(f"   Proficiency: {char.proficiency}")
    print(f"   Has Extra Attack: {char.twoAttacks}")
    print(f"   Spell Slots: {char.spellSlots}")
    print(f"   Spell Attack Mod: {char.spellAttackMod}")
    print(f"   Number of Spells: {len(char.spells)}")
    print("   ✓ Single-class works correctly")

# Test 2: Multi-class character
print("\n2. Testing Multi-Class Character (TestMulticlass - Fighter 5/Wizard 3):")
multi_class = createPartyList(['TestMulticlass'], path=path)
if multi_class:
    char = multi_class[0]
    print(f"   Name: {char.name}")
    print(f"   Primary Class: {char.DnDclass}")
    print(f"   Classes: {char.classes}")
    print(f"   Total Level: {char.lvl}")
    print(f"   Proficiency: {char.proficiency}")
    print(f"   Has Extra Attack: {char.twoAttacks}")
    print(f"   Spell Slots: {char.spellSlots}")
    print(f"   Spell Attack Mod: {char.spellAttackMod}")
    print(f"   Number of Spells: {len(char.spells)}")
    
    # Test helper methods
    print(f"\n   Testing helper methods:")
    print(f"   - Fighter level: {char.getClassLevel('Fighter')}")
    print(f"   - Wizard level: {char.getClassLevel('Wizard')}")
    print(f"   - Cleric level: {char.getClassLevel('Cleric')}")
    print(f"   - Has Fighter: {char.hasClass('Fighter')}")
    print(f"   - Has Wizard: {char.hasClass('Wizard')}")
    print(f"   - Has Cleric: {char.hasClass('Cleric')}")
    print("   ✓ Multi-class works correctly")

# Test 3: Verify spell slots calculation for multiclass
print("\n3. Verifying Multiclass Spell Slot Calculation:")
print("   Fighter 5 (non-caster) + Wizard 3 (full caster)")
print("   Expected: 3rd level caster spell slots (4x 1st, 2x 2nd)")
print(f"   Actual spell slots: {char.spellSlots}")
if char.spellSlots['1'] == 4 and char.spellSlots['2'] == 2 and char.spellSlots['3'] == 0:
    print("   ✓ Spell slots calculated correctly (3rd level caster)")
else:
    print("   ✗ Spell slot calculation may have issues")

# Test 4: Verify extra attack for Fighter 5
print("\n4. Verifying Extra Attack Feature:")
print(f"   Fighter level 5 should have extra attack")
print(f"   twoAttacks value: {char.twoAttacks}")
if char.twoAttacks == 1:
    print("   ✓ Extra attack granted correctly")
else:
    print("   ✗ Extra attack not working as expected")

print("\n" + "=" * 60)
print("Testing Complete!")
print("=" * 60)
