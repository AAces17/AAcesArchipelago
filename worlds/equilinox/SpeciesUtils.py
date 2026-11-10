from __future__ import annotations

import json
import pkgutil

from . import Evolution

class Species:
    def __init__(self,
                 is_plant: bool,
                 name: str,
                 evolution_stage: int,
                 previous_evolution: str,
                 evolution_requirements: list[Evolution.EvolutionRequirement],
                 cost: int,
                 dp_earn: int,
                 spreads: str,
                 suitable_biomes: str,
                 unsuitable_biomes: str,
                 liked_species: str,
                 disliked_species: str,
                 preferred_altitude: str,
                 eats: str,
                 id: int):
        self.is_plant = is_plant
        self.name = name
        self.evolution_stage = evolution_stage
        self.previous_evolution = previous_evolution
        self.evolution_requirements = evolution_requirements
        self.cost = cost
        self.dp_earn = dp_earn
        self.spreads = spreads
        self.suitable_biomes = suitable_biomes
        self.unsuitable_biomes = unsuitable_biomes
        self.liked_species = liked_species
        self.disliked_species = disliked_species
        self.preferred_altitude = preferred_altitude
        self.eats = eats
        self.id = id

    def spreads_biome(self, biome: str) -> bool:
        return self.spreads == biome

    def get_priors(self) -> set[Species]:
        return get_all_priors(self)

    def get_children(self) -> set[Species]:
        return get_children(self)

    def get_suitable_biomes(self) -> list[str]:
        if self.suitable_biomes == "": return []
        return self.suitable_biomes.split(";")

    def get_previous_evolution(self) -> Species | None:
        return get_species_from_name(self.previous_evolution)

    def get_base(self) -> Species:
        if self.is_base_species(): return self
        s = self.get_previous_evolution()
        assert s is not None
        while not s.is_base_species(): s = s.get_previous_evolution()
        assert s is not None
        return s

    def get_diet(self) -> set[Species]:
        if self.eats == "": return set()
        diet = get_required_species_from_string(self.eats)
        one_list = set()
        for list in diet:
            for item in list:
                if item not in one_list:
                    one_list.add(item)
        return one_list

    def is_base_species(self) -> bool:
        return self.evolution_stage == 1

    def __eq__(self, other: Species) -> bool:
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

def get_species_from_name(name: str) -> Species | None:
    for species in all_species:
        if species.name == name:
            return species
    return None

def get_spreaders(biome: str, only_ideal: bool = False) -> set[Species]:
    spreaders = set()
    for species in get_species_from_category("Plants"):
        if species.spreads_biome(biome):
            if not only_ideal:
                spreaders.add(species)
            elif "Barren" in species.get_suitable_biomes() or len(species.get_suitable_biomes()) == 0 or "Barren Land" in species.get_suitable_biomes():
                spreaders.add(species)
    return spreaders

def get_species_evo_tree(species: Species) -> set[Species]:
    s_set = get_all_priors(species)
    s_set.add(species)

    for s in all_species:
        if s in s_set or s.is_base_species() or s.is_plant != species.is_plant: continue
        if s.get_previous_evolution() in s_set:
            s_set.add(s)
    for s in all_species:
        if s in s_set or s.is_base_species() or s.is_plant != species.is_plant: continue
        if s.get_previous_evolution() in s_set:
            s_set.add(s)
    for s in all_species:
        if s in s_set or s.is_base_species() or s.is_plant != species.is_plant: continue
        if s.get_previous_evolution() in s_set:
            s_set.add(s)
    return s_set

def get_all_priors(species: Species) -> set[Species]:
    s_set = set()
    s = species
    while s.evolution_stage != 1:
        s = s.get_previous_evolution()
        s_set.add(s)
    return s_set

def remove_later_evo_stages(species_set: set[Species | None]) -> set[Species]:
    new_set = set()

    for s in species_set:
        if s is None: continue
        priors = get_all_priors(s)
        if not any(sp in species_set for sp in priors):
            new_set.add(s)

    return new_set

def get_children(species: Species) -> set[Species]:
    children = set()
    for s in all_species:
        if species in get_all_priors(s):
            children.add(s)
    return children

