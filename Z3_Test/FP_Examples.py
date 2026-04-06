from z3 import *
import numpy as np
import time

def print_model(s, vars, verify_fn=None, verify_args=None):
    if s.check() == sat:
        m = s.model()
        for v in vars:
            print(f"{v}: {m[v]}")
        
        if verify_fn:
            verify_fn(m, *verify_args)
        else:
            verify_witness(m, vars)
    else:
        print("Unsat (Property holds or is too constrained)")

def verify_witness(m, vars):
    print("\n--- Witness Verification (Python Floats) ---")
    for v in vars:
        try:
            val = m[v].py_value()
            if val is None: val = float('nan')
            print(f"{v} = {val!r}")
        except:
            print(f"{v} = {m[v]}")

def verify_matrix_associativity_numpy(m, A_vars, B_vars, C_vars):
    def to_np(mat_vars):
        def get_val(v):
            val = m[v].py_value()
            return val if val is not None else float('nan')
        return np.array([[get_val(v) for v in row] for row in mat_vars])
    
    A, B, C = to_np(A_vars), to_np(B_vars), to_np(C_vars)
    res1 = (A @ B) @ C
    res2 = A @ (B @ C)
    
    print("\n--- Numpy Verification (Matrix Associativity) ---")
    print(f"(A * B) * C:\n{res1}")
    print(f"A * (B * C):\n{res2}")
    print(f"Equal? {np.array_equal(res1, res2)}")
    print(f"Max Diff: {np.max(np.abs(res1 - res2))}")

def verify_det_product_numpy(m, A_vars, B_vars):
    def to_np(mat_vars):
        def get_val(v):
            val = m[v].py_value()
            return val if val is not None else float('nan')
        return np.array([[get_val(v) for v in row] for row in mat_vars])
    
    A, B = to_np(A_vars), to_np(B_vars)
    det_AB = np.linalg.det(A @ B)
    detA_detB = np.linalg.det(A) * np.linalg.det(B)
    
    print("\n--- Numpy Verification (Determinant Product Rule) ---")
    print(f"det(A * B): {det_AB}")
    print(f"det(A) * det(B): {detA_detB}")
    print(f"Equal? {det_AB == detA_detB}")
    print(f"Diff: {abs(det_AB - detA_detB)}")

def mat_mul_nxn(A, B, n, rm):
    C = [[None for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            res = fpMul(rm, A[i][0], B[0][j])
            for k in range(1, n):
                res = fpAdd(rm, res, fpMul(rm, A[i][k], B[k][j]))
            C[i][j] = res
    return C

def check_scalar_mult_associativity():
    print("\n--- Scalar Multiplication Associativity: (A * B) * C != A * (B * C) ---")
    fp_sort = Float64()
    A, B, C = FP('A', fp_sort), FP('B', fp_sort), FP('C', fp_sort)
    rm = RoundNearestTiesToEven()
    
    res1 = fpMul(rm, fpMul(rm, A, B), C)
    res2 = fpMul(rm, A, fpMul(rm, B, C))
    
    s = Solver()
    for v in [A, B, C]:
        s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)), Not(fpIsZero(v)))
    
    s.add(res1 != res2)
    print_model(s, [A, B, C])

def check_distributive_law():
    print("\n--- Distributive Law: A * (B + C) != (A * B) + (A * C) ---")
    fp_sort = Float64()
    A, B, C = FP('A', fp_sort), FP('B', fp_sort), FP('C', fp_sort)
    rm = RoundNearestTiesToEven()
    
    res1 = fpMul(rm, A, fpAdd(rm, B, C))
    res2 = fpAdd(rm, fpMul(rm, A, B), fpMul(rm, A, C))
    
    s = Solver()
    for v in [A, B, C]:
        s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)), Not(fpIsZero(v)))
    
    s.add(res1 != res2)
    print_model(s, [A, B, C])

def mat_mul_2x2(A, B, rm):
    return [
        [fpAdd(rm, fpMul(rm, A[0][0], B[0][0]), fpMul(rm, A[0][1], B[1][0])),
         fpAdd(rm, fpMul(rm, A[0][0], B[0][1]), fpMul(rm, A[0][1], B[1][1]))],
        [fpAdd(rm, fpMul(rm, A[1][0], B[0][0]), fpMul(rm, A[1][1], B[1][0])),
         fpAdd(rm, fpMul(rm, A[1][0], B[0][1]), fpMul(rm, A[1][1], B[1][1]))]
    ]

