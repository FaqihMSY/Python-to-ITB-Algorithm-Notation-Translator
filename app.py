import re
from flask import Flask, render_template, request, jsonify

def ganti_operator(teks: str) -> str:
    penggantian = [
        ('==', '='), ('!=', '≠'), ('>=', '≥'), ('<=', '≤'),
        (' and ', ' AND '), (' or ', ' OR '), ('not ', 'NOT '),
        ('**', '^'), ('//', ' div '), ('%', ' mod '),
    ]
    for py_op, algo_op in penggantian:
        teks = teks.replace(py_op, algo_op)
    return teks

def infer_tipe_dari_nilai(nilai: str) -> str:
    nilai = nilai.strip()
    if re.fullmatch(r'-?\d+', nilai): return 'integer'
    if re.fullmatch(r'-?\d+\.\d+', nilai): return 'real'
    if (nilai.startswith(('"', "'"))) and (nilai.endswith(('"', "'"))): return 'string'
    if nilai in ['True', 'False']: return 'boolean'
    if re.fullmatch(r'\w+\(.*\)', nilai): return '<tipe_bentukan>'
    return '<tipe_data>'

def proses_parameter(params_str: str) -> str:
    if not params_str.strip():
        return ""
    params = [p.strip() for p in params_str.split(',')]
    return ", ".join([f"input {p}: <tipe>" for p in params])

