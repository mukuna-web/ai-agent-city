"""
Simulation subsystems — each implements update(world, tick, event_bus).
Registered with the SimulationEngine at different frequencies.
"""
from .need_decay import NeedDecaySystem
from .agent_cognition import AgentCognitionSystem
from .production import ProductionUpdateSystem
from .death import DeathSystem
from .status_reporter import StatusReporterSystem
