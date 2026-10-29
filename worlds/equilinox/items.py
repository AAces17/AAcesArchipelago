from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification
from . import SpeciesUtils, Tasks

if TYPE_CHECKING:
    from .world import EquilinoxWorld

ITEM_NAME_TO_ID = {}

DEFAULT_ITEM_CLASSIFICATIONS = {}

species_unlock_items = []

def set_item_names_to_id():
    all_species = SpeciesUtils.all_species

    # Base Species Unlocks
    for species in all_species:
        if species.is_base_species():

            id = species.id
            item_name = f"{species.name} Permit"
            if species.is_plant:
                id += 10000
            else:
                id += 11000
            ITEM_NAME_TO_ID[item_name] = id
            DEFAULT_ITEM_CLASSIFICATIONS[item_name] = ItemClassification.progression
            species_unlock_items.append(item_name)

    ITEM_NAME_TO_ID["100 dp"] = 80001
    ITEM_NAME_TO_ID["500 dp"] = 80005

    ITEM_NAME_TO_ID["1,000 dp"] = 80010
    ITEM_NAME_TO_ID["2,500 dp"] = 80025
    ITEM_NAME_TO_ID["5,000 dp"] = 80050
    ITEM_NAME_TO_ID["7,500 dp"] = 80075

    ITEM_NAME_TO_ID["10,000 dp"] = 80100
    ITEM_NAME_TO_ID["25,000 dp"] = 80250
    ITEM_NAME_TO_ID["50,000 dp"] = 80500
    ITEM_NAME_TO_ID["75,000 dp"] = 80750

    ITEM_NAME_TO_ID["100,000 dp"] = 81000

    DEFAULT_ITEM_CLASSIFICATIONS["100 dp"] = ItemClassification.filler
    DEFAULT_ITEM_CLASSIFICATIONS["500 dp"] = ItemClassification.filler

    DEFAULT_ITEM_CLASSIFICATIONS["1,000 dp"] = ItemClassification.filler
    DEFAULT_ITEM_CLASSIFICATIONS["2,500 dp"] = ItemClassification.filler
    DEFAULT_ITEM_CLASSIFICATIONS["5,000 dp"] = ItemClassification.filler | ItemClassification.useful
    DEFAULT_ITEM_CLASSIFICATIONS["7,500 dp"] = ItemClassification.filler | ItemClassification.useful

    DEFAULT_ITEM_CLASSIFICATIONS["10,000 dp"] = ItemClassification.progression
    DEFAULT_ITEM_CLASSIFICATIONS["25,000 dp"] = ItemClassification.progression
    DEFAULT_ITEM_CLASSIFICATIONS["50,000 dp"] = ItemClassification.progression_skip_balancing | ItemClassification.useful
    DEFAULT_ITEM_CLASSIFICATIONS["75,000 dp"] = ItemClassification.progression_skip_balancing | ItemClassification.useful

    DEFAULT_ITEM_CLASSIFICATIONS["100,000 dp"] = ItemClassification.progression_skip_balancing | ItemClassification.useful

    ITEM_NAME_TO_ID["Progressive DP/Min Bonus"] = 70001
    DEFAULT_ITEM_CLASSIFICATIONS["Progressive DP/Min Bonus"] = ItemClassification.progression

    DEFAULT_ITEM_CLASSIFICATIONS["Filler"] = 90001
    DEFAULT_ITEM_CLASSIFICATIONS["Filler"] = ItemClassification.filler

    #return ITEM_NAME_TO_ID

class EquilinoxItem(Item):
    game = "Equilinox"

def get_random_filler_item_name(world: EquilinoxWorld) -> str:
    filler_items = ["100 dp", "500 dp", "1,000 dp", "2,500 dp", "5,000 dp", "7,500 dp", "10,000 dp"]
    weights =      [ 6,        12,       15,         10,         5,          3,          1         ]
    return world.random.choices(filler_items, weights=weights, k=1)[0]


