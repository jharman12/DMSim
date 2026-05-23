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
        map_obj._coord_idx[coord1],
        map_obj._coord_idx[coord2]
    ))
    x1, y1 = coord1
    x2, y2 = coord2
    xDiff = x2 - x1
    yDiff = y2 - y1

    pts = np.array(map_obj._coord_list)
    lineCoord = np.array([(0.0, 0.0) for _ in range(dist + 1)])
    for i in range(int(dist) + 1):
        lineCoord[i] = [coord1[0] + i * xDiff / dist, coord1[1] + i * yDiff / dist - 0.01]
    snapCoord = [tuple(pts[spatial.KDTree(pts).query(coord)[1]]) for coord in lineCoord]
    return snapCoord


def _bfs_path_dest(start_idx, target_idx, max_steps, map_obj):
    """Return the hex index reached after walking *max_steps* along the
    wall-aware BFS shortest path from start_idx toward target_idx.

    Returns target_idx if it is within max_steps, the furthest point along
    the path otherwise, or None if target_idx is completely unreachable.
    """
    from collections import deque
    if start_idx == target_idx:
        return start_idx

    coords = map_obj._coord_list
    walls = getattr(map_obj, 'walls', set())
    wall_idx_set = {map_obj._coord_idx[c] for c in walls if c in map_obj._coord_idx}

    parent = {start_idx: None}
    queue = deque([start_idx])
    found = False
    while queue:
        cur = queue.popleft()
        if cur == target_idx:
            found = True
            break
        for nb in map_obj._neighbors_of(coords[cur]):
            if nb not in parent and nb not in wall_idx_set:
                parent[nb] = cur
                queue.append(nb)

    if not found:
        return None  # Target fully enclosed by walls — unreachable

    # Reconstruct path: start → target
    path = []
    cur = target_idx
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()  # path[0] = start, path[-1] = target

    # Return the point max_steps along the path (capped at end)
    return path[min(max_steps, len(path) - 1)]


def calcMoveHexes(actor, map_obj, type=None):
    """Return list of hex indices the actor can reach, routing around walls.

    Uses BFS (breadth-first search) so walls act as true blockers — the actor
    cannot pass through a wall hex to reach hexes on the other side.
    For multi-hex actors, only returns destinations where the full footprint fits.
    """
    from collections import deque
    from engine.size_utils import get_size_cat, can_place_footprint

    arrayCenters = map_obj.arrayCenters
    coords = map_obj._coord_list
    walls = getattr(map_obj, 'walls', set())

    actor_coord = next(
        (c for c in arrayCenters if arrayCenters[c] is actor),
        next((c for c in arrayCenters if arrayCenters[c] == actor), None)
    )
    start = map_obj._coord_idx[actor_coord]

    speed = int(actor.speed / 5)
    limit = speed * 2 if type == 'dash' else speed

    # Convert wall coord-tuples to _coord_idx indices for fast BFS lookup
    wall_idx_set = {map_obj._coord_idx[c] for c in walls if c in map_obj._coord_idx}

    cost = {start: 0}
    queue = deque([start])

    while queue:
        cur = queue.popleft()
        if cost[cur] >= limit:
            continue
        for nb in map_obj._neighbors_of(coords[cur]):
            if nb not in cost and nb not in wall_idx_set:
                cost[nb] = cost[cur] + 1
                queue.append(nb)

    size_cat = get_size_cat(actor)
    if size_cat in ('Tiny', 'Small', 'Medium'):
        return [
            i for i in cost
            if arrayCenters[coords[i]] == '' or arrayCenters[coords[i]] is actor
        ]

    # Multi-hex: only reachable if full footprint can fit at destination
    return [
        i for i in cost
        if can_place_footprint(coords[i], size_cat, map_obj, actor)
    ]


