# AI Agent City: Learning System Design

## Overview
The Learning System enables AI agents to acquire knowledge, adapt behaviors, and improve decision-making over time within the simulated city environment.

---

## 1. Learning System Architecture

### 1.1 Core Components

```
+--------------------------------------------------+
|                  LEARNING SYSTEM                  |
|                                                   |
|  +-------------+  +------------+  +------------+  |
|  | Experience  |  | Knowledge  |  | Behavior   |  |
|  | Collector   |  | Graph      |  | Optimizer  |  |
|  +------+------+  +------+-----+  +------+-----+  |
|         |                |               |         |
|  +------v----------------v---------------v------+  |
|  |            Learning Pipeline                 |  |
|  |  [Observe] -> [Encode] -> [Reason] -> [Act]  |  |
|  +----------------------------------------------+  |
|         |                |               |         |
|  +------v------+  +------v-----+  +------v-----+  |
|  | Short-term  |  | Long-term  |  | Shared     |  |
|  | Memory      |  | Memory     |  | Knowledge  |  |
|  +-------------+  +------------+  +------------+  |
+--------------------------------------------------+
```

### 1.2 Experience Collector
- **Sensory Input Layer**: Gathers data from the agent's environment (location, nearby agents, available resources, events)
- **Interaction Logger**: Records all agent-to-agent and agent-to-environment interactions
- **Reward Signal Tracker**: Captures outcomes (positive/negative) of actions taken
- **Temporal Context**: Timestamps and sequences events for causal reasoning

### 1.3 Knowledge Graph
- **Entity Nodes**: Agents, locations, objects, skills, resources
- **Relationship Edges**: owns, knows, located_at, trades_with, depends_on
- **Confidence Scores**: Each fact has a confidence weight (0.0 - 1.0) that decays over time
- **Storage**: Graph database (Neo4j or in-memory for MVP)

### 1.4 Behavior Optimizer
- **Policy Engine**: Maps states to actions using learned preferences
- **Multi-objective Optimization**: Balances survival, wealth, social standing, skill growth
- **Exploration vs Exploitation**: Epsilon-greedy strategy with decay — agents explore early, exploit learned strategies later

### 1.5 Memory Architecture

| Memory Type | Duration | Capacity | Purpose |
|---|---|---|---|
| Working Memory | Current tick | 10 items | Immediate decision context |
| Short-term Memory | 50 ticks | 100 items | Recent events and interactions |
| Long-term Memory | Permanent | Unlimited (pruned) | Core knowledge and learned behaviors |
| Shared Knowledge | Permanent | City-wide | Collective facts available to all agents |

---

## 2. Learning Mechanisms

### 2.1 Reinforcement Learning (Primary)
```python
class AgentLearner:
    def __init__(self, agent_id: str):
        self.q_table: dict[tuple, dict[str, float]] = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.3  # exploration rate
        self.epsilon_decay = 0.995

    def choose_action(self, state: tuple, available_actions: list[str]) -> str:
        if random.random() < self.epsilon:
            return random.choice(available_actions)
        q_values = self.q_table.get(state, {})
        return max(available_actions, key=lambda a: q_values.get(a, 0.0))

    def update(self, state, action, reward, next_state):
        current_q = self.q_table.setdefault(state, {}).get(action, 0.0)
        next_max = max(self.q_table.get(next_state, {}).values(), default=0.0)
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max - current_q
        )
        self.q_table[state][action] = new_q
        self.epsilon *= self.epsilon_decay
```

### 2.2 Social Learning (Observation-based)
- Agents observe successful neighbors and copy high-reward strategies
- Trust network: agents weight observations by trust in the source agent
- Gossip protocol: agents share learned facts during interactions

### 2.3 Skill Acquisition
```python
class SkillSystem:
    def __init__(self):
        self.skills: dict[str, float] = {}  # skill_name -> proficiency (0.0-1.0)
        self.xp: dict[str, int] = {}

    def practice(self, skill: str, difficulty: float) -> bool:
        proficiency = self.skills.get(skill, 0.0)
        success = random.random() < proficiency
        xp_gain = int(difficulty * 10) if success else int(difficulty * 3)
        self.xp[skill] = self.xp.get(skill, 0) + xp_gain
        # Level up check
        if self.xp[skill] >= self.xp_threshold(skill):
            self.skills[skill] = min(1.0, proficiency + 0.05)
            self.xp[skill] = 0
        return success

    def xp_threshold(self, skill: str) -> int:
        level = int(self.skills.get(skill, 0.0) * 20)
        return 100 + (level * 50)  # progressively harder
```

### 2.4 Emotional State (influences learning)
- **Mood**: happy, neutral, stressed, fearful — affects risk tolerance
- **Motivation**: high/low — affects learning rate multiplier
- **Social bonds**: trust scores with other agents affect cooperation willingness

---

## 3. Integration Points

### With Simulation Engine
- Learning system receives state updates each tick
- Outputs action decisions back to simulation
- Skill checks feed into simulation physics

### With Agent Architecture (Tejas's component)
- Agents expose a `LearnerInterface` that the learning system drives
- Agent personality traits set initial learning parameters
- Agent goals feed into reward function design

### With Economy System
- Trade outcomes generate reward signals
- Market prices inform resource valuation learning
- Job performance links to skill progression