def get_species_from_category(cat: str) -> set[Species]:
    list_set = set()
    match cat:
        case "Animals":
            return {s for s in all_species if not s.is_plant}
        case "Plants":
            return {s for s in all_species if s.is_plant}
        case "Trees":
            return (get_species_from_category("Forest Trees") |
                    get_species_from_category("Grassland Trees") |
                    get_species_from_category("Woodland Trees") |
                    get_species_from_category("Lush Trees") |
                    get_species_from_category("Desert Trees") |
                    get_species_from_category("Mountain Trees") |
                    get_species_from_category("Swamp Trees") |
                    get_species_from_category("Jungle Trees") |
                    get_species_from_category("Tropical Trees"))
        case "Forest Trees":
            list_set = {"Tall Tree",
                        "Juniper Tree",
                        "Cedar Tree",
                        "Acer Tree",
                        "Large Tree"
                        }
        case "Grassland Trees":
            list_set = {"Birch Tree",
                        "Red Maple Tree",
                        "Wobbly Tree",
                        "Pagoda Tree",
                        "Eucalyptus Tree",
                        "Autumnal Tree"
                        }
        case "Woodland Trees":
            list_set = {"Oak Tree",
                        "Elm Tree",
                        "Sycamore Tree",
                        "Apple Tree",
                        "Nut Tree",
                        "Ash Tree"
                        }
        case "Lush Trees":
            list_set = {"Red Tree",
                        "Pink Tree",
                        "Spiral Tree",
                        "Cherry Tree"
                        }
        case "Desert Trees":
            list_set = {"Joshua Tree",
                        "Umbrella Tree"
                        }
        case "Mountain Trees":
            list_set = {"Spruce Tree",
                        "Fir Tree",
                        "Pine Tree"
                        }
        case "Swamp Trees":
            list_set = {"Willow Tree",
                        "Slimy Tree",
                        "Dead Tree"
                        }
        case "Jungle Trees":
            list_set = {"Vine Tree",
                        "Ficus Tree",
                        "Canopy Tree",
                        "Witchwood Tree"
                        }
        case "Tropical Trees":
            list_set = {"Palm Tree",
                        "Flower Tree",
                        "Banana Tree",
                        "Orange Tree",
                        "Mango Tree"
                        }
        case "Bushes":
            return (get_species_from_category("Fruit Bushes") |
                    get_species_from_category("Leafy Bushes"))
        case "Fruit Bushes":
            list_set = {"Tomato Plant",
                        "Berry Bush",
                        "Holly Bush",
                        "Blueberry Bush"
                        }
        case "Leafy Bushes":
            list_set = {"Jungle Plant",
                        "Leafy Plant",
                        "Bromeliad",
                        "Bamboo",
                        "Starbloom Bush"
                        }
        case "Cacti":
            list_set = {"Yucca",
                        "Small Cactus",
                        "Prickly Pear",
                        "Medium Cactus",
                        "Giant Cactus"
                        }
        case "Rocks/Stones":
            return (get_species_from_category("Stones") |
                    get_species_from_category("Large Rocks"))
        case "Stones":
            list_set = {"Stones",
                        "Brown Stones",
                        #"Shell"
                        }
        case "Large Rocks":
            list_set = {"Rock",
                        "Brown Rock",
                        #"Jungle Rocks",
                        #"Snow Rocks",
                        #"Desert Rock"
                        }
        case "Small Plants":
            return (get_species_from_category("Water Plants") |
                    get_species_from_category("Grasses") |
                    get_species_from_category("Vegetables") |
                    get_species_from_category("Ferns") |
                    get_species_from_category("Flowers") |
                    get_species_from_category("Herbs") |
                    get_species_from_category("Mushrooms"))
        case "Water Plants":
            list_set = {"Seaweed",
                        "Kelp",
                        "Water Lily",
                        "Tropical Seaweed",
                        "Coral",
                        "Bulrush"
                        }
        case "Grasses":
            list_set = {"Grass Tuft",
                        "Wheat",
                        "Barley",
                        "Swamp Grass",
                        "Desert Grass",
                        "Jungle Grass",
                        "Lush Grass",
                        "Flowery Grass"
                        }
        case "Vegetables":
            return (get_species_from_category("Root Vegetables") |
                    get_species_from_category("Vegetable Plant"))
        case "Root Vegetables":
            list_set = {"Carrot",
                        "Potato Plant",
                        "Turnip"
                        }
        case "Vegetable Plant": # This category exists in game but has nothing in it
            list_set = set()
        case "Ferns":
            list_set = {"Fern"}
        case "Flowers":
            list_set = {"Daisy",
                        "Buttercup",
                        "Tulip",
                        "Heather",
                        "Pansies",
                        "Bluebell",
                        "Poppy",
                        "Lily",
                        "Snap Dragon",
                        "Jungle Flower",
                        "Rose",
                        "Marigolds",
                        "Tropical Flower",
                        "Sunflower",
                        "Primrose",
                        "Swamp Flower",
                        "Healbloom",
                        "Fly Trapper"
                        }
        case "Herbs":
            list_set = {"Wild Mint",
                        "Oregano",
                        "Rosemary",
                        "Sage"
                        }
        case "Mushrooms":
            list_set = {"Button Mushroom",
                        "Tropical Mushroom",
                        "Jungle Mushroom",
                        "Red Mushroom",
                        "Tall Mushroom"
                        }
        case "Fish":
            return (get_species_from_category("Small Fish") |
                    get_species_from_category("Big Fish") |
                    get_species_from_category("Weird Fish"))
        case "Small Fish":
            list_set = {"Trout",
                        "Redfish",
                        "Salmon",
                        "Clown Fish",
                        "Angel Fish",
                        "Royal Gramma",
                        "Neon Fish"
                        }
        case "Big Fish":
            list_set = {"Pike",
                        "Dolphin"
                        }
        case "Weird Fish":
            list_set = {"Jellyfish"}
        case "Insects":
            list_set = {"Fly",
                        "Butterfly",
                        "Bee"
                        }
        case "Reptiles":
            list_set = {"Lizard",
                        "Frog",
                        "Turtle",
                        "Toad"
                        }
        case "Herbivores":
            return (get_species_from_category("Large Herbivores") |
                    get_species_from_category("Medium Herbivores") |
                    get_species_from_category("Small Herbivores"))
        case "Large Herbivores":
            list_set = {"Bear", "Camel"}
        case "Medium Herbivores":
            list_set = {"Sheep",
                        "Wild Boar",
                        "Deer",
                        "Goat",
                        "Warthog"
                        }
        case "Small Herbivores":
            list_set = {"Guinea Pig",
                        "Rabbit",
                        "Squirrel",
                        "Desert Hare",
                        "Meerkat",
                        "Beaver"
                        }
        case "Birds":
            return (get_species_from_category("Small Birds") |
                    get_species_from_category("Birds of Prey"))
        case "Small Birds":
            list_set = {"Chicken",
                        "Duck",
                        "Sparrow",
                        "Toucan",
                        "Dove",
                        "Peacock"
                        }
        case "Birds of Prey":
            list_set = {"Eagle"}
        case "Carnivores":
            return (get_species_from_category("Small Carnivores") |
                    get_species_from_category("Large Carnivores"))
        case "Small Carnivores":
            list_set = {"Fox"}
        case "Large Carnivores":
            list_set = {"Wolf"}
        case "Fallen Fruit":
            list_set = {"Tomato Plant",
                        "Berry Bush",
                        "Holly Bush",
                        "Blueberry Bush",
                        "Apple Tree",
                        "Banana Tree",
                        "Orange Tree",
                        "Mango Tree",
                        "Prickly Pear",
                        "Nut Tree",
                        "Wheat",
                        "Barley",
                        "Desert Grass",
                        "Palm Tree",
                        "Witchwood Tree"
                        }
        case "Nuts":
            list_set = {"Nut Tree"}
        case _:
            raise ValueError(f"Equilinox: Invalid species category: \"{cat}\"")

    species_list = {get_species_from_name(s) for s in list_set}
    if any(s is None for s in species_list): raise ValueError(f"Equilinox: Species category {cat} got a None species")
    return {s for s in species_list if s is not None}

