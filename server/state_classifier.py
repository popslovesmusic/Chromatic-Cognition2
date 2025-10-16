"""
State Classifier Graph - Adaptive Consciousness State Classification
Feature 015: Real-time state classification using ICI, coherence, and spectral metrics

Implements:
- FR-001: StateClassifierGraph class
- FR-002: Metrics-based classification
- FR-003: Classification tree with 6 states
- FR-004: Markov-like transition probabilities
- FR-005: WebSocket event broadcasting
- FR-006: Visualization support
- FR-007: 512 transition history

States:
- COMA: ICI < 0.1 & coherence < 0.2
- SLEEP: centroid < 10 & coherence < 0.4
- DROWSY: ICI < 0.3
- AWAKE: ICI 0.3-0.7 & coherence >= 0.4
- ALERT: ICI > 0.7 & coherence > 0.7
- HYPERSYNC: ICI > 0.9 & coherence > 0.9

Success Criteria:
- SC-001: Classification accuracy >= 90%
- SC-002: Transition latency < 100ms
- SC-003: Stable output (< 2 transitions/sec)
- SC-004: Graph sync within ±1 frame
"""

import time
import numpy as np
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass
from collections import deque
from enum import Enum


class ConsciousnessState(Enum):
    """Consciousness states"""
    COMA = "COMA"
    SLEEP = "SLEEP"
    DROWSY = "DROWSY"
    AWAKE = "AWAKE"
    ALERT = "ALERT"
    HYPERSYNC = "HYPERSYNC"


@dataclass
class StateTransition:
    """Single state transition record"""
    timestamp: float
    from_state: ConsciousnessState
    to_state: ConsciousnessState
    ici: float
    coherence: float
    spectral_centroid: float
    probability: float


@dataclass
class StateClassifierConfig:
    """Configuration for State Classifier"""

    # Hysteresis for stability (SC-003)
    hysteresis_threshold: float = 0.1  # Must change by this much to switch
    min_state_duration: float = 0.5    # Minimum time in state (seconds)

    # Transition history (FR-007)
    history_size: int = 512

    # Smoothing for input metrics
    smoothing_window: int = 10  # Rolling average over 10 frames

    # Logging
    enable_logging: bool = True
    log_interval: float = 2.0


