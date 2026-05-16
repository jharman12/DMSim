"""
Tactical targeting helpers: AoE shape finders, line drawing, movement helpers.
All functions accept a map object and return coordinate data — no side effects.
"""
import re
import time
import operator
import numpy as np
from scipy import spatial


def drawLine(coord1, coord2, map_obj):
    dist = int(map_obj.distanceCalc(
        list(map_obj.arrayCenters).index(coord1),
        list(map_obj.arrayCenters).index(coord2)
    ))
    x1, y1 = coord1
    x2, y2 = coord2
    xDiff = x2 - x1
    yDiff = y2 - y1

    pts = np.array(list(map_obj.arrayCenters))
    lineCoord = np.array([(0.0, 0.0) for _ in range(dist + 1)])
    for i in range(int(dist) + 1):
        lineCoord[i] = [coord1[0] + i * xDiff / dist, coord1[1] + i * yDiff / dist - 0.01]
    snapCoord = [tuple(pts[spatial.KDTree(pts).query(coord)[1]]) for coord in lineCoord]
    return snapCoord


def calcMoveHexes(actor, map_obj, type=None):
    """Return list of hex indices the actor can reach, routing around walls.

    Uses BFS (breadth-first search) so walls act as true blockers — the actor
    cannot pass through a wall hex to reach hexes on the other side.
    """
    from collections import deque

    arrayCenters = map_obj.arrayCenters
    coords = list(arrayCenters)
    n = len(coords)
    walls = getattr(map_obj, 'walls', set())

    actor_coord = next(c for c in arrayCenters if arrayCenters[c] == actor)
    start = coords.index(actor_coord)

    speed = int(actor.speed / 5)
    limit = speed * 2 if type == 'dash' else speed

    # Precompute neighbours once using the same doubled-height metric as the map.
    # Two hexes are adjacent if their distance is exactly 1.
    def _hex_dist(a, b):
        drow = abs(a[1] - b[1])
        dcol = abs(a[0] - b[0])
        return dcol + max(0, (drow - dcol) / 2)

    neighbors = [
        [j for j in range(n) if i != j and _hex_dist(coords[i], coords[j]) == 1]
        for i in range(n)
    ]

    # BFS — cost is number of hexes moved
    cost = {start: 0}
    queue = deque([start])

    while queue:
        cur = queue.popleft()
        if cost[cur] >= limit:
            continue
        for nb in neighbors[cur]:
            if nb not in cost and nb not in walls:
                cost[nb] = cost[cur] + 1
                queue.append(nb)

    # Only return hexes the actor can actually stand on (empty or self)
    return [
        i for i in cost
        if arrayCenters[coords[i]] == '' or arrayCenters[coords[i]] == actor
    ]


def coordWithinReach(actorCoord, targetCoord, reach, map_obj):
    hexLimit = reach
    dist = map_obj.distanceCalc(
        list(map_obj.arrayCenters).index(targetCoord),
        list(map_obj.arrayCenters).index(actorCoord)
    )
    if dist <= hexLimit:
        return actorCoord
    line = drawLine(actorCoord, targetCoord, map_obj)
    moveTo = [
        coord for coord in line
        if map_obj.distanceCalc(
            list(map_obj.arrayCenters).index(targetCoord),
            list(map_obj.arrayCenters).index(coord)
        ) <= hexLimit
    ][0]
    moverIndex = list(map_obj.arrayCenters).index(moveTo)
    actorIndex = list(map_obj.arrayCenters).index(actorCoord)
    if map_obj.arrayCenters[moveTo] != '':
        return map_obj.nearestFreeHex(actorIndex, moverIndex)
    return moveTo


