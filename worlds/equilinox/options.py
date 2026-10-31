from dataclasses import dataclass

from Options import OptionGroup, PerGameCommonOptions, Range, Toggle, Choice, OptionSet


class TasksRewardDP(Toggle):
    """
    Should tasks reward the normal DP amount upon completion.
    If off, some filler DP items are replaced with larger
    sums of DP to replace the missing task rewards (if there
    is space for them in the item pool).
    """
    display_name = "Tasks Reward DP"
    default = True

class StartingDP(Range):
    """
    Starting DP Balance. The vanilla value is 2500.
    This is not exact; you will start with a balance *near* the selected value.
    """
    display_name = "Starting DP Balance"
    range_start = 2500
    range_end = 500000
    default = 5000

class DPInItempool(Range):
    """
    How much DP should be in the item pool? Note, currently the only filler
    item is small amounts of DP, so there will be more than just this much
    in the item pool. This option allows you to force the addition of larger
    DP items to the pool. If 'Tasks Reward DP' is off, some larger DP amounts
    will have already been added. We recommend at least some additional DP,
    since you may receive expensive Species before having a lot of DP earn per minute.
    """
    display_name = "Additional DP in Item Pool"
    range_start = 0
    range_end = 1000000
    default = 200000

class DPPerMinItemCount(Range):
    """
    Adds this many 'Progressive DP/Min Bonus' items to the pool. Each one
    of these received gives an additional 20 dp/min.
    """
    display_name = "DP/Min Bonus Items"
    range_start = 0
    range_end = 40
    default = 5

class FreeEvolution(Toggle):
    """
    Removes the DP cost from evolution. Other requirements
    still must be fulfilled.
    """
    display_name = "Free Evolution"
    default = True

class SizeChecks(Toggle):
    """
    Adds checks for breeding species of size 1.10 and 1.20.
    """
    display_name = "Include Size Checks"
    default = True

class GoalSelection(Choice):
    """
    Completion condition:
        Completionist: Complete all 60 tasks
        Evolve Species: Evolve the required number of species from the given list (see subsequent options)
    """
    display_name = "Goal Condition"
    option_completionist = 0
    option_evolve_species = 1
    default = 0

class EvolutionGoalSpeciesRequirements(OptionSet):
    """
    Does nothing if Goal Condition is not 'Evolve Species'.
    The set of species from which you will need to evolve X to goal,
    where X is given by 'Evolution Goal Count'.
    """
    display_name = "Evolution Goal Species Requirements"
    valid_keys = [
        'Wheat',
        'Buttercup',
        'Wild Mint',
        'Tulip',
        'Oregano',
        'Kelp',
        'Water Lily',
        'Sage',
        'Heather',
        'Elm Tree',
        'Red Maple Tree',
        'Sycamore Tree',
        'Juniper Tree',
        'Apple Tree',
        'Fern',
        'Pansies',
        'Bluebell',
        'Tropical Mushroom',
        'Cedar Tree',
        'Barley',
        'Tropical Seaweed',
        'Wobbly Tree',
        'Poppy',
        'Spruce Tree',
        'Lily',
        'Snap Dragon',
        'Small Cactus',
        'Jungle Mushroom',
        'Desert Grass',
        'Carrot',
        'Jungle Flower',
        'Potato Plant',
        'Prickly Pear',
        'Red Mushroom',
        'Rose',
        'Coral',
        'Marigolds',
        'Turnip',
        'Berry Bush',
        'Tropical Flower',
        'Jungle Plant',
        'Sunflower',
        'Holly Bush',
        'Leafy Plant',
        'Tall Mushroom',
        'Medium Cactus',
        'Nut Tree',
        'Acer Tree',
        'Ash Tree',
        'Primrose',
        'Bromeliad',
        'Blueberry Bush',
        'Bulrush',
        'Slimy Tree',
        'Red Tree',
        'Swamp Flower',
        'Ficus Tree',
        'Pagoda Tree',
        'Bamboo',
        'Flower Tree',
        'Healbloom',
        'Banana Tree',
        'Eucalyptus Tree',
        'Umbrella Tree',
        'Canopy Tree',
        'Fly Trapper',
        'Orange Tree',
        'Autumnal Tree',
        'Large Tree',
        'Mango Tree',
        'Giant Cactus',
        'Pine Tree',
        'Witchwood Tree',
        'Starbloom Bush',
        'Dead Tree',
        'Spiral Tree',
        'Cherry Tree',
        'Redfish',
        'Wild Boar',
        'Duck',
        'Salmon',
        'Rabbit',
        'Sparrow',
        'Squirrel',
        'Clown Fish',
        'Deer',
        'Angel Fish',
        'Goat',
        'Desert Hare',
        'Royal Gramma',
        'Warthog',
        'Neon Fish',
        'Frog',
        'Pike',
        'Eagle',
        'Turtle',
        'Fly',
        'Toad',
        'Meerkat',
        'Toucan',
        'Dove',
        'Bee',
        'Wolf',
        'Dolphin',
        'Peacock',
        'Beaver',
        'Camel']
    default = ['Camel', 'Giant Cactus']
    #valid_keys_casefold = True

class EvolutionGoalCount(Range):
    """
    Does nothing if Goal Condition is not 'Evolve Species'.
    Sets how many of the species selected in 'Evolution Goal Species Requirements'
    do you need to evolve to complete the goal. Setting this to 0 or a number greater than
    the number of selected species means you will need to evolve *all* of the selected
    species to complete the goal.
    """
    display_name = 'Evolution Goal Count'
    range_start = 0
    range_end = 107
    default = 0


@dataclass
class EquilinoxOptions(PerGameCommonOptions):
    tasks_reward_dp: TasksRewardDP
    starting_dp: StartingDP
    itempool_dp: DPInItempool
    size_checks: SizeChecks
    free_evolution: FreeEvolution
    goal_selection: GoalSelection
    dp_per_min_bonus_count: DPPerMinItemCount
    evo_goal_species: EvolutionGoalSpeciesRequirements
    evo_goal_count: EvolutionGoalCount

option_groups = [
    OptionGroup(
      "Goal Options",
        [GoalSelection, EvolutionGoalSpeciesRequirements, EvolutionGoalCount],
    ),
    OptionGroup(
        "Gameplay Options",
        [FreeEvolution]
    ),
    OptionGroup(
        "DP Options",
        [TasksRewardDP, StartingDP, DPInItempool, DPPerMinItemCount],
    ),
    OptionGroup(
        "Trait Checks",
        [SizeChecks]
    )
]

option_presets = {
    "Default": {
        "tasks_reward_dp": True,
        "starting_dp": 5000,
        "itempool_dp": 150000,
        "size_checks": True,
        "free_evolution": True,
        "goal_selection": 0,
        "dp_per_min_bonus_count": 5,
        "evo_goal_species": ['Camel', 'Giant Cactus'],
        "evo_goal_count": 0,
    }
}
