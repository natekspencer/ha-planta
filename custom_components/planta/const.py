"""Constants for the Planta integration."""

from typing import Final

DOMAIN: Final = "planta"

CONF_ENABLED_SENSORS: Final = "enabled_sensors"
CONF_APPLY_TO_EXISTING: Final = "apply_to_existing"
CONF_ENABLE_ALL: Final = "enable_all"

# List-based actions: each item has an `actionType` such as `pruning:topping` or
# `customTask:<id>` that is used to complete it
PRUNING: Final = "pruning"
CUSTOM_TASKS: Final = "customTasks"
TASK_LISTS: Final = (PRUNING, CUSTOM_TASKS)
PRUNING_PREFIX: Final = "pruning:"
CUSTOM_TASK_PREFIX: Final = "customTask:"

PRUNING_TECHNIQUES: Final = (
    "deadHeadingPinching",
    "deadWooding",
    "cutBackOneThird",
    "removeSuckersPinching",
    "removeFlowersPinching",
    "lollipopping",
    "topping",
    "thinning",
)
