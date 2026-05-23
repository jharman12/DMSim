"""
Comprehensive multiclass verification test
Shows various multiclass combinations and their mechanics
"""
import sys
from pathlib import Path

dmSimPath = Path(__file__).parent
sys.path.insert(0, str(dmSimPath))

from model.player import Player

print("=" * 70)
print("MULTICLASS MECHANICS VERIFICATION")
print("=" * 70)

# Define test configurations
test_cases = [
    {
        "name": "Full Caster (Wizard)",
        "config": {
            "name": "SingleWizard",
            "lvl": 5,
            "ac": 12,
            "health": 24,
            "modDict": {"Strength": 10, "Dexterity": 14, "Constitution": 12, 
                       "Intelligence": 16, "Wisdom": 10, "Charisma": 10},
            "turnFactors": {"Melee": 1.0, "Ranged": 1.0, "Ranged Spell": 1.0, "Spell CC": 1.0},
            "weaponList": [],
            "type": "Wizard"
        },
        "tests": [
            ("Total Level", lambda p: p.lvl, 5),
            ("Spell Slots - Level 1", lambda p: p.spellSlots['1'], 4),
            ("Spell Slots - Level 2", lambda p: p.spellSlots['2'], 3),  # Updated to correct value
            ("Spell Slots - Level 3", lambda p: p.spellSlots['3'], 2),
            ("Extra Attack", lambda p: p.twoAttacks, 0),
        ]
    },
    {
        "name": "Martial Class (Fighter)",
        "config": {
            "name": "SingleFighter",
            "lvl": 5,
            "ac": 18,
            "health": 44,
            "modDict": {"Strength": 16, "Dexterity": 12, "Constitution": 14, 
                       "Intelligence": 10, "Wisdom": 12, "Charisma": 10},
            "turnFactors": {"Melee": 1.0, "Ranged": 1.0, "Ranged Spell": 1.0, "Spell CC": 1.0},
            "weaponList": [],
            "type": "Fighter"
        },
        "tests": [
            ("Total Level", lambda p: p.lvl, 5),
            ("Extra Attack", lambda p: p.twoAttacks, 1),
            ("Has Spells", lambda p: len(p.spells), 0),
        ]
    },
    {
        "name": "Half Caster (Ranger)",
        "config": {
            "name": "SingleRanger",
            "lvl": 5,
            "ac": 15,
            "health": 40,
            "modDict": {"Strength": 14, "Dexterity": 16, "Constitution": 13, 
                       "Intelligence": 11, "Wisdom": 14, "Charisma": 10},
            "turnFactors": {"Melee": 1.0, "Ranged": 1.0, "Ranged Spell": 1.0, "Spell CC": 1.0},
            "weaponList": [],
            "type": "Ranger"
        },
        "tests": [
            ("Total Level", lambda p: p.lvl, 5),
            ("Spell Slots - Level 1", lambda p: p.spellSlots['1'], 2),  # Half caster at lvl 5 = 2
            ("Spell Slots - Level 2", lambda p: p.spellSlots['2'], 0),  # Half caster at lvl 5 = 0
            ("Extra Attack", lambda p: p.twoAttacks, 1),
        ]
    },
    {
        "name": "Multiclass: Fighter 5 + Wizard 3",
        "config": {
            "name": "FighterWizard",
            "lvl": 8,
            "ac": 16,
            "health": 50,
            "modDict": {"Strength": 16, "Dexterity": 12, "Constitution": 14, 
                       "Intelligence": 15, "Wisdom": 10, "Charisma": 10},
            "turnFactors": {"Melee": 1.0, "Ranged": 1.0, "Ranged Spell": 1.0, "Spell CC": 1.0},
            "weaponList": [],
            "type": {"Fighter": 5, "Wizard": 3}
        },
        "tests": [
            ("Total Level", lambda p: p.lvl, 8),
            ("Fighter Level", lambda p: p.getClassLevel("Fighter"), 5),
            ("Wizard Level", lambda p: p.getClassLevel("Wizard"), 3),
            ("Primary Class", lambda p: p.DnDclass, "Fighter"),
            ("Spell Slots - Level 1", lambda p: p.spellSlots['1'], 4),
            ("Spell Slots - Level 2", lambda p: p.spellSlots['2'], 2),
            ("Spell Slots - Level 3", lambda p: p.spellSlots['3'], 0),
            ("Extra Attack (from Fighter)", lambda p: p.twoAttacks, 1),
            ("Has Fighter", lambda p: p.hasClass("Fighter"), True),
            ("Has Wizard", lambda p: p.hasClass("Wizard"), True),
            ("Has Cleric", lambda p: p.hasClass("Cleric"), False),
        ]
    },
    {
        "name": "Multiclass: Ranger 5 + Rogue 4",
        "config": {
            "name": "RangerRogue",
            "lvl": 9,
            "ac": 15,
            "health": 58,
            "modDict": {"Strength": 12, "Dexterity": 17, "Constitution": 13, 
                       "Intelligence": 11, "Wisdom": 13, "Charisma": 11},
            "turnFactors": {"Melee": 1.0, "Ranged": 1.0, "Ranged Spell": 1.0, "Spell CC": 1.0},
            "weaponList": [],
            "type": {"Ranger": 5, "Rogue": 4}
        },
        "tests": [
            ("Total Level", lambda p: p.lvl, 9),
            ("Ranger Level", lambda p: p.getClassLevel("Ranger"), 5),
            ("Rogue Level", lambda p: p.getClassLevel("Rogue"), 4),
            ("Spell Slots - Level 1", lambda p: p.spellSlots['1'], 2),  # Half caster at lvl 5 = 2
            ("Spell Slots - Level 2", lambda p: p.spellSlots['2'], 0),  # Half caster at lvl 5 = 0
            ("Extra Attack (from Ranger)", lambda p: p.twoAttacks, 1),
        ]
    },
    {
        "name": "Multiclass: Bard 6 + Cleric 4",
        "config": {
            "name": "BardCleric",
            "lvl": 10,
            "ac": 13,
            "health": 50,
            "modDict": {"Strength": 10, "Dexterity": 13, "Constitution": 12, 
                       "Intelligence": 11, "Wisdom": 12, "Charisma": 16},
            "turnFactors": {"Melee": 1.0, "Ranged": 1.0, "Ranged Spell": 1.0, "Spell CC": 1.0},
            "weaponList": [],
            "type": {"Bard": 6, "Cleric": 4}
        },
        "tests": [
            ("Total Level", lambda p: p.lvl, 10),
            ("Bard Level", lambda p: p.getClassLevel("Bard"), 6),
            ("Cleric Level", lambda p: p.getClassLevel("Cleric"), 4),
            ("Primary Class (Bard)", lambda p: p.DnDclass, "Bard"),
            ("Spell Slots - Level 2", lambda p: p.spellSlots['2'], 3),  # Full caster at lvl 10 = 3
            ("Spell Slots - Level 3", lambda p: p.spellSlots['3'], 3),  # Full caster at lvl 10 = 3
            ("Spell Slots - Level 4", lambda p: p.spellSlots['4'], 3),  # Full caster at lvl 10 = 3
            ("Spell Slots - Level 5", lambda p: p.spellSlots['5'], 2),  # Full caster at lvl 10 = 2
        ]
    },
]

