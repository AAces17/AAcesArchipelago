from dataclasses import dataclass

from Options import OptionGroup, PerGameCommonOptions, Range, Toggle, Choice


class TasksRewardDP(Toggle):
    """
    Should tasks reward the normal DP amount upon completion.
    If off, some filler DP items are replaced with larger
    sums of DP to replace the missing task rewards.
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
    range_end = 100000
    default = 5000

class DPInItempool(Range):
    """
    How much DP should be in the itempool? Note, currently the only filler
    item is small amounts of DP, so there will be more than just this much
    in the item pool. This option allows you to force the addition of larger
    DP items to the pool. If 'Tasks Reward DP' is off, some larger DP amounts
    will have already been added. We recommend at least some additional DP,
    since you may receive expensive Species before having a lot of DP earn per minute.
    """
    display_name = "Additional DP in Itempool"
    range_start = 0
    range_end = 500000
    default = 150000

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
    Completion condition
    """
    display_name = "Goal"
    option_completionist = 0
    option_evolve_camel = 1
    default = 0

@dataclass
class EquilinoxOptions(PerGameCommonOptions):
    tasks_reward_dp: TasksRewardDP
    starting_dp: StartingDP
    itempool_dp: DPInItempool
    size_checks: SizeChecks
    free_evolution: FreeEvolution
    goal_selection: GoalSelection

option_groups = [
    OptionGroup(
      "Goal Options",
        [GoalSelection]
    ),
    OptionGroup(
        "Gameplay Options",
        [FreeEvolution]
    ),
    OptionGroup(
        "DP Options",
        [TasksRewardDP, StartingDP, DPInItempool],
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
        "goal_selection": 0
    }
}
