import pdfplumber
import re
import os
import json

def extract_monsters_from_pdf(pdf_path, start_page=300):
    monsters = {}
    current_monster = None
    monster_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(start_page, len(pdf.pages)):
            page = pdf.pages[page_num]
            # Get page width
            width = page.width
            height = page.height
            
            # Crop to left column
            left_bbox = (0, 0, width/2, height)
            left_page = page.crop(left_bbox)
            left_text = left_page.extract_text()
            
            # Crop to right column
            right_bbox = (width/2, 0, width, height)
            right_page = page.crop(right_bbox)
            right_text = right_page.extract_text()
            
            # Process left column first, then right
            for text in [left_text, right_text]:
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            # Check if line looks like a monster name
                            if (re.match(r'^[A-Z][A-Za-z\s]+$', line) and 
                                len(line) > 2 and 
                                not any(char.isdigit() for char in line) and
                                not ':' in line and
                                not line.startswith('STR') and
                                not line.startswith('DEX') and
                                not 'Damage' in line and
                                not 'Senses' in line and
                                not 'Languages' in line and
                                not 'Challenge' in line and
                                not line in ['Actions', 'Legendary Actions', 'Reactions', 'Traits', 'Fungi Actions']):
                                # Possible monster name
                                if current_monster and monster_text:
                                    monsters[current_monster] = '\n'.join(monster_text)
                                current_monster = line
                                monster_text = [line]
                            elif current_monster:
                                monster_text.append(line)

    # Add the last monster
    if current_monster and monster_text:
        monsters[current_monster] = '\n'.join(monster_text)

    return monsters

def parse_monster_text(text):
    lines = text.strip().split('\n')
    monster = {}
    
    if len(lines) < 2:
        return None  # Skip invalid
    
    # Load spell list
    with open('spells/spellList.json', 'r') as f:
        spellList = json.load(f)
    
    # Name
    monster['name'] = lines[0]
    
    # Size, type, alignment
    size_type_match = re.match(r'(\w+) (\w+) \(([^)]+)\), (.+)', lines[1])
    if size_type_match:
        monster['size'] = size_type_match.group(1)
        monster['type'] = size_type_match.group(2)
        monster['subtype'] = size_type_match.group(3)
        monster['alignment'] = size_type_match.group(4)
    
    # Parse other stats
    i = 2
    while i < len(lines):
        line = lines[i]
        if line.startswith('Armor Class'):
            ac_match = re.search(r'Armor Class (\d+)', line)
            if ac_match:
                monster['ac'] = int(ac_match.group(1))
        elif line.startswith('Hit Points'):
            hp_match = re.search(r'Hit Points (\d+)', line)
            if hp_match:
                monster['hp'] = int(hp_match.group(1))
        elif line.startswith('Speed'):
            speed_match = re.search(r'Speed (\d+)', line)
            if speed_match:
                monster['speed'] = int(speed_match.group(1))
        elif line.startswith('STR DEX CON INT WIS CHA'):
            # Ability scores
            i += 1
            if i < len(lines):
                scores_line = lines[i]
                mods = re.findall(r'[+-]?\d+', scores_line)
                monster['modDict'] = {
                    'Strength': int(mods[0]) if len(mods) > 0 else 0,
                    'Dexterity': int(mods[1]) if len(mods) > 1 else 0,
                    'Constitution': int(mods[2]) if len(mods) > 2 else 0,
                    'Intelligence': int(mods[3]) if len(mods) > 3 else 0,
                    'Wisdom': int(mods[4]) if len(mods) > 4 else 0,
                    'Charisma': int(mods[5]) if len(mods) > 5 else 0,
                }
        elif 'Spellcasting.' in line:
            bSpells = True
            dc_match = re.search(r'DC (\d+)', line)
            if dc_match:
                monster['spellAttackMod'] = int(dc_match.group(1)) - 8  # Approximate
            hit_match = re.search(r'\+(\d+) to hit', line)
            if hit_match:
                monster['spellAttackMod'] = int(hit_match.group(1))
            # Parse spells in following lines
            i += 1
            while i < len(lines) and not lines[i].startswith(('Actions', 'Legendary Actions', 'Reactions', 'Traits')):
                spell_line = lines[i]
                if '(' in spell_line and 'slots' in spell_line and ':' in spell_line:
                    times_match = re.search(r'\((\d+) slots?\)', spell_line)
                    if times_match:
                        times = int(times_match.group(1))
                        spell_part = spell_line.split(':')[1]
                        spell_names = [s.strip().lower() for s in spell_part.split(',')]
                        for spell_name in spell_names:
                            for name in spellList.keys():
                                if name.lower() == spell_name:
                                    monster.setdefault('spells', {})[name] = [times, spellList[name]]
                                    break
                elif 'At will' in spell_line and ':' in spell_line:
                    times = 9999
                    spell_part = spell_line.split(':')[1]
                    spell_names = [s.strip().lower() for s in spell_part.split(',')]
                    for spell_name in spell_names:
                        for name in spellList.keys():
                            if name.lower() == spell_name:
                                monster.setdefault('spells', {})[name] = [times, spellList[name]]
                                break
                i += 1
            continue
        elif line.startswith('Challenge'):
            cr_match = re.search(r'Challenge (.+?) \(', line)
            if cr_match:
                monster['cr'] = cr_match.group(1)
        elif line.startswith('Actions'):
            # Parse actions
            monster['weaponList'] = []
            i += 1
            while i < len(lines) and not lines[i].startswith(('Legendary Actions', 'Reactions', 'Traits')):
                action_line = lines[i]
                if '.' in action_line and ('Weapon Attack' in action_line or 'Spell Attack' in action_line):
                    weapon = parse_weapon(action_line)
                    if weapon:
                        monster['weaponList'].append(weapon)
                elif 'Multiattack' in action_line:
                    monster['multiAttack'] = parse_multiattack(action_line)
                i += 1
            continue
        i += 1
    
    # Defaults
    monster.setdefault('turnFactors', {'Melee': 1.0, 'Ranged': 0.0, 'Ranged Spell': 0.0, 'Spell CC': 0.0})
    monster.setdefault('spells', {})
    monster.setdefault('spellAttackMod', 0)
    monster.setdefault('multiAttack', {})
    monster.setdefault('legRes', 0)
    monster.setdefault('legActions', [0, []])
    monster.setdefault('image', None)
    
    return monster

