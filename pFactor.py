from collections import defaultdict, deque
from search import fetchAllLists, getRelationsData

# Relation type weights for P-Factor (sequel detection)
RELATION_WEIGHTS = {
    'SEQUEL': 0.15,
    'PREQUEL': 0.10,
    'SIDE_STORY': 0.08,
    'PARENT': 0.08,
    'SPIN_OFF': 0.05,
    'ALTERNATIVE': 0.03,
    'CHARACTER': 0.02,
}

# Display labels: relationType describes what the RELATED node is to the queried node
# so we invert for display from the current anime's perspective
DISPLAY_RELATION = {
    'PREQUEL': 'Sequel to',
    'SEQUEL': 'Prequel to',
    'PARENT': 'Side story of',
    'SIDE_STORY': 'Related to',
    'SPIN_OFF': 'Related to',
    'ALTERNATIVE': 'Alt. of',
    'CHARACTER': 'Related to',
    'SOURCE': 'Based on',
    'ADAPTATION': 'Related to',
    'OTHER': 'Related to',
}

# Relation types that define franchise ordering (prequel → sequel direction)
FORWARD_RELATIONS = {'SEQUEL', 'SIDE_STORY', 'SPIN_OFF'}
REVERSE_RELATIONS = {'PREQUEL', 'PARENT'}


def bFactor(episodes, score):
    """
    Bingability factor: bonus for shorter, more accessible anime.

    Short series (1-13 eps) are easiest to commit to and get the highest bonus.
    Longer series need progressively higher scores to justify the time investment.

    Returns: float in [0, 0.06] range
    """
    if not episodes or episodes <= 0 or not score:
        return 0

    if episodes <= 13:
        return 0.06
    elif episodes <= 26:
        return round(max((score - 70) * 0.002, 0), 4)
    elif episodes <= 52:
        return round(max((score - 80) * 0.001, 0), 4)
    else:
        return 0


def pFactor(relations, watched_ids):
    """
    Previous season factor: bonus for anime related to titles you've watched.
    Uses the highest-weighted matching relation type.

    Returns: (factor: float, relation_info: str or None)
    """
    best_weight = 0
    best_relation = None

    for rel in relations:
        if rel['id'] in watched_ids:
            weight = RELATION_WEIGHTS.get(rel['relationType'], 0)
            if weight > best_weight:
                best_weight = weight
                label = DISPLAY_RELATION.get(rel['relationType'], 'Related to')
                best_relation = f"{label} {rel['title']}"

    return best_weight, best_relation


def aplCalc(score, p_val, b_val, p_weight=0.6, b_weight=0.4):
    """
    Calculate APL priority score.
    APL = Score x (1 + P*pWeight + B*bWeight)
    """
    if not score:
        return 0
    return round(score * (1 + p_val * p_weight + b_val * b_weight), 2)


def _sort_by_franchise_order(group):
    """Sort a group of related anime by watch order (prequel → sequel)."""
    id_to_anime = {a['id']: a for a in group}
    group_ids = set(id_to_anime.keys())

    # Build directed edges using a set to deduplicate
    edge_set = set()
    for anime in group:
        for rel in anime.get('_relations', []):
            if rel['id'] not in group_ids:
                continue
            if rel['relationType'] in FORWARD_RELATIONS:
                edge_set.add((anime['id'], rel['id']))
            elif rel['relationType'] in REVERSE_RELATIONS:
                edge_set.add((rel['id'], anime['id']))

    # Build adjacency list from deduplicated edges
    in_degree = {aid: 0 for aid in group_ids}
    adj = defaultdict(list)
    for frm, to in edge_set:
        adj[frm].append(to)
        in_degree[to] += 1

    # Kahn's topological sort (break ties by APL descending)
    queue = deque(sorted(
        [aid for aid in group_ids if in_degree[aid] == 0],
        key=lambda x: id_to_anime[x]['APL'],
        reverse=True
    ))
    ordered = []

    while queue:
        node = queue.popleft()
        ordered.append(id_to_anime[node])
        for nb in adj[node]:
            in_degree[nb] -= 1
            if in_degree[nb] == 0:
                queue.append(nb)

    # Handle cycles (shouldn't happen but be safe)
    if len(ordered) < len(group):
        ordered_ids = {a['id'] for a in ordered}
        for a in group:
            if a['id'] not in ordered_ids:
                ordered.append(a)

    return ordered