def moveWithingReach(actor, target, reach, map_obj):
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]
    targetCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == target][0]
    hexLimit = reach / 5
    dist = map_obj.distanceCalc(
        list(map_obj.arrayCenters).index(targetCoord),
        list(map_obj.arrayCenters).index(actorCoord)
    )
    if dist <= hexLimit:
        return
    line = drawLine(actorCoord, targetCoord, map_obj)
    moveTo = [
        coord for coord in line
        if map_obj.distanceCalc(
            list(map_obj.arrayCenters).index(targetCoord),
            list(map_obj.arrayCenters).index(coord)
        ) <= hexLimit
    ][0]
    if map_obj.arrayCenters[moveTo] != '':
        map_obj.moveToNearest(actor, target)
    else:
        map_obj.moveActor(actor, moveTo)


def bestSphere(actor, map_obj, radius, reach, targets='enemy'):
    reachLimit = (reach + actor.speed) / 5
    setRatio = 4
    hexLimit = radius / 5
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]

    if targets == 'party':
        enemyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]
        partyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]
    else:
        enemyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]
        partyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]

    distances = {
        'Enemy': [[map_obj.distanceCalc(c1, list(map_obj.arrayCenters).index(c2)) for c1 in enemyList]
                  for c2 in list(map_obj.arrayCenters)],
        'Ally': [[map_obj.distanceCalc(c1, list(map_obj.arrayCenters).index(c2)) for c1 in partyList]
                 for c2 in list(map_obj.arrayCenters)]
    }
    desired = len(enemyList)
    goalAchieved = 0
    myIndex = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
               if map_obj.arrayCenters[i] == actor][0]

    while goalAchieved == 0:
        for i in range(len(distances['Ally'])):
            if map_obj.distanceCalc(myIndex, i) > reachLimit:
                continue
            sumEnemies = sum(1 for dist in distances['Enemy'][i] if dist <= hexLimit)
            if sumEnemies == 0:
                continue
            sumAllies = sum(1 for dist in distances['Ally'][i] if dist <= hexLimit)

            enemiesHit = [list(map_obj.arrayCenters)[c] for c in enemyList
                          if map_obj.distanceCalc(c, i) <= hexLimit]
            partyHit = [list(map_obj.arrayCenters)[c] for c in partyList
                        if map_obj.distanceCalc(c, i) <= hexLimit]
            totalHit = enemiesHit + partyHit

            if sumAllies == 0 and sumEnemies == desired:
                return (desired, actorCoord, list(map_obj.arrayCenters)[i], totalHit)
            if sumAllies == 0 and sumEnemies < desired:
                continue
            if sumAllies != 0 and sumEnemies / sumAllies >= setRatio:
                return (sumEnemies, actorCoord, list(map_obj.arrayCenters)[i], totalHit)

        desired -= 1
        if desired == 0:
            return (0, 0)


