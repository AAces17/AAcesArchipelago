from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Location, Region

from . import items, SpeciesUtils, Tasks
from .items import EquilinoxItem

if TYPE_CHECKING:
    from .world import EquilinoxWorld

class EquilinoxLocation(Location):
    game = "Equilinox"

    def __init__(self, player, name, id: int, region: Region):
        super().__init__(player, name, id, region)

def get_loc_names_to_id_dict() -> dict[str, int]:
    loc_name_to_id = {}

    all_species = SpeciesUtils.all_species
    all_tasks = Tasks.all_tasks

    for task in all_tasks:
        loc_name_to_id[f"Complete Task '{task.name}'"] = task.id + 10000

    for species in all_species:

        if species.name not in SpeciesUtils.rocks_and_stones:

            # Size checks: 31XYYYZZZ
            locId = 310
            if not species.is_plant: # X = 1 if animal else 0
                locId += 1
            locId *= 1000
            locId += species.id # YYY = species id
            locId *= 1000
            locId += 110 # ZZZ = size (110 <=> 1.10)

            loc_name_to_id[f"Grow a Big {species.name} (Size 1.10)"] = locId

            locId += 10

            loc_name_to_id[f"Grow a Huge {species.name} (Size 1.20)"] = locId

        if not species.is_base_species():
            id = species.id
            loc_name = f"Evolve {species.name}"
            if species.is_plant:
                id += 20000
            else:
                id += 21000
            loc_name_to_id[loc_name] = id



    return loc_name_to_id

def get_location_names_with_ids(location_names: list[str]) -> dict[str, int | None]:
    return {location_name: get_loc_names_to_id_dict()[location_name] for location_name in location_names}

def create_all_locations(world: EquilinoxWorld) -> None:
    create_regular_locations(world)
    create_events(world)

def create_regular_locations(world: EquilinoxWorld) -> None:
    all_locs = get_loc_names_to_id_dict()

    locations_to_include = []

    task_locations = [name for name, id in all_locs.items() if 10000 < id < 20000]
    if world.options.goal_selection == 0: task_locations.remove("Complete Task 'Completionist'")

    evolution_locations = [name for name, id in all_locs.items() if 20000 < id < 30000]

    size_locations = [name for name, id in all_locs.items() if 310000000 < id < 320000000]


    locations_to_include += task_locations
    locations_to_include += evolution_locations
    if world.options.size_checks.value == 1: locations_to_include += size_locations

    menu = world.get_region("Menu")

    menu.add_locations(get_location_names_with_ids(locations_to_include), EquilinoxLocation)


def create_events(world: EquilinoxWorld) -> None:
    menu = world.get_region("Menu")

    for species in SpeciesUtils.all_species:
        menu.add_event(f"{species.name} Unlock", species.name, location_type=EquilinoxLocation, item_type=EquilinoxItem)

    menu.add_event(
        "Game finished", "Victory", location_type=EquilinoxLocation, item_type=items.EquilinoxItem
    )