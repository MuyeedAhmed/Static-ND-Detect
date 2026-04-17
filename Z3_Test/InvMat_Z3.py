from z3 import *
import numpy as np

def Inverse2x2():
    fp_sort = Float64()
    rm = RoundNearestTiesToEven()

    a, b = FP('a', fp_sort), FP('b', fp_sort)
    c, d = FP('c', fp_sort), FP('d', fp_sort)

    det = fpSub(rm, fpMul(rm, a, d), fpMul(rm, b, c))
    one = fpRealToFP(rm, RealVal(1.0), fp_sort)
    inv_det = fpDiv(rm, one, det)
    
    a_inv = [[fpMul(rm, inv_det, d), fpMul(rm, inv_det, fpNeg(b))],
             [fpMul(rm, inv_det, fpNeg(c)), fpMul(rm, inv_det, a)]]

    res = [
        [fpAdd(rm, fpMul(rm, a, a_inv[0][0]), fpMul(rm, b, a_inv[1][0])),
         fpAdd(rm, fpMul(rm, a, a_inv[0][1]), fpMul(rm, b, a_inv[1][1]))],
        [fpAdd(rm, fpMul(rm, c, a_inv[0][0]), fpMul(rm, d, a_inv[1][0])),
         fpAdd(rm, fpMul(rm, c, a_inv[0][1]), fpMul(rm, d, a_inv[1][1]))]
    ]

    zero = fpRealToFP(rm, RealVal(0.0), fp_sort)
    I = [[one, zero], [zero, one]]

    s = Solver()
    
    for v in [a, b, c, d]:
        s.add(Not(fpIsNaN(v)), Not(fpIsInf(v)), Not(fpIsZero(v)))
        s.add(v >= 1.0)
        s.add(v <= 10.0)
    
    s.add(Not(fpIsZero(det)), Not(fpIsNaN(det)), Not(fpIsInf(det)))
    
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
        
        print(f"\nStrictly equal to Identity? {np.array_equal(prod, np.eye(2))}")
        print(f"Max difference from Identity: {np.max(np.abs(prod - np.eye(2)))}")
    else:
        print("No such matrix found.")

if __name__ == "__main__":
    Inverse2x2()