def bestLine2(actor, map_obj, length, reach):
    startTime = time.time()
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]
    moveLimit = reach + actor.speed / 5
    myIndex = list(map_obj.arrayCenters).index(actorCoord)
    movementCoords = [coord for coord in map_obj.arrayCenters.keys()
                      if map_obj.distanceCalc(myIndex, list(map_obj.arrayCenters).index(coord)) <= moveLimit
                      and map_obj.arrayCenters[coord] == '']
    hexLimit = int(length / 5)

    if actor in map_obj.enemy:
        enemyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]
    else:
        enemyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]

    if len(enemyList) == 1:
        enemyDist = map_obj.distanceCalc(myIndex, enemyList[0])
        if enemyDist > moveLimit + hexLimit:
            return (0, 0)
        targetCoord = list(map_obj.arrayCenters)[enemyList[0]]
        line = drawLine(actorCoord, targetCoord, map_obj)
        moveTo = [coord for coord in line
                  if map_obj.distanceCalc(list(map_obj.arrayCenters).index(targetCoord),
                                          list(map_obj.arrayCenters).index(coord)) <= moveLimit + hexLimit
                  and (map_obj.arrayCenters[coord] == '' or map_obj.arrayCenters[coord] == actor)][0]
        return (1, moveTo, moveTo, [targetCoord])

    test = []
    for enemy in enemyList:
        for e2 in enemyList:
            e2Dist = map_obj.distanceCalc(myIndex, e2)
            enemyDist = map_obj.distanceCalc(myIndex, enemy)
            if e2 == enemy or enemyDist > moveLimit + hexLimit or e2Dist > moveLimit + hexLimit:
                continue
            enemyCoord = list(map_obj.arrayCenters)[enemy]
            e2Coord = list(map_obj.arrayCenters)[e2]
            line = drawLine(enemyCoord, e2Coord, map_obj)
            sumEnemies = sum(1 for badGuy in enemyList if list(map_obj.arrayCenters)[badGuy] in line)
            test.append([(sumEnemies, 0), enemyCoord, e2Coord])

    test = list({tuple(sorted(i)): i for i in test}.values())
    test.sort()
    test.reverse()

    maxX = max(coord[0] for coord in list(map_obj.arrayCenters))
    maxY = max(coord[1] for coord in list(map_obj.arrayCenters))
    test = np.asarray(test)
    testRing = np.asarray([coord for coord in list(map_obj.arrayCenters)
                           if coord[1] in (0, 1, maxY - 1, maxY) or coord[0] in (0, maxX)])

    possibleCoords = []
    for targets in test:
        possibleCoords.clear()
        firstCoord = tuple(targets[1])
        secondCoord = tuple(targets[2])
        maX = max(firstCoord[0], secondCoord[0])
        maY = max(firstCoord[1], secondCoord[1])
        miX = min(firstCoord[0], secondCoord[0])
        miY = min(firstCoord[1], secondCoord[1])

        for coord in testRing:
            coord = tuple(coord)
            if (maX, maY) in [firstCoord, secondCoord]:
                if coord[0] < maX or coord[1] < maY:
                    continue
            elif coord[0] > miX or coord[1] < maY:
                continue
            if miX < coord[0] < maX or miY < coord[1] < maY:
                continue

            guys = targets[0][0]
            if firstCoord != coord:
                line = drawLine(coord, firstCoord, map_obj)
                inBetweenCoords = [x for x in line if miX <= x[0] <= maX and miY <= x[1] <= maY]
                sumEnemies = sum(1 for badGuy in enemyList if list(map_obj.arrayCenters)[badGuy] in inBetweenCoords)
                if secondCoord in line and sumEnemies == guys:
                    possibleCoords += [c for c in line if c not in inBetweenCoords]

            if secondCoord != coord:
                line2 = drawLine(coord, secondCoord, map_obj)
                inBetweenCoords = [x for x in line2 if miX <= x[0] <= maX and miY <= x[1] <= maY]
                sumEnemies = sum(1 for badGuy in enemyList if list(map_obj.arrayCenters)[badGuy] in inBetweenCoords)
                if firstCoord in line2 and sumEnemies == guys:
                    possibleCoords += [c for c in line2 if c not in inBetweenCoords]

        moveTo = [x for x in possibleCoords if x in movementCoords]
        if len(moveTo) != 0:
            badGuys = [list(map_obj.arrayCenters)[badGuy] for badGuy in enemyList
                       if list(map_obj.arrayCenters)[badGuy] in inBetweenCoords]
            return [guys, moveTo[0], moveTo[0], badGuys]

    return (0, 0)


