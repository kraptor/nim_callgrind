# Copyright (c) 2021 kraptor
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

from typing import List, Iterable, Tuple

import os
import re
import argparse


def has_number(name: str) -> bool:
    if name is None:
        return False

    for c in name:
        if c.isnumeric():
            return True
    return False


def is_callgrind_function(line: str) -> bool:
    if " " not in line: return False
    if "fn=" in line: return True
    if "cfn=" in line: return True
    return False


def get_raw_functions(data: Iterable[str]) -> List[str]:
    functions = []

    for line in data:
        line = line.strip()        

        if not is_callgrind_function(line):
            continue

        _, raw_fun = line.split(" ", maxsplit=1)
        functions.append(raw_fun)
        
    return functions


def is_nim_function(raw_name: str) -> bool:
    if "tyObject" in raw_name   : return True

    if raw_name.startswith("0x"): return False
    if raw_name.startswith("_") : return False
    if "std::" in raw_name      : return False
    if raw_name.startswith("(") : return False
    if not has_number(raw_name) : return False
    if re.search(r"_[a-zA-Z]+Z\w*\w", raw_name) is None: return False
    
    return True


def remove_number(name: str) -> str:
    # remove number from name
    c = 0
    for n in reversed(name):
        if n.isnumeric():
            c += 1
    c += 1 # remove extra to delete underscore
    name = name[0:-c] 
    return name


def get_name_and_fileinfo(name: str) -> Tuple[str, str]:
    c = 0
    for n in reversed(name):
        if n == "_":
            break
        c += 1
    c += 1 # remove extra underscore

    fname = name[:-c]
    finfo = name[-c:]
    finfo = finfo.replace("_", "")
    finfo = finfo.replace("Z", ".")

    return fname, finfo


def get_function_name(raw_name: str) -> str:
    name, params = raw_name.split("(", 1)
    name = remove_number(name)
    fname, finfo = get_name_and_fileinfo(name)
    return fname, finfo


def get_parameter(param: str) -> str:
    param = param.strip()

    prefix = ""
    if param.endswith("&"): prefix = "var"
    if param.endswith("*"): prefix = "ptr"
    if prefix != "":
        param = param[:-1]

    if param.startswith("tyObject"):
        param = param[9:param.find("__")]

        if param.endswith("colonObjectType"):
            param = param[:-len("colonObjectType")]
            
        return f"{prefix} {param}".strip()

    if param.startswith("tySequence"):
        return f"{prefix} seq".strip()

    param = param.replace("NimStringV2", "string")
    param = param.replace("unsigned char", "byte")
    param = param.replace("unsigned int", "uint")

    return f"{prefix} {param}".strip()


def get_function_params(raw_name: str) -> Tuple[str]:
    
    attribs = ""
    if "[" in raw_name:
        attribs = raw_name[raw_name.find("[") + 1: raw_name.find("]")]
    
    raw_name = raw_name[raw_name.find("(") + 1:raw_name.find(")")]
    params = [get_parameter(p) for p in raw_name.split(",")]
    return params, attribs
    

def demangle_nim_function(raw_name: str) -> Tuple[str, str, Iterable[str]]:
    fun_name, fun_module = get_function_name(raw_name)
    fun_params, fun_attribs = get_function_params(raw_name)
    return (
        fun_name,
        fun_module,
        fun_params,
        fun_attribs
    )


def main(file_input: str, file_output: str):
    with open(file_input) as f:
        raw_functions = get_raw_functions(f)
        
    mangle_map = {}
    for fun in raw_functions:
        if not is_nim_function(fun):
            continue
        mangle_map[fun] = demangle_nim_function(fun)

    with open(file_output, "w") as output:
        with open(file_input, "r") as input:
            for line in input:
                line = line.strip()

                if is_callgrind_function(line):
                    for mangled_name, (new_name, module, parameters, attribs) in mangle_map.items():
                        if mangled_name in line:
                            line = line.replace(mangled_name, f"{new_name}({', '.join(parameters)}) [{module}] [{attribs}]")
                
                output.write(line)
                output.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Process a callgrind file and demangle Nim symbols"
    )

    parser.add_argument("input_file", help="Callgrind input file")
    parser.add_argument("output_file", help="Demangled output file")

    args = parser.parse_args()


    if not os.path.exists(args.input_file):
        print(f"Can't open file: {args.input_file}")

    main(args.input_file, args.output_file)