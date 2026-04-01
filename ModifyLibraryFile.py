import os
import ast
import shutil
import pandas as pd
import csv

class ModifyLibraryFile:
    RANDOM_KEYWORDS = {
        "random", "rand", "seed", "shuffle", "sample", "choice",
        "rvs", "qrvs", "time", "clock", "perf_counter", "uuid",
        "urandom", "getrandom", "hash", "id"
    }
    FP_SENSITIVE_KEYWORDS = {
        "dot", "matmul", "linalg", "solve", "eig", "svd", "inv", "det"
    }

    def __init__(self, FilePath):
        self.FilePath = FilePath
        self.OriginalCodeTemporaryPath = self.FilePath[:-3]+"_Original.py"
        self.OutputFilePath = self.FilePath[:-3]+"_Output.py"
        
        self.VariableDF = pd.DataFrame()
    
    def is_nondeterministic(self, node_value):
        rhs_string = ast.unparse(node_value).lower()
        
        all_keywords = self.RANDOM_KEYWORDS | self.FP_SENSITIVE_KEYWORDS
        
        for subnode in ast.walk(node_value):
            if isinstance(subnode, ast.Call):
                func_name = ast.unparse(subnode.func).lower()
                if any(kw in func_name for kw in all_keywords):
                    return True
        
        if any(kw in rhs_string for kw in self.RANDOM_KEYWORDS):
            return True
            
        return False

    def init_decorator(self):
        self.NewFile.write("import pandas as pd\n")
        self.NewFile.write("import numpy\n\n")

        self.NewFile.write("def _add_taint(variable, name):\n")
        self.NewFile.write("    # Static taint source for Pysa\n")
        self.NewFile.write("    _source = input()\n")
        self.NewFile.write("    try:\n")
        self.NewFile.write("        if isinstance(variable, (int, float, complex, numpy.number)):\n")
        self.NewFile.write("            return variable + _source\n")
        self.NewFile.write("        elif isinstance(variable, (list, dict, set, pd.DataFrame, numpy.ndarray)):\n")
        self.NewFile.write("            # For collections, returning the source is enough to mark the variable as tainted\n")
        self.NewFile.write("            return _source\n")
        self.NewFile.write("    except:\n")
        self.NewFile.write("        pass\n")
        self.NewFile.write("    return _source\n")
    def reset(self):
        os.remove(self.FilePath)
        os.rename(self.OriginalCodeTemporaryPath, self.FilePath)
        os.system('rm -rf VariableValues/*')
           
    
    def add_taint(self, spaces, functionName, variableName, lineCount):
        self.NewFile.write(f"{spaces}{variableName} = _add_taint({variableName}, \'{variableName}\', {lineCount})#Taint\n")

    def GetVariableNamesAndLineNumber(self):
        var_dict = {'LineNumber': [], 'VariableName': [], 'StartLineNumber': [], 'RHS_String': []}
        # function_name = None
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                if not self.is_nondeterministic(node.value):
                    continue
                rhs_string = ast.unparse(node.value)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_dict['LineNumber'].append(node.end_lineno)
                        var_dict['VariableName'].append(target.id)
                        var_dict['StartLineNumber'].append(node.lineno)
                        var_dict['RHS_String'].append(rhs_string)
                        
                    elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        if target.value.id == 'self':
                            s = f'self.{target.attr}'
                        else:
                            s = f'{target.value.id}.{target.attr}'
                        var_dict['LineNumber'].append(node.end_lineno)
                        var_dict['VariableName'].append(s)
                        var_dict['StartLineNumber'].append(node.lineno)
                        var_dict['RHS_String'].append(rhs_string)
                    elif isinstance(target, ast.Subscript):
                        # e[:, it % convergence_iter] = E
                        if isinstance(target.value, ast.Name):
                            var_dict['LineNumber'].append(node.end_lineno)
                            var_dict['VariableName'].append(target.value.id)
                            var_dict['StartLineNumber'].append(node.lineno)
                            var_dict['RHS_String'].append(rhs_string)
                        # S.flat[:: (n_samples + 1)] = preference
                        elif isinstance(target.value.value, ast.Name):
                            var_dict['LineNumber'].append(node.end_lineno)
                            var_dict['VariableName'].append(target.value.value.id)
                            var_dict['StartLineNumber'].append(node.lineno)
                            var_dict['RHS_String'].append(rhs_string)
                    # a, b = 5, 7
                    else:
                        try:
                            variable_names = [target.id for target in node.targets[0].elts if isinstance(target, ast.Name)]
                            for v in variable_names:
                                var_dict['LineNumber'].append(node.end_lineno)
                                var_dict['VariableName'].append(v)
                                var_dict['StartLineNumber'].append(node.lineno)
                                var_dict['RHS_String'].append(rhs_string)
                        except Exception as e:
                            # print("Error in ", node.lineno, self.FilePath, "\nError:", e)
                            pass
            elif isinstance(node, ast.AugAssign):
                if not self.is_nondeterministic(node.value):
                    continue
                rhs_string = ast.unparse(node.value)
                if isinstance(node.target, ast.Name):
                    var_dict['LineNumber'].append(node.end_lineno)
                    var_dict['VariableName'].append(node.target.id)
                    var_dict['StartLineNumber'].append(node.lineno)
                    var_dict['RHS_String'].append(rhs_string)
            
            
        self.VariableDF = pd.DataFrame(var_dict)
        # print(self.VariableDF)
        
    def CreateNewFileWithDecorator(self):
        self.GetVariableNamesAndLineNumber()
        if self.VariableDF.shape[0] == 0:
            print("No variables found in the file.")
            self.NewFile.write(self.code)
            return
        RandomVars = self.VariableDF
        
        self.init_decorator()
        OrginalFile = open(self.OriginalCodeTemporaryPath, 'r')
        OrginalFileLines = OrginalFile.readlines()
        OFLines = iter(OrginalFileLines)
        lineCount = 0
        spaces = ''
        for line in OFLines:
            self.NewFile.write(line)
            lineCount+=1
            if RandomVars[RandomVars["StartLineNumber"] == lineCount].shape[0] > 0:
                num_spaces = len(line) - len(line.lstrip(' '))
                spaces = ' ' * num_spaces
            filtered_df = RandomVars[RandomVars["LineNumber"] == lineCount]
            if filtered_df.shape[0] > 0:
                for index, row in filtered_df.iterrows():
                    self.add_taint(spaces, "Global", row["VariableName"], row["LineNumber"])
                spaces = ''

                
    
    def fit(self):
        if os.path.exists(self.OriginalCodeTemporaryPath) == 0:
            shutil.copy(self.FilePath, self.OriginalCodeTemporaryPath)
        
        with open(self.FilePath, 'r') as file:
            self.code = file.read()
        try:
            self.tree = ast.parse(self.code)
        except SyntaxError as e:
            print(f"Syntax error in file {self.FilePath}: {e}")
            return
        
        self.NewFile = open(self.OutputFilePath, 'w')
        
        self.CreateNewFileWithDecorator()
        
        os.remove(self.FilePath)
        os.rename(self.OutputFilePath, self.FilePath)
        os.remove(self.OriginalCodeTemporaryPath)
        
        

        
        
        