def bestSquare(actor, map_obj, length, reach):
    setRatio = 4
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]
    moveLimit = reach / 5 + actor.speed / 5
    myIndex = list(map_obj.arrayCenters).index(actorCoord)
    movementCoords = [coord for coord in map_obj.arrayCenters.keys()
                      if map_obj.distanceCalc(myIndex, list(map_obj.arrayCenters).index(coord)) <= moveLimit
                      and map_obj.arrayCenters[coord] == '']
    hexLimit = int(length / 5)

    if actor in map_obj.enemy:
        enemyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]
        partyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]
    else:
        enemyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]
        partyList = [list(map_obj.arrayCenters).index(i) for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]

    desired = len(enemyList)
    distances = [[coord2 for coord1 in enemyList
                  if map_obj.distanceCalc(coord1, list(map_obj.arrayCenters).index(coord2)) <= hexLimit]
                 for coord2 in movementCoords]
    flat = list(set(x for xs in distances for x in xs))

    operations = [
        [operator.sub, 1, operator.add, 1, operator.add, 0, operator.sub, 0],
        [operator.sub, 1, operator.sub, 1, operator.add, 0, operator.sub, 0],
        [operator.add, 1, operator.add, 1, operator.add, 0, operator.sub, 0],
        [operator.add, 1, operator.sub, 1, operator.add, 0, operator.sub, 0],
        [operator.sub, 1, operator.add, 2, operator.add, 1, operator.sub, 5],
        [operator.add, 1, operator.sub, 2, operator.sub, 1, operator.add, 5],
        [operator.add, 1, operator.sub, 2, operator.sub, 1, operator.sub, 5],
        [operator.sub, 1, operator.add, 2, operator.add, 1, operator.add, 5],
    ]

    if len(flat) == 0:
        return (0, 0)

    finalList = []
    for moveCoord in flat:
        maxHit = 0
        totalHit = []
        for op in operations:
            startCoord = (op[0](moveCoord[0], op[1]), op[2](moveCoord[1], op[3]))
            squareCoords = []
            for k in range(hexLimit):
                for l in range(hexLimit):
                    x = op[4](op[0](startCoord[0], k), op[5])
                    if op[2] == operator.add:
                        y = op[6](operator.sub(startCoord[1], 2 * l), op[7])
                    else:
                        y = op[6](operator.add(startCoord[1], 2 * l), op[7])
                    if x % 2 != y % 2:
                        y = op[2](y, 1)
                    squareCoords.append((x, y))

            sumEnemies = sum(1 for ind in enemyList if list(map_obj.arrayCenters)[ind] in squareCoords)
            if sumEnemies == 0:
                continue
            sumAllies = sum(1 for ind in partyList if list(map_obj.arrayCenters)[ind] in squareCoords)

            if sumEnemies >> maxHit:
                maxHit = sumEnemies
                enemiesHit = [list(map_obj.arrayCenters)[ind] for ind in enemyList
                              if list(map_obj.arrayCenters)[ind] in squareCoords]
                partyHitList = [list(map_obj.arrayCenters)[ind] for ind in partyList
                                if list(map_obj.arrayCenters)[ind] in squareCoords]
                totalHit = enemiesHit + partyHitList

            if sumAllies == 0 and sumEnemies == desired:
                enemiesHit = [list(map_obj.arrayCenters)[ind] for ind in enemyList
                              if list(map_obj.arrayCenters)[ind] in squareCoords]
                partyHitList = [list(map_obj.arrayCenters)[ind] for ind in partyList
                                if list(map_obj.arrayCenters)[ind] in squareCoords]
                totalHit = enemiesHit + partyHitList
                line = drawLine(actorCoord, moveCoord, map_obj)
                options = [
                    x for x in line
                    if map_obj.distanceCalc(list(map_obj.arrayCenters).index(x),
                                            list(map_obj.arrayCenters).index(actorCoord)) <= actor.speed / 5
                    and map_obj.distanceCalc(list(map_obj.arrayCenters).index(x),
                                             list(map_obj.arrayCenters).index(moveCoord)) <= reach / 5
                ]
                return (desired, options[0], moveCoord, totalHit)

            if sumAllies == 0 and sumEnemies < desired:
                continue
            if sumAllies != 0 and sumEnemies / sumAllies >= setRatio:
                enemiesHit = [list(map_obj.arrayCenters)[ind] for ind in enemyList
                              if list(map_obj.arrayCenters)[ind] in squareCoords]
                partyHitList = [list(map_obj.arrayCenters)[ind] for ind in partyList
                                if list(map_obj.arrayCenters)[ind] in squareCoords]
                totalHit = enemiesHit + partyHitList
                line = drawLine(actorCoord, moveCoord, map_obj)
                options = [
                    x for x in line
                    if map_obj.distanceCalc(list(map_obj.arrayCenters).index(x),
                                            list(map_obj.arrayCenters).index(actorCoord)) <= actor.speed / 5
                    and map_obj.distanceCalc(list(map_obj.arrayCenters).index(x),
                                             list(map_obj.arrayCenters).index(moveCoord)) <= reach / 5
                ]
                return (sumEnemies, options[0], moveCoord, totalHit)

        finalList.append((moveCoord, maxHit, totalHit))

    onlyHits = [x[1] for x in finalList]
    maxEnemies = max(onlyHits)
    max_index = onlyHits.index(maxEnemies)
    line = drawLine(actorCoord, finalList[max_index][0], map_obj)
    options = [
        x for x in line
        if map_obj.distanceCalc(list(map_obj.arrayCenters).index(x),
                                list(map_obj.arrayCenters).index(actorCoord)) <= actor.speed / 5
        and map_obj.distanceCalc(list(map_obj.arrayCenters).index(x),
                                 list(map_obj.arrayCenters).index(finalList[max_index][0])) <= reach / 5
    ]
    return (maxEnemies, options[0], finalList[max_index][0], finalList[max_index][2])


