from z3 import *

def check_fp_associativity():
    fp_sort = Float64()
    
    A = FP('A', fp_sort)
    B = FP('B', fp_sort)
    C = FP('C', fp_sort)
    
    rm = RoundNearestTiesToEven()
    
    sum1 = fpAdd(rm, fpAdd(rm, A, B), C)
    sum2 = fpAdd(rm, A, fpAdd(rm, B, C))
    
    s = Solver()
    
    s.add(Not(fpIsNaN(A)), Not(fpIsInf(A)))
    s.add(Not(fpIsNaN(B)), Not(fpIsInf(B)))
    s.add(Not(fpIsNaN(C)), Not(fpIsInf(C)))
    
    s.add(sum1 != sum2)
    
    if s.check() == sat:
        m = s.model()
        print(f"A: {m[A]}")
        print(f"B: {m[B]}")
        print(f"C: {m[C]}")
    else:
        print("Unsat")

if __name__ == "__main__":
    check_fp_associativity()
    
    