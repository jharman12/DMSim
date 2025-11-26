# testing healing effects

import json
import pathlib
import re
dmSimPath = str(pathlib.Path(__file__).parent.resolve())[0:-6]
#print(dmSimPath)
with open(dmSimPath + "\\spells\\spellList.json", "r") as file:
    spellList = json.load(file)
spells = {}
highestSpell = 9
DnDclass = 'Cleric'
for spell in spellList:
    if  spellList[spell]["effect"] == 'Healing':
        if spellList[spell]['dice'][0] != '':
            print(spell, spellList[spell]['area'], spellList[spell]['combat'])
        spells[spell] = spellList[spell]

print(int(re.findall(r'\d+', '70')[0]))
##print(spells)

