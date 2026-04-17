from z3 import *
import numpy as np
import time

def Inverse2x2(simple=True):
    fp_sort = Float64()
    rm = RoundNearestTiesToEven()

    a, b = FP('a', fp_sort), FP('b', fp_sort)
    c, d = FP('c', fp_sort), FP('d', fp_sort)

    det = fpSub(rm, fpMul(rm, a, d), fpMul(rm, b, c))
    one = fpRealToFP(rm, RealVal(1.0), fp_sort)
    zero = fpRealToFP(rm, RealVal(0.0), fp_sort)
    inv_det = fpDiv(rm, one, det)
    
    a_inv = [[fpMul(rm, inv_det, d), fpMul(rm, inv_det, fpNeg(b))],
             [fpMul(rm, inv_det, fpNeg(c)), fpMul(rm, inv_det, a)]]

    res = [
        [fpAdd(rm, fpMul(rm, a, a_inv[0][0]), fpMul(rm, b, a_inv[1][0])),
         fpAdd(rm, fpMul(rm, a, a_inv[0][1]), fpMul(rm, b, a_inv[1][1]))],
        [fpAdd(rm, fpMul(rm, c, a_inv[0][0]), fpMul(rm, d, a_inv[1][0])),
         fpAdd(rm, fpMul(rm, c, a_inv[0][1]), fpMul(rm, d, a_inv[1][1]))]
    ]
    
    s = Solver()
    
    for v in [a, b, c, d]:
        s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)), Not(fpIsZero(v)))
    
    s.add(Not(fpIsZero(det)), Not(fpIsNaN(det)), Not(fpIsInf(det)))
    
    if simple:
        s.add(res[0][1] != zero) 
    else:
        I = [[one, zero], [zero, one]]
        s.add(Or([res[i][j] != I[i][j] for i in range(2) for j in range(2)]))
    
    if s.check() == sat:
        m = s.model()
        def get_val(v):
            val = m.evaluate(v, model_completion=True).py_value()
            return float(val) if val is not None else 0.0
        
        A_np = np.array([[get_val(a), get_val(b)], [get_val(c), get_val(d)]])
        A_inv_vals = [[get_val(a_inv[i][j]) for j in range(2)] for i in range(2)]
        A_inv_np = np.array(A_inv_vals)
        
        print("Matrix A:")
        print(A_np)
        print("\nCalculated Inverse (A_inv):")
        print(A_inv_np)
        
        prod = A_np @ A_inv_np
        print("\nA * A_inv:")
        print(prod)
        
        print(f"\n Equal: {np.array_equal(prod, np.eye(2))}")
        print(f"Max difference: {np.max(np.abs(prod - np.eye(2)))}")
    else:
        print("Unsat.")

def Inverse_nxn(N=2, fp_type='double', timeout=60000, simple=True):
    fp_sort = Float64() if fp_type == 'double' else Float32()
    rm = RoundNearestTiesToEven()
    
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]

    def det_sym(M):
        n = len(M)
        if n == 1: return M[0][0]
        if n == 2: return fpSub(rm, fpMul(rm, M[0][0], M[1][1]), fpMul(rm, M[0][1], M[1][0]))
        d = None
        for j in range(n):
            minor = [row[:j] + row[j+1:] for row in M[1:]]
            term = fpMul(rm, M[0][j], det_sym(minor))
            if j % 2 == 1: term = fpNeg(term)
            d = term if d is None else fpAdd(rm, d, term)
        return d

    def inv_sym(M):
        n = len(M)
        if n == 1:
            one = fpRealToFP(rm, RealVal(1.0), fp_sort)
            return [[fpDiv(rm, one, M[0][0])]], M[0][0]
        
        d = det_sym(M)
        cofactors = [[None for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                minor = [row[:j] + row[j+1:] for row in (M[:i] + M[i+1:])]
                cofactor = det_sym(minor)
                if (i + j) % 2 == 1: cofactor = fpNeg(cofactor)
                cofactors[i][j] = cofactor
        
        adj = [[cofactors[j][i] for j in range(n)] for i in range(n)]
        one = fpRealToFP(rm, RealVal(1.0), fp_sort)
        inv_det = fpDiv(rm, one, d)
        inv = [[fpMul(rm, inv_det, adj[i][j]) for j in range(n)] for i in range(n)]
        return inv, d

    A_inv, det = inv_sym(A)

    def mul_sym(M1, M2):
        n = len(M1)
        res = [[None for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                s = None
                for k in range(n):
                    term = fpMul(rm, M1[i][k], M2[k][j])
                    s = term if s is None else fpAdd(rm, s, term)
                res[i][j] = s
        return res

    prod_sym = mul_sym(A, A_inv)
    I = [[(fpRealToFP(rm, RealVal(1.0), fp_sort) if i == j else fpRealToFP(rm, RealVal(0.0), fp_sort)) for j in range(N)] for i in range(N)]

    s = Solver()
    s.set("timeout", timeout)
    
    for row in A:
        for v in row:
            s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)), Not(fpIsZero(v)))
            s.add(v >= 0.5, v <= 5.0)

    s.add(Not(fpIsZero(det)), Not(fpIsNaN(det)), Not(fpIsInf(det)))
    if simple:
        s.add(prod_sym[0][1] != zero)
    else:
        s.add(Or([prod_sym[i][j] != I[i][j] for i in range(N) for j in range(N)]))

    res = s.check()

    if res == sat:
        m = s.model()
        def gv(v):
            try: return float(m.evaluate(v, model_completion=True).py_value())
            except: return 0.0
        
        A_np = np.array([[gv(A[i][j]) for j in range(N)] for i in range(N)])
        A_inv_np = np.array([[gv(A_inv[i][j]) for j in range(N)] for i in range(N)])
        print(f"\nMatrix A:\n{A_np}\n\nInverse:\n{A_inv_np}")
        p = A_np @ A_inv_np
        print(f"\nA * A_inv:\n{np.round(p, 15)}")
        print(f"\nStrictly equal to I? {np.array_equal(p, np.eye(N))}")
        print(f"Max diff: {np.max(np.abs(p - np.eye(N)))}")
    else:
        print(f"Result: {res}")



if __name__ == "__main__":
    start_time = time.time()
    Inverse2x2()
    print(f"Execution time: {time.time() - start_time:.2f} seconds")
    start_time = time.time()
    Inverse_nxn(N=3, fp_type='double', timeout=60000)
    print(f"Execution time: {time.time() - start_time:.2f} seconds")
    