def bestCone(actor, map_obj, length, reach):
    """Find optimal cone placement to hit the most enemies."""
    actor_hex = None
    arrayCenters = list(map_obj.arrayCenters)
    valueAt = map_obj.arrayCenters
    indexOf = {k: i for i, k in enumerate(arrayCenters)}
    empty_hexes = [k for k in arrayCenters if valueAt[k] == '']

    for k, v in valueAt.items():
        if v == actor:
            actor_hex = k
            break
    if actor_hex is None:
        return (0, 0)

    actor_index = indexOf[actor_hex]
    moveLimit = actor.speed / 5
    hexLimit = int(length / 5)

    movementCoords = [k for k in empty_hexes
                      if map_obj.distanceCalc(actor_index, indexOf[k]) <= moveLimit]

    if actor in map_obj.enemy:
        enemies = [indexOf[k] for k, v in valueAt.items() if v != '' and v not in map_obj.enemy]
        allies = [indexOf[k] for k, v in valueAt.items() if v != '' and v not in map_obj.party]
    else:
        enemies = [indexOf[k] for k, v in valueAt.items() if v != '' and v not in map_obj.party]
        allies = [indexOf[k] for k, v in valueAt.items() if v != '' and v not in map_obj.enemy]

    desired = len(enemies)
    enemyDist = [[map_obj.distanceCalc(indexOf[mv], e) for e in enemies] for mv in movementCoords]
    allyDist = [[map_obj.distanceCalc(indexOf[mv], a) for a in allies] for mv in movementCoords]

    operations2 = [
        [[operator.sub, 1], [operator.add, 1], [operator.sub, 1], [operator.sub, 1]],
        [[operator.sub, 1], [operator.sub, 1], [operator.add, 0], [operator.sub, 2]],
        [[operator.add, 0], [operator.sub, 2], [operator.add, 1], [operator.sub, 1]],
        [[operator.add, 1], [operator.sub, 1], [operator.add, 1], [operator.add, 1]],
        [[operator.add, 1], [operator.add, 1], [operator.add, 0], [operator.add, 2]],
        [[operator.add, 0], [operator.add, 2], [operator.sub, 1], [operator.add, 1]],
    ]
    enemyCoords = [arrayCenters[e] for e in enemies]
    allyCoords = [arrayCenters[a] for a in allies]

    while desired > 0:
        for i, mv in enumerate(movementCoords):
            e_count = sum(1 for d in enemyDist[i] if d <= hexLimit)
            if e_count == 0:
                continue
            a_count = sum(1 for d in allyDist[i] if d <= hexLimit)
            if a_count == 0 and e_count < desired:
                continue
            if e_count != desired:
                continue

            for op in operations2:
                finalCoord = []
                x0, y0 = mv

                for cell in range(hexLimit):
                    if op[0][1] == 0:
                        px = op[0][0](x0, op[0][1])
                        py = op[1][0](op[1][0](y0, cell * 2), op[1][1])
                    else:
                        px = op[0][0](op[0][0](x0, cell), op[0][1])
                        py = op[1][0](op[1][0](y0, cell), op[1][1])

                    if op[2][1] == 0:
                        nx = op[2][0](x0, op[2][1])
                        ny = op[3][0](op[3][0](y0, cell * 2), op[3][1])
                    else:
                        nx = op[2][0](op[2][0](x0, cell), op[2][1])
                        ny = op[3][0](op[3][0](y0, cell), op[3][1])

                    dx = abs(px - nx)
                    dy = abs(py - ny)

                    if dx == 0 and dy == 2:
                        finalCoord.append((px, py))
                        finalCoord.append((nx, ny))
                    else:
                        maxX, minX = max(px, nx), min(px, nx)
                        maxY, minY = max(py, ny), min(py, ny)
                        if op[0] == op[2]:
                            for y in range(minY, maxY + 1):
                                finalCoord.append((px, y))
                        else:
                            if op[3][1] == 2:
                                yLine = list(range(minY, maxY + 1))
                                xLine = list(range(maxX, minX - 1, -1))
                            else:
                                yLine = list(range(minY, maxY + 1))
                                xLine = list(range(minX, maxX + 1))
                            for k in range(len(xLine)):
                                finalCoord.append((xLine[k], yLine[k]))

                enemyHit = [c for c in finalCoord if c in enemyCoords]
                allyHit = [c for c in finalCoord if c in allyCoords]

                if len(allyHit) == 0 and len(enemyHit) == desired:
                    return (desired, mv, mv, enemyHit)
                if len(allyHit) > 0 and len(enemyHit) / len(allyHit) >= 4:
                    return (len(enemyHit), mv, mv, enemyHit + allyHit)

        desired -= 1

    return (0, 0)


