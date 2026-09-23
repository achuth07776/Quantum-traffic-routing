from app.schemas.quantum import QAOAExecutionRequest, QAOAExecutionResponse
from optimization.quantum_native.qaoa_qubo import QAOAQuboSolver, QUBOProblem

class QuantumService:
    def __init__(self):
        pass

    def execute_qaoa(self, req: QAOAExecutionRequest) -> QAOAExecutionResponse:
        qubo = QUBOProblem(
            problem_name=req.problem_name,
            num_variables=req.num_variables,
            variable_labels=req.variable_labels,
            q_matrix=req.q_matrix
        )
        
        solver = QAOAQuboSolver(p_layers=req.p_layers)
        res = solver.solve(qubo)
        
        return QAOAExecutionResponse(
            status="SUCCESS",
            optimal_bitstring=res.optimal_bitstring,
            optimal_state_label=res.optimal_state_label,
            optimal_cost=res.optimal_cost,
            ground_state_energy=res.ground_state_energy,
            qaoa_layers=res.qaoa_layers,
            optimal_gamma=res.optimal_gamma,
            optimal_beta=res.optimal_beta,
            state_probabilities=res.state_probabilities,
            quantum_circuit_qasm=res.quantum_circuit_qasm,
            circuit_depth=res.circuit_depth,
            qubit_count=res.qubit_count,
            runtime_ms=res.runtime_ms,
            is_converged=res.is_converged
        )
