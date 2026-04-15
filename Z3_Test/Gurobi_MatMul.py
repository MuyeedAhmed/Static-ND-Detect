import gurobipy as gp
from gurobipy import GRB
import numpy as np
import time
import pickle

import os
from decimal import Decimal, getcontext

def mat_mul_nxn_gurobi(model, A, B, n):
    C = [[model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"C_{i}_{j}") for j in range(n)] for i in range(n)]
    
    for i in range(n):
        for j in range(n):
            model.addConstr(C[i][j] == gp.quicksum(A[i][k] * B[k][j] for k in range(n)))
            
    return C

def check_matrix_associativity_gurobi(n=2):
    print(f"--- Gurobi MatMul ({n}x{n}) ---")
    
    m = gp.Model("MatrixAssociativity")
    m.setParam('NonConvex', 2) 
    m.setParam('FeasibilityTol', 1e-9)
    m.setParam('NumericFocus', 3) 
    m.setParam('ScaleFlag', 0) 
    
    def fresh_mat(name, n):
        mat = [[m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"{name}_{i}_{j}") for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(n):
                v = mat[i][j]
                is_nonzero = m.addVar(vtype=GRB.BINARY, name=f"nz_{name}_{i}_{j}")
                is_pos = m.addVar(vtype=GRB.BINARY, name=f"pos_{name}_{i}_{j}")
                is_neg = m.addVar(vtype=GRB.BINARY, name=f"neg_{name}_{i}_{j}")
                
                m.addConstr(is_pos + is_neg == is_nonzero)
                
                m.addGenConstrIndicator(is_nonzero, False, v == 0)
                m.addGenConstrIndicator(is_pos, True, v >= 1e-4)
                m.addGenConstrIndicator(is_neg, True, v <= -1e-4)
        return mat
    
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
        print(f"Max squared difference: {m.ObjVal}")
        print(f"AB_C[0][0]: {AB_C[0][0].X}")
        print(f"A_BC[0][0]: {A_BC[0][0].X}")

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

        with open('solution.pkl', 'wb') as f:
            pickle.dump({'A': A_val, 'B': B_val, 'C': C_val}, f)
        verify()
    else:
        print("No counterexample")



getcontext().prec = 100

def verify():
    pickle_file = 'solution.pkl'
    with open(pickle_file, 'rb') as f:
        data = pickle.load(f)

    A_list = data['A']
    B_list = data['B']
    C_list = data['C']

    A_np = np.array(A_list)
    B_np = np.array(B_list)
    C_np = np.array(C_list)

    print(f"A:\n{A_np}")
    print(f"B:\n{B_np}")
    print(f"C:\n{C_np}")

    AB_np = np.dot(A_np, B_np)
    ABC_np = np.dot(AB_np, C_np)
    
    BC_np = np.dot(B_np, C_np)
    A_BC_np = np.dot(A_np, BC_np)
    
    print(f"(AB)C[0,0]: {ABC_np[0,0]}")
    print(f"A(BC)[0,0]: {A_BC_np[0,0]}")
    print(f"(AB)C:\n{ABC_np}")
    print(f"A(BC):\n{A_BC_np}")

    diff_np = ABC_np[0,0] - A_BC_np[0,0]
    print(f"Difference: {diff_np}")
    print(f"Squared Difference: {diff_np**2}")

    # print("\n--- Decimal Verification ---")
    # def mat_mul_decimal(M1, M2):
    #     n = len(M1)
    #     res = [[Decimal(0) for _ in range(n)] for _ in range(n)]
    #     for i in range(n):
    #         for j in range(n):
    #             for k in range(n):
    #                 res[i][j] += Decimal(str(M1[i][k])) * Decimal(str(M2[k][j]))
    #     return res

    # A_dec = [[Decimal(str(x)) for x in row] for row in A_list]
    # B_dec = [[Decimal(str(x)) for x in row] for row in B_list]
    # C_dec = [[Decimal(str(x)) for x in row] for row in C_list]

    # ABC_dec = mat_mul_decimal(mat_mul_decimal(A_dec, B_dec), C_dec)
    # A_BC_dec = mat_mul_decimal(A_dec, mat_mul_decimal(B_dec, C_dec))

    # print(f"(AB)C[0,0]: {ABC_dec[0][0]}")
    # print(f"A(BC)[0,0]: {A_BC_dec[0][0]}")
    
    # diff_dec = ABC_dec[0][0] - A_BC_dec[0][0]
    # print(f"Difference: {diff_dec}")
    # print(f"Squared Difference: {diff_dec**2}")


if __name__ == "__main__":
    check_matrix_associativity_gurobi(5)
    
