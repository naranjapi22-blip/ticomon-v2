# Release and duplicate management

## Atomic release

`build_core()` constructs `ReleaseApplicationService` with
`NeonReleaseUnitOfWork`. The UoW owns one PostgreSQL connection and one
transaction for the complete release operation.

Within that boundary, the application:

1. Rejects repeated collection numbers.
2. Loads and locks all requested creatures in stable `collection_number`
   order, filtering by `trainer_id`.
3. Rejects missing numbers, foreign creatures, missing species, and invalid
   reward calculations before deletion.
4. Loads and locks the trainer Candy inventory once.
5. Calculates and merges rewards by Candy type in the domain inventory.
6. Deletes all validated creatures with one owner-filtered batch operation.
7. Replaces the trainer Candy rows once.

The database transaction commits only after both creature deletion and Candy
persistence succeed. Any exception rolls back both changes. Empty batch
operations are safe no-ops.

`ReleaseApplicationService` retains a compatibility constructor path for
existing consumers that provide separate creature and Candy repositories. That
path is not the production wiring and does not provide the same cross-repository
atomicity guarantee.

## Duplicate management

Duplicate species are retrieved once from the creature repository. The
application requests all required species with `SpeciesRepository.get_many()`
and builds an ID map, preserving the repository's duplicate order while
avoiding an individual species lookup for every result. Type filtering uses the
same single species map.

`NeonSpeciesRepository.get_many()` and `find_by_spawn_rarity()` load variants
only for the species rows returned by their species query. `_load_all_variants()`
is reserved for operations such as `get_all()` that genuinely load the full
species catalogue.
