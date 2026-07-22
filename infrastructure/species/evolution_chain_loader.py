from collections import defaultdict, deque

from core.evolution.evolution_chain import EvolutionChain


def build_evolution_chains(rows) -> dict[int, EvolutionChain]:
    """Build chains and real root-to-node depths from evolution edges."""
    outgoing: dict[int, list[tuple[int, int]]] = defaultdict(list)
    incoming: dict[int, set[int]] = defaultdict(set)
    nodes: set[int] = set()
    for row in rows:
        source = int(row["from_species_id"])
        target = int(row["to_species_id"])
        outgoing[source].append((target, 0))
        incoming[target].add(source)
        nodes.update((source, target))

    chains: dict[int, EvolutionChain] = {}
    visited: set[int] = set()
    for start in sorted(nodes):
        if start in visited:
            continue
        component: set[int] = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in component:
                continue
            component.add(node)
            queue.extend(target for target, _ in outgoing.get(node, ()))
            queue.extend(incoming.get(node, ()))
        visited.update(component)
        roots = sorted(node for node in component if not incoming.get(node))
        root = roots[0] if roots else min(component)
        depths: dict[int, int] = {root: 1}
        queue = deque([root])
        while queue:
            node = queue.popleft()
            for target, _ in outgoing.get(node, ()):
                candidate = depths[node] + 1
                if candidate > depths.get(target, 0):
                    depths[target] = candidate
                    queue.append(target)
        for node in component:
            depths.setdefault(node, 1)
        ordered = sorted(component, key=lambda node: (depths[node], node))
        chain = EvolutionChain(
            id=root,
            species=ordered,
            candy_requirements={},
            stage_by_species=depths,
        )
        for node in component:
            chains[node] = chain
    return chains