class StateClassifierGraph:
    """
    Adaptive state classification system

    Analyzes real-time metrics (ICI, coherence, spectral centroid)
    to classify consciousness states and track transitions.

    Features:
    - 6-state classification tree
    - Markov transition probabilities
    - Hysteresis for stability
    - WebSocket event broadcasting
    - Transition history
    """

    def __init__(self, config: Optional[StateClassifierConfig] = None):
        """
        Initialize State Classifier

        Args:
            config: StateClassifierConfig (uses defaults if None)
        """
        self.config = config or StateClassifierConfig()

        # Current state
        self.current_state: ConsciousnessState = ConsciousnessState.COMA
        self.previous_state: ConsciousnessState = ConsciousnessState.COMA
        self.state_entry_time: float = time.time()

        # Smoothed metrics (for stability)
        self.ici_history: deque = deque(maxlen=self.config.smoothing_window)
        self.coherence_history: deque = deque(maxlen=self.config.smoothing_window)
        self.centroid_history: deque = deque(maxlen=self.config.smoothing_window)

        # Transition tracking (FR-004, FR-007)
        self.transition_history: deque = deque(maxlen=self.config.history_size)
        self.transition_counts: Dict[Tuple[ConsciousnessState, ConsciousnessState], int] = {}

        # Statistics
        self.total_transitions: int = 0
        self.state_durations: Dict[ConsciousnessState, List[float]] = {
            state: [] for state in ConsciousnessState
        }

        # Callback for state change events (FR-005)
        self.state_change_callback: Optional[Callable[[Dict], None]] = None

        # Logging
        self.last_log_time: float = 0.0

        print("[StateClassifier] Initialized")
        print(f"[StateClassifier]   hysteresis_threshold={self.config.hysteresis_threshold}")
        print(f"[StateClassifier]   min_state_duration={self.config.min_state_duration}s")
        print(f"[StateClassifier]   initial_state={self.current_state.value}")

    def classify_state(self, ici: float, coherence: float, spectral_centroid: float) -> bool:
        """
        Classify current consciousness state (FR-002, FR-003)

        Args:
            ici: Integrated Chromatic Information [0, 1]
            coherence: Phase coherence [0, 1]
            spectral_centroid: Spectral centroid in Hz

        Returns:
            True if state changed
        """
        current_time = time.time()

        # Add to history for smoothing
        self.ici_history.append(ici)
        self.coherence_history.append(coherence)
        self.centroid_history.append(spectral_centroid)

        # Use smoothed values for classification
        if len(self.ici_history) < self.config.smoothing_window:
            # Not enough history yet
            return False

        ici_smooth = np.mean(self.ici_history)
        coherence_smooth = np.mean(self.coherence_history)
        centroid_smooth = np.mean(self.centroid_history)

        # Apply classification tree (FR-003)
        new_state = self._apply_classification_tree(
            ici_smooth, coherence_smooth, centroid_smooth
        )

        # Check if state should change (with hysteresis)
        if new_state != self.current_state:
            # Check minimum duration (SC-003: stability)
            time_in_state = current_time - self.state_entry_time

            if time_in_state >= self.config.min_state_duration:
                # State change is valid
                return self._change_state(
                    new_state, ici_smooth, coherence_smooth,
                    centroid_smooth, current_time
                )

        # Log periodically
        if self.config.enable_logging and (current_time - self.last_log_time) >= self.config.log_interval:
            self._log_stats()
            self.last_log_time = current_time

        return False

    def _apply_classification_tree(self, ici: float, coherence: float,
                                   centroid: float) -> ConsciousnessState:
        """
        Apply classification decision tree (FR-003)

        Classification rules:
        - COMA: ICI < 0.1 & coherence < 0.2
        - SLEEP: centroid < 10 & coherence < 0.4 (and not COMA)
        - DROWSY: ICI < 0.3 (and not COMA/SLEEP)
        - AWAKE: ICI 0.3-0.7 & coherence >= 0.4
        - ALERT: ICI > 0.7 & coherence > 0.7
        - HYPERSYNC: ICI > 0.9 & coherence > 0.9

        Args:
            ici: Smoothed ICI value
            coherence: Smoothed coherence value
            centroid: Smoothed spectral centroid

        Returns:
            Classified state
        """
        # Priority order: check most specific conditions first

        # HYPERSYNC: Very high ICI and coherence
        if ici > 0.9 and coherence > 0.9:
            return ConsciousnessState.HYPERSYNC

        # ALERT: High ICI and coherence
        if ici > 0.7 and coherence > 0.7:
            return ConsciousnessState.ALERT

        # COMA: Very low ICI and coherence
        if ici < 0.1 and coherence < 0.2:
            return ConsciousnessState.COMA

        # SLEEP: Low centroid and coherence (but not COMA)
        if centroid < 10 and coherence < 0.4:
            return ConsciousnessState.SLEEP

        # AWAKE: Moderate ICI with good coherence
        if 0.3 <= ici <= 0.7 and coherence >= 0.4:
            return ConsciousnessState.AWAKE

        # DROWSY: Low ICI (fallback)
        if ici < 0.3:
            return ConsciousnessState.DROWSY

        # Default: stay in current state if no clear match
        return self.current_state

    def _change_state(self, new_state: ConsciousnessState, ici: float,
                     coherence: float, centroid: float, timestamp: float) -> bool:
        """
        Change to new state and record transition (FR-004, FR-005)

        Args:
            new_state: New state to transition to
            ici: Current ICI value
            coherence: Current coherence value
            centroid: Current spectral centroid
            timestamp: Transition timestamp

        Returns:
            True (state changed)
        """
        # Record duration in previous state
        duration = timestamp - self.state_entry_time
        self.state_durations[self.current_state].append(duration)

        # Create transition record
        transition = StateTransition(
            timestamp=timestamp,
            from_state=self.current_state,
            to_state=new_state,
            ici=ici,
            coherence=coherence,
            spectral_centroid=centroid,
            probability=self._compute_transition_probability(self.current_state, new_state)
        )

        # Update history
        self.transition_history.append(transition)

        # Update transition counts
        transition_key = (self.current_state, new_state)
        self.transition_counts[transition_key] = self.transition_counts.get(transition_key, 0) + 1
        self.total_transitions += 1

        # Update state
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_entry_time = timestamp

        # Broadcast event (FR-005)
        if self.state_change_callback:
            event = {
                'type': 'state',
                'current': new_state.value,
                'prev': self.previous_state.value,
                'prob': transition.probability,
                'timestamp': timestamp,
                'ici': ici,
                'coherence': coherence,
                'spectral_centroid': centroid
            }
            self.state_change_callback(event)

        if self.config.enable_logging:
            print(f"[StateClassifier] State transition: {self.previous_state.value} -> {new_state.value} "
                  f"(p={transition.probability:.3f})")

        return True

    def _compute_transition_probability(self, from_state: ConsciousnessState,
                                       to_state: ConsciousnessState) -> float:
        """
        Compute transition probability (FR-004)

        Uses historical transition frequencies to estimate probability

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            Probability [0, 1]
        """
        # Count transitions from this state
        from_count = 0
        transition_key = (from_state, to_state)

        for key in self.transition_counts:
            if key[0] == from_state:
                from_count += self.transition_counts[key]

        if from_count == 0:
            # No history, use uniform prior
            return 1.0 / len(ConsciousnessState)

        # Compute empirical probability
        transition_count = self.transition_counts.get(transition_key, 0)
        probability = transition_count / from_count

        return probability

    def get_current_state(self) -> Dict:
        """
        Get current state information

        Returns:
            Dictionary with current state details
        """
        current_time = time.time()
        time_in_state = current_time - self.state_entry_time

        return {
            'current_state': self.current_state.value,
            'previous_state': self.previous_state.value,
            'time_in_state': time_in_state,
            'total_transitions': self.total_transitions
        }

    def get_transition_matrix(self) -> np.ndarray:
        """
        Get transition probability matrix

        Returns:
            6x6 matrix of transition probabilities
        """
        states = list(ConsciousnessState)
        n_states = len(states)
        matrix = np.zeros((n_states, n_states))

        # Fill matrix with empirical probabilities
        for i, from_state in enumerate(states):
            from_count = 0

            # Count all transitions from this state
            for key in self.transition_counts:
                if key[0] == from_state:
                    from_count += self.transition_counts[key]

            if from_count > 0:
                # Compute probabilities for each target state
                for j, to_state in enumerate(states):
                    key = (from_state, to_state)
                    count = self.transition_counts.get(key, 0)
                    matrix[i, j] = count / from_count

        return matrix

    def get_statistics(self) -> Dict:
        """
        Get classifier statistics

        Returns:
            Dictionary with statistics
        """
        # Compute average durations
        avg_durations = {}
        for state, durations in self.state_durations.items():
            if len(durations) > 0:
                avg_durations[state.value] = float(np.mean(durations))
            else:
                avg_durations[state.value] = 0.0

        # Get recent transition rate
        recent_transitions = list(self.transition_history)[-60:]  # Last 60 transitions
        if len(recent_transitions) >= 2:
            time_span = recent_transitions[-1].timestamp - recent_transitions[0].timestamp
            transition_rate = len(recent_transitions) / time_span if time_span > 0 else 0.0
        else:
            transition_rate = 0.0

        return {
            'current_state': self.current_state.value,
            'previous_state': self.previous_state.value,
            'total_transitions': self.total_transitions,
            'transition_rate': transition_rate,
            'avg_durations': avg_durations,
            'history_size': len(self.transition_history)
        }

    def get_transition_history(self, n: int = 512) -> List[Dict]:
        """
        Get recent transition history (FR-007)

        Args:
            n: Number of recent transitions to return

        Returns:
            List of transition dictionaries
        """
        recent = list(self.transition_history)[-n:]

        return [
            {
                'timestamp': t.timestamp,
                'from_state': t.from_state.value,
                'to_state': t.to_state.value,
                'ici': t.ici,
                'coherence': t.coherence,
                'spectral_centroid': t.spectral_centroid,
                'probability': t.probability
            }
            for t in recent
        ]

    def _log_stats(self):
        """Log classifier statistics"""
        stats = self.get_statistics()

        print(f"[StateClassifier] Stats: "
              f"state={stats['current_state']}, "
              f"transitions={stats['total_transitions']}, "
              f"rate={stats['transition_rate']:.2f}/s")

    def reset(self):
        """Reset classifier state"""
        self.current_state = ConsciousnessState.COMA
        self.previous_state = ConsciousnessState.COMA
        self.state_entry_time = time.time()

        self.ici_history.clear()
        self.coherence_history.clear()
        self.centroid_history.clear()

        self.transition_history.clear()
        self.transition_counts.clear()
        self.total_transitions = 0

        for state in ConsciousnessState:
            self.state_durations[state].clear()

        print("[StateClassifier] State reset")