def groupResults(results):
    """
    Group related anime together by franchise.

    Uses Union-Find to identify connected components among planning anime,
    then orders within each group by franchise watch order (prequel → sequel).
    Groups are sorted by the highest APL score in each group.
    """
    if not results:
        return results

    planning_ids = {a['id'] for a in results}

    # Union-Find
    parent = {a['id']: a['id'] for a in results}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Union anime that share relations within the planning list
    for anime in results:
        for rel in anime.get('_relations', []):
            if rel['id'] in planning_ids:
                union(anime['id'], rel['id'])

    # Collect groups
    groups = {}
    for anime in results:
        root = find(anime['id'])
        if root not in groups:
            groups[root] = []
        groups[root].append(anime)

    # Sort within each multi-anime group by franchise order
    for root in groups:
        if len(groups[root]) > 1:
            groups[root] = _sort_by_franchise_order(groups[root])

    # Sort groups by highest APL in group (descending)
    sorted_groups = sorted(
        groups.values(),
        key=lambda g: max(a['APL'] for a in g),
        reverse=True
    )

    # Flatten and assign group metadata
    output = []
    for group_idx, group in enumerate(sorted_groups):
        for anime in group:
            anime['group'] = group_idx
            anime['groupSize'] = len(group)
            output.append(anime)

    # Fill in relation info for grouped anime that don't have a watched relation
    # Prefer "Sequel to X" (what to watch before this) over "Prequel to X" (what follows)
    for anime in output:
        if anime['groupSize'] > 1 and not anime.get('relation'):
            follows_rel = None   # "Sequel to X" - tells user what comes before
            other_rel = None     # "Prequel to X" or other - tells user what follows
            for rel in anime.get('_relations', []):
                if rel['id'] in planning_ids:
                    label = DISPLAY_RELATION.get(rel['relationType'], 'Related to')
                    text = f"{label} {rel['title']}"
                    if rel['relationType'] in REVERSE_RELATIONS and follows_rel is None:
                        follows_rel = text
                    elif other_rel is None:
                        other_rel = text
            anime['relation'] = follows_rel or other_rel

    return output


def getPFactorData(username, progress_callback=None):
    """
    Main calculation pipeline. Fetches user data and calculates APL scores.
    Groups related anime by franchise and orders by watch order within groups.
    """
    if progress_callback:
        progress_callback(0, 100, "Fetching anime lists...")

    all_lists = fetchAllLists(username)

    planning = all_lists.get('PLANNING', [])

    allowed_formats = {'TV', 'TV_SHORT'}
    planning = [
        a for a in planning
        if a.get('format') in allowed_formats and a.get('status') == 'FINISHED'
    ]

    if not planning:
        return []

    watched_ids = set()
    for status in ('COMPLETED', 'CURRENT', 'REPEATING'):
        for anime in all_lists.get(status, []):
            watched_ids.add(anime['id'])

    if progress_callback:
        progress_callback(5, 100, "Fetching relation data...")

    results = []
    total = len(planning)

    for i, anime in enumerate(planning):
        if progress_callback:
            pct = 5 + int((i / total) * 90)
            progress_callback(
                pct, 100,
                f"Processing {i+1}/{total}: {anime['title']['romaji'][:30]}"
            )

        relations = getRelationsData(anime['id'])

        p_val, relation_info = pFactor(relations, watched_ids)
        b_val = bFactor(anime.get('episodes'), anime.get('averageScore'))
        apl_score = aplCalc(anime.get('averageScore', 0), p_val, b_val)

        eps = anime.get('episodes') or 0
        dur = anime.get('duration') or 24
        watch_hours = round((eps * dur) / 60, 1) if eps > 0 else 0

        results.append({
            'title': anime['title']['romaji'],
            'APL': apl_score,
            'averageScore': anime.get('averageScore', 0),
            'episodes': eps,
            'duration': dur,
            'watchTime': watch_hours,
            'pfactor': p_val,
            'bfactor': b_val,
            'relation': relation_info,
            'id': anime['id'],
            '_relations': relations,
        })

    # Group related anime by franchise, order within groups
    results = groupResults(results)

    # Clean up internal field
    for r in results:
        r.pop('_relations', None)

    if progress_callback:
        progress_callback(100, 100, f"Done! {len(results)} anime processed.")

    return results
