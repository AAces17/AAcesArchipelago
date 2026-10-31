from __future__ import annotations

import dataclasses
import typing

from BaseClasses import CollectionState
from NetUtils import JSONMessagePart
from rule_builder.options import OptionFilter
from rule_builder.rules import Has, True_, Rule, False_, CanReachLocation, HasFromListUnique, HasAny, HasGroupUnique
from typing import TYPE_CHECKING, override

from . import SpeciesUtils, Tasks, Evolution

if TYPE_CHECKING:
    from .world import EquilinoxWorld


def set_all_rules(world: EquilinoxWorld) -> None:
    set_all_location_rules(world)
    set_completion_condition(world)


def set_all_location_rules(world: EquilinoxWorld) -> None:
    set_evolution_rules(world)
    completionist_rule = set_task_rules(world)
    set_trait_rules(world)

    victory = world.get_location("Game finished")
    if world.options.goal_selection.value == 0:
        #Completionist
        world.set_rule(victory, completionist_rule)
    elif world.options.goal_selection.value == 1:
        #Evolve from a set of species
        required_species = world.options.evo_goal_species.value
        required_count = world.options.evo_goal_count.value

        if required_count == 0 or required_count > len(required_species):
            required_count = len(required_species)

        print(f"Needs {required_count} of the following to goal: \n\t{required_species}")

        world.set_rule(victory, HasFromListUnique(*required_species, count=required_count))
    return

def set_trait_rules(world: EquilinoxWorld) -> None:
    for species in SpeciesUtils.all_species:
        if species.name not in SpeciesUtils.rocks_and_stones:
            if species.name == "Camel" and world.options.goal_selection == 1: continue
            if world.options.size_checks.value == 1:
                sizeLoc1 = world.get_location(f"Grow a Big {species.name} (Size 1.10)")
                sizeLoc2 = world.get_location(f"Grow a Huge {species.name} (Size 1.20)")

                extra_rule = True_()

                # TODO: replace with a cleaner Satisfaction fxn
                suitable_biomes = species.get_suitable_biomes()
                if len(suitable_biomes) > 0:
                    biome_rule = False_()
                    for biome in suitable_biomes:
                        biome_rule = biome_rule | CanAccessBiome(biome, 50)
                    extra_rule = extra_rule & biome_rule
                if species.eats != "":
                    extra_rule = extra_rule & CanGetAtLeastOneDiet(species)
                if species.liked_species != "":
                    # Make sure that at least one liked species is accessible
                    reqs = SpeciesUtils.get_required_species_from_string(species.liked_species)
                    for spec_list in reqs:
                        if len(spec_list) < 1: continue
                        liked_rule = False_()
                        for spec in spec_list:
                            liked_rule = liked_rule | (Has(spec.name) & CanAffordDP(spec.cost))
                        extra_rule = extra_rule & liked_rule

                world.set_rule(sizeLoc1, Has(species.name) & CanAffordDP(species.cost + 20000 * species.evolution_stage) & extra_rule)
                world.set_rule(sizeLoc2, Has(species.name) & CanAffordDP(species.cost + 50000 * species.evolution_stage) & extra_rule)

def set_evolution_rules(world: EquilinoxWorld) -> None:
    for species in SpeciesUtils.all_species:
        event_loc = world.get_location(f"{species.name} Unlock")
        world.set_rule(event_loc, species_access_rules[species.name])
        if not species.is_base_species():
            loc = world.get_location(f"Evolve {species.name}")
            world.set_rule(loc, Has(species.name) & CanAffordDP(species.cost * species.evolution_stage))


