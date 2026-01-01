from dataclasses import dataclass
import random as r
import numpy as np
#import matplotlib.pyplot as plt
import time
#import pandas as pd
import sys
import pathlib

# Add root directory to path for imports
dmSimPath = str(pathlib.Path(__file__).parent.parent.parent.resolve())
sys.path.insert(0, dmSimPath)

from modelMethods import takeTurn, removeDeadActors, rollSave
from model.Simulation.map import Map

class Encounter:
    def __init__(self, partyList, npcList, enemyList, n):
        global output
        output = open('encounter.out', 'w+')
        startTime = time.time()
        self.winners = []
        self.partyState = []
        self.combatStats = []  # Track detailed stats for each combat
        sims = n
        
        for i in range(sims):
            #r.seed(i+240)
            #try:
            self.preCombat(partyList,npcList,enemyList)
            #except Exception as e:
            #    print('The model crashed in seed', i, 'with error\n', e)
            #    sys.exit()
        
        partyWinners = len([x[2] for x in self.winners if x[2] == 'Party'])
        enemyWinners = len([x[2] for x in self.winners if x[2] == 'Enemy'])
        turns = sum([x[1] for x in self.winners])/sims
        print('Party Wins:', partyWinners,' vs Enemy Wins: ', enemyWinners, ' Average Turns: ', turns)
        endTime = time.time()
        print(f'Simulation took {endTime - startTime:.2f} seconds')
        output.close()
       
        self.printEncounterStats(partyList, npcList)
    
    def preCombat(self, partyList, npcList, enemyList):
        enemy2List = [enemy for enemy in enemyList]
        party2List = [party for party in partyList] + [npc for npc in npcList]
        totalList = enemy2List+party2List
        for actor in totalList:
            actor.health = actor.maxHealth
            actor.defineSpellSlots()
            actor.legRes = actor.maxLegRes
            actor.legActions = actor.maxLegActions
            actor.cc = []
        
        # Run combat and get results
        survivors, turns, winner = self.combat2(enemyList=enemy2List, partyList=party2List)
        self.winners.append((survivors, turns, winner))
        
        # Track detailed stats for each party member
        combatStat = {
            'winner': winner,
            'turns': turns,
            'party_stats': [],
            'any_deaths': False
        }
        
        for actor in partyList + npcList:
            is_alive = actor in party2List and actor.health > 0
            spell_slots_used = {}
            for level, max_slots in actor.maxSpellSlots.items():
                current_slots = actor.spellSlots.get(level, 0)
                spell_slots_used[level] = max_slots - current_slots
            
            combatStat['party_stats'].append({
                'name': actor.name,
                'final_health': max(0, actor.health),
                'max_health': actor.maxHealth,
                'health_percent': (max(0, actor.health) / actor.maxHealth * 100) if actor.maxHealth > 0 else 0,
                'is_alive': is_alive,
                'spell_slots_used': spell_slots_used,
                'spell_slots_remaining': dict(actor.spellSlots)
            })
            
            if not is_alive:
                combatStat['any_deaths'] = True
        
        self.combatStats.append(combatStat)
        
        # Keep legacy tracking for compatibility
        stateHealth = [[x.name, x.health, x.maxHealth, x.spellSlots] for x in partyList] + [[x.name, x.health, x.maxHealth, x.spellSlots] for x in npcList]
        for state in stateHealth:
            if state[1] < 0:
                state[1] = 0
        ##print(stateHealth)
        self.partyState.append(stateHealth)

    def combat2(self, enemyList, partyList):
        global map
        map = Map(20, partyList, enemyList)
        totalList = enemyList + partyList
        initList = {x:(r.randint(1,20) + x.initMod) for x in totalList}
        sortedInitList = dict(sorted(initList.items(), key = lambda x:x[1], reverse=True))
        turn = 0
        while len(map.party) != 0 and len(map.enemy) != 0:
            '''
            combat order:
                see if you have legRes and are cc'ed
                    if yes to both, use legRes and not be cc'ed
                if you are still cc'ed, spend turn trying to not be cc'ed
                    either way skip turn
            '''
            turn += 1
            for actor in list(sortedInitList.keys()):
                
                print('\t It is: '+actor.name+ ' turn w/ health = '+ str(actor.health) + '\n')
                #time.sleep(10)
                for healthCheck in list(sortedInitList.keys()):
                    print('\t\t', healthCheck.name, healthCheck.health)
                if not actor in list(sortedInitList.keys()): # you've already been removed
                    continue
                if actor.legRes >= 1 and len(actor.cc) > 0: # if cced and has legendary resistance... use it and continue
                    actor.legRes = actor.legRes - 1
                    #print('\t Actor used Leg Res to not be cced : '+actor.name+ ' has  '+ str(actor.legRes) + ' more\n')
                    actor.cc = []
                elif len(actor.cc) > 0: # if actor cced then spend turn trying to save
                    outcome = rollSave(actor, actor.cc[1][0], actor.cc[2]) 
                    #print('\t Actor cced, trying to save...either way no turn taken \n')
                    if outcome: # if failed save... still cced
                        continue
                    else: # if passed save... no long cced
                        actor.cc = []
                        continue    
                if actor in map.enemy: # if on enemy list your enemy is the party
                    if len(map.party) == 0: # if enemies already down... skip turn
                        
                        continue
                    takeTurn(actor, map)
                    removeDeadActors(map, sortedInitList)
                    
                else: # if not on enemy list your enemy is enemyList
                    if len(map.enemy) == 0: # if enemies already down... skip turn
                        continue
                    takeTurn(actor, map, interactive=False)
                    removeDeadActors(map, sortedInitList)

                    for enemy in map.enemy:
                        if enemy.legActions >= 1 and len(map.party) != 0:
                            print('\t Legendary Action taken by: ' + enemy.name + '\n')
                            enemy.takeLegAction(map)
                            removeDeadActors(map, sortedInitList)
                
            
                
        survivors = [x.name for x in list(sortedInitList.keys()) if x.health > 0]
        print(survivors)
        if len(enemyList) == 0:
            winner = 'Party'
        else:
            winner = 'Enemy'
        print('Winner: ' + winner+ '. Turns: '+ str(turn) + '. Survivors: ' + str(survivors) + '\n')
        return survivors, turn, winner
    
    def printEncounterStats(self, partyList, npcList):
        """Print detailed statistics about the simulated encounters."""
        if not self.combatStats:
            return
        
        n_sims = len(self.combatStats)
        party_wins = sum(1 for stat in self.combatStats if stat['winner'] == 'Party')
        enemy_wins = sum(1 for stat in self.combatStats if stat['winner'] == 'Enemy')
        
        print("\n" + "="*60)
        print("ENCOUNTER ANALYSIS")
        print("="*60)
        
        # Win rate
        print(f"\nWin Rate:")
        print(f"  Party Wins: {party_wins}/{n_sims} ({party_wins/n_sims*100:.1f}%)")
        print(f"  Enemy Wins: {enemy_wins}/{n_sims} ({enemy_wins/n_sims*100:.1f}%)")
        
        # Combat length
        avg_turns = sum(stat['turns'] for stat in self.combatStats) / n_sims
        min_turns = min(stat['turns'] for stat in self.combatStats)
        max_turns = max(stat['turns'] for stat in self.combatStats)
        print(f"\nCombat Duration:")
        print(f"  Average Rounds: {avg_turns:.1f}")
        print(f"  Min Rounds: {min_turns}")
        print(f"  Max Rounds: {max_turns}")
        
        # Death statistics
        combats_with_deaths = sum(1 for stat in self.combatStats if stat['any_deaths'])
        print(f"\nParty Deaths:")
        print(f"  Combats with deaths: {combats_with_deaths}/{n_sims} ({combats_with_deaths/n_sims*100:.1f}%)")
        
        # Per-character statistics
        all_characters = partyList + npcList
        print(f"\nPer-Character Statistics:")
        
        for character in all_characters:
            char_stats = []
            for combat in self.combatStats:
                char_stat = next((s for s in combat['party_stats'] if s['name'] == character.name), None)
                if char_stat:
                    char_stats.append(char_stat)
            
            if not char_stats:
                continue
            
            deaths = sum(1 for s in char_stats if not s['is_alive'])
            avg_health_percent = sum(s['health_percent'] for s in char_stats) / len(char_stats)
            avg_final_health = sum(s['final_health'] for s in char_stats) / len(char_stats)
            
            print(f"\n  {character.name}:")
            print(f"    Death Rate: {deaths}/{n_sims} ({deaths/n_sims*100:.1f}%)")
            print(f"    Avg Final Health: {avg_final_health:.1f}/{character.maxHealth} ({avg_health_percent:.1f}%)")
            
            # Spell slot usage
            if character.maxSpellSlots:
                print(f"    Avg Spell Slots Used:")
                for level in sorted(character.maxSpellSlots.keys()):
                    if level == '0' or character.maxSpellSlots[level] == 0:
                        continue
                    total_used = sum(s['spell_slots_used'].get(level, 0) for s in char_stats)
                    avg_used = total_used / len(char_stats)
                    max_slots = character.maxSpellSlots[level]
                    print(f"      Level {level}: {avg_used:.1f}/{max_slots}")
        
        print("\n" + "="*60)
    
    def combat(self, enemyList, partyList):
        global map
        map = Map(15, partyList, enemyList)
        totalList = enemyList + partyList
        initList = {x:(r.randint(1,20) + x.initMod) for x in totalList}
        sortedInitList = dict(sorted(initList.items(), key = lambda x:x[1], reverse=True))
        turn = 0
        while len(map.party) != 0 and len(map.enemy) != 0:
            turn += 1
            for actor in list(sortedInitList.keys()):
                print('\t It is: '+actor.name+ ' turn w/ health = '+ str(actor.health) + '\n')
                if not actor.alive: # if actor down dont take turn
                    #print(actor.name, ' is down', actor.health)
                    #print(map.party)
                    if actor in map.party:
                        #print(actor.name, 'rolling death saves')
                        actor.rollDeathSave()
                        fails, passes = sum(actor.deathSaves['fail']), sum(actor.deathSaves['pass'])
                        if fails >= 3:
                            #print('Actor failed death saves', actor.deathSaves, 'actor is dead, removing from map')
                            if len(actorCoord) != 0:
                                map.arrayCenters[actorCoord[0]] = ''
                            del sortedInitList[actor]
                            map.party.remove(actor)

                    else:

                        #print('\t Actor down, skipping turn and removing from initList\n')
                        
                        del sortedInitList[actor]
                    if actor.health != 1:
                        continue 
                #print('Check to see who is dead.')
                for deadActor in list(sortedInitList.keys()):
                    if 0 >= int(deadActor.health): # if actor down dont take turn
                        
                        
                        if deadActor in map.enemy:
                            #print('\t', deadActor.name, ' is down', deadActor.health)
                        
                            #print('\t\t Removing dead actor from map to prevent over targeting.\n')
                            actorCoord = [coord for coord in list(map.arrayCenters) if map.arrayCenters[coord] == deadActor]
                            #print(deadActor.name, 'is enemy')
                            index = enemyList.index(deadActor)
                            if len(actorCoord) != 0:
                                map.arrayCenters[actorCoord[0]] = ''
                            del map.enemy[index]
                            
                        
                        continue 
                if actor.legRes >= 1 and len(actor.cc) > 0: # if cced and has legendary resistance... use it and continue
                    actor.legRes = actor.legRes - 1
                    #print('\t Actor used Leg Res to not be cced : '+actor.name+ ' has  '+ str(actor.legRes) + ' more\n')
                    actor.cc = []
                elif len(actor.cc) > 0: # if actor cced then spend turn trying to save
                    outcome = actor.rollSave(actor.cc[1][0], actor.cc[2]) 
                    #print('\t Actor cced, trying to save...either way no turn taken \n')
                    if outcome: # if failed save... still cced
                        continue
                    else: # if passed save... no long cced
                        actor.cc = []
                        continue    
                #else: # if not down and not cced... takeTurn
                if actor in map.enemy: # if on enemy list your enemy is the party
                    actor.legActions = actor.maxLegActions
                    for zero in map.party: # remove zeros from targetting for overkill
                        if zero.health <= 0:
                            map.party.remove(zero)
                            actorCoord = [coord for coord in list(map.arrayCenters) if map.arrayCenters[coord] == zero][0]
                            map.arrayCenters[actorCoord] = ''
                    if len(map.party) == 0: # if enemies already down... skip turn
                        #print('\t Party is down \n')
                        continue
                    actor.takeTurn(map)
                    
                else: # if not on enemy list your enemy is enemyList
                    for zero in map.enemy: # remove zeros from targetting for overkill
                        if zero.health <= 0:
                            map.enemy.remove(zero)
                            actorCoord = [coord for coord in list(map.arrayCenters) if map.arrayCenters[coord] == zero][0]
                            map.arrayCenters[actorCoord] = ''
                    if len(map.enemy) == 0: # if enemies already down... skip turn
                        continue
                    actor.takeTurn(map)
                    for enemy in map.enemy:
                        if enemy.legActions >= 1:
                            thing = 1
                            #print('\t Legendary Action taken by: ' + enemy.name + '\n')
                            enemy.takeLegAction(map)

        survivors = [x.name for x in list(sortedInitList.keys()) if x.health > 0]
        if len(enemyList) == 0:
            winner = 'Party'
        else:
            winner = 'Enemy'
        #print('Winner: ' + winner+ '. Turns: '+ str(turn) + '. Survivors: ' + str(survivors) + '\n')
        return survivors, turn, winner

    def runStats(self, sims):

        unpackedState = []
        for state in self.partyState:
            for player in state:
                unpackedState.append([player[0], player[1], player[2]])


        dmgLines = []
        ccList = []
        with open('encounter.out') as infile:
            for line in infile:
                if 'dmg' in line: # who did and took the most dmg
                    split = line.split()
                    if split[3] =='0':
                        continue
                    dmgLines.append([split[0], split[3], split[6]])
                if 'Failed' in line:
                    split = line.split()
                    ccList.append(split[0])

        df = pd.DataFrame({
            'Attacker': [x[0] for x in dmgLines],
            'Damage': [float(x[1]) for x in dmgLines],
            'Victim': [x[2] for x in dmgLines]
        })
        df2 = pd.DataFrame({
            'Name': ccList
        })

        df3 = pd.DataFrame({
            'name': [x[0] for x in unpackedState],
            'curHealth': [x[1] for x in unpackedState ],
            'maxHealth': [x[2] for x in unpackedState ]
        })


        howMuchDmg = df.groupby('Attacker')['Damage'].apply(np.sum).div(sims)
        victimDmg = df.groupby('Victim')['Damage'].apply(np.sum).div(sims)

        Failures = df2['Name'].value_counts().div(sims)
        df3['Percent'] = 100 * df3['curHealth']/df3['maxHealth']
        Percent = df3.groupby('name')['Percent'].apply(np.mean)
        max = sum(df3['maxHealth'])
        curr = sum(df3['curHealth'])
        #print(curr/max)
        ##print(Failures)
        ##print(howMuchDmg)
        ##print(victimDmg)


        self.dmgTaken_plt = victimDmg.plot.barh(y = 'Damage Taken', title = 'Average Damage Taken in Combat')
        #plt.show()
        self.dmgDone_plt = howMuchDmg.plot.barh(y = 'Damage Done', title = 'Average Damage Done in Combat')
        plt.show()
        self.healthRemaining_plt = Percent.plot.barh(y = 'Percent Health Left', title = 'Average Percent of Health after combat')
        plt.show()

        
