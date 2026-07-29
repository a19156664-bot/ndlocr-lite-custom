import os

def resolve_export_dir(image_path, pdf_source=None) -> str:
    if pdf_source is not None:
        return os.path.dirname(os.path.abspath(pdf_source))
    return os.path.dirname(os.path.abspath(image_path))

def export_basename(image_path, scope, export_dir) -> str:
    if scope == "current":
        return os.path.splitext(os.path.basename(image_path))[0]
    elif scope == "all":
        abs_path = os.path.abspath(export_dir)
        clean_dir = abs_path.replace('\\', '/')
        parts = [p for p in clean_dir.split('/') if p]
        
        if not parts:
            return "export_all"
            
        last = parts[-1]
        
        if len(last) == 2 and last[1] == ':':
            return "export_all"
            
        return f"{last}_all"

def export_targets(image_path, scope, pdf_source=None):
    exp_dir = resolve_export_dir(image_path, pdf_source)
    basename = export_basename(image_path, scope, exp_dir)
    return os.path.join(exp_dir, f"{basename}.csv"), os.path.join(exp_dir, f"{basename}.txt")