def create_item_with_correct_classification(world: EquilinoxWorld, name: str) -> EquilinoxItem:
    classification = DEFAULT_ITEM_CLASSIFICATIONS[name]
    return EquilinoxItem(name, classification, ITEM_NAME_TO_ID[name], world.player)

def get_nearest_money_item(world: EquilinoxWorld, amt: int) -> EquilinoxItem:
    if amt >= 90000:
        return world.create_item("100,000 dp") # 90,000 -
    elif amt >= 65000:
        return world.create_item("75,000 dp")  # 65,000 - 90,000
    elif amt >= 40000:
        return world.create_item("50,000 dp")  # 40,000 - 65,000
    elif amt >= 20000:
        return world.create_item("25,000 dp")  # 20,000 - 40,000
    elif amt >= 9000:
        return world.create_item("10,000 dp")  # 9,000 - 20,000
    elif amt >= 6500:
        return world.create_item("7,500 dp")   # 6,500 - 9,000
    elif amt >= 4000:
        return world.create_item("5,000 dp")   # 4,000 - 6,500
    elif amt >= 2000:
        return world.create_item("2,500 dp")   # 2,000 - 4,000
    elif amt >= 750:
        return world.create_item("1,000 dp")   # 750 - 2,000
    elif amt >= 400:
        return world.create_item("500 dp")     # 400 - 750
    else:
        return world.create_item("100 dp")     # 0 - 400

def approx_money_as_sum(amt: int, max_summands: int, possible_values=None) -> list[int]:
    if amt < 100: return []
    if possible_values is None:
        possible_values = [100000, 75000, 50000, 25000, 10000, 7500, 5000, 2500, 1000, 500, 100]
    possible_values = sorted(possible_values, reverse=True)
    running_sum = 0
    summands = []

    for val in possible_values:
        while running_sum < amt:
            if len(summands) >= max_summands: break
            if (running_sum + val) > amt: break
            running_sum += val
            summands.append(val)

    return summands

def create_all_items(world: EquilinoxWorld) -> None:
    item_pool: list[Item] = [
        get_nearest_money_item(world, 50000)
    ]

    for unlock in species_unlock_items:
        if unlock == "Grass Tuft Permit": continue
        item_pool.append(world.create_item(unlock))

    dp_bonuses_to_add = min(world.options.dp_per_min_bonus_count.value, missing_item_count(world, item_pool))

    for _ in range(dp_bonuses_to_add):
        item_pool.append(world.create_item("Progressive DP/Min Bonus"))

    dp_in_pool = world.options.itempool_dp.value
    dp_to_add = []

    max_summands = min(7, missing_item_count(world, item_pool))

    if dp_in_pool > 100:
        if dp_in_pool > 250000:
            dp_to_add = [100000, 75000] + approx_money_as_sum(dp_in_pool-175000, max_summands, possible_values=[50000, 25000, 10000, 7500, 5000, 2500, 1000])
        elif dp_in_pool > 100000:
            dp_to_add = [75000] + approx_money_as_sum(dp_in_pool-75000, max_summands, possible_values=[50000, 25000, 10000, 7500, 5000, 2500, 1000])
        else:
            dp_to_add = approx_money_as_sum(dp_in_pool, max_summands, possible_values=[50000, 25000, 10000, 7500, 5000, 2500, 1000])

    for dp in dp_to_add:
        item_pool.append(get_nearest_money_item(world, dp))

    if not world.options.tasks_reward_dp:
        for task in Tasks.all_tasks:
            if missing_item_count(world, item_pool) > 0:
                item_pool.append(get_nearest_money_item(world, task.cash_reward))

    # Filler items
    needed_number_of_filler_items = missing_item_count(world, item_pool)

    item_pool += [world.create_filler() for _ in range(needed_number_of_filler_items)]


    world.multiworld.itempool += item_pool

def missing_item_count(world: EquilinoxWorld, item_pool: list[Item]) -> int:
    return len(world.multiworld.get_unfilled_locations(world.player)) - len(item_pool)