import json
import sys
from pathlib import Path
input_file = "../TestProj/pyre-output/call-graph.json"
output_file = "filtered_file.json"

def filter_call_graphs(input_path, output_path):
    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
                is_call_graph = record.get("kind") == "call_graph"
                is_not_wildcard = record.get("data", {}).get("filename") != "*"
                
                if is_call_graph and is_not_wildcard:
                    outfile.write(json.dumps(record) + "\n")    
            except json.JSONDecodeError:
                continue

def filter_higher_order_call_graph(input_path, output_path):
    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
                is_call_graph = record.get("kind") == "higher_order_call_graph"
                is_not_wildcard = record.get("data", {}).get("filename") != "*"
                
                if is_call_graph and is_not_wildcard:
                    outfile.write(json.dumps(record) + "\n")    
            except json.JSONDecodeError:
                continue

def filter_taint_output(input_path, output_path):
    external_indicators = ["site-packages", "typeshed", "/usr/lib/"]

    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
                data = record.get("data", {})
                filename = data.get("filename", "")
                if filename == "*":
                    continue
                
                path = data.get("path", "")
                if any(indicator in path for indicator in external_indicators):
                    continue
                outfile.write(json.dumps(record) + "\n")
                    
            except json.JSONDecodeError:
                continue


def process_directory(input_folder_path):
    input_dir = Path(input_folder_path)
    output_dir = input_dir / "Filtered"
    
    output_dir.mkdir(exist_ok=True)
        
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix == '.json':
            if file_path.name == "call-graph.json":
                filter_call_graphs(file_path, output_dir / f"{file_path.name}")
            elif file_path.name == "higher-order-call-graph.json":
                filter_higher_order_call_graph(file_path, output_dir / f"{file_path.name}")
            elif file_path.name == "taint-output.json":
                filter_taint_output(file_path, output_dir / f"{file_path.name}")

if __name__ == "__main__":
    path = sys.argv[1] 
    if not path:
        print("Please provide the input folder path as an argument.")
    else:
        process_directory(path)