def check_matrix_mult_associativity():
    print("\n--- Matrix Multiplication Associativity (2x2): (A * B) * C != A * (B * C) ---")
    fp_sort = Float64()
    rm = RoundNearestTiesToEven()
    
    def fresh_mat(name):
        return [[FP(f"{name}_{i}{j}", fp_sort) for j in range(2)] for i in range(2)]
    
    A, B, C = fresh_mat('A'), fresh_mat('B'), fresh_mat('C')
    
    AB_C = mat_mul_2x2(mat_mul_2x2(A, B, rm), C, rm)
    A_BC = mat_mul_2x2(A, mat_mul_2x2(B, C, rm), rm)
    
    s = Solver()
    vars = []
    for mat in [A, B, C]:
        for row in mat:
            for v in row:
                s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)))
                vars.append(v)
    
    disjunction = Or([AB_C[i][j] != A_BC[i][j] for i in range(2) for j in range(2)])
    s.add(disjunction)
    
    print_model(s, vars, verify_fn=verify_matrix_associativity_numpy, verify_args=(A, B, C))

def det_2x2(M, rm):
    return fpSub(rm, fpMul(rm, M[0][0], M[1][1]), fpMul(rm, M[0][1], M[1][0]))

def check_det_product_rule():
    print("\n--- Determinant Product Rule: det(A * B) != det(A) * det(B) ---")
    fp_sort = Float64()
    rm = RoundNearestTiesToEven()
    
    def fresh_mat(name):
        return [[FP(f"{name}_{i}{j}", fp_sort) for j in range(2)] for i in range(2)]
    
    A, B = fresh_mat('A'), fresh_mat('B')
    
    det_AB = det_2x2(mat_mul_2x2(A, B, rm), rm)
    detA_detB = fpMul(rm, det_2x2(A, rm), det_2x2(B, rm))
    
    s = Solver()
    vars = []
    for mat in [A, B]:
        for row in mat:
            for v in row:
                s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)))
                vars.append(v)
    
    s.add(det_AB != detA_detB)
    print_model(s, vars, verify_fn=verify_det_product_numpy, verify_args=(A, B))

def check_matrix_mult_associativity_nxn(n):
    print(f"\n--- Matrix Multiplication Associativity ({n}x{n}): (A * B) * C != A * (B * C) ---")
    fp_sort = Float64()
    rm = RoundNearestTiesToEven()
    
    def fresh_mat(name, n):
        return [[FP(f"{name}_{i}{j}", fp_sort) for j in range(n)] for i in range(n)]
    
    A, B, C = fresh_mat('A', n), fresh_mat('B', n), fresh_mat('C', n)
    
    AB_C = mat_mul_nxn(mat_mul_nxn(A, B, n, rm), C, n, rm)
    A_BC = mat_mul_nxn(A, mat_mul_nxn(B, C, n, rm), n, rm)
    
    s = Solver()
    vars = []
    for mat in [A, B, C]:
        for row in mat:
            for v in row:
                s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)))
                vars.append(v)
    
    disjunction = Or([AB_C[i][j] != A_BC[i][j] for i in range(n) for j in range(n)])
    s.add(disjunction)
    
    print_model(s, vars, verify_fn=verify_matrix_associativity_numpy, verify_args=(A, B, C))

if __name__ == "__main__":

    start_time = time.time()
    check_scalar_mult_associativity()
    end_time = time.time()
    print(f"Time taken for scalar multiplication associativity: {end_time - start_time:.2f} seconds")
    start_time = time.time()
    check_distributive_law()
    end_time = time.time()
    print(f"Time taken for distributive law: {end_time - start_time:.2f} seconds")
    start_time = time.time()
    check_matrix_mult_associativity()
    end_time = time.time()
    print(f"Time taken for matrix multiplication associativity: {end_time - start_time:.2f} seconds")
    start_time = time.time()
    check_det_product_rule()
    end_time = time.time()
    print(f"Time taken for determinant product rule: {end_time - start_time:.2f} seconds")
    start_time = time.time()
    check_matrix_mult_associativity_nxn(3)
    end_time = time.time()
    print(f"Time taken for 3x3 matrix multiplication associativity: {end_time - start_time:.2f} seconds")