def terjemahkan_python_ke_notasi_final(kode_python: str) -> str:
    if not kode_python.strip():
        return ""

    try:
        lines = kode_python.strip().replace('\t', '    ').split('\n')
        
        output_lines = []
        
        patterns = {
            'comment': re.compile(r'^\s*#\s*(.*)'),
            'def': re.compile(r'^\s*def\s+(\w+)\s*\((.*?)\):'),
            'if': re.compile(r'^\s*if\s+(.*):'),
            'elif': re.compile(r'^\s*elif\s+(.*):'),
            'else': re.compile(r'^\s*else:'),
            'while': re.compile(r'^\s*while\s+(.*):'),
            'for_range': re.compile(r'^\s*for\s+(\w+)\s+in\s+range\((.*?)\):'),
            'return': re.compile(r'^\s*return(\s+.*)?'),
            'break': re.compile(r'^\s*break\s*'),
            'print': re.compile(r'^\s*print\((.*)\)'),
            'input': re.compile(r'^\s*(\w+)\s*=\s*.*?input\((.*)\)'),
            'assignment': re.compile(r'^\s*([a-zA-Z_][\w]*)\s*=\s*(.*)')
        }
        
        functions_info = {}
        current_func = None
        for line in lines:
            stripped_line = line.strip()
            if match := patterns['def'].match(stripped_line):
                current_func = match.group(1)
                functions_info[current_func] = {'has_return_value': False, 'return_type': '<tipe_hasil>'}
            elif match := patterns['return'].match(stripped_line):
                if current_func and match.group(1) and match.group(1).strip():
                    functions_info[current_func]['has_return_value'] = True
                    return_val = match.group(1).strip()
                    functions_info[current_func]['return_type'] = infer_tipe_dari_nilai(return_val)

        program_utama_lines = []
        fungsi_blocks = {}
        current_func_lines = []
        base_indent = -1

        i = 0
        while i < len(lines):
            line = lines[i]
            indent = len(line) - len(line.lstrip(' '))
            stripped = line.strip()

            if patterns['def'].match(stripped):
                if current_func_lines:
                    fungsi_blocks[def_match.group(1)] = current_func_lines
                
                def_match = patterns['def'].match(stripped)
                current_func_name = def_match.group(1)
                base_indent = indent
                current_func_lines = [line]
                
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() == "" or (len(lines[j]) - len(lines[j].lstrip(' '))) > base_indent:
                        current_func_lines.append(lines[j])
                        j += 1
                    else:
                        break
                fungsi_blocks[current_func_name] = current_func_lines
                i = j -1
            else:
                program_utama_lines.append(line)
            i += 1

        output_lines.append("PROGRAM Utama")
        output_lines.append("KAMUS")
        
        temp_global_vars = {}
        for line in program_utama_lines:
             if match := patterns['assignment'].match(line.strip()):
                var, val = match.groups()
                if var not in temp_global_vars:
                    temp_global_vars[var] = infer_tipe_dari_nilai(val)
        for var, tipe in sorted(temp_global_vars.items()):
            output_lines.append(f"    {var} : {tipe}")

        output_lines.append("\nALGORITMA")
        
        def terjemahkan_blok(block_lines):
            translated_lines = []
            i = 0
            while i < len(block_lines):
                line = block_lines[i]
                indent = len(line) - len(line.lstrip(' '))
                stripped = line.strip()

                if not stripped:
                    pass
                elif (match := patterns['comment'].match(stripped)):
                    translated_lines.append(f"{' ' * indent}{{ {match.group(1)} }}")
                elif (match := patterns['if'].match(stripped)):
                    kondisi = ganti_operator(match.group(1))
                    translated_lines.append(f"{' ' * indent}if {kondisi} then")
                elif (match := patterns['elif'].match(stripped)):
                    kondisi = ganti_operator(match.group(1))
                    translated_lines.append(f"{' ' * indent}else if {kondisi} then")
                elif (match := patterns['else'].match(stripped)):
                    translated_lines.append(f"{' ' * indent}else")
                elif (match := patterns['while'].match(stripped)):
                    if match.group(1).strip() == 'True':
                        j = i + 1
                        aksi1_lines = []
                        kondisi_berhenti, aksi2_lines = "", []
                        found_iterate_pattern = False
                        
                        while j < len(block_lines) and (len(block_lines[j]) - len(block_lines[j].lstrip(' '))) > indent:
                            inner_stripped = block_lines[j].strip()
                            if (if_match := patterns['if'].match(inner_stripped)) and \
                               (j + 2 < len(block_lines)) and \
                               (patterns['break'].match(block_lines[j+1].strip())) and \
                               (patterns['else'].match(block_lines[j+2].strip())):
                                
                                kondisi_berhenti = ganti_operator(if_match.group(1))
                                k = j + 3
                                while k < len(block_lines) and (len(block_lines[k]) - len(block_lines[k].lstrip(' '))) > (len(block_lines[j+2]) - len(block_lines[j+2].lstrip(' '))):
                                    aksi2_lines.append(block_lines[k])
                                    k += 1
                                found_iterate_pattern = True
                                i = k -1
                                break
                            else:
                                aksi1_lines.append(block_lines[j])
                            j += 1
                        
                        if found_iterate_pattern:
                            translated_lines.append(f"{' ' * indent}iterate")
                            translated_lines.extend(terjemahkan_blok(aksi1_lines))
                            translated_lines.append(f"{' ' * (indent+4)}stop {kondisi_berhenti}")
                            translated_lines.extend(terjemahkan_blok(aksi2_lines))
                        else:
                            translated_lines.append(f"{' ' * indent}repeat")
                            until_condition = ""
                            inner_block = []
                            j = i + 1
                            while j < len(block_lines) and (len(block_lines[j]) - len(block_lines[j].lstrip(' '))) > indent:
                                if (if_match := patterns['if'].match(block_lines[j].strip())) and \
                                   (j + 1 < len(block_lines)) and \
                                   (patterns['break'].match(block_lines[j+1].strip())):
                                   until_condition = ganti_operator(if_match.group(1))
                                   j += 1
                                else:
                                    inner_block.append(block_lines[j])
                                j += 1
                            translated_lines.extend(terjemahkan_blok(inner_block))
                            if until_condition:
                                translated_lines.append(f"{' ' * indent}until {until_condition}")
                            i = j - 1
                    else:
                        kondisi = ganti_operator(match.group(1))
                        translated_lines.append(f"{' ' * indent}while {kondisi} do")
                elif (match := patterns['for_range'].match(stripped)):
                    var, args = match.groups()
                    arg_list = [a.strip() for a in args.split(',')]
                    try:
                         if len(arg_list) == 1:
                            n = eval(arg_list[0])
                            translated_lines.append(f"{' ' * indent}repeat {n} times")
                         else:
                            start, stop = eval(arg_list[0]), eval(arg_list[1])
                            step = eval(arg_list[2]) if len(arg_list) > 2 else 1
                            if step > 0:
                                translated_lines.append(f"{' ' * indent}{var} traversal [{start}..{stop - 1}]")
                            else:
                                translated_lines.append(f"{' ' * indent}{var} traversal [{start}..{stop + 1}]")
                    except:
                        translated_lines.append(f"{' ' * indent}{{ for loop: {stripped} }}")
                elif (match := patterns['return'].match(stripped)):
                    if match.group(1) and match.group(1).strip():
                        nilai = ganti_operator(match.group(1).strip())
                        translated_lines.append(f"{' ' * indent}→ {nilai}")
                    else:
                        pass
                elif (match := patterns['print'].match(stripped)):
                    nilai = ganti_operator(match.group(1))
                    translated_lines.append(f"{' ' * indent}output({nilai})")
                elif (match := patterns['input'].match(stripped)):
                    var, prompt = match.groups()
                    if prompt: translated_lines.append(f"{' ' * indent}output({prompt})")
                    translated_lines.append(f"{' ' * indent}input({var})")
                elif (match := patterns['assignment'].match(stripped)):
                    var, val = match.groups()
                    val = ganti_operator(val)
                    translated_lines.append(f"{' ' * indent}{var} ← {val}")
                elif stripped not in ['break', 'pass'] and not patterns['def'].match(stripped):
                     translated_lines.append(f"{' ' * indent}{ganti_operator(stripped)}")
                
                i += 1
            
            return translated_lines

        output_lines.extend(terjemahkan_blok(program_utama_lines))
        
        if fungsi_blocks:
            output_lines.append("\n{ REALISASI FUNGSI/PROSEDUR }")
            for func_name, func_lines in fungsi_blocks.items():
                header_line = func_lines[0].strip()
                body_lines = func_lines[1:]
                def_match = patterns['def'].match(header_line)
                nama, params_str = def_match.groups()
                params_formatted = proses_parameter(params_str)
                info = functions_info[nama]

                if info['has_return_value']:
                    output_lines.append(f"\nfunction {nama}({params_formatted}) -> {info['return_type']}")
                else:
                    output_lines.append(f"\nprocedure {nama}({params_formatted})")
                
                output_lines.append("KAMUS LOKAL")
                local_vars = {}
                for l in body_lines:
                    if m := patterns['assignment'].match(l.strip()):
                        var, val = m.groups()
                        if var not in local_vars:
                            local_vars[var] = infer_tipe_dari_nilai(val)
                for var, tipe in sorted(local_vars.items()):
                     output_lines.append(f"    {var} : {tipe}")

                output_lines.append("\nALGORITMA")
                output_lines.extend(terjemahkan_blok(body_lines))

        return '\n'.join(output_lines)

    except Exception as e:
        import traceback
        return f"Terjadi error saat menerjemahkan:\n{traceback.format_exc()}"

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate_code():
    data = request.get_json()
    python_code = data.get('code', '')
    translated_code = terjemahkan_python_ke_notasi_final(python_code)
    return jsonify({'translation': translated_code})

if __name__ == '__main__':
    app.run(debug=True)