def parse_weapon(action_line):
    # Example: "Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage."
    name = action_line.split('.')[0].strip()
    attack_type = 'Melee' if 'Melee' in action_line else 'Ranged'
    range_match = re.search(r'reach (\d+)|range (\d+)', action_line)
    range_val = int(range_match.group(1) or range_match.group(2)) if range_match else 5
    attack_mod_match = re.search(r'([+-]\d+) to hit', action_line)
    attack_mod = int(attack_mod_match.group(1)) if attack_mod_match else 0
    dmg_match = re.search(r'Hit: (\d+) \((\d+)d(\d+) ([+-]\d+)\)', action_line)
    if dmg_match:
        dmg_total = int(dmg_match.group(1))
        dice_count = int(dmg_match.group(2))
        dice_type = int(dmg_match.group(3))
        dmg_mod = int(dmg_match.group(4))
    else:
        dice_count = 1
        dice_type = 6
        dmg_mod = 0
    return {
        'name': name,
        'attackType': attack_type,
        'range': range_val,
        'attackMod': attack_mod,
        'diceType': [dice_type],
        'diceCount': [dice_count],
        'dmgMod': dmg_mod
    }

def parse_multiattack(line):
    # Simple parsing, e.g., "Multiattack. The monster makes two attacks."
    return {}

def parse_monster_files_to_json(monster_texts_dir, output_json):
    monsters = {}
    for filename in os.listdir(monster_texts_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(monster_texts_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            monster = parse_monster_text(text)
            if monster:
                monsters[monster['name']] = monster
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(monsters, f, indent=2)
    
    print(f"Saved {len(monsters)} monsters to {output_json}")

def main():
    pdf_path = 'SRD_CC_v5.1.pdf'
    monsters = extract_monsters_from_pdf(pdf_path)

    # Create a directory for monster text files
    os.makedirs('monster_texts', exist_ok=True)

    for name, text in monsters.items():
        # Clean the name for filename
        filename = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') + '.txt'
        filepath = os.path.join('monster_texts', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Extracted {name}")

    # Now parse and save to JSON
    parse_monster_files_to_json('monster_texts', 'actors/savedObjs/monsters.json')

if __name__ == "__main__":
    main()