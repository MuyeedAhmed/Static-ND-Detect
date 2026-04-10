import gurobipy as gp
from gurobipy import GRB
import numpy as np
import time
import pickle

def mat_mul_nxn_gurobi(model, A, B, n):
    C = [[model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"C_{i}_{j}") for j in range(n)] for i in range(n)]
    
    for i in range(n):
        for j in range(n):
            model.addConstr(C[i][j] == gp.quicksum(A[i][k] * B[k][j] for k in range(n)))
            
    return C

def check_matrix_associativity_gurobi(n=2):
    print(f"--- Gurobi Matrix Multiplication ({n}x{n}) ---")
    
    m = gp.Model("MatrixAssociativity")
    m.setParam('NonConvex', 2) 

    def fresh_mat(name, n):
        return [[m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"{name}_{i}_{j}") for j in range(n)] for i in range(n)]
    
    A = fresh_mat('A', n)
    B = fresh_mat('B', n)
    C = fresh_mat('C', n)

    AB = mat_mul_nxn_gurobi(m, A, B, n)
    AB_C = mat_mul_nxn_gurobi(m, AB, C, n)

    BC = mat_mul_nxn_gurobi(m, B, C, n)
    A_BC = mat_mul_nxn_gurobi(m, A, BC, n)

    diff = m.addVar(name="diff")
    m.addConstr(diff == AB_C[0][0] - A_BC[0][0])
    m.addConstr(diff * diff >= 1)
    m.setObjective(diff * diff, GRB.MAXIMIZE)
    m.Params.SolutionLimit = 1
    m.optimize()

    if m.SolCount > 0 or m.status == GRB.OPTIMAL or m.status == GRB.SUBOPTIMAL:
        print(f"Max squared difference found: {m.ObjVal}")
        print(f"AB_C[0][0]: {AB_C[0][0].X}")
        print(f"A_BC[0][0]: {A_BC[0][0].X}")

        # Extract values
        def get_vals(mat, n):
            return [[mat[i][j].X for j in range(n)] for i in range(n)]
        
        A_val = get_vals(A, n)
        B_val = get_vals(B, n)
        C_val = get_vals(C, n)

        print("\nMatrix A:")
        print(np.array(A_val))
        print("\nMatrix B:")
        print(np.array(B_val))
        print("\nMatrix C:")
        print(np.array(C_val))

        # Save to pickle
        with open('solution.pkl', 'wb') as f:
            pickle.dump({'A': A_val, 'B': B_val, 'C': C_val}, f)
        print("\nSaved solution to solution.pkl")
    else:
        print("No counterexample.")

if __name__ == "__main__":
    check_matrix_associativity_gurobi(2)