def get_required_species_from_string(string: str) -> list[set[Species]]:
    if string == "" or string is None:
        return []
    required : list[set[Species]] = []
    species_list = string.split(";")
    for species in species_list:
        species = species.split(" (")[0]
        s = get_species_from_name(species)
        if s is not None:
            if species == "Stones":
                required.append(get_species_from_category("Stones"))
            else:
                required.append({s})
        elif species == "Hive" or species == "Honey":
            s = get_species_from_name("Bee")
            assert s is not None
            required.append({s})
            required.append(get_species_from_category("Flowers"))
        elif species == "Beaver Lodge":
            s = get_species_from_name("Beaver")
            assert s is not None
            required.append({s})
            required.append(get_species_from_category("Trees"))
        elif species == "Nest":
            s = get_species_from_name("Sparrow")
            t1 = get_species_from_name("Oak Tree")
            t2 = get_species_from_name("Birch Tree")
            assert s is not None
            assert t1 is not None
            assert t2 is not None
            required.append({s})
            required.append({t1, t2})
        else:
            required.append(get_species_from_category(species))
    return required

def get_evolution_reqs_from_json(e_obj, plant: bool) -> list[Evolution.EvolutionRequirement]:
    reqs = []

    if e_obj["color"] != "":
        reqs.append(Evolution.ColorRequirement(e_obj["color"]))

    if e_obj["nearby_species"] != "":
        reqs.append(Evolution.NearbySpeciesRequirement(e_obj["nearby_species"]))

    if e_obj["satisfaction"] != 0:
        reqs.append(Evolution.SatisfactionRequirement(e_obj["satisfaction"]))

    if e_obj["size"] != 0:
        reqs.append(Evolution.SizeRequirement(e_obj["size"]))

    if e_obj["biome"] != "":
        reqs.append(Evolution.BiomeRequirement(e_obj["biome"]))

    if e_obj["altitude"] != "":
        reqs.append(Evolution.AltitudeRequirement(e_obj["altitude"]))

    if not plant:
        if e_obj["diet"] != "":
            reqs.append(Evolution.DietRequirement(e_obj["diet"]))
        if e_obj["speed"] != 0:
            reqs.append(Evolution.SpeedRequirement(e_obj["speed"]))

    return reqs

