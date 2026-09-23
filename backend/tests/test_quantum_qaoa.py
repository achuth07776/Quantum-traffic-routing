import pytest
from optimization.quantum_native.qaoa_qubo import QAOAQuboSolver, QUBOProblem

def test_qaoa_qubo_solver_two_vehicle_conflict():
    # 2 vehicles, each with 2 alternative routes (x0, x1 for Vehicle 1; x2, x3 for Vehicle 2)
    # Constraints:
    # 1) Exactly one route chosen per vehicle: penalty 10 * (x0 + x1 - 1)^2 and 10 * (x2 + x3 - 1)^2
    # 2) Route 0 and Route 2 share the same narrow flyover: conflict penalty 15 * x0 * x2
    # Individual route costs: Route 0 = 5.0, Route 1 = 8.0, Route 2 = 6.0, Route 3 = 9.0
    
    # Mathematical QUBO Matrix Q (4x4):
    # Variables: [x0, x1, x2, x3]
    # Expansion:
    # (x0+x1-1)^2 = x0 + x1 + 2*x0*x1 - 2*x0 - 2*x1 + 1 = -x0 - x1 + 2*x0*x1 + 1
    # Cost = 5*x0 + 8*x1 + 6*x2 + 9*x3 + 10*(-x0 - x1 + 2*x0*x1) + 10*(-x2 - x3 + 2*x2*x3) + 15*x0*x2
    # Diagonal:
    # Q[0,0] = 5 - 10 = -5
    # Q[1,1] = 8 - 10 = -2
    # Q[2,2] = 6 - 10 = -4
    # Q[3,3] = 9 - 10 = -1
    # Off-diagonal:
    # Q[0,1] = 20
    # Q[2,3] = 20
    # Q[0,2] = 15
    
    q_matrix = [
        [-5.0, 20.0, 15.0,  0.0],
        [ 0.0, -2.0,  0.0,  0.0],
        [ 0.0,  0.0, -4.0, 20.0],
        [ 0.0,  0.0,  0.0, -1.0]
    ]
    
    qubo = QUBOProblem(
        problem_name="emergency_vehicle_conflict_dispatch",
        num_variables=4,
        variable_labels=["V1_Flyover", "V1_Arterial", "V2_Flyover", "V2_Arterial"],
        q_matrix=q_matrix,
        description="Two emergency vehicles avoiding shared bottleneck collision"
    )
    
    solver = QAOAQuboSolver(p_layers=2)
    result = solver.solve(qubo)
    
    assert result.qubit_count == 4
    assert result.circuit_depth > 0
    assert "OPENQASM 2.0" in result.quantum_circuit_qasm
    assert "h q[0];" in result.quantum_circuit_qasm
    assert "cx q[" in result.quantum_circuit_qasm
    assert result.runtime_ms < 2000.0
    assert len(result.state_probabilities) > 0