def _bfs_cost_from(source_idx, map_obj, ignore_occupants=True):
    """Return a dict {hex_idx: BFS_steps} for every hex reachable from source_idx,
    routing around walls.  Occupants are ignored (pass-through) so this gives the
    true wall-aware path distance from any hex to source_idx.

    This is used to rank movement candidates by wall-aware distance to the target.
    """
    from collections import deque

    coords = map_obj._coord_list
    walls  = getattr(map_obj, 'walls', set())
    wall_idx_set = {map_obj._coord_idx[c] for c in walls if c in map_obj._coord_idx}

    cost  = {source_idx: 0}
    queue = deque([source_idx])
    while queue:
        cur = queue.popleft()
        for nb in map_obj._neighbors_of(coords[cur]):
            if nb not in cost and nb not in wall_idx_set:
                cost[nb] = cost[cur] + 1
                queue.append(nb)
    return cost


def coordWithinReach(actorCoord, targetCoord, reach, map_obj):
    """Return the destination coord the actor should move to in order to get
    within *reach* hexes of targetCoord, routing around walls via BFS path-following.
    Returns actorCoord unchanged if already in range or no actor found there."""
    hexLimit = reach
    dist = map_obj.distanceCalc(
        map_obj._coord_idx[targetCoord],
        map_obj._coord_idx[actorCoord]
    )
    if dist <= hexLimit:
        return actorCoord

    actor = map_obj.arrayCenters.get(actorCoord)
    if not actor or actor == '':
        return actorCoord

    start_idx  = map_obj._coord_idx[actorCoord]
    target_idx = map_obj._coord_idx[targetCoord]
    speed      = int(actor.speed / 5)

    dest_idx = _bfs_path_dest(start_idx, target_idx, speed, map_obj)
    if dest_idx is None:
        return actorCoord  # Surrounded by walls — can't move toward target

    moveTo = map_obj._coord_list[dest_idx]
    if map_obj.arrayCenters.get(moveTo) not in ('', actor):
        return map_obj.nearestFreeHex(start_idx, dest_idx, actor=actor)
    return moveTo


def moveWithingReach(actor, target, reach, map_obj):
    """Move actor toward target along the wall-aware BFS path, stopping within
    *reach* feet if possible, otherwise as close as movement allows."""
    actorCoord = next(
        (c for c in map_obj.arrayCenters if map_obj.arrayCenters[c] is actor), None
    )
    targetCoord = next(
        (c for c in map_obj.arrayCenters if map_obj.arrayCenters[c] is target), None
    )
    if actorCoord is None or targetCoord is None:
        return
    hexLimit = reach / 5
    dist = map_obj.distanceCalc(
        map_obj._coord_idx[targetCoord],
        map_obj._coord_idx[actorCoord]
    )
    if dist <= hexLimit:
        return

    start_idx  = map_obj._coord_idx[actorCoord]
    target_idx = map_obj._coord_idx[targetCoord]
    speed      = int(actor.speed / 5)

    dest_idx = _bfs_path_dest(start_idx, target_idx, speed, map_obj)
    if dest_idx is None:
        return  # No path around walls

    moveTo = map_obj._coord_list[dest_idx]
    if map_obj.arrayCenters.get(moveTo) not in ('', actor):
        map_obj.moveToNearest(actor, targetCoord)
    else:
        map_obj.moveActor(actor, moveTo)


def bestSphere(actor, map_obj, radius, reach, targets='enemy'):
    from engine.size_utils import dedup_actor_list
    reachLimit = (reach + actor.speed) / 5
    setRatio = 4
    hexLimit = radius / 5
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]
    coord_idx = map_obj._coord_idx
    coord_list = map_obj._coord_list

    if targets == 'party':
        enemyList = dedup_actor_list([coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy], map_obj)
        partyList = dedup_actor_list([coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party], map_obj)
    else:
        enemyList = dedup_actor_list([coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party], map_obj)
        partyList = dedup_actor_list([coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy], map_obj)

    distances = {
        'Enemy': [[map_obj.distanceCalc(c1, coord_idx[c2]) for c1 in enemyList]
                  for c2 in coord_list],
        'Ally': [[map_obj.distanceCalc(c1, coord_idx[c2]) for c1 in partyList]
                 for c2 in coord_list]
    }
    desired = len(enemyList)
    goalAchieved = 0
    myIndex = coord_idx[actorCoord]

    while goalAchieved == 0:
        for i in range(len(distances['Ally'])):
            if map_obj.distanceCalc(myIndex, i) > reachLimit:
                continue
            sumEnemies = sum(1 for dist in distances['Enemy'][i] if dist <= hexLimit)
            if sumEnemies == 0:
                continue
            sumAllies = sum(1 for dist in distances['Ally'][i] if dist <= hexLimit)

            enemiesHit = [coord_list[c] for c in enemyList
                          if map_obj.distanceCalc(c, i) <= hexLimit]
            partyHit = [coord_list[c] for c in partyList
                        if map_obj.distanceCalc(c, i) <= hexLimit]
            totalHit = enemiesHit + partyHit

            if sumAllies == 0 and sumEnemies == desired:
                return (desired, actorCoord, coord_list[i], totalHit)
            if sumAllies == 0 and sumEnemies < desired:
                continue
            if sumAllies != 0 and sumEnemies / sumAllies >= setRatio:
                return (sumEnemies, actorCoord, coord_list[i], totalHit)

        desired -= 1
        if desired == 0:
            return (0, 0)