def set_task_rules(world: EquilinoxWorld) -> Rule:
    tasks = Tasks.all_tasks
    completionist_rule = True_()
    for task in tasks:
        if task.name == "Completionist": continue
        task_loc = world.get_location(f"Complete Task '{task.name}'")
        rule = True_()
        individual_requirements: set[SpeciesUtils.Species] = set()
        at_least_one_requirements = []
        for obj in task.get_required_species():
            req_set = SpeciesUtils.remove_later_evo_stages(obj)
            if len(req_set) == 1:
                creature = req_set.pop()
                if not creature in individual_requirements:
                    individual_requirements.add(creature)
            else:
                at_least_one_requirements.append(req_set)

        new_at_least_one_requirements = []

        if len(at_least_one_requirements) > 0:
            for req_set in at_least_one_requirements:
                if len(req_set & individual_requirements) == 0:
                    if all(len(req_set & s.get_priors()) == 0 for s in individual_requirements):
                        new_at_least_one_requirements.append(req_set)

        filtered_req_sets = []

        if len(new_at_least_one_requirements) > 0:
            new_at_least_one_requirements.sort(key=len, reverse=True)
            for s in new_at_least_one_requirements:
                if not any(s.issubset(already_added_set) for already_added_set in filtered_req_sets):
                    filtered_req_sets.append(s)

        for requirement in individual_requirements:
            rule = rule & Has(requirement.name) & CanAffordDP(requirement.cost * 3)
            if task.requires_species_satisfaction:

                # TODO: replace with a cleaner Satisfaction fxn
                suitable_biomes = requirement.get_suitable_biomes()
                if len(suitable_biomes) > 0:
                    biome_rule = False_()
                    for biome in suitable_biomes:
                        biome_rule = biome_rule | CanAccessBiome(biome, 50)
                    rule = rule & biome_rule
                if requirement.eats != "":
                    rule = rule & CanGetAtLeastOneDiet(requirement)
                if requirement.liked_species != "":
                    # Make sure that at least one liked species is accessible
                    reqs = SpeciesUtils.get_required_species_from_string(requirement.liked_species)
                    for spec_list in reqs:
                        extra_rule = False_()
                        for spec in spec_list:
                            extra_rule = extra_rule | (Has(spec.name) & CanAffordDP(spec.cost))
                        rule = rule & extra_rule

        for req_list in new_at_least_one_requirements:
            if len(req_list) == 0 or all(s is None for s in req_list):
                continue
            can_get_at_least_one_from_list = False_()
            for species in req_list:
                if species is None: continue

                if task.requires_species_satisfaction:
                    sat_rule = False_()
                    suitable_biomes = species.get_suitable_biomes()
                    found_something = False
                    if len(suitable_biomes) > 0:
                        biome_rule = False_()
                        for biome in suitable_biomes:
                            biome_rule = biome_rule | CanAccessBiome(biome, 50)
                        sat_rule = sat_rule & biome_rule
                        found_something = True
                    if species.eats != "":
                        sat_rule = sat_rule & CanGetAtLeastOneDiet(species)
                        found_something = True
                    if species.liked_species != "":
                        # Make sure that at least one liked species is accessible
                        reqs = SpeciesUtils.get_required_species_from_string(species.liked_species)
                        extra_rule = False_()
                        for spec_list in reqs:
                            for spec in spec_list:
                                extra_rule = extra_rule | (Has(spec.name) & CanAffordDP(spec.cost))
                        sat_rule = sat_rule & extra_rule
                        found_something = True
                    if not found_something:
                        sat_rule = True_()
                else:
                    sat_rule = True_()

                can_get_at_least_one_from_list = can_get_at_least_one_from_list | (Has(species.name) & CanAffordDP(species.cost * 3) & sat_rule)
            rule = rule & can_get_at_least_one_from_list

        completionist_rule = completionist_rule & CanReachLocation(f"Complete Task '{task.name}'")


        world.set_rule(task_loc, rule)

    if world.options.goal_selection != 0:
        completionist_loc = world.get_location(f"Complete Task 'Completionist'")
        world.set_rule(completionist_loc, completionist_rule)
    return completionist_rule



def set_completion_condition(world: EquilinoxWorld) -> None:
    world.set_completion_rule(Has("Victory"))

