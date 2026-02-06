"""
Action Sequencer

Randomizes the order and timing of actions to avoid predictable patterns.
Simulates natural human behavior where actions are not performed in fixed sequences.
"""

import random
import logging
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ActionPriority(Enum):
    """Priority levels for actions."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Action:
    """Represents a single action to perform."""
    name: str
    action_type: str
    callback: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: ActionPriority = ActionPriority.MEDIUM
    weight: float = 1.0  # Higher weight = more likely to be selected
    
    def execute(self) -> Any:
        """Execute the action callback."""
        return self.callback(*self.args, **self.kwargs)


class ActionSequencer:
    """
    Randomizes action sequences to avoid detection.
    
    Features:
    - Weighted random selection
    - Priority-based ordering
    - Interleaving different action types
    - Configurable randomization
    
    Example:
        sequencer = ActionSequencer()
        
        # Add actions to the queue
        sequencer.add_action("like_post_1", "like", like_callback, args=(post_id,))
        sequencer.add_action("follow_user", "follow", follow_callback, args=(user_id,))
        sequencer.add_action("like_post_2", "like", like_callback, args=(post_id_2,))
        
        # Get randomized sequence
        for action in sequencer.get_sequence():
            action.execute()
            # Add delay between actions
    """
    
    def __init__(
        self,
        max_consecutive_same_type: int = 3,
        shuffle_strength: float = 0.7
    ):
        """
        Initialize the sequencer.
        
        Args:
            max_consecutive_same_type: Maximum actions of same type in a row
            shuffle_strength: How much to randomize (0.0=ordered, 1.0=fully random)
        """
        self._actions: List[Action] = []
        self.max_consecutive_same_type = max_consecutive_same_type
        self.shuffle_strength = shuffle_strength
        
        # Track action type weights for balancing
        self._type_weights: Dict[str, float] = {}
        
        logger.info(
            f"ActionSequencer initialized: "
            f"max_consecutive={max_consecutive_same_type}, "
            f"shuffle_strength={shuffle_strength}"
        )
    
    def add_action(
        self,
        name: str,
        action_type: str,
        callback: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: ActionPriority = ActionPriority.MEDIUM,
        weight: float = 1.0
    ) -> None:
        """
        Add an action to the queue.
        
        Args:
            name: Unique name for the action
            action_type: Type of action (e.g., "like", "follow")
            callback: Function to call when executing
            args: Positional arguments for callback
            kwargs: Keyword arguments for callback
            priority: Action priority level
            weight: Selection weight (higher = more likely)
        """
        action = Action(
            name=name,
            action_type=action_type,
            callback=callback,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            weight=weight
        )
        self._actions.append(action)
        logger.debug(f"Added action: {name} (type={action_type})")
    
    def add_actions_batch(self, actions: List[Dict]) -> None:
        """
        Add multiple actions at once.
        
        Args:
            actions: List of action dictionaries with keys:
                     name, action_type, callback, args, kwargs, priority, weight
        """
        for action_dict in actions:
            self.add_action(**action_dict)
    
    def get_sequence(self, respect_priority: bool = True) -> List[Action]:
        """
        Get a randomized sequence of actions.
        
        Args:
            respect_priority: If True, higher priority actions come first (with randomization)
            
        Returns:
            List of actions in randomized order
        """
        if not self._actions:
            return []
        
        actions = self._actions.copy()
        
        # Sort by priority if requested
        if respect_priority:
            actions.sort(key=lambda a: a.priority.value, reverse=True)
        
        # Apply weighted shuffle
        result = self._weighted_shuffle(actions)
        
        # Ensure we don't have too many consecutive same-type actions
        result = self._break_consecutive(result)
        
        logger.debug(f"Generated sequence of {len(result)} actions")
        return result
    
    def _weighted_shuffle(self, actions: List[Action]) -> List[Action]:
        """
        Shuffle actions with weighted randomization.
        
        Preserves some ordering based on shuffle_strength.
        """
        if self.shuffle_strength <= 0:
            return actions
        
        if self.shuffle_strength >= 1:
            # Full random shuffle with weights
            return self._random_weighted_sample(actions, len(actions))
        
        # Partial shuffle: keep some order, shuffle some
        result = []
        remaining = actions.copy()
        
        while remaining:
            # Decide if we pick next in order or random
            if random.random() > self.shuffle_strength:
                # Pick next in order
                result.append(remaining.pop(0))
            else:
                # Pick random weighted
                weights = [a.weight for a in remaining]
                idx = random.choices(range(len(remaining)), weights=weights)[0]
                result.append(remaining.pop(idx))
        
        return result
    
    def _random_weighted_sample(
        self,
        actions: List[Action],
        count: int
    ) -> List[Action]:
        """Select actions randomly based on weights."""
        result = []
        remaining = actions.copy()
        
        for _ in range(min(count, len(remaining))):
            if not remaining:
                break
            weights = [a.weight for a in remaining]
            idx = random.choices(range(len(remaining)), weights=weights)[0]
            result.append(remaining.pop(idx))
        
        return result
    
    def _break_consecutive(self, actions: List[Action]) -> List[Action]:
        """
        Rearrange to avoid too many consecutive same-type actions.
        """
        if len(actions) <= 1:
            return actions
        
        result = [actions[0]]
        remaining = actions[1:]
        consecutive_count = 1
        last_type = actions[0].action_type
        
        while remaining:
            # Find next action to add
            found = False
            
            for i, action in enumerate(remaining):
                if action.action_type != last_type:
                    # Different type, reset counter
                    result.append(remaining.pop(i))
                    last_type = action.action_type
                    consecutive_count = 1
                    found = True
                    break
                elif consecutive_count < self.max_consecutive_same_type:
                    # Same type but within limit
                    result.append(remaining.pop(i))
                    consecutive_count += 1
                    found = True
                    break
            
            if not found and remaining:
                # No suitable action found, just add the first one
                action = remaining.pop(0)
                result.append(action)
                if action.action_type == last_type:
                    consecutive_count += 1
                else:
                    consecutive_count = 1
                    last_type = action.action_type
        
        return result
    
    def clear(self) -> None:
        """Clear all pending actions."""
        self._actions.clear()
        logger.debug("Cleared all actions")
    
    def get_action_count(self) -> int:
        """Get number of pending actions."""
        return len(self._actions)
    
    def get_actions_by_type(self, action_type: str) -> List[Action]:
        """Get all actions of a specific type."""
        return [a for a in self._actions if a.action_type == action_type]
    
    def remove_action(self, name: str) -> bool:
        """
        Remove an action by name.
        
        Returns:
            True if removed, False if not found
        """
        for i, action in enumerate(self._actions):
            if action.name == name:
                self._actions.pop(i)
                logger.debug(f"Removed action: {name}")
                return True
        return False