def bestLine2(actor, map_obj, length, reach):
    startTime = time.time()
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]
    moveLimit = reach + actor.speed / 5
    coord_idx = map_obj._coord_idx
    coord_list = map_obj._coord_list
    myIndex = coord_idx[actorCoord]
    movementCoords = [coord for coord in map_obj.arrayCenters.keys()
                      if map_obj.distanceCalc(myIndex, coord_idx[coord]) <= moveLimit
                      and map_obj.arrayCenters[coord] == '']
    hexLimit = int(length / 5)

    if actor in map_obj.enemy:
        enemyList = [coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]
    else:
        enemyList = [coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]

    if len(enemyList) == 1:
        enemyDist = map_obj.distanceCalc(myIndex, enemyList[0])
        if enemyDist > moveLimit + hexLimit:
            return (0, 0)
        targetCoord = coord_list[enemyList[0]]
        line = drawLine(actorCoord, targetCoord, map_obj)
        moveTo = [coord for coord in line
                  if map_obj.distanceCalc(coord_idx[targetCoord],
                                          coord_idx[coord]) <= moveLimit + hexLimit
                  and (map_obj.arrayCenters[coord] == '' or map_obj.arrayCenters[coord] == actor)][0]
        return (1, moveTo, moveTo, [targetCoord])

    test = []
    for enemy in enemyList:
        for e2 in enemyList:
            e2Dist = map_obj.distanceCalc(myIndex, e2)
            enemyDist = map_obj.distanceCalc(myIndex, enemy)
            if e2 == enemy or enemyDist > moveLimit + hexLimit or e2Dist > moveLimit + hexLimit:
                continue
            enemyCoord = coord_list[enemy]
            e2Coord = coord_list[e2]
            line = drawLine(enemyCoord, e2Coord, map_obj)
            sumEnemies = sum(1 for badGuy in enemyList if coord_list[badGuy] in line)
            test.append([(sumEnemies, 0), enemyCoord, e2Coord])

    test = list({tuple(sorted(i)): i for i in test}.values())
    test.sort()
    test.reverse()

    maxX = max(coord[0] for coord in coord_list)
    maxY = max(coord[1] for coord in coord_list)
    test = np.asarray(test)
    testRing = np.asarray([coord for coord in coord_list
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
                sumEnemies = sum(1 for badGuy in enemyList if coord_list[badGuy] in inBetweenCoords)
                if secondCoord in line and sumEnemies == guys:
                    possibleCoords += [c for c in line if c not in inBetweenCoords]

            if secondCoord != coord:
                line2 = drawLine(coord, secondCoord, map_obj)
                inBetweenCoords = [x for x in line2 if miX <= x[0] <= maX and miY <= x[1] <= maY]
                sumEnemies = sum(1 for badGuy in enemyList if coord_list[badGuy] in inBetweenCoords)
                if firstCoord in line2 and sumEnemies == guys:
                    possibleCoords += [c for c in line2 if c not in inBetweenCoords]

        moveTo = [x for x in possibleCoords if x in movementCoords]
        if len(moveTo) != 0:
            badGuys = [coord_list[badGuy] for badGuy in enemyList
                       if coord_list[badGuy] in inBetweenCoords]
            return [guys, moveTo[0], moveTo[0], badGuys]

    return (0, 0)


def bestSquare(actor, map_obj, length, reach):
    setRatio = 4
    actorCoord = [x for x in map_obj.arrayCenters.keys() if map_obj.arrayCenters[x] == actor][0]
    moveLimit = reach / 5 + actor.speed / 5
    coord_idx = map_obj._coord_idx
    coord_list = map_obj._coord_list
    myIndex = coord_idx[actorCoord]
    movementCoords = [coord for coord in map_obj.arrayCenters.keys()
                      if map_obj.distanceCalc(myIndex, coord_idx[coord]) <= moveLimit
                      and map_obj.arrayCenters[coord] == '']
    hexLimit = int(length / 5)

    if actor in map_obj.enemy:
        enemyList = [coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]
        partyList = [coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]
    else:
        enemyList = [coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.party]
        partyList = [coord_idx[i] for i in map_obj.arrayCenters.keys()
                     if map_obj.arrayCenters[i] != '' and map_obj.arrayCenters[i] not in map_obj.enemy]

    desired = len(enemyList)
    distances = [[coord2 for coord1 in enemyList
                  if map_obj.distanceCalc(coord1, coord_idx[coord2]) <= hexLimit]
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

            sumEnemies = sum(1 for ind in enemyList if coord_list[ind] in squareCoords)
            if sumEnemies == 0:
                continue
            sumAllies = sum(1 for ind in partyList if coord_list[ind] in squareCoords)

            if sumEnemies >> maxHit:
                maxHit = sumEnemies
                enemiesHit = [coord_list[ind] for ind in enemyList if coord_list[ind] in squareCoords]
                partyHitList = [coord_list[ind] for ind in partyList if coord_list[ind] in squareCoords]
                totalHit = enemiesHit + partyHitList

            if sumAllies == 0 and sumEnemies == desired:
                enemiesHit = [coord_list[ind] for ind in enemyList if coord_list[ind] in squareCoords]
                partyHitList = [coord_list[ind] for ind in partyList if coord_list[ind] in squareCoords]
                totalHit = enemiesHit + partyHitList
                line = drawLine(actorCoord, moveCoord, map_obj)
                options = [
                    x for x in line
                    if map_obj.distanceCalc(coord_idx[x], coord_idx[actorCoord]) <= actor.speed / 5
                    and map_obj.distanceCalc(coord_idx[x], coord_idx[moveCoord]) <= reach / 5
                ]
                return (desired, options[0], moveCoord, totalHit)

            if sumAllies == 0 and sumEnemies < desired:
                continue
            if sumAllies != 0 and sumEnemies / sumAllies >= setRatio:
                enemiesHit = [coord_list[ind] for ind in enemyList if coord_list[ind] in squareCoords]
                partyHitList = [coord_list[ind] for ind in partyList if coord_list[ind] in squareCoords]
                totalHit = enemiesHit + partyHitList
                line = drawLine(actorCoord, moveCoord, map_obj)
                options = [
                    x for x in line
                    if map_obj.distanceCalc(coord_idx[x], coord_idx[actorCoord]) <= actor.speed / 5
                    and map_obj.distanceCalc(coord_idx[x], coord_idx[moveCoord]) <= reach / 5
                ]
                return (sumEnemies, options[0], moveCoord, totalHit)

        finalList.append((moveCoord, maxHit, totalHit))

    onlyHits = [x[1] for x in finalList]
    maxEnemies = max(onlyHits)
    max_index = onlyHits.index(maxEnemies)
    line = drawLine(actorCoord, finalList[max_index][0], map_obj)
    options = [
        x for x in line
        if map_obj.distanceCalc(coord_idx[x], coord_idx[actorCoord]) <= actor.speed / 5
        and map_obj.distanceCalc(coord_idx[x], coord_idx[finalList[max_index][0]]) <= reach / 5
    ]
    return (maxEnemies, options[0], finalList[max_index][0], finalList[max_index][2])


def bestCone(actor, map_obj, length, reach):
    """Find optimal cone placement to hit the most enemies."""
    actor_hex = None
    arrayCenters = map_obj._coord_list
    valueAt = map_obj.arrayCenters
    indexOf = map_obj._coord_idx
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
    arrayCenters = map_obj._coord_list

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
    arrayCenters = map_obj._coord_list
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