def get_species() -> list[Species]:
    return get_plants() + get_animals()

def plant_object_decoder(p_obj):
    return Species(True,
                   p_obj["name"],
                   p_obj["evolution_stage"],
                   p_obj["previous_evolution"],
                   get_evolution_reqs_from_json(p_obj["evolution_requirement"], True),
                   p_obj["traits"]["cost"],
                   0,
                   p_obj["traits"]["spreads"],
                   p_obj["traits"]["suitable_biomes"],
                   p_obj["traits"]["unsuitable_biomes"],
                   p_obj["traits"]["liked_species"],
                   p_obj["traits"]["disliked_species"],
                   p_obj["traits"]["preferred_altitude"],
                   "",
                   p_obj["id"])

def get_plants() -> list[Species]:
    plants_raw_data = pkgutil.get_data(__name__, "data/plants.json")
    if not plants_raw_data:
        return []

    raw_list = json.loads(plants_raw_data)

    plant_list = [plant_object_decoder(item) for item in raw_list]
    return plant_list

def animal_object_decoder(a_obj):
    return Species(False,
                   a_obj["name"],
                   a_obj["evolution_stage"],
                   a_obj["previous_evolution"],
                   get_evolution_reqs_from_json(a_obj["evolution_requirement"], False),
                   a_obj["traits"]["cost"],
                   a_obj["traits"]["dp_earn"],
                   "",
                   a_obj["traits"]["suitable_biomes"],
                   a_obj["traits"]["unsuitable_biomes"],
                   a_obj["traits"]["liked_species"],
                   a_obj["traits"]["disliked_species"],
                   a_obj["traits"]["preferred_altitude"],
                   a_obj["traits"]["eats"],
                   a_obj["id"])

def get_animals() -> list[Species]:
    animals_raw_data = pkgutil.get_data(__name__, "data/animals.json")
    if not animals_raw_data:
        return []

    raw_list = json.loads(animals_raw_data)

    animal_list = [animal_object_decoder(item) for item in raw_list]
    return animal_list

all_species : list[Species] = []
rocks_and_stones = {"Stones",
                        "Brown Stones",
                        "Shell",
                        "Rock",
                        "Brown Rock",
                        "Jungle Rocks",
                        "Snow Rocks",
                        "Desert Rock"
                        }