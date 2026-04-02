import pandas as pd
import os
import re
import sys

BASE_PATH = sys.argv[1]

import re

def find_function_body_start(file_path, full_define):
    func_name = full_define.split('.')[-1]
    patterns = [
        re.compile(fr'^\s*def\s+{func_name}\s*\('),
        re.compile(fr'^\s*async\s+def\s+{func_name}\s*\('),
        re.compile(fr'^\s*class\s+{func_name}\s*[\(:]'),
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                if any(p.match(line) for p in patterns):
                    current_idx = i
                    while current_idx < len(lines):
                        if ':' in lines[current_idx]:
                            body_start_idx = current_idx + 1
                            
                            while body_start_idx < len(lines) and not lines[body_start_idx].strip():
                                body_start_idx += 1
                                
                            return body_start_idx + 1
                        current_idx += 1
                            
    except Exception:
        pass
    return None

def extract_docstring(file_path, start_line, num_lines=20):
    if not start_line or not os.path.exists(file_path):
        return "Source not found"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        snippet_lines = lines[start_line-1 : start_line + num_lines]
        return "".join(snippet_lines[:12]).strip()
    except Exception as e:
        return f"Error: {str(e)}"

def main(input_file):
    output_file = input_file.replace('.xlsx', '_with_comments.xlsx')
    df = pd.read_excel(input_file)
    results = []
    
    for index, row in df.iterrows():
        rel_path = row['Path']
        full_define = str(row['Function'])
        
        full_path = os.path.join(BASE_PATH, rel_path)
        function_start_line = find_function_body_start(full_path, full_define)        

        comment_snippet = extract_docstring(full_path, function_start_line)
        
        row_dict = row.to_dict()
        row_dict['FunctionLine'] = function_start_line if function_start_line else "Not Found"
        row_dict['Comment'] = comment_snippet
        results.append(row_dict)

    final_df = pd.DataFrame(results)
    final_df.to_excel(output_file, index=False)
    
if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print("Usage: python script.py <input_file.xlsx>")
    #     sys.exit(1)

    input_file = "../Results/Filtered/" + os.path.basename(os.path.normpath(BASE_PATH)) + ".xlsx"
    # input_file = "Results/scipy.xlsx"
    main(input_file)