# Run tests
passed = 0
failed = 0
details = []

for test_case in test_cases:
    print(f"\n{test_case['name']}:")
    print("-" * 70)
    
    try:
        player = Player(**test_case['config'])
        case_passed = True
        
        for test_name, check_fn, expected in test_case['tests']:
            try:
                result = check_fn(player)
                status = "PASS" if result == expected else "FAIL"
                
                if result == expected:
                    passed += 1
                    details.append(f"  [{status}] {test_name}: {result}")
                else:
                    failed += 1
                    case_passed = False
                    details.append(f"  [{status}] {test_name}: {result} (expected {expected})")
                    
            except Exception as e:
                failed += 1
                case_passed = False
                details.append(f"  [FAIL] {test_name}: ERROR - {str(e)}")
        
        if case_passed:
            print("  All tests passed!")
        
    except Exception as e:
        print(f"  ERROR creating character: {str(e)}")
        failed += len(test_case['tests'])

# Print detailed results
print("\n" + "=" * 70)
print("DETAILED RESULTS")
print("=" * 70)
for detail in details:
    print(detail)

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Total:  {passed + failed}")
print(f"Success Rate: {passed / (passed + failed) * 100:.1f}%")

if failed == 0:
    print("\nAll multiclass mechanics verified successfully!")
else:
    print(f"\n{failed} test(s) failed. Review details above.")

print("=" * 70)