species_access_rules: dict[str, Rule] = {
    "Grass Tuft": Has("Grass Tuft Permit"),
    "Daisy": Has("Daisy Permit"),
    "Stones": Has("Stones Permit"),
    "Brown Stones": Has("Brown Stones Permit"),
    "Seaweed": Has("Seaweed Permit"),
    "Button Mushroom": Has("Button Mushroom Permit"),
    "Oak Tree": Has("Oak Tree Permit"),
    "Rosemary": Has("Rosemary Permit"),
    "Shell": Has("Shell Permit"),
    "Rock": Has("Rock Permit"),
    "Brown Rock": Has("Brown Rock Permit"),
    "Birch Tree": Has("Birch Tree Permit"),
    "Tall Tree": Has("Tall Tree Permit"),
    "Jungle Rocks": Has("Jungle Rocks Permit"),
    "Yucca": Has("Yucca Permit"),
    "Snow Rocks": Has("Snow Rocks Permit"),
    "Tomato Plant": Has("Tomato Plant Permit"),
    "Swamp Grass": Has("Swamp Grass Permit"),
    "Jungle Grass": Has("Jungle Grass Permit"),
    "Desert Rock": Has("Desert Rock Permit"),
    "Lush Grass": Has("Lush Grass Permit"),
    "Fir Tree": Has("Fir Tree Permit"),
    "Willow Tree": Has("Willow Tree Permit"),
    "Flowery Grass": Has("Flowery Grass Permit"),
    "Joshua Tree": Has("Joshua Tree Permit"),
    "Vine Tree": Has("Vine Tree Permit"),
    "Palm Tree": Has("Palm Tree Permit"),
    "Pink Tree": Has("Pink Tree Permit"),
    "Chicken": Has("Chicken Permit"),
    "Sheep": Has("Sheep Permit"),
    "Trout": Has("Trout Permit"),
    "Guinea Pig": Has("Guinea Pig Permit"),
    "Lizard": Has("Lizard Permit"),
    "Fox": Has("Fox Permit"),
    "Jellyfish": Has("Jellyfish Permit"),
    "Butterfly": Has("Butterfly Permit"),
    "Bear": Has("Bear Permit"),
    "Wheat":
        Has("Grass Tuft")
        & HasAny(
            "Brown Stones",
            "Stones",
        ),
    "Buttercup":
        Has("Daisy"),
    "Wild Mint":
        Has("Grass Tuft")
        & HasAny(
            "Tulip",
            "Wheat",
            "Daisy",
        ),
    "Tulip":
        Has("Daisy") &
        Has("Birch Tree"),
    "Oregano":
        Has("Grass Tuft") &
        Has("Button Mushroom"),
    "Kelp":
        Has("Seaweed")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Water Lily":
        Has("Seaweed") &
        Has("Trout")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Sage":
        Has("Rosemary") &
        Has("Tall Tree")
        & HasAny(
            "Brown Stones",
            "Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Heather":
        Has("Rosemary")
        & HasAny(
            "Prickly Pear",
            "Palm Tree",
            "Apple Tree",
            "Wheat",
            "Tomato Plant",
            "Witchwood Tree",
            "Nut Tree",
            "Barley",
        )
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Elm Tree":
        Has("Oak Tree")
        & HasAny(
            "Oregano",
            "Buttercup",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Red Maple Tree":
        Has("Birch Tree") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Sycamore Tree":
        Has("Oak Tree")
        & HasAny(
            "Swamp Flower",
            "Tropical Flower",
            "Primrose",
            "Heather",
            "Daisy",
            "Jungle Flower",
        )
        & HasAny(
            "Oregano",
            "Rosemary",
            "Wild Mint",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Juniper Tree":
        Has("Tall Tree") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Apple Tree":
        Has("Oak Tree")
        & HasAny(
            "Heather",
            "Sage",
            "Rosemary",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Fern":
        Has("Rosemary") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Pansies":
        Has("Daisy")
        & HasAny(
            "Heather",
            "Sage",
            "Rosemary",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Tropical Mushroom":
        Has("Button Mushroom")
        & HasAny(
            "Tropical Flower",
            "Flowery Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Cedar Tree":
        Has("Tall Tree") &
        Has("Rosemary")
        & HasAny(
            "Prickly Pear",
            "Palm Tree",
            "Apple Tree",
            "Wheat",
            "Tomato Plant",
            "Witchwood Tree",
            "Nut Tree",
            "Barley",
        )
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Wobbly Tree":
        Has("Birch Tree") &
        Has("Sheep")
        & HasAny(
            "Grass Tuft",
            "Wheat",
        )
        & HasFromListUnique(
            "Tulip",
            "Wheat",
            "Grass Tuft",
            "Daisy",
            "Wild Mint",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Spruce Tree":
        Has("Birch Tree") &
        Has("Fir Tree") &
        Has("Daisy")
        & HasAny(
            "Bluebell",
            "Holly Bush",
            "Fir Tree",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Small Cactus":
        Has("Yucca")
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        ),
    "Jungle Mushroom":
        Has("Button Mushroom")
        & HasAny(
            "Jungle Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus")
        & HasAny("Vine Tree", "Fir Tree", "Willow Tree"),
    "Jungle Flower":
        Has("Jungle Grass") &
        Has("Vine Tree")
        & HasAny(
            "Stones",
            "Brown Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Prickly Pear":
        Has("Yucca") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Red Mushroom":
        Has("Button Mushroom")
        & HasAny(
            "Willow Tree",
            "Slimy Tree",
            "Swamp Grass",
        ),
    "Turnip":
        Has("Willow Tree") &
        Has("Swamp Grass")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Berry Bush":
        Has("Tomato Plant")
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
            ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Tropical Flower":
        Has("Lizard") &
        Has("Flowery Grass"),
    "Jungle Plant":
        Has("Jungle Grass") &
        Has("Jungle Rocks"),
    "Leafy Plant":
        Has("Flowery Grass") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Primrose":
        Has("Lush Grass")
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Bulrush":
        Has("Swamp Grass")
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Slimy Tree":
        Has("Willow Tree")
        & HasAny(
            "Rock",
            "Brown Rock",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Red Tree":
        Has("Pink Tree") &
        Has("Lush Grass") &
        Has("Button Mushroom")
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        )
        & HasAny(
            "Willow Tree",
            "Slimy Tree",
            "Swamp Grass",
        )
        & HasAny(
            "Lush Grass",
            "Primrose",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Ficus Tree":
        Has("Vine Tree") &
        Has("Button Mushroom")
        & HasAny(
            "Jungle Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Pagoda Tree":
        Has("Birch Tree") &
        Has("Daisy")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Poppy",
            "Snap Dragon",
            "Sycamore Tree",
            "Oregano",
            "Buttercup",
            "Marigolds",
            "Elm Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Flower Tree":
        Has("Lizard") &
        Has("Palm Tree") &
        Has("Button Mushroom")
        & HasAny(
            "Tropical Flower",
            "Flowery Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Banana Tree":
        Has("Palm Tree") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Umbrella Tree":
        Has("Joshua Tree") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Redfish":
        Has("Seaweed") &
        Has("Trout")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Wild Boar":
        Has("Sheep")
        & HasAny(
            "Prickly Pear",
            "Palm Tree",
            "Apple Tree",
            "Wheat",
            "Tomato Plant",
            "Witchwood Tree",
            "Nut Tree",
            "Barley",
        )
        & (
            HasFromListUnique(
                "Elm Tree",
                "Oregano",
                "Snap Dragon",
                "Poppy",
                "Marigolds",
                "Buttercup",
                "Sycamore Tree",
                count=2
            )
            | HasFromListUnique(
                "Heather",
                "Sage",
                "Tall Tree",
                "Cedar Tree",
                "Rosemary",
                "Fern",
                "Juniper Tree",
                "Acer Tree",
                "Potato Plant",
            count=2
            )
        ),
    "Duck":
        Has("Chicken") &
        Has("Seaweed") &
        Has("Trout")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Salmon":
        Has("Seaweed") &
        Has("Trout")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Rabbit":
        Has("Oak Tree") &
        Has("Guinea Pig")
        & HasAny(
            "Swamp Flower",
            "Tropical Flower",
            "Primrose",
            "Heather",
            "Daisy",
            "Jungle Flower",
        )
        & HasAny(
            "Oregano",
            "Rosemary",
            "Wild Mint",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Poppy",
            "Snap Dragon",
            "Sycamore Tree",
            "Oregano",
            "Buttercup",
            "Marigolds",
            "Elm Tree",
            count=2
        ),
    "Sparrow":
        Has("Chicken") &
        Has("Tall Tree") &
        Has("Rosemary")
        & HasAny(
            "Prickly Pear",
            "Palm Tree",
            "Apple Tree",
            "Wheat",
            "Tomato Plant",
            "Witchwood Tree",
            "Nut Tree",
            "Barley",
        )
        & HasAny(
            "Rock",
            "Brown Rock",
            "Stones",
            "Brown Stones",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        ) & HasAny("Sheep", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Squirrel":
        Has("Oak Tree") &
        Has("Daisy") &
        Has("Guinea Pig")
        & HasAny(
            "Oregano",
            "Rosemary",
            "Wild Mint",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Poppy",
            "Snap Dragon",
            "Sycamore Tree",
            "Oregano",
            "Buttercup",
            "Marigolds",
            "Elm Tree",
            count=2
        ),
    "Deer":
        Has("Tomato Plant") &
        Has("Sheep")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Poppy",
            "Snap Dragon",
            "Sycamore Tree",
            "Oregano",
            "Buttercup",
            "Marigolds",
            "Elm Tree",
            count=2
        ),
    "Goat":
        Has("Sheep")
        & HasAny(
            "Bluebell",
            "Spruce Tree",
            "Holly Bush",
            "Fir Tree",
        ),
    "Frog":
        Has("Lizard")
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Plant",
            "Jungle Grass",
            "Ficus Tree",
            "Vine Tree",
            "Jungle Flower",
            count=2
        ),
    "Turtle":
        Has("Seaweed") &
        Has("Lizard") &
        Has("Flowery Grass")
        & HasAny(
            "Rock",
            "Brown Rock",
        )
        & HasAny(
            "Tropical Flower",
            "Flowery Grass",
        ),
    "Fly":
        Has("Willow Tree") &
        Has("Swamp Grass") &
        Has("Butterfly") &
        Has("Button Mushroom")
        & HasAny(
            "Rock",
            "Brown Rock",
        ),
    "Bee":
        Has("Daisy") &
        Has("Butterfly")
        & Has("Poppy")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Snap Dragon",
            "Sycamore Tree",
            "Oregano",
            "Buttercup",
            "Marigolds",
            "Elm Tree",
            count=1
        ),
    "Wolf":
        Has("Snow Rocks") &
        Has("Fox") & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Bluebell":
        Has("Birch Tree") &
        Has("Daisy")
        & HasAny(
            "Fir Tree",
            "Spruce Tree",
            "Holly Bush",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Barley":
        Has("Tall Tree") &
        Has("Rosemary")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        ),
    "Tropical Seaweed":
        Has("Seaweed")
        & HasAny(
            "Rock",
            "Brown Rock",
        )
        & HasAny(
            "Flowery Grass",
            "Tropical Flower",
        ),
    "Poppy":
        Has("Daisy")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Lily":
        Has("Daisy")
        & HasAny(
            "Heather",
            "Sage",
            "Rosemary",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Snap Dragon":
        Has("Guinea Pig") &
        Has("Daisy"),
    "Carrot":
        Has("Guinea Pig") &
        Has("Oak Tree") &
        Has("Grass Tuft")
        & HasAny(
            "Heather",
            "Daisy",
            "Swamp Flower",
            "Primrose",
            "Jungle Flower",
            "Tropical Flower",
        )
        & HasAny(
            "Wild Mint",
            "Rosemary",
            "Oregano",
        )
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Daisy",
            "Grass Tuft",
            "Wheat",
            "Wild Mint",
            "Tulip",
            count=3
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Progressive DP/Min Bonus"),
    "Potato Plant":
        Has("Sheep") &
        Has("Tall Tree") &
        Has("Rosemary")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Heather",
            "Sage",
            "Rosemary",
        )
        & HasFromListUnique(
            "Heather",
            "Sage",
            "Tall Tree",
            "Cedar Tree",
            "Rosemary",
            "Fern",
            "Juniper Tree",
            "Acer Tree",
            count=2
        ) & HasAny("Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Rose":
        Has("Birch Tree") &
        Has("Daisy")
        & HasAny(
            "Oregano",
            "Buttercup",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig"),
    "Holly Bush":
        Has("Tomato Plant") &
        HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Tall Mushroom":
        Has("Button Mushroom")
        & HasAny(
            "Primrose",
            "Lush Grass",
        )
        & HasAny(
            "Slimy Tree",
            "Willow Tree",
            "Swamp Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Medium Cactus":
        Has("Yucca") &
        Has("Joshua Tree")
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Nut Tree":
        Has("Guinea Pig") &
        Has("Oak Tree") &
        Has("Daisy")
        & HasAny(
            "Wild Mint",
            "Rosemary",
            "Oregano",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Progressive DP/Min Bonus"),
    "Acer Tree":
        Has("Sheep") &
        Has("Tall Tree") &
        Has("Rosemary")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        ) & HasAny("Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Ash Tree":
        Has("Oak Tree")
        & HasAny(
            "Heather",
            "Daisy",
            "Swamp Flower",
            "Primrose",
            "Jungle Flower",
            "Tropical Flower",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Bromeliad":
        Has("Lizard") &
        Has("Flowery Grass") &
        Has("Butterfly"),
    "Blueberry Bush":
        Has("Tomato Plant") &
        Has("Butterfly") &
        Has("Daisy")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Swamp Flower":
        Has("Lizard") &
        Has("Swamp Grass")
        & HasAny(
            "Rock",
            "Brown Rock",
        )
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Grass",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Flower",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Bamboo":
        Has("Button Mushroom") &
        Has("Lush Grass")
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Primrose",
            "Lush Grass",
        )
        & HasAny(
            "Slimy Tree",
            "Willow Tree",
            "Swamp Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Healbloom":
        Has("Lizard") &
        Has("Flowery Grass") &
        HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Eucalyptus Tree":
        Has("Birch Tree") &
        Has("Butterfly") &
        HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Canopy Tree":
        Has("Lizard") &
        Has("Button Mushroom") &
        Has("Vine Tree")
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Grass",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Flower",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Orange Tree":
        Has("Palm Tree") &
        Has("Flowery Grass") &
        Has("Butterfly") &
        Has("Button Mushroom") &
        Has("Lizard")
        & HasAny(
            "Flowery Grass",
            "Tropical Flower",
        )
        & HasFromListUnique(
            "Flowery Grass",
            "Coral",
            "Leafy Plant",
            "Tropical Seaweed",
            "Tropical Flower",
            "Bromeliad",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Autumnal Tree":
        Has("Guinea Pig") &
        Has("Birch Tree") &
        Has("Sheep")
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Daisy",
            "Grass Tuft",
            "Wheat",
            "Wild Mint",
            "Tulip",
            count=2
        ),
    "Mango Tree":
        Has("Palm Tree") &
        Has("Daisy") &
        Has("Butterfly") &
        Has("Button Mushroom") &
        Has("Lizard")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        )
        & HasAny(
            "Flowery Grass",
            "Tropical Flower",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Pine Tree":
        Has("Birch Tree") &
        Has("Fir Tree") &
        Has("Daisy")
        & HasAny(
            "Guinea Pig",
            "Sheep",
            "Bear",
        )
        & HasAny(
            "Fir Tree",
            "Spruce Tree",
            "Bluebell",
            "Holly Bush",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Witchwood Tree":
        Has("Vine Tree") &
        Has("Butterfly") &
        Has("Button Mushroom") &
        Has("Jungle Grass")
        & HasAny(
            "Brown Stones",
            "Stones",
        )
        & HasAny(
            "Jungle Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Starbloom Bush":
        Has("Jungle Grass") &
        Has("Tall Tree") &
        Has("Vine Tree") &
        Has("Chicken") &
        Has("Jungle Rocks") &
        Has("Button Mushroom") &
        Has("Rosemary") &
        Has("Lizard")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Grass",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Flower",
            count=2
        ),
    "Dead Tree":
        Has("Sheep") &
        Has("Tall Tree") &
        Has("Willow Tree") &
        Has("Rosemary") &
        Has("Lizard")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Slimy Tree",
            "Willow Tree",
            "Swamp Grass",
        )
        & HasFromListUnique(
            "Red Mushroom",
            "Slimy Tree",
            "Swamp Grass",
            "Swamp Flower",
            "Willow Tree",
            count=2
        )
        & HasAny(
            "Heather",
            "Sage",
            "Rosemary",
        )
        & HasFromListUnique(
            "Potato Plant",
            "Heather",
            "Sage",
            "Tall Tree",
            "Cedar Tree",
            "Rosemary",
            "Fern",
            "Juniper Tree",
            "Acer Tree",
            count=2
        )
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Grass",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Flower",
            count=2
        ),
    "Spiral Tree":
        Has("Lizard") &
        Has("Pink Tree") &
        Has("Button Mushroom") &
        Has("Lush Grass")
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Primrose",
            "Lush Grass",
        )
        & HasAny(
            "Slimy Tree",
            "Willow Tree",
            "Swamp Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Cherry Tree":
        Has("Pink Tree") &
        Has("Button Mushroom") &
        Has("Lush Grass")
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Guinea Pig",
            "Sheep",
            "Bear",
        )
        & HasAny(
            "Primrose",
            "Lush Grass",
        )
        & HasFromListUnique(
            "Red Tree",
            "Primrose",
            "Pink Tree",
            "Bamboo",
            "Lush Grass",
            count=2
        )
        & HasAny(
            "Slimy Tree",
            "Willow Tree",
            "Swamp Grass",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Clown Fish":
        Has("Trout") &
        Has("Seaweed")
        & HasAny(
            "Rock",
            "Brown Rock",
        )
        & HasAny(
            "Flowery Grass",
            "Tropical Flower",
        ),
    "Angel Fish":
        Has("Trout") &
        Has("Seaweed")
        & HasAny(
            "Rock",
            "Brown Rock",
        )
        & HasAny(
            "Flowery Grass",
            "Tropical Flower",
        ) & HasAny("Sheep", "Chicken", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Desert Hare":
        Has("Guinea Pig") &
        Has("Oak Tree") &
        Has("Grass Tuft")
        & HasAny(
            "Heather",
            "Daisy",
            "Swamp Flower",
            "Primrose",
            "Jungle Flower",
            "Tropical Flower",
        )
        & HasAny(
            "Wild Mint",
            "Rosemary",
            "Oregano",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        )
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Daisy",
            "Grass Tuft",
            "Wheat",
            "Wild Mint",
            "Tulip",
            count=3
        ) & HasAny("Sheep", "Chicken", "Trout", "Progressive DP/Min Bonus"),
    "Royal Gramma":
        Has("Trout") &
        Has("Seaweed")
        & HasAny(
            "Rock",
            "Brown Rock",
        ) & HasAny("Sheep", "Chicken", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Warthog":
        Has("Sheep") &
        Has("Tall Tree") &
        Has("Rosemary")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Heather",
            "Sage",
            "Rosemary",
        )
        & HasFromListUnique(
            "Potato Plant",
            "Heather",
            "Sage",
            "Tall Tree",
            "Cedar Tree",
            "Rosemary",
            "Fern",
            "Juniper Tree",
            "Acer Tree",
            count=2
        ) & HasAny("Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Pike":
        Has("Seaweed") &
        Has("Trout") &
        Has("Swamp Grass")
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        ) & HasAny("Sheep", "Chicken", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Eagle":
        Has("Daisy") &
        Has("Birch Tree") &
        Has("Tall Tree") &
        Has("Chicken") &
        Has("Rosemary") &
        Has("Fir Tree")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasAny(
            "Fir Tree",
            "Spruce Tree",
            "Bluebell",
            "Holly Bush",
        ) & HasAny("Sheep", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Toad":
        Has("Lizard")
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Grass",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Flower",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Toucan":
        Has("Tall Tree") &
        Has("Vine Tree") &
        Has("Chicken") &
        Has("Button Mushroom") &
        Has("Rosemary") &
        Has("Lizard")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Grass",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Flower",
            count=2
        ),
    "Dove":
        Has("Tall Tree") &
        Has("Rosemary") &
        Has("Lush Grass") &
        Has("Chicken")
        & HasAny(
            "Tomato Plant",
            "Barley",
            "Palm Tree",
            "Apple Tree",
            "Witchwood Tree",
            "Wheat",
            "Prickly Pear",
            "Nut Tree",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        ) & HasAny("Sheep", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Peacock":
        Has("Daisy") &
        Has("Chicken") &
        Has("Trout") &
        Has("Butterfly") &
        Has("Seaweed")
        & HasAny(
            "Rock",
            "Brown Rock",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ),
    "Beaver":
        Has("Swamp Grass") &
        Has("Birch Tree") &
        Has("Sheep") &
        Has("Guinea Pig") &
        Has("Oak Tree")
        & HasAny(
            "Heather",
            "Daisy",
            "Swamp Flower",
            "Primrose",
            "Jungle Flower",
            "Tropical Flower",
        )
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Wild Mint",
            "Rosemary",
            "Oregano",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        )
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Daisy",
            "Grass Tuft",
            "Wheat",
            "Wild Mint",
            "Tulip",
            count=2
        ),
    "Camel":
        Has("Tomato Plant") &
        Has("Swamp Grass") &
        Has("Daisy") &
        Has("Birch Tree") &
        Has("Sheep") &
        Has("Butterfly") &
        Has("Guinea Pig") &
        Has("Oak Tree")
        & HasAny(
            "Brown Stones",
            "Rock",
            "Stones",
            "Brown Rock",
        )
        & HasAny(
            "Wild Mint",
            "Rosemary",
            "Oregano",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Elm Tree",
            "Oregano",
            "Snap Dragon",
            "Poppy",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        )
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Daisy",
            "Grass Tuft",
            "Wheat",
            "Wild Mint",
            "Tulip",
            count=2
        ),
    "Desert Grass":
        Has("Rosemary") &
        Has("Desert Rock") &
        Has("Tall Tree")
        & HasAny(
            "Palm Tree",
            "Wheat",
            "Apple Tree",
            "Tomato Plant",
            "Barley",
            "Prickly Pear",
            "Nut Tree",
            "Witchwood Tree",
        )
        & HasAny(
            "Brown Rock",
            "Brown Stones",
            "Rock",
            "Stones",
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Coral":
        Has("Trout") &
        Has("Seaweed") &
        Has("Shell")
        & HasAny(
            "Brown Rock",
            "Rock",
        )
        & HasAny(
            "Tropical Flower",
            "Flowery Grass",
        ) & HasAny("Sheep", "Chicken", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Marigolds":
        Has("Daisy") &
        Has("Oak Tree") &
        Has("Guinea Pig")
        & HasAny(
            "Rosemary",
            "Oregano",
            "Wild Mint",
        )
        & HasAny(
            "Rosemary",
            "Sage",
            "Heather",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Snap Dragon",
            "Poppy",
            "Elm Tree",
            "Oregano",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Progressive DP/Min Bonus"),
    "Sunflower":
        Has("Daisy")
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Snap Dragon",
            "Poppy",
            "Elm Tree",
            "Oregano",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Fly Trapper":
        Has("Willow Tree") &
        Has("Swamp Grass") &
        Has("Button Mushroom") &
        Has("Butterfly") &
        Has("Lizard")
        & HasAny(
            "Brown Rock",
            "Brown Stones",
            "Rock",
            "Stones",
        )
        & HasAny(
            "Jungle Grass",
        )
        & HasFromListUnique(
            "Jungle Flower",
            "Vine Tree",
            "Jungle Plant",
            "Ficus Tree",
            "Jungle Grass",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Large Tree":
        Has("Rosemary") &
        Has("Sheep") &
        Has("Tall Tree")
        & HasAny(
            "Palm Tree",
            "Wheat",
            "Apple Tree",
            "Tomato Plant",
            "Barley",
            "Prickly Pear",
            "Nut Tree",
            "Witchwood Tree",
        )
        & HasAny(
            "Brown Rock",
            "Brown Stones",
            "Rock",
            "Stones",
        ) & HasAny("Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Giant Cactus":
        Has("Grass Tuft") &
        Has("Guinea Pig") &
        Has("Yucca") &
        Has("Oak Tree") &
        Has("Joshua Tree")
        & HasAny(
            "Jungle Flower",
            "Swamp Flower",
            "Heather",
            "Tropical Flower",
            "Daisy",
            "Primrose",
        )
        & HasAny(
            "Brown Rock",
            "Brown Stones",
            "Rock",
            "Stones",
        )
        & HasAny(
            "Rosemary",
            "Oregano",
            "Wild Mint",
        )
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Wild Mint",
            "Wheat",
            "Grass Tuft",
            "Daisy",
            "Tulip",
            count=3
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Snap Dragon",
            "Poppy",
            "Elm Tree",
            "Oregano",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        ) & HasAny("Sheep", "Chicken", "Trout", "Progressive DP/Min Bonus"),
    "Neon Fish":
        Has("Seaweed") &
        Has("Trout") &
        Has("Lizard") &
        Has("Shell")
        & HasAny(
            "Brown Rock",
            "Rock",
        )
        & HasAny(
            "Tropical Flower",
            "Flowery Grass",
        ) & HasAny("Sheep", "Chicken", "Guinea Pig", "Progressive DP/Min Bonus"),
    "Meerkat":
        Has("Desert Rock") &
        Has("Rosemary") &
        Has("Grass Tuft") &
        Has("Guinea Pig") &
        Has("Oak Tree") &
        Has("Tall Tree")
        & HasAny(
            "Palm Tree",
            "Wheat",
            "Apple Tree",
            "Tomato Plant",
            "Barley",
            "Prickly Pear",
            "Nut Tree",
            "Witchwood Tree",
        )
        & HasAny(
            "Jungle Flower",
            "Swamp Flower",
            "Heather",
            "Tropical Flower",
            "Daisy",
            "Primrose",
        )
        & HasAny(
            "Brown Rock",
            "Brown Stones",
            "Rock",
            "Stones",
        )
        & HasAny(
            "Oregano",
            "Buttercup",
        )
        & HasFromListUnique(
            "Snap Dragon",
            "Poppy",
            "Elm Tree",
            "Oregano",
            "Marigolds",
            "Buttercup",
            "Sycamore Tree",
            count=2
        )
        & HasAny(
            "Wheat",
            "Grass Tuft",
        )
        & HasFromListUnique(
            "Wild Mint",
            "Wheat",
            "Grass Tuft",
            "Daisy",
            "Tulip",
            count=3
        ) & HasAny("Sheep", "Chicken", "Trout", "Progressive DP/Min Bonus"),
    "Dolphin":
        Has("Trout") &
        Has("Swamp Grass") &
        Has("Seaweed")
        & HasAny(
            "Brown Rock",
            "Brown Stones",
            "Rock",
            "Stones",
        )
        & HasAny(
            "Tropical Flower",
            "Flowery Grass",
        )
        & HasAny("Sheep", "Chicken", "Guinea Pig", "Progressive DP/Min Bonus"),
}


@dataclasses.dataclass()
class CanAffordDP(Rule['EquilinoxWorld'], game="Equilinox"):

    def __init__(self, dp: int, options: typing.Iterable[OptionFilter] = (), filtered_resolution: bool = False):
        super().__init__(options=options, filtered_resolution=filtered_resolution)
        self.dp = dp

    @typing.override
    def _instantiate(self, world: 'EquilinoxWorld') -> Rule.Resolved:
        if self.dp <= 2500: return True_().resolve(world)
        return self.Resolved(self.dp, world, player=world.player)

    class Resolved(Rule.Resolved):
        dp: int
        world: EquilinoxWorld

        @override
        def explain_json(self, state: CollectionState | None = None) -> list[JSONMessagePart]:
            can_afford = state and _can_afford_dp(self.world, self.dp, state)
            color = "yellow"
            start = "(This text shouldn't be visible) "
            if can_afford and self.dp <= 10000:
                start = "Received at least "
                color = "green"
            elif can_afford and self.dp <= 60000:
                start = "Received at least one source of DP/min to afford "
                color = "green"
            elif can_afford:
                start = "Received at least two sources of DP/min to afford "
                color = "green"
            elif state is not None:
                if self.dp <= 10000:
                    start = "Haven't received at least "
                elif self.dp <= 60000:
                    start = "Haven't received at least one source of DP/min to afford "
                else:
                    start = "Haven't received at least two sources of DP/min to afford "
                color = "salmon"
            return [
                {"type": "text", "text": start},
                {"type": "color", "color": color, "text": str(self.dp)},
                {"type": "text", "text": " DP"},
            ]

        @override
        def explain_str(self, state: CollectionState | None = None) -> str:
            if state is None:
                return str(self)
            if _can_afford_dp(self.world, self.dp, state):
                return f"Received at least {self.dp} DP (and/or enough to generate it)"
            return f"Have not received at least {self.dp} DP (and/or enough to generate it)"

        @override
        def __str__(self) -> str:
            return f"Receive at least {self.dp} dp (or generators, for higher amounts)"


        @typing.override
        def _evaluate(self, state: CollectionState) -> bool:
            #print(f"Can afford called with {self.dp}")
            return _can_afford_dp(self.world, self.dp, state)

def _can_afford_dp(world: EquilinoxWorld, target: int, state: CollectionState) -> bool:

    if target > 60000:
        return (state.has_from_list_unique(["Sheep", "Chicken", "Trout", "Guinea Pig"], world.player, 2)
                or state.has("Progressive DP/Min Bonus", world.player, count=5)
                or (state.has("Progressive DP/Min Bonus", world.player, count=3)
                    and state.has_any(["Sheep", "Chicken", "Trout", "Guinea Pig"], world.player)))
    elif target > 10000:
        return (state.has_any(["Sheep", "Chicken", "Trout", "Guinea Pig"], world.player)
                or state.has("Progressive DP/Min Bonus", world.player, count=2))

    return state.has_any(["50,000 dp", "75,000 dp", "100,000 dp", "250,000 dp",
                          "Sheep", "Chicken", "Trout", "Guinea Pig", "Progressive DP/Min Bonus"], world.player)


@dataclasses.dataclass()
class CanAccessBiome(Rule['EquilinoxWorld'], game="Equilinox"):
    def __init__(self, biome: str, percent: int, options: typing.Iterable[OptionFilter] = (), filtered_resolution: bool = False):
        super().__init__(options=options, filtered_resolution=filtered_resolution)
        self.biome = biome
        self.percent = percent

    @typing.override
    def _instantiate(self, world: 'EquilinoxWorld') -> Rule.Resolved:
        if self.percent <= 0: return True_().resolve(world)

        good_spreaders = SpeciesUtils.get_spreaders(self.biome, True)
        has_any_good_spreaders = False_()

        for species in good_spreaders:
            has_any_good_spreaders = has_any_good_spreaders | Has(species.name)

        if self.percent > 85:
            return (has_any_good_spreaders & HasGroupUnique(self.biome, count=3)).resolve(world)
        if self.percent > 55:
            return (has_any_good_spreaders & HasGroupUnique(self.biome, count=2)).resolve(world)

        else: return has_any_good_spreaders.resolve(world)


@dataclasses.dataclass()
class CanGetAtLeastOneDiet(Rule['EquilinoxWorld'], game="Equilinox"):
    def __init__(self, species: SpeciesUtils.Species, options: typing.Iterable[OptionFilter] = (), filtered_resolution: bool = False):
        super().__init__(options=options, filtered_resolution=filtered_resolution)
        self.species = species

    @typing.override
    def _instantiate(self, world: 'EquilinoxWorld') -> Rule.Resolved:
        if self.species.eats == "": return True_().resolve(world)
        diet = self.species.get_diet()
        diet = SpeciesUtils.remove_later_evo_stages(diet)
        rule = False_()
        for food in diet:
            rule = rule | ( Has(food.name) & CanAffordDP(food.cost) )
        return rule.resolve(world)