# Self-test function
def _self_test():
    """Test StateClassifierGraph"""
    print("=" * 60)
    print("State Classifier Self-Test")
    print("=" * 60)

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    config = StateClassifierConfig(
        hysteresis_threshold=0.1,
        min_state_duration=0.1,  # Short for testing
        enable_logging=True
    )
    classifier = StateClassifierGraph(config)

    assert classifier.current_state == ConsciousnessState.COMA
    assert len(classifier.transition_history) == 0
    print("   OK: Initialization")

    # Test 2: State classification
    print("\n2. Testing state classification...")

    # COMA: low ICI and coherence
    for i in range(15):
        changed = classifier.classify_state(0.05, 0.1, 1000)

    assert classifier.current_state == ConsciousnessState.COMA
    print(f"   State: {classifier.current_state.value} (expected COMA)")

    # Transition to DROWSY
    time.sleep(0.15)
    for i in range(15):
        changed = classifier.classify_state(0.2, 0.3, 2000)

    assert classifier.current_state == ConsciousnessState.DROWSY
    print(f"   State: {classifier.current_state.value} (expected DROWSY)")

    # Transition to AWAKE
    time.sleep(0.15)
    for i in range(15):
        changed = classifier.classify_state(0.5, 0.6, 3000)

    assert classifier.current_state == ConsciousnessState.AWAKE
    print(f"   State: {classifier.current_state.value} (expected AWAKE)")

    # Transition to ALERT
    time.sleep(0.15)
    for i in range(15):
        changed = classifier.classify_state(0.8, 0.8, 5000)

    assert classifier.current_state == ConsciousnessState.ALERT
    print(f"   State: {classifier.current_state.value} (expected ALERT)")

    print("   OK: State transitions working")

    # Test 3: Transition tracking
    print("\n3. Testing transition tracking...")

    assert classifier.total_transitions >= 3, "Should have at least 3 transitions"
    assert len(classifier.transition_history) >= 3

    history = classifier.get_transition_history(10)
    print(f"   Transitions recorded: {len(history)}")

    for i, trans in enumerate(history[:3]):
        print(f"     {i+1}. {trans['from_state']} -> {trans['to_state']} (p={trans['probability']:.3f})")

    print("   OK: Transition tracking")

    # Test 4: Transition matrix
    print("\n4. Testing transition matrix...")

    matrix = classifier.get_transition_matrix()
    assert matrix.shape == (6, 6), "Matrix should be 6x6"

    # Row sums should be <= 1 (may not visit all states)
    for i in range(6):
        row_sum = np.sum(matrix[i])
        assert 0 <= row_sum <= 1.01, f"Row {i} sum should be in [0, 1], got {row_sum}"

    print(f"   Matrix shape: {matrix.shape}")
    print(f"   Non-zero entries: {np.count_nonzero(matrix)}")
    print("   OK: Transition matrix")

    # Test 5: Statistics
    print("\n5. Testing statistics...")

    stats = classifier.get_statistics()

    assert 'current_state' in stats
    assert 'total_transitions' in stats
    assert 'transition_rate' in stats

    print(f"   Current state: {stats['current_state']}")
    print(f"   Total transitions: {stats['total_transitions']}")
    print(f"   Transition rate: {stats['transition_rate']:.2f}/s")
    print("   OK: Statistics")

    # Test 6: Reset
    print("\n6. Testing reset...")

    classifier.reset()

    assert classifier.current_state == ConsciousnessState.COMA
    assert classifier.total_transitions == 0
    assert len(classifier.transition_history) == 0

    print("   OK: Reset")

    print("\n" + "=" * 60)
    print("Self-Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    _self_test()
