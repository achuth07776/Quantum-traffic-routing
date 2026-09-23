from typing import List, Dict
from pydantic import BaseModel, Field, model_validator

MAX_QAOA_NUM_VARIABLES = 20

class QAOAExecutionRequest(BaseModel):
    problem_name: str = "emergency_fleet_conflict"
    num_variables: int = Field(
        default=4,
        ge=1,
        le=MAX_QAOA_NUM_VARIABLES,
        description=(
            "Number of QUBO variables (qubits). The solver enumerates all 2**num_variables "
            f"basis states, so this is capped at {MAX_QAOA_NUM_VARIABLES}."
        )
    )
    variable_labels: List[str] = Field(
        default_factory=lambda: ["Ambulance_Flyover", "Ambulance_Bypass", "FireTruck_Flyover", "FireTruck_Bypass"]
    )
    q_matrix: List[List[float]] = Field(
        default_factory=lambda: [
            [-5.0, 20.0, 15.0,  0.0],
            [ 0.0, -2.0,  0.0,  0.0],
            [ 0.0,  0.0, -4.0, 20.0],
            [ 0.0,  0.0,  0.0, -1.0]
        ]
    )
    p_layers: int = 2

    @model_validator(mode="after")
    def _validate_q_matrix_dimensions(self):
        n = self.num_variables
        rows = len(self.q_matrix)
        cols = len(self.q_matrix[0]) if self.q_matrix else 0
        if rows != n or any(len(row) != n for row in self.q_matrix):
            raise ValueError(
                f"q_matrix must be {n}x{n} (matching num_variables={n}); got {rows}x{cols}"
            )
        return self

class QAOAExecutionResponse(BaseModel):
    status: str
    optimal_bitstring: str
    optimal_state_label: str
    optimal_cost: float
    ground_state_energy: float
    qaoa_layers: int
    optimal_gamma: List[float]
    optimal_beta: List[float]
    state_probabilities: Dict[str, float]
    quantum_circuit_qasm: str
    circuit_depth: int
    qubit_count: int
    runtime_ms: float
    is_converged: bool