# ---------------------------------------------------------------------------
# Hex spell-area geometry helpers
# These were previously methods on CustomGraphicsView (TestingMap.py).
# They are pure geometry over map coordinates — no Qt dependency.
# ---------------------------------------------------------------------------

import math


def hex_calc_hexes(index1: int, index2: int, hex_limit: int, map_obj) -> list:
    """
    Return the indexes of all hexes within a cone/sweep of *hex_limit* hexes
    starting at *index1* and aimed toward *index2*.
    """
    arrayCenters = list(map_obj.arrayCenters)

    operations2 = [
        [[operator.sub, 1], [operator.add, 1], [operator.sub, 1], [operator.sub, 1]],
        [[operator.sub, 1], [operator.sub, 1], [operator.add, 0], [operator.sub, 2]],
        [[operator.add, 0], [operator.sub, 2], [operator.add, 1], [operator.sub, 1]],
        [[operator.add, 1], [operator.sub, 1], [operator.add, 1], [operator.add, 1]],
        [[operator.add, 1], [operator.add, 1], [operator.add, 0], [operator.add, 2]],
        [[operator.add, 0], [operator.add, 2], [operator.sub, 1], [operator.add, 1]],
    ]

    ox, oy = arrayCenters[index1]
    tx, ty = arrayCenters[index2]
    angle = math.atan2((oy - ty), (ox - tx))

    dir_angles = [
        math.radians(0),
        math.radians(60),
        math.radians(120),
        math.radians(180),
        math.radians(-120),
        math.radians(-60),
    ]

    best_op_idx = min(
        range(6),
        key=lambda i: abs((angle - dir_angles[i] + math.pi) % (2 * math.pi) - math.pi),
    )
    selected_op = operations2[best_op_idx]

    affected_coords = []
    for cell in range(hex_limit):
        if selected_op[0][1] == 0:
            px = selected_op[0][0](ox, selected_op[0][1])
            py = selected_op[1][0](selected_op[1][0](oy, cell * 2), selected_op[1][1])
        else:
            px = selected_op[0][0](selected_op[0][0](ox, cell), selected_op[0][1])
            py = selected_op[1][0](selected_op[1][0](oy, cell), selected_op[1][1])

        if selected_op[2][1] == 0:
            nx = selected_op[2][0](ox, selected_op[2][1])
            ny = selected_op[3][0](selected_op[3][0](oy, cell * 2), selected_op[3][1])
        else:
            nx = selected_op[2][0](selected_op[2][0](ox, cell), selected_op[2][1])
            ny = selected_op[3][0](selected_op[3][0](oy, cell), selected_op[3][1])

        dx = abs(px - nx)
        dy = abs(py - ny)

        if dx == 0 and dy == 2:
            affected_coords.append((px, py))
            affected_coords.append((nx, ny))
        else:
            max_x, min_x = max(px, nx), min(px, nx)
            max_y, min_y = max(py, ny), min(py, ny)
            if selected_op[0] == selected_op[2]:
                for y in range(min_y, max_y + 1):
                    affected_coords.append((px, y))
            else:
                if selected_op[3][1] == 2:
                    y_line = list(range(min_y, max_y + 1))
                    x_line = list(range(max_x, min_x - 1, -1))
                else:
                    y_line = list(range(min_y, max_y + 1))
                    x_line = list(range(min_x, max_x + 1))
                for k in range(len(x_line)):
                    affected_coords.append((x_line[k], y_line[k]))

    coord_set = set(affected_coords)
    return [i for i, coord in enumerate(arrayCenters) if coord in coord_set]


