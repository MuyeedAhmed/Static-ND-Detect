from z3 import *
import numpy as np
import time

def print_model(s, vars, verify_fn=None, verify_args=None):
    if s.check() == sat:
        m = s.model()
        print("Sat")
        
        if verify_fn:
            verify_fn(m, *verify_args)
        else:
            verify_witness(m, vars)
    else:
        print("Unsat")

def verify_witness(m, vars):
    for v in vars:
        if "00" in str(v):
            try:
                val = m[v].py_value()
                if val is None: val = float('nan')
                print(f"{v} = {val!r}")
            except:
                print(f"{v} = {m[v]}")

def verify_matrix_zero_numpy(m, A_vars, B_vars, n):
    def to_np(mat_vars):
        def get_val(v):
            val = m[v].py_value()
            return val if val is not None else float('nan')
        return np.array([[get_val(v) for v in row] for row in mat_vars])
    
    A, B = to_np(A_vars), to_np(B_vars)
    res = A @ B
    
    print(f"\n--- Numpy Verification (n={n}) ---")
    print(f"A[0][0]: {A[0][0]}")
    print(f"B[0][0]: {B[0][0]}")
    print(f"AB[0][0]: {res[0][0]}")

def check_matrix_zero_element(n):
    print(f"\n--- Checking if AB[0][0] == 0 for positive {n}x{n} matrices ---")
    fp_sort = Float64()
    rm = RoundNearestTiesToEven()
    zero = FPVal(0.0, fp_sort)
    
    def fresh_mat(name, n):
        return [[FP(f"{name}_{i}{j}", fp_sort) for j in range(n)] for i in range(n)]
    
    A = fresh_mat('A', n)
    B = fresh_mat('B', n)
    
    res = fpMul(rm, A[0][0], B[0][0])
    for k in range(1, n):
        res = fpAdd(rm, res, fpMul(rm, A[0][k], B[k][0]))
    
    s = Solver()
    vars = []
    
    for mat in [A, B]:
        for row in mat:
            for v in row:
                s.add(Not(fpIsNaN(v)))
                s.add(Not(fpIsInf(v)))
                s.add(fpGT(v, zero))
                vars.append(v)
    s.add(fpIsZero(res))
    
    start_time = time.time()
    print_model(s, vars, verify_fn=verify_matrix_zero_numpy, verify_args=(A, B, n))
    end_time = time.time()
    print(f"Time: {end_time - start_time:.2f}")

if __name__ == "__main__":
    check_matrix_zero_element(2)
