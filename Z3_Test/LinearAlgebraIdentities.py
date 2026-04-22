from z3 import *
import numpy as np
import time


def matmul_sym(M1, M2, fp=True, rm=None):
    n, m, p = len(M1), len(M2[0]), len(M1[0])
    res = [[None for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s = None
            for k in range(p):
                term = fpMul(rm, M1[i][k], M2[k][j]) if fp else M1[i][k] * M2[k][j]
                if s is None: s = term
                else: s = fpAdd(rm, s, term) if fp else s + term
            res[i][j] = s
    return res

def transpose_sym(M):
    return [[M[j][i] for j in range(len(M))] for i in range(len(M[0]))]

def add_sym(M1, M2, fp=True, rm=None):
    n, m = len(M1), len(M1[0])
    return [[(fpAdd(rm, M1[i][j], M2[i][j]) if fp else M1[i][j] + M2[i][j]) for j in range(m)] for i in range(n)]

def det_sym(M, fp=True, rm=None):
    n = len(M)
    if n == 1: return M[0][0]
    if n == 2:
        if fp: return fpSub(rm, fpMul(rm, M[0][0], M[1][1]), fpMul(rm, M[0][1], M[1][0]))
        return M[0][0] * M[1][1] - M[0][1] * M[1][0]
    d = None
    for j in range(n):
        minor = [row[:j] + row[j+1:] for row in M[1:]]
        term = fpMul(rm, M[0][j], det_sym(minor, fp, rm)) if fp else M[0][j] * det_sym(minor)
        if j % 2 == 1:
            term = fpNeg(term) if fp else -term
        if d is None: d = term
        else: d = fpAdd(rm, d, term) if fp else d + term
    return d

def inv_sym(M, fp=True, rm=None, fp_sort=None):
    n = len(M)
    d = det_sym(M, fp, rm)
    if n == 1:
        one = fpRealToFP(rm, RealVal(1.0), fp_sort) if fp else 1
        return [[(fpDiv(rm, one, M[0][0]) if fp else one / M[0][0])]], d
    
    cofactors = [[None for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            minor = [row[:j] + row[j+1:] for row in (M[:i] + M[i+1:])]
            cofactor = det_sym(minor, fp, rm)
            if (i + j) % 2 == 1:
                cofactor = fpNeg(cofactor) if fp else -cofactor
            cofactors[i][j] = cofactor
    
    adj = [[cofactors[j][i] for j in range(n)] for i in range(n)]
    if fp:
        one = fpRealToFP(rm, RealVal(1.0), fp_sort)
        inv_det = fpDiv(rm, one, d)
        inv = [[fpMul(rm, inv_det, adj[i][j]) for j in range(n)] for i in range(n)]
    else:
        inv = [[adj[i][j] / d for j in range(n)] for i in range(n)]
    return inv, d

def identity_sym(N, fp=True, rm=None, fp_sort=None):
    res = [[None for _ in range(N)] for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                res[i][j] = fpRealToFP(rm, RealVal(1.0), fp_sort) if fp else 1.0
            else:
                res[i][j] = fpRealToFP(rm, RealVal(0.0), fp_sort) if fp else 0.0
    return res

# Z3 run
def check_identity(name, solver_cond, matrices, LHS_sym=None, RHS_sym=None, timeout=1800000):
    s = Solver()
    s.set("timeout", timeout)
    s.add(solver_cond)
    
    print(f"--- Checking Identity (FP): {name} ---")
    start = time.time()
    res = s.check()
    duration = time.time() - start
    
    if res == sat:
        print(f"Result: SAT (Counter-example found in {duration:.2f}s)")
        m = s.model()
        def gv(v):
            try:
                val = m.evaluate(v, model_completion=True)
                if is_fp(val):
                    return float(val.py_value())
                return float(val.as_decimal(10).replace("?", ""))
            except:
                return 0.0
        
        vals = {}
        for m_name, m_sym in matrices.items():
            val = np.array([[gv(v) for v in row] for row in m_sym])
            vals[m_name] = val
            print(f"Matrix {m_name}:\n{val}")

        if LHS_sym is not None and RHS_sym is not None:
            def eval_sym(sym):
                if isinstance(sym, list):
                    return np.array([[gv(v) for v in row] for row in sym])
                return gv(sym)
            
            lhs_val = eval_sym(LHS_sym)
            rhs_val = eval_sym(RHS_sym)
            print(f"LHS Value:\n{lhs_val}")
            print(f"RHS Value:\n{rhs_val}")
            print(f"Difference (LHS - RHS):\n{lhs_val - rhs_val}")
            
    elif res == unsat:
        print(f"Result: UNSAT (Identity holds in {duration:.2f}s)")
    else:
        print(f"Result: {res}")
    print()

def get_fp_setup(N):
    fp_sort = Float32()
    rm = RoundNearestTiesToEven()
    return fp_sort, rm

def get_valid_constraints(matrices):
    conds = []
    for M in matrices:
        for row in M:
            for v in row:
                conds.append(Not(fpIsNaN(v)))
                conds.append(Not(fpIsInf(v)))
                conds.append(Not(fpIsSubnormal(v)))
                # conds.append(v >= 0.5)
                # conds.append(v <= 2.0)
    return And(conds)

# (A+B)^T = A^T + B^T
def VerifyTransposeSum(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    B = [[FP(f'b_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    LHS = transpose_sym(add_sym(A, B, fp=True, rm=rm))
    RHS = add_sym(transpose_sym(A), transpose_sym(B), fp=True, rm=rm)
    
    valid = get_valid_constraints([A, B])
    # diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    diff = (LHS[0][1] != RHS[0][1])
   
    check_identity("(A+B)^T = A^T + B^T", And(valid, diff), {"A": A, "B": B}, LHS, RHS)

# (A*B)^T = B^T * A^T
def VerifyTransposeProduct(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    B = [[FP(f'b_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    AB = matmul_sym(A, B, fp=True, rm=rm)
    LHS = transpose_sym(AB)
    RHS = matmul_sym(transpose_sym(B), transpose_sym(A), fp=True, rm=rm)
    
    valid = get_valid_constraints([A, B])
    # diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    diff = (LHS[0][1] != RHS[0][1])
    
    check_identity("(A*B)^T = B^T * A^T", And(valid, diff), {"A": A, "B": B}, LHS, RHS)

# (A^-1)^-1 = A
def VerifyInverseInverse(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    A_inv, detA = inv_sym(A, fp=True, rm=rm, fp_sort=fp_sort)
    LHS, detA_inv = inv_sym(A_inv, fp=True, rm=rm, fp_sort=fp_sort)
    RHS = A
    
    valid = And(get_valid_constraints([A]), 
                Not(fpIsZero(detA)), Not(fpIsNaN(detA)), Not(fpIsInf(detA)),
                Not(fpIsZero(detA_inv)), Not(fpIsNaN(detA_inv)), Not(fpIsInf(detA_inv)))
    
    # diff = Or([LHS[i][j] != A[i][j] for i in range(N) for j in range(N)])
    diff = (LHS[0][1] != A[0][1])
    
    check_identity("(A^-1)^-1 = A", And(valid, diff), {"A": A}, LHS, RHS)

# (A*B)^-1 = B^-1 * A^-1
def VerifyInverseProduct(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    B = [[FP(f'b_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    AB = matmul_sym(A, B, fp=True, rm=rm)
    LHS, detAB = inv_sym(AB, fp=True, rm=rm, fp_sort=fp_sort)
    
    A_inv, detA = inv_sym(A, fp=True, rm=rm, fp_sort=fp_sort)
    B_inv, detB = inv_sym(B, fp=True, rm=rm, fp_sort=fp_sort)
    RHS = matmul_sym(B_inv, A_inv, fp=True, rm=rm)
    
    valid = And(get_valid_constraints([A, B]),
                Not(fpIsZero(detA)), Not(fpIsNaN(detA)), Not(fpIsInf(detA)),
                Not(fpIsZero(detB)), Not(fpIsNaN(detB)), Not(fpIsInf(detB)),
                Not(fpIsZero(detAB)), Not(fpIsNaN(detAB)), Not(fpIsInf(detAB)))
    
    # diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    diff = (LHS[0][1] != RHS[0][1])

    check_identity("(A*B)^-1 = B^-1 * A^-1", And(valid, diff), {"A": A, "B": B}, LHS, RHS)

# (A^T)^-1 = (A^-1)^T
def VerifyTransposeInverse(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    AT = transpose_sym(A)
    LHS, detAT = inv_sym(AT, fp=True, rm=rm, fp_sort=fp_sort)
    
    A_inv, detA = inv_sym(A, fp=True, rm=rm, fp_sort=fp_sort)
    RHS = transpose_sym(A_inv)
    
    valid = And(get_valid_constraints([A]),
                Not(fpIsZero(detA)), Not(fpIsNaN(detA)), Not(fpIsInf(detA)),
                Not(fpIsZero(detAT)), Not(fpIsNaN(detAT)), Not(fpIsInf(detAT)))
    
    # diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    diff = (LHS[0][1] != RHS[0][1])

    check_identity("(A^T)^-1 = (A^-1)^T", And(valid, diff), {"A": A}, LHS, RHS)

# A * A^-1 = I
def VerifyInverseIdentity(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    A_inv, detA = inv_sym(A, fp=True, rm=rm, fp_sort=fp_sort)
    
    LHS = matmul_sym(A, A_inv, fp=True, rm=rm)
    RHS = identity_sym(N, fp=True, rm=rm, fp_sort=fp_sort)
    
    valid = And(get_valid_constraints([A]),
                Not(fpIsZero(detA)), Not(fpIsNaN(detA)), Not(fpIsInf(detA)))
    
    diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    
    check_identity("A * A^-1 = I", And(valid, diff), {"A": A}, LHS, RHS)

# det(A*B) = det(A) * det(B)
def VerifyDeterminantProduct(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    B = [[FP(f'b_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    AB = matmul_sym(A, B, fp=True, rm=rm)
    LHS = det_sym(AB, fp=True, rm=rm)
    
    detA = det_sym(A, fp=True, rm=rm)
    detB = det_sym(B, fp=True, rm=rm)
    RHS = fpMul(rm, detA, detB)
    
    valid = get_valid_constraints([A, B])
    diff = (LHS != RHS)
    
    check_identity("det(A*B) = det(A) * det(B)", And(valid, diff), {"A": A, "B": B}, LHS, RHS)

# A(BC) = (AB)C
def VerifyMultiplicationAssociativity(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    B = [[FP(f'b_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    C = [[FP(f'c_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    BC = matmul_sym(B, C, fp=True, rm=rm)
    LHS = matmul_sym(A, BC, fp=True, rm=rm)
    
    AB = matmul_sym(A, B, fp=True, rm=rm)
    RHS = matmul_sym(AB, C, fp=True, rm=rm)
    
    valid = get_valid_constraints([A, B, C])
    diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    
    check_identity("A(BC) = (AB)C", And(valid, diff), {"A": A, "B": B, "C": C}, LHS, RHS)

# A(B+C) = AB + AC
def VerifyDistributivity(N=2):
    fp_sort, rm = get_fp_setup(N)
    A = [[FP(f'a_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    B = [[FP(f'b_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    C = [[FP(f'c_{i}_{j}', fp_sort) for j in range(N)] for i in range(N)]
    
    BplusC = add_sym(B, C, fp=True, rm=rm)
    LHS = matmul_sym(A, BplusC, fp=True, rm=rm)
    
    AB = matmul_sym(A, B, fp=True, rm=rm)
    AC = matmul_sym(A, C, fp=True, rm=rm)
    RHS = add_sym(AB, AC, fp=True, rm=rm)
    
    valid = get_valid_constraints([A, B, C])
    diff = Or([LHS[i][j] != RHS[i][j] for i in range(N) for j in range(N)])
    
    check_identity("A(B+C) = AB + AC", And(valid, diff), {"A": A, "B": B, "C": C}, LHS, RHS)

if __name__ == "__main__":
    VerifyTransposeSum(N=2)
    VerifyInverseInverse(N=2)
    VerifyInverseProduct(N=2)
    VerifyTransposeProduct(N=2)
    VerifyTransposeInverse(N=2)
    # VerifyInverseIdentity(N=2)
    # VerifyDeterminantProduct(N=2)
    # VerifyMultiplicationAssociativity(N=2)
    # VerifyDistributivity(N=2)