def hex_calc_line(index1: int, index2: int, hex_limit: int, map_obj) -> list:
    """
    Return the indexes of hexes along the line from *index1* toward *index2*,
    up to *hex_limit* hexes away.
    """
    arrayCenters = map_obj.arrayCenters
    coord1 = list(arrayCenters)[index1]
    coord2 = list(arrayCenters)[index2]

    if map_obj.distanceCalc(index1, index2) >= hex_limit:
        line = drawLine(coord1, coord2, map_obj)
        hexes = [list(arrayCenters).index(coord) for coord in line]
        return [i for i in hexes if map_obj.distanceCalc(i, index1) <= hex_limit and i != index1]

    cone = hex_calc_hexes(index1, index2, hex_limit, map_obj)
    max_dist_hexes = [i for i in cone if map_obj.distanceCalc(i, index1) == hex_limit]

    for idx in max_dist_hexes:
        new_coord = list(arrayCenters)[idx]
        line = drawLine(coord1, new_coord, map_obj)
        if coord2 in line:
            return [list(arrayCenters).index(x) for x in line if x != coord1]

    return []


def hex_calc_square(index1: int, index2: int, hex_limit: int, map_obj) -> list:
    """Return the indexes of hexes inside a square AoE from *index1* aimed at *index2*."""
    arrayCenters = list(map_obj.arrayCenters)
    move_coord = arrayCenters[index2]

    operations = [
        [operator.sub, 1, operator.add, 1, operator.add, 0, operator.sub, 0],
        [operator.sub, 1, operator.sub, 1, operator.add, 0, operator.sub, 0],
        [operator.add, 1, operator.add, 1, operator.add, 0, operator.sub, 0],
        [operator.add, 1, operator.sub, 1, operator.add, 0, operator.sub, 0],
        [operator.sub, 1, operator.add, 2, operator.add, 1, operator.sub, 5],
        [operator.add, 1, operator.sub, 2, operator.sub, 1, operator.add, 5],
        [operator.add, 1, operator.sub, 2, operator.sub, 1, operator.sub, 5],
        [operator.sub, 1, operator.add, 2, operator.add, 1, operator.add, 5],
    ]

    op = operations[0]
    start_coord = (op[0](move_coord[0], op[1]), op[2](move_coord[1], op[3]))
    square_coords = []
    for k in range(hex_limit):
        for l in range(hex_limit):
            x = op[4](op[0](start_coord[0], k), op[5])
            if op[2] == operator.add:
                y = op[6](operator.sub(start_coord[1], 2 * l), op[7])
            else:
                y = op[6](operator.add(start_coord[1], 2 * l), op[7])
            if x % 2 != y % 2:
                y = op[2](y, 1)
            if (x, y) in arrayCenters:
                square_coords.append((x, y))

    return [arrayCenters.index(coord) for coord in square_coords]
